// ep1 v3 (ep1_fable_v3.mp4): the same film re-shot on the enlarged island (384x384 cells, world 768 wide).
// Camera keyframes in film seconds; fable_timeline.mjs (v1/v2, small island) is left as it was.
export const FPS = 24;
export const DURATION = 57.0;

export const LANDING = { x: 236, z: 124 };
// where the castaway lies: the lowest sand step by the water, seaward (south-east) of LANDING
export const LIE = { x: 247, z: 135 };

//            t      tx   ty  tz    dist  az     pol    hour
const K = (t, tx, ty, tz, dist, az, pol, hour, fov = 38) => ({ t, tx, ty, tz, dist, az, pol, hour, fov });
export const SHOTS = {
  // a: dawn at sea level -> rise to the whole island -> one sweep through the five districts while a day passes
  a: {
    from: 0, to: 12.75, keys: [
      K(0.0, 20, 10, 0, 2000, 1.08, 1.56, 5.15),
      K(1.4, 20, 10, 0, 1880, 1.05, 1.55, 5.75),
      K(3.5, 20, 10, 15, 1760, 0.82, 0.98, 7.0),
      K(4.35, 22, 10, 20, 1690, 0.76, 0.95, 7.6),
      K(5.2, 228, 4, 112, 150, 1.30, 1.20, 9.0), // 砂浜
      K(5.8, 220, 4, 120, 145, 1.18, 1.20, 10.0),
      K(6.45, -31, 3, 195, 170, 0.25, 1.15, 11.5), // 入り江
      K(6.9, -31, 4, 185, 165, 0.12, 1.16, 12.3),
      K(7.55, 0, 8, 19, 170, -0.55, 1.20, 14.0), // 平原
      K(8.0, -10, 8, 14, 165, -0.68, 1.21, 15.0),
      K(8.8, -180, 12, -46, 130, -1.35, 1.25, 18.3), // 森（夕方→夜）
      K(9.9, -192, 12, -50, 115, -1.55, 1.27, 20.6),
      K(10.75, 104, 36, -173, 200, -2.55, 1.30, 22.3), // 高原（夜ふけ。1日目のうちに収める）
      K(12.75, 104, 38, -173, 170, -2.95, 1.24, 23.8),
    ],
  },
  // b2: next morning on the landing beach, looking in from the sea (south-east) so the shoreline runs across the screen;
  // the castaway (drawn by the compositor) lies at LIE
  b2: {
    from: 12.25, to: 19.45, keys: [
      K(12.25, LIE.x - 6, 3, LIE.z - 6, 230, 0.42, 1.10, 5.7),
      K(14.6, LIE.x - 3, 2.6, LIE.z - 3, 90, 0.58, 1.13, 6.0),
      K(16.4, LIE.x - 0.5, 2.2, LIE.z - 0.5, 42, 0.72, 1.12, 6.25),
      K(17.9, LIE.x, 2.0, LIE.z, 26, 0.84, 1.10, 6.5),
      K(19.45, LIE.x, 2.0, LIE.z, 24, 0.90, 1.10, 6.7),
    ],
  },
  // c: midday whole island (comments) -> top-down map -> candidate sites A/B/C -> map
  c: {
    from: 19.45, to: 19.45 + 548 / 24, keys: [
      K(19.45, 45, 10, 115, 1750, 0.55, 0.88, 10.5),
      K(23.5, 30, 10, 125, 1680, 0.30, 0.87, 11.5),
      K(25.6, 22, 10, 128, 1620, 0.18, 0.86, 12.0),
      K(27.2, -5, 10, 90, 1400, 0.08, 0.80, 12.4),
      K(29.2, 25, 6, 135, 1780, 0.0, 0.10, 13.0), // 地図ビュー
      K(31.5, 25, 6, 135, 1750, 0.0, 0.10, 13.4),
      K(32.6, 0, 8, 25, 280, 0.40, 0.98, 13.8), // A 平原
      K(34.4, 0, 8, 25, 250, 0.15, 1.02, 14.2),
      K(35.4, -36, 4, 160, 260, -0.30, 1.02, 14.6), // B 入り江
      K(36.7, -36, 4, 160, 235, -0.50, 1.05, 15.0),
      K(37.7, 232, 4, 118, 260, -1.20, 1.02, 15.4), // C 砂浜（島側から海を見る）
      K(39.2, 232, 4, 118, 235, -1.35, 1.05, 15.8),
      K(40.4, 25, 6, 135, 1780, 0.0, 0.10, 16.2), // 地図に戻る
      K(42.3, 25, 6, 135, 1750, 0.0, 0.10, 16.6),
    ],
  },
  // p: what the phone shows in the "see it in the app" part (film frames 1015-1247) — the island slowly orbiting.
  // Recorded at 540x960 (--half): it only ever fills a phone screen / a blurred backdrop.
  p: {
    from: 1015 / 24, to: 1248 / 24, keys: [
      K(42.29, 25, 10, 70, 1720, 0.95, 0.90, 9.5),
      K(47.0, 25, 10, 70, 1680, 0.78, 0.90, 12.0),
      K(52.0, 25, 10, 70, 1650, 0.62, 0.90, 14.5),
    ],
  },
  // d: sunset pull-back for the end title (dissolve from the phone part 51.5-52.0)
  d: {
    from: 51.5, to: 57.0, keys: [
      K(51.5, 20, 70, 0, 1500, 0.40, 1.40, 17.3),
      K(54.2, 20, 74, 0, 1560, 0.47, 1.42, 17.65),
      K(57.0, 20, 78, 0, 1620, 0.55, 1.44, 18.0),
    ],
  },
};

// world points whose screen position is exported per frame; y = 'g+N' means terrain height + N
export const POINTS = {
  beach: [228, 'g+12', 112], cove: [-31, 'g+16', 195], plain: [0, 'g+12', 19], forest: [-186, 'g+16', -46], highland: [104, 'g+10', -173],
  lie: [LIE.x, 'g+0', LIE.z],
  eye0: [-198, 'g+2.4', -54], eye1: [-182, 'g+2.4', -70], eye2: [-214, 'g+2.4', -38], eye3: [-170, 'g+2.4', -54], eye4: [-206, 'g+2.4', -74], eye5: [-226, 'g+2.4', -58],
  pinA: [0, 'g+0', 25], pinB: [-36, 'g+0', 156], pinC: [LANDING.x, 'g+0', LANDING.z],
  cPlain: [0, 'g+2', 25], cCove: [-31, 'g+2', 190], cForest: [-190, 'g+10', -46], cHigh: [104, 'g+4', -173], cBeach: [LANDING.x, 'g+2', LANDING.z],
};

// monotone cubic (PCHIP): continuous velocity, no overshoot past a keyframe value
function pchip(ts, ys, t) {
  const n = ts.length;
  if (t <= ts[0]) return ys[0];
  if (t >= ts[n - 1]) return ys[n - 1];
  const h = [], d = [];
  for (let i = 0; i < n - 1; i++) { h.push(ts[i + 1] - ts[i]); d.push((ys[i + 1] - ys[i]) / h[i]); }
  const m = new Array(n).fill(0);
  for (let i = 1; i < n - 1; i++) {
    if (d[i - 1] * d[i] > 0) { const w1 = 2 * h[i] + h[i - 1], w2 = h[i] + 2 * h[i - 1]; m[i] = (w1 + w2) / (w1 / d[i - 1] + w2 / d[i]); }
  }
  let i = 0;
  while (t > ts[i + 1]) i++;
  const s = (t - ts[i]) / h[i], s2 = s * s, s3 = s2 * s;
  return (2 * s3 - 3 * s2 + 1) * ys[i] + (s3 - 2 * s2 + s) * h[i] * m[i] + (-2 * s3 + 3 * s2) * ys[i + 1] + (s3 - s2) * h[i] * m[i + 1];
}

const FIELDS = ['tx', 'ty', 'tz', 'dist', 'az', 'pol', 'hour', 'fov'];
export function poseAt(shot, t) {
  const keys = SHOTS[shot].keys;
  const ts = keys.map((k) => k.t);
  const p = {};
  for (const f of FIELDS) {
    const ys = keys.map((k) => (f === 'dist' ? Math.log(k[f]) : k[f]));
    const v = pchip(ts, ys, t);
    p[f] = f === 'dist' ? Math.exp(v) : v;
  }
  // castaway's-eye bob while drifting at sea level (first seconds only)
  if (shot === 'a' && t < 3) p.ty += Math.sin(t * 3.1) * 3.2 * Math.max(0, 1 - t / 2.6);
  return p;
}
export const frameCount = (shot) => Math.round((SHOTS[shot].to - SHOTS[shot].from) * FPS);
