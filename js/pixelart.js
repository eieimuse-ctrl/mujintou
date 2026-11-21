// 画像ファイルを使わず、Canvas でドット絵のテクスチャ／スプライト／アイコンを生成する。

import { mulberry32, hashStr } from './rng.js';
import { JOBS, DEFAULT_JOB } from './config.js';

export function makeCanvas(w, h) {
  const c = document.createElement('canvas');
  c.width = w;
  c.height = h;
  return c;
}

const INK = '#231d36';

// 文字の並びでドット絵を描く（'.' は透明）
function drawBitmap(ctx, rows, palette, ox = 0, oy = 0) {
  rows.forEach((row, y) => {
    for (let x = 0; x < row.length; x++) {
      const col = palette[row[x]];
      if (!col) continue;
      ctx.fillStyle = col;
      ctx.fillRect(ox + x, oy + y, 1, 1);
    }
  });
}

export function shade(hex, amount) {
  // amount: -1（黒）〜 +1（白）
  const m = /^#?([0-9a-f]{6})$/i.exec(String(hex).trim());
  const v = m ? parseInt(m[1], 16) : 0x888888;
  const ch = [(v >> 16) & 255, (v >> 8) & 255, v & 255].map((c) => {
    const t = amount < 0 ? 0 : 255;
    return Math.round(c + (t - c) * Math.abs(amount));
  });
  return `#${ch.map((c) => c.toString(16).padStart(2, '0')).join('')}`;
}

export function normalizeColor(value, fallback = '#4a90d9') {
  const s = String(value || '').trim();
  if (/^#[0-9a-f]{6}$/i.test(s)) return s.toLowerCase();
  if (/^#[0-9a-f]{3}$/i.test(s)) return `#${s[1]}${s[1]}${s[2]}${s[2]}${s[3]}${s[3]}`.toLowerCase();
  return fallback;
}

// ---- 地形・箱・海のテクスチャ ----------------------------------------------

export const TILE = 8;
export const ATLAS_ROWS = { grass: 0, sand: 1, rock: 2, dirt: 3 };

// 4種×4バリエーションの明暗タイル（頂点カラーに掛け合わせて使う）
export function terrainAtlas() {
  const c = makeCanvas(TILE * 4, TILE * 4);
  const ctx = c.getContext('2d');
  const rnd = mulberry32(8128);
  const gray = (v) => `rgb(${v},${v},${v})`;
  const specs = [
    { base: 234, dark: [0.15, 204], light: [0.08, 255] },
    { base: 240, dark: [0.07, 216], light: [0.05, 255] },
    { base: 230, dark: [0.13, 194], light: [0.07, 252] },
    { base: 232, dark: [0.12, 200], light: [0.04, 250] },
  ];
  specs.forEach((sp, row) => {
    for (let v = 0; v < 4; v++) {
      for (let y = 0; y < TILE; y++) {
        for (let x = 0; x < TILE; x++) {
          const r = rnd();
          let g = sp.base;
          if (row === 3 && y % 4 === 3) g = 214; // 土の層
          if (r < sp.dark[0]) g = sp.dark[1];
          else if (r > 1 - sp.light[0]) g = sp.light[1];
          ctx.fillStyle = gray(g);
          ctx.fillRect(v * TILE + x, row * TILE + y, 1, 1);
        }
      }
      if (row === 0) {
        // 草の葉先
        for (let n = 0; n < 2; n++) {
          const x = 1 + Math.floor(rnd() * 6);
          const y = 1 + Math.floor(rnd() * 5);
          ctx.fillStyle = gray(196);
          ctx.fillRect(v * TILE + x, row * TILE + y, 1, 2);
          ctx.fillStyle = gray(255);
          ctx.fillRect(v * TILE + x + 1, row * TILE + y, 1, 1);
        }
      }
      if (row === 2) {
        // 岩のひび
        let x = Math.floor(rnd() * 5);
        for (let y = 1; y < 7; y++) {
          ctx.fillStyle = gray(178);
          ctx.fillRect(v * TILE + x, row * TILE + y, 1, 1);
          if (rnd() < 0.5) x = Math.min(7, x + 1);
        }
      }
    }
  });
  return c;
}

export function voxelTexture() {
  const c = makeCanvas(8, 8);
  const ctx = c.getContext('2d');
  const rnd = mulberry32(4242);
  for (let y = 0; y < 8; y++) {
    for (let x = 0; x < 8; x++) {
      const r = rnd();
      const g = r < 0.14 ? 212 : r > 0.92 ? 255 : 238;
      ctx.fillStyle = `rgb(${g},${g},${g})`;
      ctx.fillRect(x, y, 1, 1);
    }
  }
  return c;
}

export function waterTexture() {
  const S = 32;
  const c = makeCanvas(S, S);
  const ctx = c.getContext('2d');
  ctx.fillStyle = '#3aa7e0';
  ctx.fillRect(0, 0, S, S);
  const rnd = mulberry32(777);
  for (let n = 0; n < 26; n++) {
    const x = Math.floor(rnd() * S);
    const y = Math.floor(rnd() * S);
    const w = 2 + Math.floor(rnd() * 4);
    ctx.fillStyle = n % 3 === 0 ? '#2f93cf' : '#8fdcf5';
    for (let k = 0; k < w; k++) ctx.fillRect((x + k) % S, y, 1, 1);
    if (n % 4 === 0) ctx.fillRect((x + 1) % S, (y + 1) % S, Math.max(1, w - 2), 1);
  }
  return c;
}

// ---- 島民スプライト ---------------------------------------------------------

export const FRAME_W = 18;
export const FRAME_H = 24;
// sit / shock / eat は動画の演技用（PWA の暮らしでは使わない）
export const FRAMES = { idle: 0, walkA: 1, walkB: 2, workA: 3, workB: 4, cheer: 5, sit: 6, shock: 7, eat: 8 };
export const FRAME_COUNT = 9;

const SKIN = ['#f6c9a0', '#e8b088', '#c98c62', '#f9d8b8', '#a8714a', '#7d5236'];
const HAIR = ['#2b2118', '#4a2f1b', '#1f1f2e', '#7a4a24', '#b5803a', '#3b2a3f', '#c9c3b8', '#d9503f', '#3f6fb5', '#e7c766'];
const PANTS = ['#3a4466', '#5a4636', '#4b5a3c', '#3d3d48', '#7a3b3b', '#2f5f5f', '#c9b48a'];
const ACCENT = ['#e8504a', '#f0b43c', '#4fa3e0', '#57b86b', '#b07ad6', '#f2f2f2', '#2b2b38'];
const WOODC = '#8f5f38';
const METAL = '#b9bcc7';
const STONE_TOOL = '#8a8c94'; // 石の道具（5日目から。state.toolAge = 'stone'）
const HAIR_STYLES = 10;

// 見た目は ID のハッシュから決まる（同じ人はいつも同じ姿）。帽子は仕事の帽子をかぶる人とかぶらない人がいる。
export function islanderLook(person) {
  const hsh = hashStr(String(person.id));
  const h2 = hashStr(String(person.id) + '#look');
  const job = JOBS[person.job] || DEFAULT_JOB;
  const shirt = normalizeColor(person.color);
  const pick = (arr, n) => arr[n % arr.length];
  const jobHat = job.hat && job.hat !== 'none' && (h2 % 100) < 45;
  const ownHats = ['none', 'none', 'none', 'cap', 'beanie', 'ribbon', 'flower', 'bandana'];
  return {
    shirt,
    shirtDark: shade(shirt, -0.28),
    shirtLight: shade(shirt, 0.35),
    skin: pick(SKIN, hsh),
    hair: pick(HAIR, (hsh >>> 4) + ((h2 >>> 20) % 3 === 0 ? 5 : 0)),
    pants: pick(PANTS, hsh >>> 8),
    accent: pick(ACCENT, h2 >>> 3),
    hairStyle: (hsh >>> 12) % HAIR_STYLES,
    hat: jobHat ? job.hat : pick(ownHats, h2 >>> 7),
    metal: person.toolAge === 'stone' ? STONE_TOOL : METAL,
    tool: person.today?.tool || job.tool, // きょうの行動で道具を持つことがある（釣り竿など）
    glasses: (h2 >>> 11) % 5 === 0,
    beard: (h2 >>> 13) % 6 === 0,
    blush: (h2 >>> 15) % 4 === 0,
    brows: (h2 >>> 17) % 3 === 0,
    pattern: ['plain', 'plain', 'stripe', 'overalls', 'scarf', 'tank'][(h2 >>> 22) % 6],
    pack: (h2 >>> 26) % 5 === 0,
    short: (h2 >>> 28) % 4 === 0,
  };
}

// 1コマ描く（右向き）。grid は 16×22、px(x, y, color) で点を打つ。
function drawPose(px0, look, frame) {
  const { shirt, shirtDark, skin, hair, pants } = look;
  const SHOE = '#2b2540';
  // 背の低い人：上半身を1段下げる（足もとの位置は同じ）
  const px = look.short ? (x, y, c) => px0(x, y <= 17 ? y + 1 : y, c) : px0;
  const rect = (x0, y0, x1, y1, c) => {
    for (let y = y0; y <= y1; y++) for (let x = x0; x <= x1; x++) px(x, y, c);
  };
  const rect0 = (x0, y0, x1, y1, c) => {
    for (let y = y0; y <= y1; y++) for (let x = x0; x <= x1; x++) px0(x, y, c);
  };
  const sit = frame === FRAMES.sit;

  // 脚（座りは前に投げ出す）
  if (sit) {
    rect0(5, 18, 12, 19, pants);
    rect0(13, 18, 14, 19, SHOE);
  } else {
    rect(5, 16, 10, 17, pants);
    const legs = (lLen, rLen) => {
      rect0(5, 18, 6, 18 + lLen - 1, pants);
      rect0(5, 18 + lLen, 7, 18 + lLen, SHOE);
      rect0(9, 18, 10, 18 + rLen - 1, pants);
      rect0(9, 18 + rLen, 11, 18 + rLen, SHOE);
    };
    if (frame === FRAMES.walkA) legs(2, 3);
    else if (frame === FRAMES.walkB) legs(3, 2);
    else legs(3, 3);
  }
  // 座ると全体が3段下がる
  const dy = sit ? 3 : 0;
  const P = (x, y, c) => px(x, y + dy, c);
  const R = (x0, y0, x1, y1, c) => {
    for (let y = y0; y <= y1; y++) for (let x = x0; x <= x1; x++) P(x, y, c);
  };
  if (sit) R(5, 13, 10, 14, pants);

  // リュック（背中側）
  if (look.pack) {
    R(2, 10, 3, 14, '#8a5a34');
    P(2, 11, '#6e4526');
  }

  // 胴
  R(4, 10, 11, 15, shirt);
  R(4, 15, 11, 15, shirtDark);
  P(4, 10, null);
  P(11, 10, null);
  if (look.pattern === 'stripe') {
    R(4, 11, 11, 11, look.shirtLight);
    R(4, 13, 11, 13, look.shirtLight);
  } else if (look.pattern === 'overalls') {
    R(5, 13, 10, 15, pants);
    P(5, 11, pants); P(5, 12, pants); P(10, 11, pants); P(10, 12, pants);
  } else if (look.pattern === 'scarf') {
    R(5, 10, 10, 10, look.accent);
    P(10, 11, look.accent); P(10, 12, look.accent);
  } else if (look.pattern === 'tank') {
    P(5, 10, skin); P(10, 10, skin);
  }

  // 頭
  R(5, 6, 11, 8, skin);
  R(6, 9, 10, 9, skin);
  const hs = look.hairStyle;
  if (hs === 6) {
    // 坊主
    R(5, 4, 10, 4, hair);
    R(5, 5, 11, 5, skin);
    P(4, 5, hair); P(4, 6, hair);
  } else if (hs === 7) {
    // アフロ
    R(4, 1, 11, 2, hair);
    R(3, 3, 12, 5, hair);
    R(3, 6, 4, 8, hair);
    P(12, 6, hair);
  } else {
    R(5, 3, 10, 3, hair);
    R(4, 4, 11, 5, hair);
    R(4, 6, 4, 7, hair);
  }
  // 目
  P(8, 7, INK);
  P(10, 7, INK);
  if (hs === 1) {
    // 長い髪
    R(4, 6, 4, 11, hair);
    R(3, 7, 3, 10, hair);
  } else if (hs === 2) {
    R(4, 6, 5, 8, hair);
    P(11, 6, hair);
  } else if (hs === 3) {
    // ポニーテール
    R(3, 5, 3, 6, hair);
    R(2, 6, 2, 10, hair);
  } else if (hs === 4) {
    // おだんご
    R(6, 1, 9, 2, hair);
  } else if (hs === 5) {
    // ツンツン
    P(5, 2, hair); P(7, 2, hair); P(9, 2, hair); P(11, 3, hair);
  } else if (hs === 8) {
    // ボブ
    R(4, 6, 4, 9, hair);
    R(11, 6, 11, 7, hair);
  } else if (hs === 9) {
    // ふたつ結び
    R(3, 6, 3, 9, hair);
    P(2, 9, hair);
    R(12, 6, 12, 9, hair);
    P(13, 9, hair);
  }
  // 顔のちがい
  if (look.brows) {
    P(8, 6, hair); P(10, 6, hair);
  }
  if (look.glasses) {
    R(7, 7, 11, 7, INK);
    P(8, 7, '#bfe6f2'); P(10, 7, '#bfe6f2');
  }
  if (look.blush) P(11, 8, '#f08a8a');
  if (look.beard) {
    R(6, 9, 10, 9, hair);
    P(11, 8, hair);
  }
  // 驚き・食べるときの口
  if (frame === FRAMES.shock) {
    P(9, 9, INK);
    P(8, 6, INK); P(10, 6, INK);
  }

  // 帽子
  switch (look.hat) {
    case 'headband':
      R(4, 5, 11, 5, '#f4efe2');
      P(3, 5, '#f4efe2');
      P(3, 6, '#d8d2c4');
      break;
    case 'straw':
      R(5, 3, 10, 3, '#f0d98a');
      R(4, 4, 11, 4, '#d9503f');
      R(2, 5, 13, 5, '#e2c56a');
      break;
    case 'helmet':
      R(5, 3, 10, 3, '#f7cf3c');
      R(4, 4, 11, 5, '#f2c230');
      P(12, 5, '#d9a91f');
      R(7, 3, 8, 4, '#fff3b0');
      break;
    case 'safari':
      R(5, 3, 10, 3, '#b98448');
      R(5, 4, 10, 4, '#6e4526');
      R(3, 5, 12, 5, '#9c6a37');
      break;
    case 'chef':
      R(4, 0, 11, 1, '#ffffff');
      R(5, 2, 10, 3, '#ffffff');
      R(5, 4, 10, 4, '#d8d2c4');
      break;
    case 'cap':
      R(5, 3, 10, 4, look.accent);
      R(10, 5, 13, 5, shade(look.accent, -0.25));
      break;
    case 'beanie':
      R(5, 2, 10, 2, look.accent);
      R(4, 3, 11, 5, look.accent);
      R(4, 5, 11, 5, shade(look.accent, -0.25));
      P(7, 1, '#f4efe2');
      break;
    case 'ribbon':
      P(4, 3, look.accent); P(5, 4, look.accent); P(3, 4, look.accent); P(4, 5, look.accent);
      break;
    case 'flower':
      P(10, 3, '#ffffff'); P(9, 3, '#f6d34a'); P(11, 3, '#ffffff'); P(10, 2, '#ffffff'); P(10, 4, '#ffffff');
      break;
    case 'bandana':
      R(4, 4, 11, 5, look.accent);
      P(3, 6, look.accent); P(3, 7, look.accent);
      break;
    default:
      if (hs === 2) R(7, 2, 8, 2, hair);
  }

  // 腕と道具
  const tool = look.tool;
  const armC = look.pattern === 'tank' ? skin : shirt;
  const armD = look.pattern === 'tank' ? skin : shirtDark;
  const backArm = (len) => {
    R(3, 10, 3, 10 + Math.min(1, len - 1), armD);
    if (len > 2) R(3, 12, 3, 9 + len, skin);
  };
  const frontArm = (len) => {
    R(12, 10, 12, 11, armC);
    if (len > 2) R(12, 12, 12, 9 + len, skin);
  };

  if (frame === FRAMES.cheer) {
    P(3, 10, armD); P(2, 9, armD); P(2, 8, skin); P(2, 7, skin);
    P(12, 10, armC); P(13, 9, armC); P(13, 8, skin); P(13, 7, skin);
  } else if (frame === FRAMES.shock) {
    // 両手を横に広げてのけぞる
    P(3, 10, armD); P(2, 10, armD); P(1, 9, skin);
    P(12, 10, armC); P(13, 10, armC); P(14, 9, skin);
  } else if (frame === FRAMES.eat) {
    // 手を口もとへ（実を食べる・水を飲む）
    backArm(4);
    P(12, 10, armC); P(12, 9, armC); P(11, 9, skin); P(12, 8, '#d94a5a');
  } else if (frame === FRAMES.workA) {
    backArm(4);
    P(12, 10, armC); P(13, 9, armC); P(13, 8, skin);
    if (tool === 'scope') {
      R(11, 7, 14, 7, '#c9973f');
      P(15, 7, '#8fdcec');
    } else {
      P(14, 7, skin);
      if (tool === 'rod') {
        P(14, 6, WOODC); P(15, 5, WOODC); P(15, 4, WOODC); P(15, 3, WOODC); P(15, 2, '#f4efe2');
      } else if (tool === 'hammer') {
        R(14, 4, 14, 6, WOODC);
        R(13, 2, 15, 3, look.metal);
      } else if (tool === 'hoe') {
        R(14, 3, 14, 6, WOODC);
        R(14, 2, 15, 2, look.metal);
        P(15, 3, look.metal);
      } else if (tool === 'ladle') {
        R(14, 5, 14, 6, WOODC);
        R(13, 3, 15, 4, look.metal);
      }
    }
  } else if (frame === FRAMES.workB) {
    backArm(4);
    R(12, 10, 12, 11, armC);
    P(13, 12, skin); P(14, 12, skin);
    if (tool === 'scope') {
      R(13, 11, 15, 11, '#c9973f');
    } else if (tool === 'rod') {
      P(15, 11, WOODC); P(15, 10, WOODC); P(15, 9, WOODC); P(15, 8, '#f4efe2');
    } else if (tool === 'hammer') {
      R(15, 12, 15, 14, WOODC);
      R(14, 15, 15, 16, look.metal);
    } else if (tool === 'hoe') {
      R(15, 12, 15, 16, WOODC);
      R(13, 17, 15, 17, look.metal);
    } else if (tool === 'ladle') {
      R(15, 12, 15, 14, WOODC);
      R(14, 15, 15, 16, look.metal);
    }
  } else if (frame === FRAMES.walkA) {
    backArm(4);
    frontArm(3);
  } else if (frame === FRAMES.walkB) {
    backArm(3);
    frontArm(4);
  } else {
    backArm(4);
    frontArm(sit ? 3 : 4);
  }
}

// ふちどり（透明で、となりに色があるマスを塗る）
function outlineRegion(ctx, ox, oy, w, h, color = INK) {
  const img = ctx.getImageData(ox, oy, w, h);
  const d = img.data;
  const solid = (x, y) => x >= 0 && y >= 0 && x < w && y < h && d[(y * w + x) * 4 + 3] > 0;
  const edge = [];
  for (let y = 0; y < h; y++) {
    for (let x = 0; x < w; x++) {
      if (solid(x, y)) continue;
      if (solid(x - 1, y) || solid(x + 1, y) || solid(x, y - 1) || solid(x, y + 1)) edge.push(x, y);
    }
  }
  ctx.fillStyle = color;
  for (let n = 0; n < edge.length; n += 2) ctx.fillRect(ox + edge[n], oy + edge[n + 1], 1, 1);
}

// 横6コマ×縦2段（上段＝右向き、下段＝左向き）
export function islanderAtlas(person) {
  const look = islanderLook(person);
  const c = makeCanvas(FRAME_W * FRAME_COUNT, FRAME_H * 2);
  const ctx = c.getContext('2d', { willReadFrequently: true });
  for (let row = 0; row < 2; row++) {
    for (let f = 0; f < FRAME_COUNT; f++) {
      const ox = f * FRAME_W;
      const oy = row * FRAME_H;
      const px = (x, y, color) => {
        const gx = row === 0 ? x : 15 - x;
        if (gx < 0 || gx > 15 || y < 0 || y > 21) return;
        if (color === null) ctx.clearRect(ox + 1 + gx, oy + 1 + y, 1, 1);
        else {
          ctx.fillStyle = color;
          ctx.fillRect(ox + 1 + gx, oy + 1 + y, 1, 1);
        }
      };
      drawPose(px, look, f);
      outlineRegion(ctx, ox, oy, FRAME_W, FRAME_H);
    }
  }
  return c;
}

// 一覧・詳細用の顔つき全身アイコン（拡大は CSS の pixelated に任せる）
export function islanderPortrait(person, atlas = islanderAtlas(person)) {
  const c = makeCanvas(FRAME_W, FRAME_H);
  c.getContext('2d').drawImage(atlas, 0, 0, FRAME_W, FRAME_H, 0, 0, FRAME_W, FRAME_H);
  c.className = 'portrait';
  return c;
}

// ---- 吹き出し ---------------------------------------------------------------

const BUBBLE_ICONS = {
  talk: { rows: ['.......', '.......', '.......', 'K..K..K', '.......', '.......', '.......'], pal: { K: INK } },
  heart: { rows: ['.RR.RR.', 'RPRRRRR', 'RRRRRRR', '.RRRRR.', '..RRR..', '...R...', '.......'], pal: { R: '#e8475f', P: '#ffb3c0' } },
  note: { rows: ['...BBBB', '...B..B', '...B..B', '...B..B', '.BBB.BB', 'BBBB.BB', '.BB....'], pal: { B: '#2f7fd0' } },
  bolt: { rows: ['...YYY.', '..YYY..', '.YYYYY.', '...YYY.', '..YYY..', '.YY....', '.Y.....'], pal: { Y: '#f08a1d' } },
};

export const BUBBLE_W = 15;
export const BUBBLE_H = 14;
export function bubbleCanvas(icon) {
  const c = makeCanvas(BUBBLE_W, BUBBLE_H);
  const ctx = c.getContext('2d');
  ctx.fillStyle = INK;
  ctx.fillRect(1, 0, 13, 11);
  ctx.fillRect(0, 1, 15, 9);
  ctx.fillStyle = '#ffffff';
  ctx.fillRect(1, 1, 13, 9);
  ctx.fillStyle = INK;
  ctx.fillRect(5, 11, 3, 1);
  ctx.fillRect(5, 12, 2, 1);
  ctx.fillRect(5, 13, 1, 1);
  ctx.fillStyle = '#ffffff';
  ctx.fillRect(6, 10, 2, 1);
  ctx.fillRect(6, 11, 1, 1);
  const ic = BUBBLE_ICONS[icon] || BUBBLE_ICONS.talk;
  drawBitmap(ctx, ic.rows, ic.pal, 4, 2);
  return c;
}

// ---- UI 用のドット絵アイコン ------------------------------------------------

const UI_ICONS = {
  island: {
    rows: ['....GG.GG...', '...GGGGGGG..', '..GG.GTG.GG.', '..G..TT...G.', '.....TT.....', '.....TT.....', '....TT......', '...SSSSSS...', '..SSSSSSSS..', '.SSSSSSSSSS.', 'WWWWWWWWWWWW', 'W.WW.WWW.WWW'],
    pal: { G: '#3fae4f', T: '#8f5f38', S: '#f0dc9c', W: '#3aa7e0' },
  },
  people: {
    rows: ['....HHHH....', '...HHHHHH...', '...HFFFFH...', '...FKFFKF...', '...FFFFFF...', '....FFFF....', '..CCCCCCCC..', '.CCCCCCCCCC.', '.CCCCCCCCCC.', '.FCCCCCCCCF.', '..CCCCCCCC..', '..PPP..PPP..'],
    pal: { H: '#4a2f1b', F: '#f6c9a0', K: INK, C: '#e8643c', P: '#3a4466' },
  },
  scroll: {
    rows: ['.PPPPPPPPP..', 'PPDDDDDDDPP.', '.PPPPPPPPP..', '..PKKKKKP...', '..PPPPPPP...', '..PKKKPPP...', '..PPPPPPP...', '..PKKKKKP...', '..PPPPPPP...', '.PPPPPPPPP..', 'PPDDDDDDDPP.', '.PPPPPPPPP..'],
    pal: { P: '#f7e7b8', D: '#c9a86a', K: '#5e3d24' },
  },
  vote: {
    rows: ['......WWWW..', '.....WWKKW..', '....WWKKW...', '....WWWW....', '.BBBBKKBBBB.', '.BKKKKKKKKB.', '.BBBBBBBBBB.', '.BBBYYYYBBB.', '.BBBYBBYBBB.', '.BBBYYYYBBB.', '.BBBBBBBBBB.', '.DDDDDDDDDD.'],
    pal: { W: '#ffffff', K: INK, B: '#3f8fd6', Y: '#f2c230', D: '#2b5f96' },
  },
  search: {
    rows: ['...KKKK.....', '..K....K....', '.K..WW..K...', '.K.W....K...', '.K......K...', '.K......K...', '..K....K....', '...KKKKKK...', '.......KKK..', '........KKK.', '.........KK.', '............'],
    pal: { K: INK, W: '#8fdcec' },
  },
  close: {
    rows: ['KK....KK', 'KKK..KKK', '.KKKKKK.', '..KKKK..', '..KKKK..', '.KKKKKK.', 'KKK..KKK', 'KK....KK'],
    pal: { K: INK },
  },
  crown: {
    rows: ['C..C..C', 'CC.C.CC', 'CCCCCCC', 'CLCCCLC', 'CCCCCCC'],
    pal: { C: '#f2c230', L: '#fff3b0' },
  },
  home: {
    rows: ['....KK....', '...KRRK...', '..KRRRRK..', '.KRRRRRRK.', 'KKWWWWWWKK', '.KWWKKWWK.', '.KWWKKWWK.', '.KKKKKKKK.'],
    pal: { K: INK, R: '#e8643c', W: '#f7e7b8' },
  },
  heart: { rows: BUBBLE_ICONS.heart.rows.slice(0, 6), pal: BUBBLE_ICONS.heart.pal },
  note: { rows: BUBBLE_ICONS.note.rows, pal: BUBBLE_ICONS.note.pal },
  bolt: { rows: BUBBLE_ICONS.bolt.rows, pal: BUBBLE_ICONS.bolt.pal },
  talk: { rows: ['.KKKKKKK.', 'KWWWWWWWK', 'KWKWKWKWK', 'KWWWWWWWK', '.KKWKKKK.', '..KK.....'], pal: { K: INK, W: '#ffffff' } },
};

export function iconCanvas(name, palOverride) {
  const ic = UI_ICONS[name] || UI_ICONS.island;
  const c = makeCanvas(ic.rows[0].length, ic.rows.length);
  drawBitmap(c.getContext('2d'), ic.rows, { ...ic.pal, ...(palOverride || {}) });
  c.className = `px-icon px-icon-${name}`;
  c.setAttribute('aria-hidden', 'true');
  return c;
}

// HTML 中の <span data-icon="..."> をドット絵に置き換える
export function hydrateIcons(root = document) {
  root.querySelectorAll('[data-icon]').forEach((el) => {
    if (el.firstChild) return;
    el.appendChild(iconCanvas(el.dataset.icon));
  });
}
