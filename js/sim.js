// 島民の暮らしシミュレーション。
// 乱数は使わず、「時刻（スロット番号）× 島民ID」のハッシュだけで行動を決める。
// → 同じ時刻に開けば、誰の端末でも同じ島の光景になる。状態も持たない（任意の時刻を直接計算できる）。
//
// 島が広いので、島民は「いる場所」を何スロットかごと（SIM.epochSlots）に選びなおす：
//   ・いる場所＝スポット（集まり場・仕事場・見晴らし・波打ちぎわ・池のほとり・行動範囲の縁など）の1つ。
//     切り替えの時刻は島民ごとにずれていて、全員がいっせいに動くことはない。
//   ・切り替えたら、前の場所から新しい場所まで歩く速さどおりに歩く（遠ければ何スロットもかかる）。＝「遠出」
//   ・着いたあとは、その近所（SIM.localRadius）で、1スロット（既定60秒）ごとに
//       [前スロットの行動を少し続ける] → [歩いて移動] → [今スロットの行動]
//     をくり返す（仕事・ひと休み・散歩・近くにいる相手とおしゃべり・集まり場が近ければ集まり）。
//   ・場所ごとの最初のスロット（着くまで）と最後のスロットは、その場所の決まった位置にいる。
//     こうしておくと「遠出」の出発点がハッシュだけで決まり、過去をさかのぼらずに任意の時刻を計算できる。
//
// 行き先はすべて「島民の行動範囲」の中（nav が範囲の中だけを歩けるマスにしている）。
// 範囲の縁（森や高原との境目）にいる島民は、たまに障壁を匂わせるセリフを吹き出しで出す。

import { N, HALF, DISTRICTS, BIOME, NO_DISTRICT, PLAIN_CENTER, LANDING, POND } from './terrain.js';
import { hashStr, hashMix, hash01 } from './rng.js';
import { SIM, JOBS, DEFAULT_JOB, RELATION_TYPES, DEFAULT_RELATION, BARRIERS, DEFAULT_BARRIER } from './config.js';

// 島民の集まり場。拠点が決まっていれば拠点（広場）、決まるまでは漂着した砂浜。
export function resolveHub(base) {
  if (base && Number.isFinite(base.x) && Number.isFinite(base.z)) return { x: base.x, z: base.z, label: base.name || '広場', isBase: true };
  return { x: LANDING.x, z: LANDING.z, label: LANDING.name, isBase: false };
}

// 行動範囲の外の地区の「自然の障壁」（セリフ・呼び名）
export const barrierOf = (districtIndex) => BARRIERS[DISTRICTS[districtIndex]?.id] || DEFAULT_BARRIER;

// 状態の短い呼び名（詳細パネルの「いま」に出す）
export const STATUS_LABELS = {
  travel: '遠出の途中',
  walk: '移動中',
  work: '仕事中',
  gather: '集まり',
  chat: 'おしゃべり',
  wait: '待ちあわせ',
  look: '見まわり',
  wander: '散歩',
  rest: 'ひと休み',
};

const EDGE_R = 3; // 範囲外の地区までこのマス数以内なら「縁」
const LINE_MS = 9000; // セリフの周期
const LINE_SHOW_MS = 4500; // 1回のセリフを出している長さ
const LINE_KINDS = new Set(['wander', 'rest', 'work', 'wait']); // 立ち止まっている行動のときだけ話す
const KEY_SPAN = 262144; // N*N より大きい2の累乗（並べ替えのキーにマス番号を埋め込む）
const COMPASS = ['東', '南東', '南', '南西', '西', '北西', '北', '北東'];

export function createSim({ terrain, nav, pathfinder, islanders, buildings, hub = resolveHub(null), outOfRange = new Set(), seed = 1 }) {
  const { idx, cellCenter, district, biome, h } = terrain;
  const n = islanders.length;
  const SLOT_MS = SIM.slotSeconds * 1000;
  const EPOCH = Math.max(3, Math.floor(SIM.epochSlots) || 8);
  const LOCAL_R = SIM.localRadius || 60;
  const CHAT_R = SIM.chatRadius || 70;
  const GATHER_R = SIM.gatherRadius || 100;
  const idHash = islanders.map((p) => hashStr(String(p.id)));
  const indexOfId = new Map(islanders.map((p, i) => [String(p.id), i]));

  // ---- スポット（行き先）を集める -------------------------------------------
  // 条件に合う歩けるマスから、ハッシュ順に、たがいに minSep 以上離れた count 個を選ぶ
  function pickCells(filter, count, minSep, salt) {
    const keys = [];
    for (let k = 0; k < N * N; k++) {
      if (nav.walk[k] && filter(k, k % N, Math.floor(k / N))) keys.push(hashMix(k, salt, seed) * KEY_SPAN + k);
    }
    const sorted = Float64Array.from(keys).sort();
    const out = [];
    for (const key of sorted) {
      const k = key % KEY_SPAN;
      const c = cellCenter(k % N, Math.floor(k / N));
      if (out.every((o) => Math.hypot(o.x - c.x, o.z - c.z) >= minSep)) {
        out.push({ ...c, k });
        if (out.length >= count) break;
      }
    }
    return out;
  }
  const NEXT4 = [
    [1, 0],
    [-1, 0],
    [0, 1],
    [0, -1],
  ];
  const besideWater = (i, j) => NEXT4.some(([di, dj]) => terrain.heightAtCell(i + di, j + dj) < 1);
  // まわりの水のほうを向く
  function faceWater(c, r = 2) {
    let fx = 0;
    let fz = 0;
    for (let dj = -r; dj <= r; dj++) {
      for (let di = -r; di <= r; di++) {
        if (terrain.heightAtCell((c.k % N) + di, Math.floor(c.k / N) + dj) < 1) {
          fx += di;
          fz += dj;
        }
      }
    }
    return { fx: c.x + fx * 4, fz: c.z + fz * 4 };
  }
  // 地区の中での方角つきの呼び名（例：「平原の北がわ」）
  function areaName(di, x, z) {
    const d = DISTRICTS[di];
    const dx = x - d.u * HALF;
    const dz = z - d.v * HALF;
    if (Math.hypot(dx, dz) < 34) return `${d.name}のまんなか`;
    const dir = COMPASS[((Math.round(Math.atan2(dz, dx) / (Math.PI / 4)) % 8) + 8) % 8];
    return `${d.name}の${dir}がわ`;
  }
  const districtIdAt = (k) => (district[k] === NO_DISTRICT ? '' : DISTRICTS[district[k]].id);

  const buildingSpots = [];
  for (const b of buildings) {
    b.spots.forEach((s, m) => {
      const p = nav.snap(s.x, s.z);
      buildingSpots.push({ ...s, x: p.x, z: p.z, kind: 'building', key: `${b.id}:${m}` });
    });
  }

  // 池のほとり（平原の北の水場）
  const pondSpots = pickCells(
    (k, i, j) => {
      const c = cellCenter(i, j);
      return nav.walkY[k] === h[k] && Math.hypot(c.x - POND.x, c.z - POND.z) < 40 && besideWater(i, j);
    },
    3,
    12,
    151,
  ).map((c, m) => ({ x: c.x, z: c.z, ...faceWater(c, 3), jobs: ['漁師'], label: `${POND.name}のほとり`, spread: 0.5, kind: 'pond', key: `pond${m}` }));

  // 波打ちぎわ（海のとなりの砂）
  const shoreSpots = pickCells((k, i, j) => biome[k] === BIOME.SAND && nav.walkY[k] === h[k] && besideWater(i, j) && !pondSpots.some((p) => Math.hypot(p.x - cellCenter(i, j).x, p.z - cellCenter(i, j).z) < 30), 12, 44, 101).map((c, m) => {
    const d = DISTRICTS[district[c.k]];
    return { x: c.x, z: c.z, ...faceWater(c), jobs: [], label: `${d.name}の波打ちぎわ`, spread: 0.6, kind: 'shore', key: `shore${m}` };
  });

  // 各地区の見晴らしスポット（散歩・探検の行き先）。行動範囲の外の地区は歩けるマスが無いので選ばれない。
  const viewSpots = [];
  DISTRICTS.forEach((d, di) => {
    const awayFromHub = (i, j) => {
      const c = cellCenter(i, j);
      return Math.hypot(c.x - hub.x, c.z - hub.z) > 26;
    };
    pickCells((k, i, j) => district[k] === di && nav.walkY[k] === h[k] && biome[k] !== BIOME.SAND && awayFromHub(i, j), 6, 52, 200 + di).forEach((c, m) => {
      viewSpots.push({ x: c.x, z: c.z, fx: c.x + (c.x - PLAIN_CENTER.x), fz: c.z + (c.z - PLAIN_CENTER.z), jobs: [], label: areaName(di, c.x, c.z), spread: 1.2, kind: 'view', key: `view${di}:${m}` });
    });
  });

  // 島の真ん中をかこむ草地
  const meadowSpots = pickCells(
    (k, i, j) => {
      const c = cellCenter(i, j);
      const dist = Math.hypot(c.x - PLAIN_CENTER.x, c.z - PLAIN_CENTER.z);
      return biome[k] === BIOME.GRASS && dist > 34 && dist < 105;
    },
    6,
    40,
    301,
  ).map((c, m) => ({ x: c.x, z: c.z, fx: c.x + 3, fz: c.z + 1, jobs: [], label: `${DISTRICTS[district[c.k]].name}の草地`, spread: 1.2, kind: 'meadow', key: `meadow${m}` }));

  // 行動範囲の縁：範囲外の地区まで EDGE_R マス以内の歩けるマス → いちばん近い範囲外の地区
  const edgeOf = new Uint8Array(N * N).fill(NO_DISTRICT);
  const edgeD2 = new Uint8Array(N * N).fill(255);
  if (outOfRange.size) {
    for (let k = 0; k < N * N; k++) {
      if (!nav.walk[k]) continue;
      const i = k % N;
      const j = Math.floor(k / N);
      for (let dj = -EDGE_R; dj <= EDGE_R; dj++) {
        for (let di = -EDGE_R; di <= EDGE_R; di++) {
          if (!terrain.inGrid(i + di, j + dj)) continue;
          const nk = idx(i + di, j + dj);
          if (h[nk] < 1 || !outOfRange.has(district[nk])) continue;
          const d2 = di * di + dj * dj;
          if (d2 < edgeD2[k]) {
            edgeD2[k] = d2;
            edgeOf[k] = district[nk];
          }
        }
      }
    }
  }
  const edgeAt = (x, z) => {
    const c = terrain.cellOf(x, z);
    return edgeOf[idx(c.i, c.j)];
  };

  // 縁の見晴らしスポット（森や高原の様子をうかがいに行く場所）。障壁のほうを向く。
  const edgeSpots = [];
  for (const di of [...outOfRange].sort((a, b) => a - b)) {
    const bar = barrierOf(di);
    pickCells((k) => edgeOf[k] === di && edgeD2[k] <= 4 && nav.walkY[k] === h[k], 5, 40, 400 + di).forEach((c, m) => {
      let fx = 0;
      let fz = 0;
      const ci = c.k % N;
      const cj = Math.floor(c.k / N);
      for (let dj = -EDGE_R; dj <= EDGE_R; dj++) {
        for (let dk = -EDGE_R; dk <= EDGE_R; dk++) {
          if (!terrain.inGrid(ci + dk, cj + dj)) continue;
          if (district[idx(ci + dk, cj + dj)] === di) {
            fx += dk;
            fz += dj;
          }
        }
      }
      edgeSpots.push({ x: c.x, z: c.z, fx: c.x + fx, fz: c.z + fz, jobs: [], label: bar.edge || `${DISTRICTS[di].name}の手前`, spread: 0.6, kind: 'edge', edge: di, key: `edge${di}:${m}` });
    });
  }

  // 料理人の持ち場：拠点のたき火（拠点が決まるまでは、集まり場の砂浜で）
  const firePos = nav.snap(hub.x + 2.1, hub.z + 0.4);
  const fireSpot = { x: firePos.x, z: firePos.z, fx: hub.x, fz: hub.z, jobs: ['料理人'], label: hub.isBase ? `${hub.label}のたき火` : hub.label, spread: 0.3, kind: 'plaza', key: 'fire' };
  const plazaSpot = { x: hub.x, z: hub.z, fx: hub.x, fz: hub.z, jobs: [], label: hub.label, spread: 0, kind: 'plaza', key: 'plaza' };

  // spots[0] は集まり場。どのスポットも「いる場所」になれる。
  const spots = [plazaSpot, fireSpot, ...buildingSpots, ...pondSpots, ...shoreSpots, ...viewSpots, ...meadowSpots, ...edgeSpots];
  spots.forEach((s, m) => {
    s.id = m;
    const a = nav.snap(s.x, s.z); // 歩いて着ける位置（遠出の経路の端）
    s.ax = a.x;
    s.az = a.z;
    const c = terrain.cellOf(a.x, a.z);
    s.districtId = districtIdAt(idx(c.i, c.j));
    s.hubDist = Math.hypot(s.x - hub.x, s.z - hub.z);
    s.nearHub = s.hubDist <= GATHER_R;
  });
  // 近所のスポット（1スロットで行き来できる範囲）
  for (const s of spots) s.near = spots.filter((o) => o !== s && Math.hypot(o.x - s.x, o.z - s.z) <= LOCAL_R);
  const scenicSpots = [...viewSpots, ...shoreSpots, ...meadowSpots, ...pondSpots];

  function jobSpots(job) {
    const tagged = spots.filter((s) => s.jobs.includes(job));
    // 探検家は、行動範囲の縁で森や高原の様子を調べることもある
    if (job === '探検家') return [...tagged, ...viewSpots, ...edgeSpots].length ? [...tagged, ...viewSpots, ...edgeSpots] : [fireSpot];
    if (job === '漁師') return [...tagged, ...shoreSpots].length ? [...tagged, ...shoreSpots] : [fireSpot];
    if (tagged.length) return tagged;
    if (job === '農家' && meadowSpots.length) return meadowSpots;
    if (buildingSpots.length) return buildingSpots;
    return viewSpots.length ? viewSpots : [fireSpot];
  }
  const jobSpotCache = new Map();
  const spotsForJob = (job) => {
    if (!jobSpotCache.has(job)) jobSpotCache.set(job, jobSpots(job));
    return jobSpotCache.get(job);
  };
  // その場所の近所にある、その仕事の仕事場
  const localJobCache = new Map();
  function localJobSpots(job, zone) {
    const key = `${job}\n${zone.id}`;
    let list = localJobCache.get(key);
    if (!list) {
      const all = spotsForJob(job);
      list = all.filter((s) => s === zone || zone.near.includes(s));
      localJobCache.set(key, list);
    }
    return list;
  }
  const homeSpotCache = new Map();
  function homeSpots(districtId) {
    if (!homeSpotCache.has(districtId)) homeSpotCache.set(districtId, scenicSpots.filter((s) => s.districtId === districtId));
    return homeSpotCache.get(districtId);
  }
  const worksAt = (person, s) => spotsForJob(person.job).includes(s);

  // 集まり場のまわりのぶらぶら位置
  const hubSpread = 8 + Math.min(30, Math.sqrt(n));
  function hubPoint(a, b) {
    const ang = hash01(a, b, 31) * Math.PI * 2;
    const r = 4.5 + hash01(a, b, 32) * hubSpread;
    return nav.snap(hub.x + Math.cos(ang) * r, hub.z + Math.sin(ang) * r);
  }
  // スポットのそば（spread の範囲）の位置
  function nearSpot(s, a, b, salt) {
    const ang = hash01(a, b, salt) * Math.PI * 2;
    const rad = (s.spread || 0) * hash01(a, b, salt + 1);
    return nav.snap(s.x + Math.cos(ang) * rad, s.z + Math.sin(ang) * rad);
  }

  function relationBetween(i, j) {
    const a = (islanders[i].relationships || []).find((r) => String(r.id) === String(islanders[j].id));
    const b = (islanders[j].relationships || []).find((r) => String(r.id) === String(islanders[i].id));
    return a || b || null;
  }

  // ---- いる場所（エポック） -----------------------------------------------------
  // 島民 i のスロット k は、エポック e の (k - k0) 番目。切り替えの時刻は島民ごとに off だけずれる。
  const epochOff = idHash.map((v) => v % EPOCH);
  const epochOf = (i, k) => Math.floor((k + epochOff[i]) / EPOCH);
  const firstSlot = (i, e) => e * EPOCH - epochOff[i];

  // エポック e に島民 i がいる場所（スポット）。ハッシュだけで決まる。
  function zoneOf(i, e) {
    const person = islanders[i];
    const hsh = idHash[i];
    const r = hash01(e, hsh, 40);
    const explorer = person.job === '探検家';
    if (r < (explorer ? 0.16 : 0.3)) return plazaSpot; // 集まり場のまわり
    if (r < (explorer ? 0.64 : 0.66)) {
      const list = spotsForJob(person.job); // 仕事場
      return list[hashMix(e, hsh, 41) % list.length];
    }
    if (r < 0.86) {
      const list = homeSpots(person.home); // 自分の起点の地区
      if (list.length) return list[hashMix(e, hsh, 42) % list.length];
    }
    if (edgeSpots.length && r < 0.93) return edgeSpots[hashMix(e, hsh, 43) % edgeSpots.length]; // 行動範囲の縁
    if (scenicSpots.length) return scenicSpots[hashMix(e, hsh, 44) % scenicSpots.length]; // 島のどこか
    return plazaSpot;
  }

  // その場所での「決まった位置と行動」。着いたとき（最初のスロット）と最後のスロットはここにいる。
  const homeCache = new Map();
  function homeEntry(i, e) {
    const key = e * 65536 + i;
    let entry = homeCache.get(key);
    if (entry) return entry;
    const person = islanders[i];
    const hsh = idHash[i];
    const s = zoneOf(i, e);
    if (s === plazaSpot) {
      const p = hubPoint(e, hsh);
      entry = { kind: 'rest', x: p.x, z: p.z, fx: hub.x, fz: hub.z, partner: -1, place: hub.label, spot: s };
    } else {
      let p = nearSpot(s, e, hsh, 45);
      if ((s.spread || 0) < 0.45) {
        // 立ち位置がせまいスポット（桟橋など）：同じマスの中で少しずらして、重なって見えないようにする
        const c = terrain.cellOf(s.ax, s.az);
        const cc = cellCenter(c.i, c.j);
        p = { x: cc.x + (((hsh >>> 4) % 5) - 2) * 0.36, z: cc.z + (((hsh >>> 8) % 5) - 2) * 0.36 };
      }
      const kind = worksAt(person, s) ? 'work' : 'wander';
      entry = { kind, x: p.x, z: p.z, fx: s.fx, fz: s.fz, partner: -1, place: s.label, spot: s };
      if (s.edge !== undefined) entry.edge = s.edge;
    }
    if (homeCache.size > Math.max(256, n * 6)) for (const kk of homeCache.keys()) if (Math.abs(Math.floor(kk / 65536) - e) > 2) homeCache.delete(kk);
    homeCache.set(key, entry);
    return entry;
  }

  // スポットからスポットへの経路（みんなが同じ道を通る＝踏みあとのような幹線。計算は1組につき1回）
  const trunkCache = new Map();
  function trunk(a, b) {
    const key = a.id * 4096 + b.id;
    let path = trunkCache.get(key);
    if (path) return path;
    // 向きは必ず「番号の小さいほう→大きいほう」で計算し、逆向きはそれを裏返す（計算の順番で道が変わらないように）
    if (a.id > b.id) path = pathfinder.measure(trunk(b, a).pts.slice().reverse());
    else path = pathfinder.findPath({ x: a.ax, z: a.az }, { x: b.ax, z: b.az });
    trunkCache.set(key, path);
    return path;
  }

  // 遠出：前の場所の決まった位置 → 新しい場所の決まった位置。歩く速さどおりにかかる時間ぶん歩く。
  const transitCache = new Map();
  function transit(i, e) {
    const key = e * 65536 + i;
    let tr = transitCache.get(key);
    if (tr) return tr;
    const from = homeEntry(i, e - 1);
    const to = homeEntry(i, e);
    const k0 = firstSlot(i, e);
    const delay = 2 + 10 * hash01(e, idHash[i], 46);
    let path;
    if (from.spot === to.spot) {
      path = pathfinder.findPath({ x: from.x, z: from.z }, { x: to.x, z: to.z });
    } else {
      const head = pathfinder.findPath({ x: from.x, z: from.z }, { x: from.spot.ax, z: from.spot.az });
      const mid = trunk(from.spot, to.spot);
      const tail = pathfinder.findPath({ x: to.spot.ax, z: to.spot.az }, { x: to.x, z: to.z });
      path = pathfinder.smooth([...head.pts, ...mid.pts.slice(1), ...tail.pts.slice(1)]);
    }
    // ふつうは歩く速さどおり。エポックの最後のスロットまでに着けないほど遠いときだけ急ぐ（この島では起きない）。
    const maxTravel = (EPOCH - 1) * SIM.slotSeconds - delay - 8;
    const travel = Math.min(path.len / SIM.walkSpeed, maxTravel);
    const t0 = k0 * SLOT_MS + delay * 1000;
    const t1 = t0 + travel * 1000;
    tr = { from, to, path, delay, travel, t0, t1, k0, kArr: Math.floor(t1 / SLOT_MS) };
    if (transitCache.size > Math.max(256, n * 6)) for (const kk of transitCache.keys()) if (Math.abs(Math.floor(kk / 65536) - e) > 2) transitCache.delete(kk);
    transitCache.set(key, tr);
    return tr;
  }

  // スロット k の島民 i は、決まった位置にいる番か（遠出の途中〜着いたスロット、またはエポックの最後のスロット）
  function fixedAt(i, k) {
    const e = epochOf(i, k);
    const k0 = firstSlot(i, e);
    if (k === k0 || k === k0 + EPOCH - 1) return true;
    return k <= transit(i, e).kArr;
  }

  // ---- スロットごとの計画 ---------------------------------------------------
  const planCache = new Map();
  function plan(k) {
    let p = planCache.get(k);
    if (!p) {
      p = computePlan(k);
      planCache.set(k, p);
      if (planCache.size > 8) {
        for (const key of planCache.keys()) if (Math.abs(key - k) > 3) planCache.delete(key);
      }
    }
    return p;
  }

  function computePlan(k) {
    const out = new Array(n).fill(null);
    const zone = new Array(n);
    const free = new Uint8Array(n);
    const gather = hashMix(k, seed, 77) % SIM.gatherEvery === 0;
    const order = [...Array(n).keys()].sort((a, b) => hashMix(k, idHash[a], 1) - hashMix(k, idHash[b], 1) || a - b);
    const taken = new Set();
    const inZone = new Map(); // スポット → そこにいて自由に動ける島民（ハッシュ順）

    // 決まった位置にいる番の島民を先に置く
    for (const i of order) {
      const e = epochOf(i, k);
      zone[i] = zoneOf(i, e);
      if (fixedAt(i, k)) {
        out[i] = homeEntry(i, e);
        taken.add(zone[i].key);
      } else {
        free[i] = 1;
        if (!inZone.has(zone[i])) inZone.set(zone[i], []);
        inZone.get(zone[i]).push(i);
      }
    }
    const closeEnough = (a, b) => a === b || Math.hypot(a.x - b.x, a.z - b.z) <= CHAT_R;

    // 会話のペアを決める（近くにいる相手とだけ）
    if (!gather) {
      for (const i of order) {
        if (!free[i] || out[i]) continue;
        if (hash01(k, idHash[i], 2) >= SIM.chatChance) continue;
        const cands = [];
        for (const r of islanders[i].relationships || []) {
          const j = indexOfId.get(String(r.id));
          if (j === undefined || j === i || !free[j] || out[j] || !closeEnough(zone[i], zone[j])) continue;
          cands.push({ j, w: 20 + Math.max(0, Number(r.affinity) || 0) });
        }
        if (!cands.length || hash01(k, idHash[i], 5) < 0.2) {
          // 同じ場所にいる、関係のない相手（人数が多い島でも調べすぎないよう、先頭の何人かだけ）
          let seen = 0;
          for (const j of inZone.get(zone[i])) {
            if (j === i || out[j] || cands.some((c) => c.j === j)) continue;
            cands.push({ j, w: 12 });
            if (++seen >= 8) break;
          }
        }
        if (!cands.length) continue;
        let pick = hash01(k, idHash[i], 3) * cands.reduce((s, c) => s + c.w, 0);
        let j = cands[cands.length - 1].j;
        for (const c of cands) {
          pick -= c.w;
          if (pick < 0) {
            j = c.j;
            break;
          }
        }
        // 会う場所：どちらかのいる場所（集まり場なら、そのまわり）
        const where = hash01(k, idHash[i], 6);
        const s = zone[where < 0.7 ? i : j];
        let base;
        if (s === plazaSpot) base = hubPoint(k, idHash[i]);
        else {
          const ang = hash01(k, idHash[i], 8) * Math.PI * 2;
          base = nav.snap(s.x + Math.cos(ang) * 2.4, s.z + Math.sin(ang) * 2.4);
        }
        const place = s.label;
        // 向かい合う2点（歩ける向きを探す）
        const pa = base;
        let pb = null;
        for (let t = 0; t < 8 && !pb; t++) {
          const ang = (hash01(k, idHash[i], 9) + t / 8) * Math.PI * 2;
          const q = { x: base.x + Math.cos(ang) * 2.0, z: base.z + Math.sin(ang) * 2.0 };
          if (nav.isWalkable(q.x, q.z) && pathfinder.lineOK(base, q)) pb = q;
        }
        if (!pb) continue;
        const rel = relationBetween(i, j);
        const icon = (rel && RELATION_TYPES[rel.type]?.icon) || DEFAULT_RELATION.icon;
        out[i] = { kind: 'chat', x: pa.x, z: pa.z, fx: pb.x, fz: pb.z, partner: j, place, icon };
        out[j] = { kind: 'chat', x: pb.x, z: pb.z, fx: pa.x, fz: pa.z, partner: i, place, icon };
      }
    }

    // 集まりに行く島民（集まり場の近くにいて、自由に動ける番）
    const gatherers = gather ? order.filter((i) => !out[i] && zone[i].nearHub && hash01(k, idHash[i], 4) < 0.85) : [];
    const gatherRank = new Map(gatherers.map((i, rank) => [i, rank]));

    for (const i of order) {
      if (out[i]) continue;
      const person = islanders[i];
      const hsh = idHash[i];
      const s = zone[i];
      const r = hash01(k, hsh, 4);
      const explorer = person.job === '探検家';

      // 集まり：集まり場の近くにいる島民が、輪になって集まる
      if (gatherRank.has(i)) {
        const rank = gatherRank.get(i);
        const perRing = 10;
        const ring = Math.floor(rank / perRing);
        const inRing = Math.min(perRing, gatherers.length - ring * perRing);
        const ang = ((rank % perRing) / inRing) * Math.PI * 2 + ring * 0.31 + hash01(k, 55) * 6.28;
        const rad = 3.8 + ring * 2.3;
        const p = nav.snap(hub.x + Math.cos(ang) * rad, hub.z + Math.sin(ang) * rad);
        out[i] = { kind: 'gather', x: p.x, z: p.z, fx: hub.x, fz: hub.z, partner: -1, place: hub.label };
        continue;
      }

      // 仕事：近所の仕事場で
      if (r < (explorer ? 0.5 : 0.62)) {
        const list = localJobSpots(person.job, s);
        if (list.length) {
          let pickIdx = hashMix(k, hsh, 10) % list.length;
          for (let t = 0; t < list.length && taken.has(list[pickIdx].key); t++) pickIdx = (pickIdx + 1) % list.length;
          const w = list[pickIdx];
          taken.add(w.key);
          const p = nearSpot(w, k, hsh, 11);
          out[i] = { kind: 'work', x: p.x, z: p.z, fx: w.fx, fz: w.fz, partner: -1, place: w.label };
          if (w.edge !== undefined) out[i].edge = w.edge;
          continue;
        }
      }

      // ひと休み：いる場所のそばで
      if (r < 0.8) {
        if (s === plazaSpot) {
          const p = hubPoint(k, hsh);
          out[i] = { kind: 'rest', x: p.x, z: p.z, fx: hub.x, fz: hub.z, partner: -1, place: hub.label };
        } else {
          const ang = hash01(k, hsh, 22) * Math.PI * 2;
          const rad = 2 + 7 * hash01(k, hsh, 23);
          const p = nav.snap(s.x + Math.cos(ang) * rad, s.z + Math.sin(ang) * rad);
          out[i] = { kind: 'rest', x: p.x, z: p.z, fx: s.fx, fz: s.fz, partner: -1, place: s.label };
        }
        continue;
      }

      // 散歩：近所に行動範囲の縁があれば、ときどき森や高原の様子を見に行く
      const edges = s.kind === 'edge' ? [s, ...s.near.filter((o) => o.kind === 'edge')] : s.near.filter((o) => o.kind === 'edge');
      if (edges.length && hash01(k, hsh, 17) < (s.kind === 'edge' ? 0.6 : 0.3)) {
        const w = edges[hashMix(k, hsh, 18) % edges.length];
        const p = nearSpot(w, k, hsh, 19);
        out[i] = { kind: 'wander', x: p.x, z: p.z, fx: w.fx, fz: w.fz, partner: -1, place: w.label, edge: w.edge };
        continue;
      }
      // 散歩：近所のスポットか、そのあたりの歩ける場所へ
      const list = s.near.filter((o) => o.kind !== 'edge' && o.kind !== 'building');
      if (list.length && hash01(k, hsh, 13) < 0.6) {
        const w = list[hashMix(k, hsh, 14) % list.length];
        const p = nearSpot(w, k, hsh, 15);
        out[i] = { kind: 'wander', x: p.x, z: p.z, fx: w.fx, fz: w.fz, partner: -1, place: w.label };
      } else {
        const ang = hash01(k, hsh, 24) * Math.PI * 2;
        const rad = 10 + (LOCAL_R * 0.55 - 10) * hash01(k, hsh, 25);
        const p = nav.snap(s.ax + Math.cos(ang) * rad, s.az + Math.sin(ang) * rad);
        const c = terrain.cellOf(p.x, p.z);
        const di = district[idx(c.i, c.j)];
        out[i] = { kind: 'wander', x: p.x, z: p.z, fx: p.x + Math.cos(ang) * 4, fz: p.z + Math.sin(ang) * 4, partner: -1, place: di === NO_DISTRICT ? s.label : areaName(di, p.x, p.z) };
      }
    }

    return { k, gather, entries: out };
  }

  // ---- 移動（スロット k での、前の場所→今の場所） ----------------------------
  // 経路は、歩きはじめるとき（delay のあと）に初めて計算する（全員ぶんを1フレームで計算しないため）。
  const legCache = new Map(); // k → 島民ごとの配列
  function leg(i, k) {
    let row = legCache.get(k);
    if (!row) {
      row = new Array(n);
      legCache.set(k, row);
      if (legCache.size > 4) for (const kk of legCache.keys()) if (Math.abs(kk - k) > 1) legCache.delete(kk);
    }
    let l = row[i];
    if (l) return l;
    const from = plan(k - 1).entries[i];
    const to = plan(k).entries[i];
    const delay = 1.5 + 9 * hash01(k, idHash[i], 20);
    l = { from, to, delay, path: null, travel: 0, arrive: 0 };
    row[i] = l;
    return l;
  }
  function route(l) {
    if (!l.path) {
      l.path = pathfinder.findPath({ x: l.from.x, z: l.from.z }, { x: l.to.x, z: l.to.z });
      l.travel = Math.min(l.path.len / SIM.walkSpeed, SIM.slotSeconds - l.delay - 6);
      l.arrive = l.delay + l.travel;
    }
    return l;
  }

  // ---- 任意の時刻の状態 -----------------------------------------------------
  // 戻り値：{ x, y, z, dx, dz, anim, bubble, line, kind, phase, place, partner, edge }
  //   anim: 'idle' | 'walk' | 'work' | 'cheer' | 'talk'
  //   bubble: 吹き出しの種類。アイコン（'talk' | 'heart' | 'note' | 'bolt'）か、セリフ 'line'（文面は line）
  //   kind: 'work' | 'gather' | 'chat' | 'wait' | 'wander' | 'rest' | 'travel'（別の場所へ遠出の途中）
  //   phase: 'linger'（前の行動の続き）| 'walk' | 'do'
  //   edge: 行動範囲の縁で様子をうかがっているときの、範囲外の地区の番号
  function stateAt(i, tMs) {
    const k = Math.floor(tMs / SLOT_MS);
    const e = (tMs - k * SLOT_MS) / 1000;
    const ep = epochOf(i, k);

    let entry;
    let lingering;
    let l = null;
    const tr = k - firstSlot(i, ep) < EPOCH - 1 ? transit(i, ep) : null;
    if (tr && k <= tr.kArr) {
      // 遠出の途中（出発前のひと呼吸 → 歩く → 着いて、その場所での行動）
      if (tMs >= tr.t0 && tMs < tr.t1) {
        const p = pathfinder.pointAt(tr.path, ((tMs - tr.t0) / (tr.t1 - tr.t0)) * tr.path.len);
        return { x: p.x, y: nav.yAt(p.x, p.z), z: p.z, dx: p.dx, dz: p.dz, anim: 'walk', bubble: null, line: '', kind: 'travel', phase: 'walk', place: tr.to.place, partner: -1, edge: undefined };
      }
      lingering = tMs < tr.t0;
      entry = lingering ? tr.from : tr.to;
    } else {
      l = leg(i, k);
      if (e >= l.delay) {
        route(l);
        if (e < l.arrive) {
          const p = pathfinder.pointAt(l.path, ((e - l.delay) / l.travel) * l.path.len);
          return { x: p.x, y: nav.yAt(p.x, p.z), z: p.z, dx: p.dx, dz: p.dz, anim: 'walk', bubble: null, line: '', kind: l.to.kind, phase: 'walk', place: l.to.place, partner: l.to.partner, edge: l.to.edge };
        }
      }
      lingering = e < l.delay;
      entry = lingering ? l.from : l.to;
    }

    const st = {
      x: entry.x,
      y: nav.yAt(entry.x, entry.z),
      z: entry.z,
      dx: entry.fx - entry.x,
      dz: entry.fz - entry.z,
      anim: 'idle',
      bubble: null,
      line: '',
      kind: entry.kind,
      phase: lingering ? 'linger' : 'do',
      place: entry.place,
      partner: entry.partner,
      edge: entry.edge,
    };

    if (entry.kind === 'work') {
      st.anim = 'work';
    } else if (entry.kind === 'gather') {
      st.anim = 'cheer';
      if (hashMix(idHash[i], Math.floor(tMs / 2400)) % 5 === 0) st.bubble = 'note';
    } else if (entry.kind === 'chat') {
      // 2人がそろっている間だけ会話する（会話は自由に動ける番どうしなので、相手も遠出の途中ではない）
      const j = entry.partner;
      const lj = leg(j, k);
      let together;
      if (lingering) together = e < Math.min(l.delay, lj.delay);
      else together = e >= Math.max(l.arrive, route(lj).arrive);
      if (together) {
        st.anim = 'talk';
        const turn = Math.floor(tMs / 1700) % 2;
        const speaker = turn === 0 ? Math.min(i, j) : Math.max(i, j);
        if (speaker === i) st.bubble = entry.icon;
      } else {
        st.kind = 'wait';
      }
    }

    // 行動範囲の縁にいると、たまに障壁を匂わせるセリフをつぶやく（「行ってみようか」投票への伏線）
    if (!st.bubble && LINE_KINDS.has(st.kind)) {
      const near = entry.edge ?? edgeAt(entry.x, entry.z);
      const lines = near === NO_DISTRICT ? null : barrierOf(near).lines;
      if (lines && lines.length) {
        const tt = tMs + (idHash[i] % LINE_MS);
        const cyc = Math.floor(tt / LINE_MS);
        const odds = entry.edge !== undefined ? 2 : 4; // 縁まで様子を見に来た人は、よくつぶやく
        if (hashMix(idHash[i], cyc, 61) % odds === 0 && tt - cyc * LINE_MS < LINE_SHOW_MS) {
          st.bubble = 'line';
          st.line = lines[hashMix(idHash[i], cyc, 62) % lines.length];
        }
      }
    }
    return st;
  }

  // ---- 詳細パネル用の「いま何をしているか」 ------------------------------------
  // 戻り値：{ key, label, text, place, districtId, partner, line, next }
  //   key:   'travel' | 'walk' | 'work' | 'gather' | 'chat' | 'wait' | 'look' | 'wander' | 'rest'
  //   label: 状態の短い呼び名（STATUS_LABELS）
  //   text:  文（例：「入り江の桟橋で釣りをしている」）
  //   districtId: いまいる地区（海の上の桟橋などは ''）
  //   partner: いっしょにいる／会いに行く相手の番号（いなければ -1）
  //   line:  いま吹き出しで言っているセリフ（なければ ''）
  //   next:  このあとの予定の文（なければ ''）
  function status(i, tMs) {
    const s = stateAt(i, tMs);
    const job = JOBS[islanders[i].job] || DEFAULT_JOB;
    const partner = s.partner >= 0 ? islanders[s.partner].displayName || islanders[s.partner].name : '';
    let key = s.kind;
    let text;
    if (s.phase === 'walk') {
      if (s.kind === 'travel') text = `${s.place}へ向かって歩いている`;
      else {
        key = 'walk';
        if (s.kind === 'chat') text = `${partner}に会いに${s.place}へ向かっている`;
        else if (s.kind === 'gather') text = `${hub.label}の集まりへ向かっている`;
        else text = `${s.place}へ歩いている`;
      }
    } else {
      switch (s.kind) {
        case 'work':
          text = `${s.place}で${job.work}`;
          break;
        case 'gather':
          text = `${hub.label}でみんなと集まっている`;
          break;
        case 'chat':
          text = `${s.place}で${partner}とおしゃべり中`;
          break;
        case 'wait':
          text = `${s.place}で${partner}を待っている`;
          break;
        case 'wander':
          if (s.edge !== undefined) {
            key = 'look';
            text = `${s.place}で${barrierOf(s.edge).look}`;
          } else text = `${s.place}を散歩している`;
          break;
        default:
          key = 'rest';
          text = `${s.place}でひと休みしている`;
      }
    }
    const c = terrain.cellOf(s.x, s.z);
    return { key, label: STATUS_LABELS[key] || '', text, place: s.place, districtId: districtIdAt(idx(c.i, c.j)), partner: s.partner, line: s.line || '', next: nextText(i, tMs, s) };
  }

  // このあとの予定（次に変わる行動）。これも時刻とIDだけで決まる。
  function nextText(i, tMs, s) {
    const k = Math.floor(tMs / SLOT_MS);
    const ep = epochOf(i, k);
    const k0 = firstSlot(i, ep);
    const job = JOBS[islanders[i].job] || DEFAULT_JOB;
    const ofEntry = (en) => {
      const partner = en.partner >= 0 ? islanders[en.partner].displayName || islanders[en.partner].name : '';
      switch (en.kind) {
        case 'work':
          return `${en.place}で${job.task || 'しごと'}`;
        case 'gather':
          return `${hub.label}の集まりへ`;
        case 'chat':
          return `${en.place}で${partner}とおしゃべり`;
        case 'wander':
          return en.edge !== undefined ? `${en.place}へ様子を見に` : `${en.place}へ散歩`;
        default:
          return `${en.place}でひと休み`;
      }
    };
    // 遠出の出発前・途中は、着いたあとの行動
    const tr = k - k0 < EPOCH - 1 ? transit(i, ep) : null;
    if (tr && k <= tr.kArr && tMs < tr.t1) return tr.from.spot === tr.to.spot ? ofEntry(tr.to) : s.phase === 'walk' ? `着いたら${ofEntry(tr.to)}` : `${tr.to.place}へ遠出`;
    // 前の行動の続き・歩いている途中は、このスロットの行動
    if (s.phase !== 'do') return ofEntry(plan(k).entries[i]);
    // 次のスロット（エポックの変わり目なら、次の場所への遠出）
    if (k === k0 + EPOCH - 1) {
      const nxt = homeEntry(i, ep + 1);
      return nxt.spot === homeEntry(i, ep).spot ? ofEntry(nxt) : `${nxt.place}へ遠出`;
    }
    return ofEntry(plan(k + 1).entries[i]);
  }

  // 文だけ（以前からの呼び出し口）
  const describe = (i, tMs) => status(i, tMs).text;

  // 集まり場から各建物への踏みあと（地面の色づけ用）
  function trails() {
    const cells = new Set();
    const start = nav.nearestOpen(hub.x + 4, hub.z + 4);
    if (start < 0) return cells;
    const seen = new Set();
    for (const s of buildingSpots) {
      if (seen.has(s.building)) continue;
      seen.add(s.building);
      const c = terrain.cellOf(s.x, s.z);
      const path = pathfinder.findCells(start, idx(c.i, c.j));
      if (path) for (const k of path) cells.add(k);
    }
    return cells;
  }

  return { SLOT_MS, EPOCH, hub, spots, plazaSpot, fireSpot, edgeSpots, edgeAt, plan, stateAt, status, describe, trails, indexOfId, zoneOf, epochOf, transit };
}
