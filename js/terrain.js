// 島の地形（高度マップ）・地区・植生・歩ける範囲を決定的に生成する。
// Three.js には依存しない（Node でもそのまま検証できる）。
//
// 座標系：x = 東が＋、z = 南が＋、y = 上。島の中心が (0, 0)。
// 1マス = CELL ワールド単位、高さは 1 単位きざみの段々（ドット絵的な見た目のため）。
//
// 地図の版（MAP_VERSION）
//   1 … 128×128マス（一辺256）のコンパクトな島（〜2026-11-16）
//   2 … 384×384マス（一辺768）の広い島。一辺3倍・面積9倍。地区の並び（東＝砂浜、南＝入り江、
//        真ん中＝平原、西＝森、北東＝高原）は同じで、岬・小島・池・雪の峰などの細部が増えた。
// state.json の座標（base・buildings）は、その版の地図の座標で書く（data.js が "map" を見て古い版を換算する）。

import { makeFastNoise2D, hash3 } from './rng.js';

export const MAP_VERSION = 2;
export const N = 384; // マス数（1辺）
export const CELL = 2; // 1マスの大きさ
export const HALF = (N * CELL) / 2; // 島の座標は -HALF 〜 +HALF
export const V1_HALF = 128; // 版1の地図の HALF（座標の換算用）
export const SEA_Y = 0.45; // 海面の高さ
export const MIN_Y = -5; // 海底の下限
export const MAX_Y = 60; // 高さの上限
export const TERRAIN_SEED = 20261116;

export const BIOME = {
  SEABED: 0,
  SAND: 1,
  GRASS: 2,
  FOREST: 3,
  HIGH: 4,
  ROCK: 5,
  PLAZA: 6,
  PATH: 7,
  SNOW: 8,
};

// 地区。u, v は島の正規化座標（-1〜1）での中心。state.json の districts[].id と対応する。
//   safe: 公開時から島民の行動範囲に入っている安全な場所か（森・高原は自然の障壁があって範囲外）
//   w:    地区の広がりやすさ（大きいほど広い。境目は「中心までの距離 ÷ w」が等しくなる線）
//   label:地区名ラベルを出す位置（u, v）。省略時は中心
// 島の真ん中は、拠点が決まるまではただの「平原」。拠点（広場）は最初の投票の結果として生まれる。
export const DISTRICTS = [
  { id: 'plain', name: '平原', u: 0.0, v: 0.05, w: 0.78, safe: true },
  { id: 'cove', name: '入り江', u: -0.08, v: 0.56, w: 0.8, safe: true, label: { u: -0.2, v: 0.5 } },
  { id: 'beach', name: '砂浜', u: 0.6, v: 0.3, w: 0.8, safe: true },
  { id: 'forest', name: '森', u: -0.5, v: -0.12, w: 1.12, safe: false },
  { id: 'highland', name: '高原', u: 0.27, v: -0.45, w: 1.0, safe: false },
];
export const DISTRICT_INDEX = Object.fromEntries(DISTRICTS.map((d, i) => [d.id, i]));
// 以前のデータとの互換：真ん中の地区は 'plaza' と書かれていても受けつける
export const DISTRICT_ALIASES = { plaza: 'plain' };
export const NO_DISTRICT = 255;
const PLAZA_RADIUS = 15; // 拠点の広場（踏み固められた地面）の半径（ワールド単位）

// 島の真ん中（平らにならされた平原の中心。拠点の第一候補）
export const PLAIN_CENTER = { x: DISTRICTS[0].u * HALF, z: DISTRICTS[0].v * HALF };
// 漂流者が打ち上がる東の砂浜。拠点が決まるまでは、ここが島民の仮の集まり場。
export const LANDING = { x: 236, z: 124, name: '漂着した砂浜' };
// 平原の北の池（森と高原のあいだの水場）
export const POND = { x: -0.05 * HALF, z: -0.3 * HALF, name: '池' };

const clamp = (x, a, b) => Math.max(a, Math.min(b, x));
const lerp = (a, b, t) => a + (b - a) * t;
const smoothstep = (a, b, x) => {
  const t = clamp((x - a) / (b - a), 0, 1);
  return t * t * (3 - 2 * t);
};
const gauss = (du, dv, s) => Math.exp(-(du * du + dv * dv) / (s * s));

// 角度 a のまわりだけ海岸線を押し出す（＋）／へこませる（−）ための山形
const lobe = (a, a0, width) => {
  let d = a - a0;
  if (d > Math.PI) d -= Math.PI * 2;
  if (d < -Math.PI) d += Math.PI * 2;
  return Math.exp(-(d * d) / (width * width));
};

function rawHeight(u, v, nz) {
  const r = Math.hypot(u, v);
  if (r > 1.2) return MIN_Y - 4;
  const a = Math.atan2(v, u);
  const wBeach = gauss(u - 0.57, v - 0.3, 0.27);

  // 海岸線：角度とノイズでいびつな形にする。砂浜側は少し張り出す。細かいノイズが岬と小さな湾をつくる。
  const coast =
    0.69 +
    0.06 * Math.sin(a * 3 + 1.3) +
    0.035 * Math.sin(a * 5 + 0.4) +
    0.08 * nz.fbm(u * 2.2 + 10, v * 2.2 + 10, 3) +
    0.06 * nz.fbm(u * 6.5 + 30, v * 6.5 + 30, 3) * (1 - 0.7 * wBeach) +
    0.05 * wBeach +
    0.1 * lobe(a, 2.42, 0.13) + // 南西の岬（先に小島がある）
    0.07 * lobe(a, -1.2, 0.16) + // 北の岬（高原の裏の崖）
    0.05 * lobe(a, 0.95, 0.1) - // 南東の小さな岬
    0.07 * lobe(a, -2.75, 0.14); // 西の湾
  const e = 1 - r / coast; // >0 が陸

  let h;
  if (e <= 0) {
    h = e * 36;
  } else {
    const inland = smoothstep(0.03, 0.22, e);
    h = 0.6 + 4.4 * smoothstep(0, 0.32, e) + 2.2 * e + (2.4 * nz.fbm(u * 3.2, v * 3.2, 4) + 1.1 * nz.fbm(u * 9 + 5, v * 9 + 5, 3)) * inland;
    // 高原（北東）：切り立った縁をもつ台地の上に、岩と雪の峰
    const mesa = gauss(u - 0.27, v + 0.43, 0.27) * (1 + 0.28 * nz.fbm(u * 5 + 7, v * 5 + 7, 3));
    h += (6 * mesa + 12 * smoothstep(0.34, 0.66, mesa)) * inland;
    h += 15 * gauss(u - 0.3, v + 0.47, 0.085) * inland;
    h += 5 * gauss(u - 0.13, v + 0.37, 0.06) * inland;
    // 森（西）：起伏のある丘
    const wForest = gauss(u + 0.48, v + 0.12, 0.34);
    h += (3.2 * nz.fbm(u * 7 + 3, v * 7 + 3, 3) + 5 * gauss(u + 0.55, v + 0.2, 0.11)) * wForest * inland;
    // ところどころ、海岸が崖になる（北側ほど多い）
    const cliff = smoothstep(0.02, 0.4, nz.fbm(u * 3.4 + 200, v * 3.4 + 200, 2) - v * 0.45 - 0.9 * wBeach);
    h += 4.5 * cliff * smoothstep(0, 0.03, e);
    // 砂浜（東）は低く平らに
    h = lerp(h, Math.min(h, 0.9 + e * 4.8), Math.min(1, wBeach * 1.25));
  }

  // 入り江（南）：海が島の内側へ食い込む
  const cu = (u + 0.09) / 0.085;
  const cv = (v - 0.67) / 0.27;
  h -= 14 * Math.exp(-(cu * cu + cv * cv));
  // 北西の小さな湾
  h -= 9 * gauss(u + 0.29, v + 0.71, 0.075);
  // 沖の小島（歩いては行けない。いつか舟で？）
  h = Math.max(h, 17 * gauss(u + 0.7, v - 0.66, 0.062) - 8, 15 * gauss(u - 0.9, v + 0.18, 0.036) - 8, 15 * gauss(u - 0.22, v + 0.95, 0.04) - 8);

  // 真ん中の平原は平らにならす（ゆるい起伏だけ残す）
  const wPlain = smoothstep(0.27, 0.11, Math.hypot(u, v - 0.05));
  h = lerp(h, 4 + 0.9 * nz.fbm(u * 8 + 60, v * 8 + 60, 2), wPlain);
  // 平原の北の池（森と高原のあいだの水場）。まわりはなだらかな窪地にする。
  const pond = Math.hypot((u + 0.05) * 0.8, v + 0.3) + 0.012 * nz.fbm(u * 20, v * 20, 2);
  h = lerp(h, 3, smoothstep(0.13, 0.055, pond));
  h = lerp(h, -2, smoothstep(0.052, 0.03, pond));
  return h;
}

// base: 拠点（{ x, z }）。拠点が決まっていれば、そのまわりを踏み固められた広場の地面にする。
// 地形（高さ）は拠点があってもなくても変わらない。
export function generateTerrain(seed = TERRAIN_SEED, { base = null } = {}) {
  const nz = makeFastNoise2D(seed);
  const h = new Int8Array(N * N);
  const biome = new Uint8Array(N * N);
  const district = new Uint8Array(N * N).fill(NO_DISTRICT);

  const idx = (i, j) => j * N + i;
  const inGrid = (i, j) => i >= 0 && j >= 0 && i < N && j < N;
  const cellCenter = (i, j) => ({ x: (i - N / 2 + 0.5) * CELL, z: (j - N / 2 + 0.5) * CELL });
  const cellOf = (x, z) => ({
    i: clamp(Math.floor(x / CELL + N / 2), 0, N - 1),
    j: clamp(Math.floor(z / CELL + N / 2), 0, N - 1),
  });

  for (let j = 0; j < N; j++) {
    const v = ((j - N / 2 + 0.5) * CELL) / HALF;
    for (let i = 0; i < N; i++) {
      const u = ((i - N / 2 + 0.5) * CELL) / HALF;
      h[j * N + i] = clamp(Math.round(rawHeight(u, v, nz)), MIN_Y, MAX_Y);
    }
  }

  const heightAtCell = (i, j) => (inGrid(i, j) ? h[idx(i, j)] : MIN_Y);

  // 地区とバイオーム
  const nd = DISTRICTS.length;
  for (let j = 0; j < N; j++) {
    for (let i = 0; i < N; i++) {
      const k = idx(i, j);
      const y = h[k];
      if (y < 1) {
        biome[k] = BIOME.SEABED;
        continue;
      }
      const x = (i - N / 2 + 0.5) * CELL;
      const z = (j - N / 2 + 0.5) * CELL;
      const u = x / HALF;
      const v = z / HALF;

      // 地区：ノイズでゆらした座標で「中心までの距離 ÷ 広がりやすさ」がいちばん小さい地区
      const wu = u + 0.075 * nz.fbm(u * 5 + 50, v * 5 + 50, 3);
      const wv = v + 0.075 * nz.fbm(u * 5 + 80, v * 5 + 80, 3);
      let d = 0;
      let best = Infinity;
      for (let n = 0; n < nd; n++) {
        const dd = Math.hypot(wu - DISTRICTS[n].u, wv - DISTRICTS[n].v) / DISTRICTS[n].w;
        if (dd < best) {
          best = dd;
          d = n;
        }
      }
      district[k] = d;

      let steep = 0;
      if (i > 0 && h[k - 1] >= 1) steep = Math.max(steep, Math.abs(h[k - 1] - y));
      if (i < N - 1 && h[k + 1] >= 1) steep = Math.max(steep, Math.abs(h[k + 1] - y));
      if (j > 0 && h[k - N] >= 1) steep = Math.max(steep, Math.abs(h[k - N] - y));
      if (j < N - 1 && h[k + N] >= 1) steep = Math.max(steep, Math.abs(h[k + N] - y));

      const id = DISTRICTS[d].id;
      const speck = hash3(i, j, seed + 5);
      const dBase = base ? Math.hypot(x - base.x, z - base.z) : Infinity;
      let b = BIOME.GRASS;
      if (y === 1) b = BIOME.SAND;
      else if ((id === 'beach' || id === 'cove') && y <= 2) b = BIOME.SAND;
      else if (dBase < PLAZA_RADIUS + (speck - 0.5) * 3) b = BIOME.PLAZA;
      else if (steep >= 3) b = BIOME.ROCK;
      else if (id === 'highland') {
        if (y >= 30 || (y >= 28 && speck < 0.55)) b = BIOME.SNOW;
        else if (y >= 25 || (y >= 23 && speck < 0.5)) b = BIOME.ROCK;
        else if (y >= 9) b = BIOME.HIGH;
      } else if (id === 'forest' && y >= 3) b = BIOME.FOREST;
      biome[k] = b;
    }
  }

  // 連続した高さ（クリック位置の補助などに使う）
  const heightAt = (x, z) => {
    const c = cellOf(x, z);
    return h[idx(c.i, c.j)];
  };

  return { N, CELL, HALF, seed, nz, h, biome, district, idx, inGrid, cellCenter, cellOf, heightAt, heightAtCell };
}

// 木・岩・草花を決定的に配置する。reserved(i, j) が true のマスには置かない。
export function generateDeco(terrain, reserved = () => false) {
  const { h, biome, district, idx, seed, nz } = terrain;
  const items = [];
  for (let j = 1; j < N - 1; j++) {
    for (let i = 1; i < N - 1; i++) {
      const k = idx(i, j);
      const y = h[k];
      if (y <= -3) continue;
      const roll = hash3(i, j, seed + 11);
      if (y < 1) {
        // 浅瀬の岩
        if (roll < 0.004 && !reserved(i, j)) items.push(makeItem(i, j, y, 'searock', true));
        continue;
      }
      if (reserved(i, j)) continue;

      const b = biome[k];
      const dId = DISTRICTS[district[k]].id;
      let kind = null;
      let blocks = true;
      if (b === BIOME.FOREST) {
        if (roll < 0.19) kind = 'tree';
        else if (roll < 0.22) (kind = 'flower'), (blocks = false);
        else if (roll < 0.226) kind = 'rock';
      } else if (b === BIOME.GRASS) {
        // 草地には、ところどころ木立（小さな林）がある
        const u = ((i - N / 2 + 0.5) * CELL) / HALF;
        const v = ((j - N / 2 + 0.5) * CELL) / HALF;
        const grove = smoothstep(0.18, 0.5, nz.fbm(u * 11 + 90, v * 11 + 90, 2));
        if (roll < 0.008 + 0.1 * grove) kind = 'tree';
        else if (roll < 0.06 + 0.1 * grove) (kind = 'flower'), (blocks = false);
        else if (roll < 0.064 + 0.1 * grove) kind = 'rock';
      } else if (b === BIOME.HIGH) {
        if (roll < 0.035) kind = 'pine';
        else if (roll < 0.055) kind = 'rock';
        else if (roll < 0.09) (kind = 'flower'), (blocks = false);
      } else if (b === BIOME.ROCK) {
        if (roll < 0.07) kind = 'rock';
      } else if (b === BIOME.SNOW) {
        if (roll < 0.03) kind = 'rock';
      } else if (b === BIOME.SAND) {
        if ((dId === 'beach' || dId === 'cove') && roll < 0.018) kind = 'palm';
        else if (roll < 0.026) kind = 'rock';
        else if (roll < 0.042) (kind = 'shell'), (blocks = false);
      }
      if (kind) items.push(makeItem(i, j, y, kind, blocks));
    }
  }
  return items;

  function makeItem(i, j, y, kind, blocks) {
    const r2 = hash3(i, j, seed + 12);
    const r3 = hash3(i, j, seed + 13);
    return {
      i,
      j,
      x: (i - N / 2 + 0.5) * CELL + (r2 - 0.5) * 0.8,
      z: (j - N / 2 + 0.5) * CELL + (r3 - 0.5) * 0.8,
      y,
      scale: 0.8 + r2 * 0.5,
      variant: Math.floor(r3 * 4),
      district: district[idx(i, j)],
      kind,
      blocks,
    };
  }
}

// 歩ける範囲を作る。
//  blocked: Set<cellIndex>（建物の敷地など）
//  decks: Map<cellIndex, y>（桟橋など、水上でも歩ける床）
//  outOfRange: Set<districtIndex>（島民の行動範囲の外。森・高原などの自然の障壁の向こう側は、日常の移動に使わない）
//  origin: 到達可能性の起点（島民の集まり場）
export function buildNav(terrain, { blocked = new Set(), decks = new Map(), outOfRange = new Set(), deco = [], origin = { x: 0, z: 0 } } = {}) {
  const { h, district, idx, cellOf, cellCenter, inGrid } = terrain;
  const open = new Uint8Array(N * N);
  const walkY = new Float32Array(N * N);
  const treeCells = new Set();
  for (const d of deco) if (d.blocks) treeCells.add(idx(d.i, d.j));

  for (let k = 0; k < N * N; k++) {
    walkY[k] = h[k];
    if (decks.has(k)) {
      open[k] = 1;
      walkY[k] = decks.get(k);
      continue;
    }
    if (h[k] < 1) continue;
    if (blocked.has(k) || treeCells.has(k)) continue;
    if (outOfRange.has(district[k])) continue;
    open[k] = 1;
  }

  const canStep = (a, b) => open[a] && open[b] && Math.abs(walkY[a] - walkY[b]) <= MAX_STEP;

  // 8方向の隣接（角抜けは禁止）
  function neighbors(i, j, out) {
    out.length = 0;
    const k = idx(i, j);
    for (let dj = -1; dj <= 1; dj++) {
      for (let di = -1; di <= 1; di++) {
        if (!di && !dj) continue;
        const ni = i + di;
        const nj = j + dj;
        if (!inGrid(ni, nj)) continue;
        const nk = idx(ni, nj);
        if (!canStep(k, nk)) continue;
        if (di && dj) {
          const k1 = idx(i + di, j);
          const k2 = idx(i, j + dj);
          if (!canStep(k, k1) || !canStep(k, k2) || !canStep(k1, nk) || !canStep(k2, nk)) continue;
        }
        out.push(ni, nj, di && dj ? Math.SQRT2 : 1);
      }
    }
    return out;
  }

  // 起点から歩いて行けるマスだけを残す
  const start = nearestOpen(origin.x, origin.z, open);
  const walk = new Uint8Array(N * N);
  if (start >= 0) {
    const queue = [start];
    walk[start] = 1;
    const buf = [];
    while (queue.length) {
      const k = queue.pop();
      neighbors(k % N, Math.floor(k / N), buf);
      for (let n = 0; n < buf.length; n += 3) {
        const nk = idx(buf[n], buf[n + 1]);
        if (!walk[nk]) {
          walk[nk] = 1;
          queue.push(nk);
        }
      }
    }
  }
  // 以降は「到達可能」なマスだけを歩行可とする
  for (let k = 0; k < N * N; k++) open[k] = walk[k];

  function nearestOpen(x, z, grid = walk, maxRing = 60) {
    const c = cellOf(x, z);
    let best = -1;
    let bestD = Infinity;
    for (let ring = 0; ring <= maxRing; ring++) {
      for (let dj = -ring; dj <= ring; dj++) {
        for (let di = -ring; di <= ring; di++) {
          if (Math.max(Math.abs(di), Math.abs(dj)) !== ring) continue;
          const i = c.i + di;
          const j = c.j + dj;
          if (!inGrid(i, j) || !grid[idx(i, j)]) continue;
          const cc = cellCenter(i, j);
          const d = (cc.x - x) ** 2 + (cc.z - z) ** 2;
          if (d < bestD) {
            bestD = d;
            best = idx(i, j);
          }
        }
      }
      if (best >= 0 && ring >= 1) break;
    }
    return best;
  }

  const isWalkable = (x, z) => {
    const c = cellOf(x, z);
    return walk[idx(c.i, c.j)] === 1;
  };
  const yAt = (x, z) => {
    const c = cellOf(x, z);
    return walkY[idx(c.i, c.j)];
  };
  // 歩ける位置へ寄せる（すでに歩けるならそのまま）
  const snap = (x, z) => {
    if (isWalkable(x, z)) return { x, z };
    const k = nearestOpen(x, z);
    if (k < 0) return { x, z };
    return cellCenter(k % N, Math.floor(k / N));
  };

  return { walk, walkY, neighbors, nearestOpen, isWalkable, yAt, snap, canStep };
}

export const MAX_STEP = 1; // 1歩で上り下りできる段差
