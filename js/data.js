// data/*.json の読み込みと、欠けた項目を補う正規化。
// 正規化は DOM に依存しないので Node でも検証できる。

import { DEFAULT_ISLAND_NAME, DATA_URLS, DEMO_DATA_URLS, RTDB_BASE, BARRIERS, DEFAULT_BARRIER } from './config.js';
import { DISTRICTS, DISTRICT_INDEX, DISTRICT_ALIASES, MAP_VERSION, HALF, V1_HALF } from './terrain.js';
import { drifterColor } from './drift.js';

async function fetchJson(url, { timeoutMs = 0 } = {}) {
  if (!timeoutMs) {
    const res = await fetch(url, { cache: 'no-cache' });
    if (!res.ok) throw new Error(`${url} を読み込めませんでした（${res.status}）`);
    return res.json();
  }
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), timeoutMs);
  try {
    const res = await fetch(url, { cache: 'no-cache', signal: ctrl.signal });
    if (!res.ok) throw new Error(`${url} を読み込めませんでした（${res.status}）`);
    return await res.json();
  } finally {
    clearTimeout(timer);
  }
}

// RTDB の REST は、配列を「数値キーのオブジェクト」で返すことがある。空配列は保存されず、キーごと消える。
// 数値キーだけのオブジェクトは配列に戻し、それ以外はそのまま（中身は再帰で直す）。キー欠落の補完は正規化側の役目。
function rtdbPlain(v) {
  if (Array.isArray(v)) return v.map(rtdbPlain);
  if (v && typeof v === 'object') {
    const keys = Object.keys(v);
    if (keys.length && keys.every((k) => /^\d+$/.test(k))) {
      return keys.sort((a, b) => Number(a) - Number(b)).map((k) => rtdbPlain(v[k]));
    }
    const out = {};
    for (const k of keys) out[k] = rtdbPlain(v[k]);
    return out;
  }
  return v;
}

// demo: true なら data/demo/ の「育った島」のデモデータを読む（?demo で開いたとき）
// 本番は Firebase RTDB を第一に読み、届かない・空・形がおかしいときは同梱の data/*.json に切り替える。
// 漂流者（drifters.json）は読めなくても島はひらく（そのときは漂流者0人）。
export async function loadData({ demo = false } = {}) {
  if (demo) {
    const urls = DEMO_DATA_URLS;
    const [stateRaw, rosterRaw, driftRaw] = await Promise.all([
      fetchJson(urls.state),
      fetchJson(urls.islanders),
      urls.drifters ? fetchJson(urls.drifters).catch(() => null) : null,
    ]);
    return normalizeData(stateRaw, rosterRaw, driftRaw);
  }
  const urls = DATA_URLS;
  const loadOne = async (name, localUrl, optional) => {
    try {
      const raw = await fetchJson(`${RTDB_BASE}/${name}.json`, { timeoutMs: 4000 });
      if (raw && typeof raw === 'object') return rtdbPlain(raw);
      throw new Error('RTDB のデータが空でした');
    } catch {
      return optional ? fetchJson(localUrl).catch(() => null) : fetchJson(localUrl);
    }
  };
  const [stateRaw, rosterRaw, driftRaw] = await Promise.all([
    loadOne('state', urls.state, false),
    loadOne('islanders', urls.islanders, false),
    loadOne('drifters', urls.drifters, true),
  ]);
  return normalizeData(stateRaw, rosterRaw, driftRaw);
}

const str = (v, fallback = '') => (typeof v === 'string' || typeof v === 'number' ? String(v) : fallback);
const int = (v, fallback) => (Number.isFinite(Number(v)) ? Math.floor(Number(v)) : fallback);
// null や空文字を 0 と読まないための数値化
const num = (v) => (typeof v === 'number' ? v : typeof v === 'string' && v.trim() !== '' ? Number(v) : NaN);
const dayOrNull = (v) => (Number.isFinite(num(v)) ? Math.max(1, Math.floor(num(v))) : null);
const districtId = (id) => DISTRICT_ALIASES[id] || id;
const voteOf = (v) => (v && typeof v === 'object' ? { question: str(v.question), adopted: str(v.adopted), note: str(v.note) } : null);

// driftRaw（漂流者）は省略できる。読めなかったとき（null）や形がおかしいときは漂流者0人。
export function normalizeData(stateRaw, rosterRaw, driftRaw = null) {
  const s = stateRaw && typeof stateRaw === 'object' ? stateRaw : {};
  const day = Math.max(1, int(s.day, 1));
  // "map" が無いか 1 のデータは、版1（128×128マス）の座標。いまの地図の座標へ換算する。
  const mapScale = int(s.map, 1) < MAP_VERSION ? HALF / V1_HALF : 1;

  // 島民の行動範囲。地区ごとに、範囲の中か（inRange）と、範囲が広がった日（expandedDay）・理由（reason）・
  // 決め手になった投票（vote）を持つ。範囲は運営が開けるものではなく、住民の投票で広がるもの。
  // 書かれていない地区は公開時の範囲（砂浜・入り江・平原は中、森・高原は自然の障壁で外）とする。
  // expandedDay が今日より先なら、その日までは範囲の外（先に書いておける）。
  const given = new Map(
    (Array.isArray(s.districts) ? s.districts : []).filter((d) => d && typeof d === 'object').map((d) => [districtId(str(d.id)), d]),
  );
  const districts = DISTRICTS.map((d) => {
    const g = given.get(d.id) || {};
    const expandedDay = dayOrNull(g.expandedDay);
    const wanted = typeof g.inRange === 'boolean' ? g.inRange : expandedDay !== null ? true : d.safe;
    const inRange = wanted && !(expandedDay !== null && expandedDay > day);
    return {
      id: d.id,
      name: str(g.name).trim() || d.name,
      inRange,
      expandedDay: inRange ? expandedDay : null,
      reason: inRange ? str(g.reason) : '',
      vote: inRange ? voteOf(g.vote) : null,
      barrier: str(g.barrier).trim() || (BARRIERS[d.id] || DEFAULT_BARRIER).barrier,
    };
  });

  // 拠点（広場）。最初の投票「拠点はどこにする？」の結果として生まれる。
  // 決まるまでは null で、島民は漂着した砂浜に集まる。
  let base = null;
  const b0 = s.base;
  if (b0 && typeof b0 === 'object' && Number.isFinite(num(b0.x)) && Number.isFinite(num(b0.z))) {
    const decidedDay = dayOrNull(b0.decidedDay);
    if (decidedDay === null || decidedDay <= day) base = { name: str(b0.name).trim() || '広場', x: num(b0.x) * mapScale, z: num(b0.z) * mapScale, decidedDay, note: str(b0.note) };
  }

  const buildings = (Array.isArray(s.buildings) ? s.buildings : [])
    .filter((b) => b && typeof b === 'object' && Number.isFinite(Number(b.x)) && Number.isFinite(Number(b.z)))
    .map((b, n) => ({
      id: str(b.id, `building-${n + 1}`),
      type: str(b.type, 'unknown'),
      name: str(b.name),
      x: Number(b.x) * mapScale,
      z: Number(b.z) * mapScale,
      rot: Number(b.rot) || 0,
      builtDay: Number.isFinite(Number(b.builtDay)) ? int(b.builtDay) : null,
      note: str(b.note),
    }))
    .filter((b) => b.builtDay === null || b.builtDay <= day);

  // 年表。expands: その日に行動範囲へ加わった地区（例：["forest"]）。
  const chronicle = (Array.isArray(s.chronicle) ? s.chronicle : [])
    .filter((c) => c && typeof c === 'object')
    .map((c) => ({
      day: int(c.day, 0),
      date: str(c.date),
      title: str(c.title, '（無題）'),
      text: str(c.text),
      vote: voteOf(c.vote),
      expands: [].concat(c.expands ?? []).map((id) => districtId(str(id))).filter((id) => id in DISTRICT_INDEX),
      auto: false,
    }));
  // 行動範囲の拡大は、必ず年表に「住民の決定」として残す。
  // 年表に expands つきの記事が無い拡大は、districts の記録から記事を自動で足す。
  for (const d of districts) {
    if (!d.inRange || d.expandedDay === null || chronicle.some((c) => c.expands.includes(d.id))) continue;
    chronicle.push({ day: d.expandedDay, date: '', title: `行動範囲が${d.name}まで広がった`, text: d.reason || '住民の投票で決まった。', vote: d.vote, expands: [d.id], auto: true });
  }
  chronicle.sort((a, b) => b.day - a.day);

  let currentVote = null;
  if (s.currentVote && typeof s.currentVote === 'object' && str(s.currentVote.question)) {
    const v = s.currentVote;
    const deadline = v.deadline ? new Date(v.deadline) : null;
    currentVote = {
      id: str(v.id),
      status: ['open', 'counting', 'closed'].includes(v.status) ? v.status : 'open',
      question: str(v.question),
      description: str(v.description),
      options: (Array.isArray(v.options) ? v.options : []).map((o, n) => ({
        key: str(o?.key, String.fromCharCode(65 + n)),
        label: str(o?.label ?? o),
        note: str(o?.note),
      })),
      deadline: deadline && !Number.isNaN(deadline.getTime()) ? deadline : null,
      postUrl: /^https:\/\//.test(str(v.postUrl)) ? str(v.postUrl) : '',
      result: v.result && typeof v.result === 'object' ? { key: str(v.result.key), note: str(v.result.note) } : null,
    };
  }

  // 森の道づくり：森の入口から光の場所まで、木が need 本（既定300）。島民1人が1本ずつ切りひらく＝島民の数だけ道が伸びる
  let forestRoad = null;
  if (s.forestRoad && typeof s.forestRoad === 'object' && int(s.forestRoad.startDay, 1) <= day) {
    const r = s.forestRoad;
    const pts = (Array.isArray(r.points) ? r.points : []).filter((p) => Array.isArray(p) && p.length >= 2 && p.every((v) => Number.isFinite(Number(v)))).map((p) => [Number(p[0]), Number(p[1])]);
    forestRoad = { points: pts.length >= 2 ? pts : [[-74, -22], [-128, -34]], need: Math.max(1, int(r.need, 300)), width: Number(r.width) > 0 ? Number(r.width) : 3.2, startDay: int(r.startDay, 1), count: 0, label: str(r.label, '光の場所') };
  }

  const state = {
    forestRoad,
    sample: s.sample === true,
    islandName: str(s.islandName).trim() || DEFAULT_ISLAND_NAME,
    day,
    updatedAt: str(s.updatedAt),
    districts,
    base,
    buildings,
    chronicle,
    currentVote,
  };

  // 名簿
  const list = Array.isArray(rosterRaw) ? rosterRaw : Array.isArray(rosterRaw?.islanders) ? rosterRaw.islanders : [];
  const seen = new Set();
  const islanders = [];
  for (const p of list) {
    if (!p || typeof p !== 'object') continue;
    const id = str(p.id).trim();
    if (!id || seen.has(id)) continue;
    const joinedDay = Math.max(1, int(p.joinedDay, 1));
    if (joinedDay > day) continue; // まだ漂着していない（先に名簿へ入れておける）
    seen.add(id);
    const anonymous = p.anonymous === true;
    const name = str(p.name).trim() || id;
    islanders.push({
      id,
      name,
      anonymous,
      displayName: anonymous ? '匿名の島民' : name,
      joinedDay,
      since: str(p.since),
      home: districtId(str(p.home, 'beach')), // 起点の地区（散歩でよく行く）。省略時は漂着した砂浜
      job: str(p.job, '島民'),
      color: str(p.color, '#4a90d9'),
      relationships: (Array.isArray(p.relationships) ? p.relationships : [])
        .filter((r) => r && str(r.id))
        .map((r) => ({ id: str(r.id), type: str(r.type, 'friend'), affinity: Math.max(0, Math.min(100, int(r.affinity, 50))) })),
      sample: p.sample === true,
      days: day - joinedDay + 1, // 在住日数（漂着した日を1日目と数える）
      missing: normalizeMissing(p.missing, day),
      today: normalizeToday(p.today, day),
    });
  }
  // 島にいない相手との関係は表示しない
  for (const p of islanders) p.relationships = p.relationships.filter((r) => seen.has(r.id) && r.id !== p.id);

  if (state.forestRoad) state.forestRoad.count = islanders.length;
  return { state, islanders, drifters: normalizeDrifters(driftRaw, seen) };
}

// 行方不明（動画の筋書き）：{ "day": 3, "text": "…", "x": -125, "z": -35 }。day 以降だけ有効。
//   地図の上ではその人の姿を消し、森の奥（x, z）に「？」と足跡を出す。詳細の「いま」は text。
export const MISSING_DEFAULT = { x: -128, z: -34, text: '森の奥へ入ったまま、戻ってこない…' };
function normalizeMissing(m, day) {
  if (!m || typeof m !== 'object') return null;
  const from = Math.max(1, int(m.day, 1));
  if (from > day || m.found === true) return null;
  const num = (v, d) => (Number.isFinite(Number(v)) ? Number(v) : d);
  return { day: from, text: str(m.text).trim() || MISSING_DEFAULT.text, x: num(m.x, MISSING_DEFAULT.x), z: num(m.z, MISSING_DEFAULT.z) };
}

// きょうの行動（動画でやったことを、次の動画まで島で続ける）：
//   { "day": 3, "text": "入り江で釣りをしている", "x": -9, "z": 187, "anim": "work", "tool": "rod", "dx": 0, "dz": 1 }
//   day の日（島の◯日目）だけ有効。次の動画で day が進むと、ふだんの暮らしに戻る。
const TODAY_ANIMS = new Set(['idle', 'work', 'sit', 'eat', 'cheer', 'shock', 'talk']);
function normalizeToday(t, day) {
  if (!t || typeof t !== 'object') return null;
  if (int(t.day, 0) !== day) return null;
  const x = Number(t.x), z = Number(t.z);
  if (!Number.isFinite(x) || !Number.isFinite(z)) return null;
  const anim = TODAY_ANIMS.has(str(t.anim)) ? str(t.anim) : 'idle';
  return {
    day,
    text: str(t.text).trim() || 'きのうの続きをしている',
    x, z, anim,
    tool: str(t.tool).trim() || null,
    dx: Number.isFinite(Number(t.dx)) ? Number(t.dx) : 0,
    dz: Number.isFinite(Number(t.dz)) ? Number(t.dz) : 1,
  };
}

// 漂流者：フォローしてから、次の動画で漂着して島民になるまでの人（drifters.json）。
//   { "updatedAt": "2026-11-17", "drifters": [ { "id": "instagram_id", "name": "表示名", "since": "2026-11-17" } ] }
// 名簿（islanders.json）にもう載っている人は、漂着ずみなので漂流者には出さない。
// islanderIds: 島民の ID の Set
export function normalizeDrifters(raw, islanderIds = new Set()) {
  const list = Array.isArray(raw) ? raw : Array.isArray(raw?.drifters) ? raw.drifters : [];
  const seen = new Set();
  const drifters = [];
  for (const p of list) {
    if (!p || typeof p !== 'object') continue;
    const id = str(p.id).trim();
    if (!id || seen.has(id) || islanderIds.has(id)) continue;
    seen.add(id);
    const anonymous = p.anonymous === true;
    const name = str(p.name).trim() || id;
    const since = str(p.since).trim();
    drifters.push({
      id,
      name,
      anonymous,
      displayName: anonymous ? '匿名の漂流者' : name,
      since: /^\d{4}-\d{2}-\d{2}$/.test(since) ? since : '', // 漂流を始めた日（日本時間、YYYY-MM-DD）
      color: drifterColor(id), // 服の色は id のハッシュで決まる
      sample: p.sample === true,
    });
  }
  return drifters;
}

// 在住日数ランキング（長い順。同じなら名簿の順）
export function rankIslanders(islanders) {
  return islanders
    .map((p, index) => ({ p, index }))
    .sort((a, b) => b.p.days - a.p.days || a.index - b.index)
    .map((e, n, arr) => ({ ...e, rank: n > 0 && arr[n - 1].p.days === e.p.days ? null : n + 1 }))
    .map((e, n, arr) => {
      // 同じ日数は同じ順位
      if (e.rank === null) {
        let m = n - 1;
        while (arr[m].rank === null) m--;
        return { ...e, rank: arr[m].rank };
      }
      return e;
    });
}
