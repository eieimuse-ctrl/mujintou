// ep1 revision: camera keyframes (film seconds) for the three takes + tracked world points.
export const FPS = 24;
export const DURATION = 48.0;

// silhouette spot (east beach, on the sand by the waterline) — y is resolved from the terrain
export const SIL = { x: 95, z: 34.5 };

//            t      tx   ty  tz    dist  az     pol    hour
const K = (t, tx, ty, tz, dist, az, pol, hour, fov = 38) => ({ t, tx, ty, tz, dist, az, pol, hour, fov });
export const SHOTS = {
  // Take 1: dawn at sea level -> rise to the whole island -> one sweep through the five districts, a full day passing
  a: {
    from: 0, to: 12.75, keys: [
      K(0.0, 0, 6, 0, 640, 1.08, 1.56, 5.15),
      K(1.4, 0, 6, 0, 590, 1.05, 1.55, 5.75),
      K(3.5, 0, 6, 6, 560, 0.82, 0.98, 7.0),
      K(4.35, 2, 6, 8, 530, 0.76, 0.95, 7.6),
      K(5.2, 72, 3, 38, 64, 1.30, 1.20, 9.0), // 砂浜
      K(5.8, 66, 3, 42, 62, 1.18, 1.20, 10.0),
      K(6.45, -13, 2, 62, 74, 0.25, 1.15, 11.5), // 入り江
      K(6.9, -13, 3, 58, 72, 0.12, 1.16, 12.3),
      K(7.55, 0, 6, 5, 74, -0.55, 1.20, 14.0), // 平原
      K(8.0, -4, 6, 3, 72, -0.68, 1.21, 15.0),
      K(8.8, -58, 8, -16, 58, -1.35, 1.25, 18.3), // 森（夕方→夜）
      K(9.9, -64, 8, -20, 50, -1.55, 1.27, 20.6),
      K(10.75, 31, 16, -56, 86, -2.55, 1.30, 25.5), // 高原（深夜）
      K(12.75, 31, 17, -56, 72, -2.95, 1.24, 28.6),
    ],
  },
  // Take b: next morning on the east beach; the silhouette is composited at SIL
  b: {
    from: 12.25, to: 19.45, keys: [
      K(12.25, SIL.x - 8, 3, SIL.z, 125, 1.22, 1.10, 5.7),
      K(14.6, SIL.x - 3, 3, SIL.z, 72, 1.42, 1.24, 6.0),
      K(16.4, SIL.x, 3.5, SIL.z, 44, 1.60, 1.32, 6.25),
      // look-at height 3.6 (was 5.6/5.9): keeps the figure's feet above the subtitle band (y < 1300 px)
      K(17.9, SIL.x, 3.6, SIL.z, 28, 1.70, 1.37, 6.5),
      K(19.45, SIL.x, 3.6, SIL.z, 26, 1.78, 1.38, 6.7),
    ],
  },
  // Take 2: midday whole island (comments) -> top-down map -> candidate sites A/B/C -> map -> sunset pull-back
  c: {
    from: 19.45, to: 48.0, keys: [
      K(19.45, 21, 6, 42, 600, 0.55, 0.88, 10.5),
      K(23.5, 12, 6, 46, 570, 0.30, 0.87, 11.5),
      K(25.6, 7, 6, 47, 545, 0.18, 0.86, 12.0),
      K(27.2, 2, 6, 30, 430, 0.08, 0.80, 12.4),
      K(29.2, 0, 4, 45, 590, 0.0, 0.10, 13.0), // 地図ビュー
      K(31.5, 0, 4, 45, 580, 0.0, 0.10, 13.4),
      K(32.6, 0, 5, 8, 120, 0.40, 0.98, 13.8), // A 平原
      K(34.4, 0, 5, 8, 108, 0.15, 1.02, 14.2),
      K(35.4, -15, 3, 54, 105, -0.30, 1.02, 14.6), // B 入り江
      K(36.7, -15, 3, 54, 96, -0.50, 1.05, 15.0),
      K(37.7, 76, 3, 38, 105, -1.20, 1.02, 15.4), // C 砂浜（島側から海を見る）
      K(39.2, 76, 3, 38, 96, -1.35, 1.05, 15.8),
      K(40.4, 0, 4, 45, 590, 0.0, 0.10, 16.2), // 地図に戻る
      K(42.3, 0, 4, 45, 580, 0.0, 0.10, 16.6),
      K(45.2, 0, 40, 0, 500, 0.45, 1.40, 17.4), // 夕焼けの引き
      K(48.0, 0, 44, 0, 540, 0.55, 1.44, 18.0),
    ],
  },
  // ---- v2 (ep1_fable_v2.mp4) — added takes; a / b / c above are untouched so v1 stays reproducible ----
  // Take b2: replaces b. Same slot (12.25-19.45) but aimed at the waterline: the castaway now LIES on the lowest
  // sand step next to the water (LIE), body along the shoreline, and the camera looks in from the sea so that the
  // shoreline runs across the screen above the subtitle band.
  b2: {
    from: 12.25, to: 19.45, keys: [
      K(12.25, 93, 3, 36.5, 125, 0.72, 1.10, 5.7),
      K(14.6, 97, 2.6, 36.5, 72, 0.86, 1.13, 6.0),
      K(16.4, 99.5, 2.2, 36.5, 40, 0.98, 1.12, 6.25),
      K(17.9, 100, 2.0, 36.5, 25, 1.08, 1.10, 6.5),
      K(19.45, 100, 2.0, 36.5, 23, 1.14, 1.10, 6.7),
    ],
  },
  // Take d: continues c from its frame 548 (pose time 42.2833): map view held under the "link in profile" part,
  // then the sunset pull-back for the title, 5.7 s later than in v1. The first two keys repeat c's so the hand-over is smooth.
  d: {
    from: 19.45 + 548 / 24, to: 19.45 + 548 / 24 + 281 / 24, keys: [
      K(40.4, 0, 4, 45, 590, 0.0, 0.10, 16.2),
      K(42.3, 0, 4, 45, 580, 0.0, 0.10, 16.6),
      K(47.9, 0, 4, 45, 556, 0.0, 0.10, 16.9),
      K(50.9, 0, 40, 0, 500, 0.45, 1.40, 17.4),
      K(54.0, 0, 44, 0, 540, 0.55, 1.44, 18.0),
    ],
  },
  // Take p: what the phone mock-up shows in the "link in profile" part — the PWA's overview of the island, slowly
  // orbiting while a day goes by (morning -> late afternoon) = "you can look in at any time".
  p: {
    from: 44.5, to: 44.5 + 87 / 24, keys: [
      K(44.5, 6, 6, 30, 560, 0.95, 0.90, 6.6),
      K(46.3, 6, 6, 30, 548, 0.78, 0.90, 12.0),
      K(48.2, 6, 6, 30, 540, 0.62, 0.90, 17.3),
    ],
  },
};

// v2: where the castaway lies (centre of the body on the sand, heading of the head end in the x/z plane)
export const LIE = { x: 99, z: 36 };

// world points whose screen position is exported per frame; y = 'g+N' means terrain height + N
export const POINTS = {
  beach: [72, 'g+7', 38], cove: [-13, 'g+9', 62], plain: [0, 'g+7', 5], forest: [-60, 'g+10', -18], highland: [31, 'g+8', -56],
  silFeet: [SIL.x, 'g+0', SIL.z], silHead: [SIL.x, 'g+5', SIL.z],
  eye0: [-66, 'g+2.2', -22], eye1: [-58, 'g+2.2', -30], eye2: [-74, 'g+2.2', -14], eye3: [-52, 'g+2.2', -22], eye4: [-70, 'g+2.2', -32], eye5: [-80, 'g+2.2', -24],
  pinA: [0, 'g+0', 5], pinB: [-15, 'g+0', 52], pinC: [78, 'g+0', 38],
  cPlain: [0, 'g+2', 5], cCove: [-15, 'g+2', 54], cForest: [-61, 'g+8', -18], cHigh: [31, 'g+4', -56], cBeach: [78, 'g+2', 38],
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
  if (shot === 'a' && t < 3) p.ty += Math.sin(t * 3.1) * 1.1 * Math.max(0, 1 - t / 2.6);
  return p;
}
export const frameCount = (shot) => Math.round((SHOTS[shot].to - SHOTS[shot].from) * FPS);
