// 森の獣（6日目〜）：ボクセルのクマ（2026-11-22 本人が4案から選んだ）。
//   BEAST_BOXES：右（+x）が頭。高さの単位は島民（スプライトの高さ 3.9）と同じ。leg: true の箱は歩くと上下する（0/1 で左右の組）
const bx = (x, y, z, w, h, d, c, leg) => ({ p: [x, y, z], s: [w, h, d], c, ...(leg != null ? { leg } : {}) });
export const BEAST_BOXES = (() => {
  const F = '#2e2622', f = '#3f342e', M = '#d8c7a8', Y = '#ffe14a', N = '#111111', C = '#cfc6b8';
  const b = [];
  b.push(bx(0, 2.3, 0, 3.6, 2.8, 2.6, F), bx(-0.2, 3.8, 0, 2.6, 0.6, 2.2, f)); // 体・背中
  b.push(bx(2.3, 3.0, 0, 1.6, 1.6, 1.8, F), bx(3.25, 2.7, 0, 0.5, 0.7, 0.9, M), bx(3.55, 2.9, 0, 0.15, 0.25, 0.35, N)); // 頭・口元・鼻
  b.push(bx(1.95, 3.95, 0.65, 0.45, 0.45, 0.35, F), bx(1.95, 3.95, -0.65, 0.45, 0.45, 0.35, F)); // 耳
  b.push(bx(2.95, 3.3, 0.91, 0.3, 0.25, 0.05, Y), bx(2.95, 3.3, -0.91, 0.3, 0.25, 0.05, Y)); // 光る目
  b.push(bx(1.3, 2.3, 1.31, 1.0, 0.9, 0.05, M), bx(1.3, 2.3, -1.31, 1.0, 0.9, 0.05, M)); // 胸の模様
  for (const [x, z, leg] of [[-1.2, -0.85, 0], [1.1, 0.85, 0], [-1.2, 0.85, 1], [1.1, -0.85, 1]]) b.push(bx(x, 0.55, z, 0.9, 1.1, 0.8, F, leg)); // 脚
  for (const z of [-0.85, 0.85]) b.push(bx(1.6, 0.06, z, 0.25, 0.12, 0.8, C)); // 爪
  return b;
})();
export const BEAST_LEN = 4.4; // 体の長さ（向きの判定・タップの大きさ用）

// （以下は2Dの絵。今は使っていない）
// 森の獣（6日目〜）：森を切りひらいて住処を追われ、畑のまわりで島民を追いかけまわす。
// 茶色い毛のかたまりに、光る黄色い目と白い牙。正体はまだ分からない（PWA でも名前は出さない）。
// 2コマ（脚の運び）。右向きに描く。動画の録画（video-tools/ep3/lib/stage.js）でも同じ絵を使う。
export const BEAST_FRAMES = [
  [
    '.....kkk..kkk...........',
    '...kkFFFkkFFFkkk........',
    '..kFfFFFFFFfFFFFkk......',
    '.kFFFFfFFFFFFFfFFFkkk...',
    'kFfFFFFFFfFFFFFFFFFFFkk.',
    'kFFFFfFFFFFFFfFFFFkYYFk.',
    'kFFFFFFFFfFFFFFFFFkYrFFk',
    'kFfFFFFFFFFFFFFFFFFFFFFk',
    '.kFFFFfFFFFFFfFFFFFFPPPk',
    '.kFFFFFFFFFFFFFFFFFWPnPk',
    '..kFFFkkFFFFFFFkkFFkWkk.',
    '..kFFk.kFFk..kFFk.kFFk..',
    '..kkk...kkk...kkk..kkk..',
  ],
  [
    '.....kkk..kkk...........',
    '...kkFFFkkFFFkkk........',
    '..kFfFFFFFFfFFFFkk......',
    '.kFFFFfFFFFFFFfFFFkkk...',
    'kFfFFFFFFfFFFFFFFFFFFkk.',
    'kFFFFfFFFFFFFfFFFFkYYFk.',
    'kFFFFFFFFfFFFFFFFFkYrFFk',
    'kFfFFFFFFFFFFFFFFFFFFFFk',
    '.kFFFFfFFFFFFfFFFFFFPPPk',
    '.kFFFFFFFFFFFFFFFFFWPnPk',
    '..kFFFFkFFFFFFFFkFFFWk..',
    '.kFFk.kFFk..kFFk..kFFk..',
    '.kkk...kkk..kkk...kkk...',
  ],
];
export const BEAST_PAL = { k: '#1a1012', F: '#6b4a34', f: '#8a6547', Y: '#ffe14a', r: '#d8322a', P: '#c98a7a', n: '#3a2224', W: '#fffaf0' };

export function beastCanvas() {
  const rows0 = BEAST_FRAMES[0];
  const w = rows0[0].length, h = rows0.length;
  const c = document.createElement('canvas');
  c.width = w * BEAST_FRAMES.length;
  c.height = h;
  const g = c.getContext('2d');
  BEAST_FRAMES.forEach((rows, f) => rows.forEach((r, y) => [...r].forEach((ch, x) => {
    if (BEAST_PAL[ch]) { g.fillStyle = BEAST_PAL[ch]; g.fillRect(f * w + x, y, 1, 1); }
  })));
  return c;
}

// 獣の位置（時刻だけで決まる。どの端末でも同じ場所に見える）：中心のまわりを、ゆがんだ輪を描いてうろつく
export function beastPose(b, tMs) {
  const t = tMs / 1000;
  const a = t * 0.11 + Math.sin(t * 0.037) * 1.6;
  const r = b.r * (0.55 + 0.35 * Math.sin(t * 0.071 + 1.3));
  const x = b.x + Math.cos(a) * r;
  const z = b.z + Math.sin(a) * r * 0.8;
  const a2 = a + 0.05;
  const r2 = b.r * (0.55 + 0.35 * Math.sin((t + 0.45) * 0.071 + 1.3));
  return { x, z, dx: b.x + Math.cos(a2) * r2 - x, dz: b.z + Math.sin(a2) * r2 * 0.8 - z };
}
