// ep2 (2日目アニメーション, ep2_post.mp4): film timeline, 24 fps, 45.6 s.
// Camera keys per take (film seconds). ty may be 'g+N' (ground at tx,tz + N); tx/tz may be 'saka' / 'C' anchors
// resolved by ep2_rec.mjs from the stage (env). The islander script lives in ep2_rec.mjs (in-page).
export const FPS = 24;
export const DURATION = 45.6;
export const LANDING = { x: 236, z: 124 };
const N = Math.hypot(LANDING.x, LANDING.z);
export const NX = LANDING.x / N, NZ = LANDING.z / N; // offshore direction
const AZ_SEA = Math.atan2(NX, NZ); // camera on the sea side looking at the island

const K = (t, tx, ty, tz, dist, az, pol, hour, fov = 38) => ({ t, tx, ty, tz, dist, az, pol, hour, fov });
export const SHOTS = {
  // L: dawn, behind the 52 drifters, they float in to the beach (landing set: 52 drifters, 0 islanders)
  L: { set: 'landing', from: 10.3, to: 15.6, keys: [
    K(10.3, LANDING.x + NX * 44, 0.6, LANDING.z + NZ * 44, 118, AZ_SEA, 1.36, 5.2, 50),
    K(12.9, LANDING.x + NX * 38, 0.6, LANDING.z + NZ * 38, 104, AZ_SEA + 0.02, 1.33, 5.5, 50),
    K(15.6, LANDING.x + NX * 12, 1.0, LANDING.z + NZ * 12, 66, AZ_SEA + 0.06, 1.25, 6.0, 50),
  ] },
  // B: on the beach — everyone washed up, standing and cheering at the waterline
  B: { from: 15.6, to: 17.2, keys: [
    K(15.6, 'beachX', 'g+1.6', 'beachZ', 50, AZ_SEA + 0.10, 1.22, 6.3, 44),
    K(17.2, 'beachX', 'g+1.6', 'beachZ', 41, AZ_SEA + 0.18, 1.20, 6.5, 44),
  ] },
  // P: the base on the plain (empty plaza) -> islanders walk in -> さか close-up -> pull back to the whole island
  P: { from: 17.2, to: 27.0, keys: [
    K(17.2, 'Cx', 'g+0', 'Cz', 560, 0.55, 0.55, 8.6),
    K(19.4, 'Cx', 'g+0', 'Cz', 250, 0.50, 0.86, 8.9),
    K(22.0, 'Cx', 'g+1', 'Cz', 92, 0.46, 1.05, 9.2),
    K(23.9, 'Cx', 'g+1', 'Cz', 70, 0.45, 1.10, 9.4),
    K(24.7, 'sakaX', 'g+2.2', 'sakaZ', 26, 0.45, 1.18, 9.5),
    K(25.85, 'sakaX', 'g+2.2', 'sakaZ', 15, 0.45, 1.22, 9.6),
    K(27.0, 12, 'g+0', 12, 900, 0.40, 0.72, 9.8),
  ] },
  // H: hungry islanders at the plaza (close) -> rise for the question title
  H: { from: 27.0, to: 32.0, keys: [
    K(27.0, 'hungX', 'g+1.6', 'hungZ', 30, 0.95, 1.16, 11.0),
    K(28.2, 'hungX', 'g+1.6', 'hungZ', 27, 1.0, 1.16, 11.2),
    K(32.0, 'Cx', 'g+2', 'Cz', 62, 1.25, 1.02, 11.8),
  ] },
  // QB/QC/QD: the three options — A fish at the cove shore, B a field on the meadow, C the forest edge
  QB: { from: 32.0, to: 34.7, keys: [
    K(32.0, 'fishX', 'g+1', 'fishZ', 38, 'fishAz', 1.13, 12.5),
    K(34.7, 'fishX', 'g+1', 'fishZ', 30, 'fishAz2', 1.10, 12.7),
  ] },
  QC: { from: 34.7, to: 36.95, keys: [
    K(34.7, 'farmX', 'g+1', 'farmZ', 38, 0.60, 1.12, 13.0),
    K(36.95, 'farmX', 'g+1', 'farmZ', 30, 0.75, 1.10, 13.2),
  ] },
  QD: { from: 36.95, to: 39.55, keys: [
    K(36.95, 'woodX', 'g+1.5', 'woodZ', 40, 'woodAz', 1.15, 13.6),
    K(39.55, 'woodX', 'g+1.5', 'woodZ', 32, 'woodAz2', 1.12, 13.8),
  ] },
  // QE: the island from above while the A/B/C list and 「コメントで教えてね」 are on screen
  QE: { from: 39.55, to: 42.1, keys: [
    K(39.55, 15, 'g+0', 40, 700, 0.35, 0.62, 14.5),
    K(42.1, 15, 'g+0', 40, 800, 0.42, 0.66, 15.0),
  ] },
  // E: sunset pull-back for the end card (as ep1 d)
  E: { from: 42.1, to: 45.6, keys: [
    K(42.1, 20, 70, 0, 1500, 0.40, 1.40, 17.3),
    K(45.6, 20, 76, 0, 1600, 0.50, 1.43, 17.8),
  ] },
  // p2: the island inside the phone (hook, 0-8 s), recorded at 540x960 (--half)
  p2: { from: 0.0, to: 8.0, half: true, keys: [
    K(0.0, 25, 10, 70, 1720, 0.95, 0.90, 10.0),
    K(8.0, 25, 10, 70, 1660, 0.75, 0.90, 10.6),
  ] },
};

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
// keys already resolved to numbers (resolveKeys)
export function poseAt(keys, t) {
  const ts = keys.map((k) => k.t);
  const p = {};
  for (const f of FIELDS) {
    const ys = keys.map((k) => (f === 'dist' ? Math.log(k[f]) : k[f]));
    const v = pchip(ts, ys, t);
    p[f] = f === 'dist' ? Math.exp(v) : v;
  }
  return p;
}
export const frameCount = (shot) => Math.round((SHOTS[shot].to - SHOTS[shot].from) * FPS);
