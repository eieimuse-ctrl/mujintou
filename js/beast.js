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
