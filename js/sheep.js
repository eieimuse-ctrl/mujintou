// もこもこのひつじ（10日目〜、島のいいね1000で流れ着いた）：ボクセルのひつじの群れ。
//   SHEEP_BOXES：右（+x）が頭。高さの単位は島民（スプライトの高さ 3.9）と同じ。leg（0/1）の箱は歩くと上下する
//   sheepPose(flock, k, tMs)：群れの中の k 頭目の位置。決まった時刻なら、どの端末でも同じ所にいる
const bx = (x, y, z, w, h, d, c, leg) => ({ p: [x, y, z], s: [w, h, d], c, ...(leg != null ? { leg } : {}) });
export const SHEEP_BOXES = (() => {
  const W = '#f4f1ea', W2 = '#e2ddd2', F = '#3a3330', P = '#f0b8b8';
  const b = [];
  b.push(bx(0, 1.55, 0, 2.6, 1.6, 1.9, W), bx(-0.4, 2.45, 0, 1.8, 0.5, 1.5, W2), bx(0.6, 2.4, 0.3, 0.9, 0.4, 0.9, W)); // もこもこの体
  b.push(bx(1.6, 1.95, 0, 0.9, 0.95, 0.9, F), bx(1.55, 2.5, 0, 0.75, 0.35, 0.95, W)); // 顔・頭の毛
  b.push(bx(1.45, 2.05, 0.6, 0.35, 0.2, 0.3, F), bx(1.45, 2.05, -0.6, 0.35, 0.2, 0.3, F)); // 耳
  b.push(bx(2.06, 2.1, 0.22, 0.05, 0.14, 0.14, '#ffffff'), bx(2.06, 2.1, -0.22, 0.05, 0.14, 0.14, '#ffffff'), bx(2.06, 1.75, 0, 0.05, 0.12, 0.3, P)); // 目・鼻
  for (const [x, z, leg] of [[-0.85, -0.55, 0], [0.8, 0.55, 0], [-0.85, 0.55, 1], [0.8, -0.55, 1]]) b.push(bx(x, 0.4, z, 0.4, 0.8, 0.4, F, leg));
  return b;
})();
export const SHEEP_LEN = 2.8;

const h01 = (n) => { let x = (n | 0) * 2654435761; x ^= x >>> 13; x = Math.imul(x, 1274126177); return ((x ^ (x >>> 16)) >>> 0) / 4294967296; };
// 群れの中心のまわりを、それぞれゆっくり歩いては草を食べる（止まる）
export function sheepPose(flock, k, tMs) {
  const t = tMs / 1000, r = flock.r || 12;
  const a0 = h01(k * 7 + 1) * Math.PI * 2, r0 = r * (0.3 + 0.7 * Math.sqrt(h01(k * 13 + 5)));
  const per = 40 + h01(k * 3 + 2) * 40; // 何秒で1か所ぶん動くか
  const seg = Math.floor(t / per), u = (t % per) / per;
  const p = (s) => { const a = a0 + (h01(k * 31 + s) - 0.5) * 2.2, rr = r0 * (0.6 + 0.6 * h01(k * 17 + s * 3)); return { x: flock.x + Math.cos(a) * rr, z: flock.z + Math.sin(a) * rr * 0.8 }; };
  const A = p(seg), B = p(seg + 1);
  const w = Math.max(0, Math.min(1, (u - 0.7) / 0.3)); // 7割は草を食べて、のこりで次へ歩く
  const e = w * w * (3 - 2 * w);
  return { x: A.x + (B.x - A.x) * e, z: A.z + (B.z - A.z) * e, dx: B.x - A.x, dz: B.z - A.z, still: w <= 0 || w >= 1, graze: w <= 0 };
}
