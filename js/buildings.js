// 建物の定義（箱の組み合わせ）と、state.json の buildings を島の上に配置する処理。
// Three.js には依存しない。描画側は boxes を、シミュレーション側は spots / 敷地を使う。
//
// ローカル座標：+z が「正面」。rot（度）は上から見た回転で、0=南向き / 90=東向き / 180=北向き / 270=西向き。

import { N, CELL } from './terrain.js';

const WOOD = '#8f5f38';
const WOOD_DARK = '#5e3d24';
const WOOD_LIGHT = '#b98952';
const WALL = '#e2c391';
const THATCH_A = '#d8b052';
const THATCH_B = '#b98c3a';
const SOIL = '#6a4427';
const SOIL_LIGHT = '#82552f';
const LEAF_A = '#4fae4a';
const LEAF_B = '#86cc4e';
const GLASS = '#8fdcec';
const RED = '#d9503f';
const WHITE = '#f4efe2';

const box = (x, y, z, w, h, d, c) => ({ p: [x, y, z], s: [w, h, d], c });

function hut() {
  const b = [];
  b.push(box(0, 0.2, 0, 5.6, 0.4, 5.6, WOOD_DARK));
  b.push(box(0, 1.7, 0, 4.6, 2.6, 4.6, WALL));
  for (const sx of [-1, 1]) for (const sz of [-1, 1]) b.push(box(sx * 2.3, 1.75, sz * 2.3, 0.55, 2.7, 0.55, WOOD));
  b.push(box(0, 1.35, 2.32, 1.2, 1.9, 0.12, WOOD_DARK)); // 扉
  b.push(box(0.35, 1.3, 2.4, 0.15, 0.15, 0.1, THATCH_A)); // 取っ手
  b.push(box(1.45, 1.95, 2.32, 0.8, 0.8, 0.12, GLASS));
  b.push(box(2.32, 1.95, -0.2, 0.12, 0.8, 1.0, GLASS));
  b.push(box(-2.32, 1.95, 0.4, 0.12, 0.8, 1.0, GLASS));
  // 段々のかやぶき屋根
  const roof = [
    [6.2, THATCH_B],
    [5.2, THATCH_A],
    [4.0, THATCH_B],
    [2.8, THATCH_A],
    [1.4, THATCH_B],
  ];
  roof.forEach(([w, c], n) => b.push(box(0, 3.3 + n * 0.6, 0, w, 0.6, w, c)));
  // 軒先のたきぎ
  b.push(box(-1.7, 0.65, 2.75, 1.0, 0.5, 0.5, WOOD));
  b.push(box(-1.7, 1.05, 2.75, 0.7, 0.35, 0.5, WOOD_LIGHT));
  return {
    label: '小屋',
    boxes: b,
    height: 6.4,
    footprint: { x0: -3.1, x1: 3.1, z0: -3.1, z1: 3.1 },
    spots: [
      { x: 0.6, z: 4.6, fx: 0, fz: 0, jobs: ['料理人', '大工'], label: '小屋' },
      { x: 4.6, z: 0.4, fx: 0, fz: 0.4, jobs: ['大工'], label: '小屋' },
      { x: -4.6, z: -0.4, fx: 0, fz: -0.4, jobs: ['大工'], label: '小屋' },
    ],
  };
}

function field() {
  const b = [];
  b.push(box(0, 0.15, 0, 9.4, 0.3, 7.4, SOIL));
  const rows = [-2.55, -0.85, 0.85, 2.55];
  rows.forEach((z, r) => {
    b.push(box(0, 0.42, z, 8.4, 0.25, 0.85, SOIL_LIGHT));
    for (let n = 0; n < 6; n++) {
      const x = -3.5 + n * 1.4;
      const tall = (n + r) % 3 === 0;
      b.push(box(x, 0.8 + (tall ? 0.15 : 0), z, 0.55, 0.5 + (tall ? 0.3 : 0), 0.55, (n + r) % 2 ? LEAF_A : LEAF_B));
      if ((n * 3 + r) % 4 === 0) b.push(box(x + 0.2, 1.0, z + 0.15, 0.3, 0.3, 0.3, RED));
    }
  });
  // 柵（正面は開けておく）
  for (const x of [-4.7, 0, 4.7]) b.push(box(x, 0.6, -3.7, 0.3, 1.2, 0.3, WOOD_LIGHT));
  for (const x of [-4.7, 4.7]) for (const z of [0, 3.7]) b.push(box(x, 0.6, z, 0.3, 1.2, 0.3, WOOD_LIGHT));
  b.push(box(0, 0.85, -3.7, 9.4, 0.18, 0.18, WOOD_LIGHT));
  for (const x of [-4.7, 4.7]) b.push(box(x, 0.85, 0, 0.18, 0.18, 7.4, WOOD_LIGHT));
  // かかし
  b.push(box(3.4, 1.3, -2.9, 0.22, 2.4, 0.22, WOOD));
  b.push(box(3.4, 1.9, -2.9, 1.8, 0.22, 0.22, WOOD));
  b.push(box(3.4, 2.75, -2.9, 0.75, 0.6, 0.6, WALL));
  b.push(box(3.4, 3.15, -2.9, 1.3, 0.2, 1.1, THATCH_A));
  return {
    label: '畑',
    boxes: b,
    height: 3.4,
    footprint: { x0: -4.9, x1: 4.9, z0: -3.9, z1: 3.9 },
    spots: [
      { x: -2.2, z: 5.0, fx: -2.2, fz: 0, jobs: ['農家'], label: '畑' },
      { x: 2.4, z: 5.0, fx: 2.4, fz: 0, jobs: ['農家'], label: '畑' },
      { x: 6.2, z: -0.6, fx: 0, fz: -0.6, jobs: ['農家'], label: '畑' },
    ],
  };
}

export const PIER_DECK_Y = 1.35;
function pier() {
  const L = 18;
  const b = [];
  const top = PIER_DECK_Y;
  for (let z = -2; z < L; z++) {
    b.push(box(0, top - 0.14, z + 0.5, 2.7, 0.28, 0.92, z % 2 ? WOOD_LIGHT : WOOD));
  }
  for (let z = 1; z <= L; z += 4.25) {
    for (const sx of [-1, 1]) b.push(box(sx * 1.35, (top - 4) / 2 + 0.35, z, 0.45, top + 4.7, 0.45, WOOD_DARK));
  }
  // 係留ぐい と ロープ
  b.push(box(-1.35, top + 0.7, L - 0.2, 0.5, 0.5, 0.5, WHITE));
  // 小舟
  const bz = L - 6;
  b.push(box(2.9, 0.55, bz, 1.7, 0.7, 4.2, RED));
  b.push(box(2.9, 0.62, bz + 2.5, 1.1, 0.56, 0.9, RED));
  b.push(box(2.9, 0.93, bz, 1.2, 0.12, 3.6, WOOD_LIGHT));
  b.push(box(2.9, 1.05, bz - 0.6, 1.5, 0.14, 0.4, WOOD));
  return {
    label: '桟橋',
    boxes: b,
    height: 2.4,
    absoluteY: true,
    snapToCell: true,
    deck: { x0: -0.95, x1: 0.95, z0: -2.2, z1: L, y: top },
    spots: [
      { x: 0, z: L - 0.9, fx: 0, fz: L + 6, jobs: ['漁師'], label: '桟橋', spread: 0 },
      { x: 0, z: L - 5, fx: -6, fz: L - 5, jobs: ['漁師'], label: '桟橋', spread: 0 },
      { x: 0, z: L - 9, fx: 6, fz: L - 9, jobs: ['漁師'], label: '桟橋', spread: 0 },
    ],
  };
}

function watchtower() {
  const b = [];
  for (const sx of [-1, 1]) for (const sz of [-1, 1]) b.push(box(sx * 1.35, 3.3, sz * 1.35, 0.42, 6.6, 0.42, WOOD));
  for (const s of [-1, 1]) {
    b.push(box(0, 2.3, s * 1.35, 2.7, 0.24, 0.24, WOOD_DARK));
    b.push(box(s * 1.35, 4.3, 0, 0.24, 0.24, 2.7, WOOD_DARK));
  }
  b.push(box(0, 6.7, 0, 3.8, 0.4, 3.8, WOOD_LIGHT));
  for (const sx of [-1, 1]) for (const sz of [-1, 1]) b.push(box(sx * 1.7, 8.0, sz * 1.7, 0.28, 2.3, 0.28, WOOD));
  for (const s of [-1, 1]) {
    b.push(box(0, 7.8, s * 1.7, 3.6, 0.2, 0.2, WOOD_DARK));
    b.push(box(s * 1.7, 7.8, 0, 0.2, 0.2, 3.6, WOOD_DARK));
  }
  b.push(box(0, 9.3, 0, 4.6, 0.45, 4.6, THATCH_B));
  b.push(box(0, 9.75, 0, 3.2, 0.45, 3.2, THATCH_A));
  b.push(box(0, 10.15, 0, 1.6, 0.4, 1.6, THATCH_B));
  // はしご
  for (const sx of [-0.45, 0.45]) b.push(box(sx, 3.3, 1.75, 0.16, 6.6, 0.16, WOOD_LIGHT));
  for (let y = 0.7; y < 6.5; y += 0.85) b.push(box(0, y, 1.75, 0.9, 0.14, 0.14, WOOD_LIGHT));
  // 旗
  b.push(box(1.7, 11.0, -1.7, 0.16, 2.4, 0.16, WOOD_DARK));
  b.push(box(2.35, 11.7, -1.7, 1.2, 0.7, 0.1, RED));
  return {
    label: '見張り台',
    boxes: b,
    height: 12.2,
    footprint: { x0: -2.1, x1: 2.1, z0: -2.1, z1: 2.3 },
    spots: [
      { x: 0, z: 3.8, fx: 0, fz: 0, jobs: ['探検家'], label: '見張り台' },
      { x: 3.8, z: 0, fx: 9, fz: 0, jobs: ['探検家'], label: '見張り台' },
    ],
  };
}

// 未対応の type は立て札で代用する（データの打ち間違いで島が壊れないように）
function signpost() {
  return {
    label: '立て札',
    boxes: [box(0, 0.9, 0, 0.3, 1.8, 0.3, WOOD), box(0, 1.9, 0.05, 1.8, 1.0, 0.2, WOOD_LIGHT), box(0, 1.9, 0.17, 1.2, 0.2, 0.05, WOOD_DARK)],
    height: 2.6,
    footprint: { x0: -0.6, x1: 0.6, z0: -0.6, z1: 0.6 },
    spots: [{ x: 0, z: 2.4, fx: 0, fz: 0, jobs: [], label: '立て札' }],
  };
}

// 砂と石の蒸留装置：石のかまど＋海水の鍋＋竹の管＋受けのつぼ
function still() {
  const b = [];
  const STONE = '#8d8f97', STONE_D = '#6f717a', SAND = '#e3cf96', POT = '#5a5f6b', WATER = '#7fc3e6', BAMBOO = '#a7b35a';
  b.push(box(0, 0.15, 0, 3.2, 0.3, 2.4, SAND));
  for (const [x, z] of [[-0.9, -0.7], [0.9, -0.7], [-0.9, 0.7], [0.9, 0.7], [0, -0.85], [0, 0.85], [-1.05, 0], [1.05, 0]]) b.push(box(x, 0.55, z, 0.55, 0.6, 0.55, (x + z) % 2 ? STONE : STONE_D));
  b.push(box(0, 0.5, 0, 0.9, 0.3, 0.9, '#e4572e')); // 火
  b.push(box(0, 1.15, 0, 1.5, 0.7, 1.5, POT));
  b.push(box(0, 1.52, 0, 1.2, 0.06, 1.2, WATER));
  b.push(box(0, 1.75, 0, 1.6, 0.12, 1.6, POT)); // ふた
  b.push(box(1.05, 1.85, 0, 1.3, 0.16, 0.16, BAMBOO)); // 管
  b.push(box(1.75, 1.2, 0, 0.16, 1.2, 0.16, BAMBOO));
  b.push(box(1.75, 0.45, 0, 0.7, 0.6, 0.7, '#b07a44')); // 受けのつぼ
  b.push(box(1.75, 0.77, 0, 0.5, 0.05, 0.5, WATER));
  return {
    label: '蒸留装置',
    boxes: b,
    height: 2.2,
    footprint: { x0: -1.7, x1: 2.2, z0: -1.3, z1: 1.3 },
    spots: [
      { x: 0, z: 2.3, fx: 0, fz: 0, jobs: ['料理人', '大工'], label: '蒸留装置' },
      { x: 2.6, z: 1.4, fx: 1.75, fz: 0, jobs: ['料理人'], label: '蒸留装置' },
    ],
  };
}

// 昔の住人の跡：くずれた小屋（柱と崩れた屋根）、炭になった焚き火、石の道具
function ruins() {
  const b = [];
  const OLD = '#6e5a44', OLD_D = '#4f4032', MOSS = '#4f7a3a', ASH = '#3b3631', STONE = '#8d8f97';
  b.push(box(0, 0.15, 0, 6.0, 0.3, 5.0, OLD_D));
  for (const [x, z, h] of [[-2.6, -2.1, 2.6], [2.6, -2.1, 1.6], [-2.6, 2.1, 1.1], [2.6, 2.1, 2.2]]) b.push(box(x, 0.3 + h / 2, z, 0.5, h, 0.5, OLD));
  b.push(box(-0.6, 2.4, -1.2, 4.6, 0.3, 2.6, OLD)); // 傾いた屋根の残り
  b.push(box(1.4, 0.55, 1.0, 2.6, 0.5, 1.2, OLD_D)); // 崩れた屋根
  b.push(box(-2.2, 0.45, -0.2, 1.2, 0.3, 1.2, MOSS));
  b.push(box(1.0, 0.6, -0.9, 0.8, 0.12, 0.8, MOSS));
  // 炭になった焚き火
  for (const [x, z] of [[-0.6, 3.6], [0.6, 3.6], [0, 3.0], [0, 4.2]]) b.push(box(x, 0.35, z, 0.5, 0.4, 0.5, STONE));
  b.push(box(0, 0.4, 3.6, 0.7, 0.2, 0.7, ASH));
  // 石の道具（石斧・石のナイフ）
  b.push(box(2.8, 0.42, 3.4, 0.9, 0.12, 0.16, OLD));
  b.push(box(3.25, 0.45, 3.4, 0.35, 0.28, 0.3, STONE));
  b.push(box(2.6, 0.4, 3.9, 0.6, 0.08, 0.2, STONE));
  return {
    label: '昔の住人の跡',
    boxes: b,
    height: 3.0,
    footprint: { x0: -3.1, x1: 3.1, z0: -2.6, z1: 2.6 },
    spots: [
      { x: 0, z: 5.2, fx: 0, fz: 3.6, jobs: ['探検家'], label: '昔の住人の跡' },
      { x: 3.6, z: 4.6, fx: 2.8, fz: 3.4, jobs: ['大工', '探検家'], label: '昔の住人の跡' },
    ],
  };
}


// 石の作業場：昔の住人の跡をまねて、石を割って道具を作る場所（5日目）
function workshop() {
  const b = [];
  const STONE = '#8d8f97', STONE_D = '#6f717a', CHIP = '#b4b6bd';
  b.push(box(0, 0.12, 0, 5.4, 0.24, 4.2, '#7a6248'));
  // 日よけ（4本柱＋葉っぱの屋根）
  for (const [x, z] of [[-2.3, -1.7], [2.3, -1.7], [-2.3, 1.7], [2.3, 1.7]]) b.push(box(x, 1.6, z, 0.34, 3.0, 0.34, WOOD));
  b.push(box(0, 3.2, 0, 5.6, 0.3, 4.4, THATCH_B));
  b.push(box(0, 3.5, 0, 4.2, 0.3, 3.0, THATCH_A));
  // 作業台と、割る前の大きな石
  b.push(box(-0.8, 0.75, -0.6, 2.4, 0.3, 1.2, WOOD_LIGHT));
  for (const [x, z] of [[-1.8, -1.0], [0.2, -1.0], [-1.8, -0.2], [0.2, -0.2]]) b.push(box(x, 0.42, z, 0.24, 0.6, 0.24, WOOD_DARK));
  b.push(box(1.6, 0.6, 0.6, 1.3, 1.0, 1.1, STONE));
  b.push(box(1.4, 1.2, 0.5, 0.8, 0.4, 0.7, STONE_D));
  b.push(box(-1.6, 0.4, 1.2, 0.9, 0.5, 0.8, STONE_D));
  // 台の上の石器（石斧・石の銛・石のくわ）
  b.push(box(-1.4, 0.98, -0.6, 0.8, 0.1, 0.14, WOOD));
  b.push(box(-1.0, 1.0, -0.6, 0.3, 0.22, 0.26, STONE));
  b.push(box(-0.3, 0.97, -0.4, 1.0, 0.08, 0.1, WOOD));
  b.push(box(0.25, 0.98, -0.4, 0.26, 0.12, 0.12, CHIP));
  b.push(box(-0.6, 0.97, -0.9, 0.12, 0.08, 0.7, WOOD));
  b.push(box(-0.6, 0.99, -1.2, 0.4, 0.1, 0.16, STONE_D));
  for (const [x, z] of [[0.9, 1.4], [1.2, 1.7], [2.3, 1.0], [0.6, 0.0]]) b.push(box(x, 0.3, z, 0.22, 0.1, 0.2, CHIP));
  return {
    label: '石の作業場',
    boxes: b,
    height: 3.8,
    footprint: { x0: -2.7, x1: 2.7, z0: -2.1, z1: 2.1 },
    spots: [
      { x: -0.8, z: 2.6, fx: -0.8, fz: -0.6, jobs: ['大工', '探検家', '漁師', '農家', '料理人'], label: '石の作業場' },
      { x: 2.4, z: 2.8, fx: 1.6, fz: 0.6, jobs: ['大工'], label: '石の作業場' },
    ],
  };
}

// 大きな木箱：海から流れ着いた。中身はまだ分からない（6日目の動画で開ける）
function bigcrate() {
  const b = [];
  const PLANK = '#a8794a', PLANK_D = '#7d5634', BAND = '#5b5f68', ROPE = '#d8c08a', WEED = '#3f7d4e', SHELL = '#efe3cf';
  const W = 6.4, H = 5.2, D = 5.2;
  for (let k = 0; k < 4; k++) b.push(box(0, 0.65 + k * 1.3, 0, W, 1.22, D, k % 2 ? PLANK : PLANK_D));
  // 角の補強と金具の帯
  for (const sx of [-1, 1]) for (const sz of [-1, 1]) b.push(box(sx * (W / 2 - 0.15), H / 2, sz * (D / 2 - 0.15), 0.5, H + 0.1, 0.5, PLANK_D));
  for (const y of [1.0, H - 1.0]) b.push(box(0, y, 0, W + 0.12, 0.28, D + 0.12, BAND));
  b.push(box(0, H + 0.05, 0, W - 0.2, 0.14, D - 0.2, PLANK));
  // ロープ（上で十字）
  b.push(box(0, H + 0.2, 0, 0.26, 0.2, D + 0.3, ROPE));
  b.push(box(0, H + 0.2, 0, W + 0.3, 0.2, 0.26, ROPE));
  b.push(box(0, H / 2, D / 2 + 0.1, 0.26, H, 0.12, ROPE));
  // 海藻と貝がら（長く海をただよっていた）
  for (const [x, y, z, w, h] of [[-2.2, 0.4, D / 2 + 0.08, 1.4, 0.7], [1.8, 0.3, D / 2 + 0.08, 0.9, 0.5], [W / 2 + 0.08, 0.5, 1.2, 0.1, 0.9]]) b.push(box(x, y, z, w, h, 0.12, WEED));
  for (const [x, y, z] of [[1.2, 1.6, D / 2 + 0.1], [-1.0, 2.4, D / 2 + 0.1], [2.4, 3.3, D / 2 + 0.1]]) b.push(box(x, y, z, 0.32, 0.26, 0.1, SHELL));
  // 「？」の焼き印
  b.push(box(-1.6, 3.4, D / 2 + 0.09, 0.7, 0.16, 0.06, '#3b2a1c'));
  b.push(box(-1.3, 3.15, D / 2 + 0.09, 0.16, 0.4, 0.06, '#3b2a1c'));
  b.push(box(-1.6, 2.85, D / 2 + 0.09, 0.16, 0.3, 0.06, '#3b2a1c'));
  b.push(box(-1.6, 2.45, D / 2 + 0.09, 0.16, 0.16, 0.06, '#3b2a1c'));
  return {
    label: '大きな木箱',
    boxes: b,
    height: H + 0.4,
    footprint: { x0: -W / 2 - 0.2, x1: W / 2 + 0.2, z0: -D / 2 - 0.2, z1: D / 2 + 0.2 },
    spots: [
      { x: 0, z: D / 2 + 1.8, fx: 0, fz: 0, jobs: ['探検家'], label: '大きな木箱' },
    ],
  };
}

// 大きな畑（6日目）：木箱の種と苗を植えた。growth 0=植えたばかり・1=芽が伸びた・2=実った（data.js が日数から決める）
//   列ごとに作物がちがう：小麦・大豆・さつまいも・綿・果物の苗
function bigfield(src = {}) {
  const g = Math.max(0, Math.min(2, Number(src.growth ?? 2)));
  const W = 26, D = 18;
  const b = [];
  b.push(box(0, 0.15, 0, W, 0.3, D, SOIL));
  const crops = [
    { leaf: '#86cc4e', ripe: '#e8c24a', tall: 1.4 }, // 小麦
    { leaf: '#5fb04a', ripe: '#c9b46a', tall: 0.8 }, // 大豆
    { leaf: '#4f9e3e', ripe: '#b0486a', tall: 0.5 }, // さつまいも
    { leaf: '#7cbf5a', ripe: '#f4efe2', tall: 1.0 }, // 綿
    { leaf: '#3f8f3a', ripe: '#e8504a', tall: 2.2 }, // 果物の苗
  ];
  const rows = 8;
  for (let r = 0; r < rows; r++) {
    const z = -D / 2 + 1.6 + r * ((D - 3.2) / (rows - 1));
    b.push(box(0, 0.4, z, W - 2.4, 0.22, 0.9, SOIL_LIGHT));
    const c = crops[r % crops.length];
    for (let n = 0; n < 11; n++) {
      const x = -W / 2 + 2.2 + n * ((W - 4.4) / 10);
      if (g === 0) {
        b.push(box(x, 0.6, z, 0.3, 0.22, 0.3, LEAF_B)); // 植えたばかりの芽
        continue;
      }
      const h = c.tall * (g === 1 ? 0.5 : 1) * (0.85 + ((n * 7 + r * 3) % 4) * 0.08);
      b.push(box(x, 0.5 + h / 2, z, 0.6, h, 0.6, c.leaf));
      if (g === 2 && (n + r) % 2 === 0) b.push(box(x + 0.18, 0.5 + h * 0.8, z + 0.2, 0.34, 0.34, 0.34, c.ripe));
    }
  }
  // 柵
  for (let x = -W / 2; x <= W / 2 + 0.01; x += W / 6) for (const z of [-D / 2, D / 2]) b.push(box(x, 0.6, z, 0.3, 1.2, 0.3, WOOD_LIGHT));
  for (let z = -D / 2 + D / 4; z < D / 2; z += D / 4) for (const x of [-W / 2, W / 2]) b.push(box(x, 0.6, z, 0.3, 1.2, 0.3, WOOD_LIGHT));
  for (const z of [-D / 2]) b.push(box(0, 0.85, z, W, 0.18, 0.18, WOOD_LIGHT));
  for (const x of [-W / 2, W / 2]) b.push(box(x, 0.85, 0, 0.18, 0.18, D, WOOD_LIGHT));
  // かかし
  b.push(box(W / 2 - 2, 1.3, -D / 2 + 1.5, 0.22, 2.4, 0.22, WOOD));
  b.push(box(W / 2 - 2, 1.9, -D / 2 + 1.5, 1.8, 0.22, 0.22, WOOD));
  b.push(box(W / 2 - 2, 2.75, -D / 2 + 1.5, 0.75, 0.6, 0.6, WALL));
  b.push(box(W / 2 - 2, 3.15, -D / 2 + 1.5, 1.3, 0.2, 1.1, THATCH_A));
  return {
    label: '大きな畑',
    boxes: b,
    height: 3.4,
    footprint: { x0: -W / 2 - 0.2, x1: W / 2 + 0.2, z0: -D / 2 - 0.2, z1: D / 2 + 0.2 },
    spots: [
      { x: -6, z: D / 2 + 1.6, fx: -6, fz: 0, jobs: ['農家'], label: '大きな畑' },
      { x: 2, z: D / 2 + 1.6, fx: 2, fz: 0, jobs: ['農家'], label: '大きな畑' },
      { x: 9, z: D / 2 + 1.6, fx: 9, fz: 0, jobs: ['農家', '料理人'], label: '大きな畑' },
      { x: -W / 2 - 1.6, z: 0, fx: 0, fz: 0, jobs: ['農家'], label: '大きな畑' },
    ],
  };
}

// クマの家（7日目）：丸太を組んだ大きな小屋。入口が広く、中に干し草
function bearhouse() {
  const b = [];
  const W = 8, D = 6.5, H = 4.2, LOG = '#7a4f2c', LOG2 = '#8f5f38', HAY = '#e3c86a';
  b.push(box(0, 0.15, 0, W, 0.3, D, '#6b5232'));
  for (let k = 0; k < 5; k++) {
    const y = 0.5 + k * 0.8, c = k % 2 ? LOG : LOG2;
    b.push(box(0, y, -D / 2 + 0.35, W, 0.7, 0.7, c)); // 奥
    b.push(box(-W / 2 + 0.35, y, 0, 0.7, 0.7, D, c), box(W / 2 - 0.35, y, 0, 0.7, 0.7, D, c)); // 左右
    if (k >= 3) b.push(box(0, y, D / 2 - 0.35, W, 0.7, 0.7, c)); // 入口の上（下は開いている）
    else for (const s of [-1, 1]) b.push(box(s * (W / 2 - 1.1), y, D / 2 - 0.35, 1.5, 0.7, 0.7, c));
  }
  b.push(box(0, H + 0.4, 0, W + 1, 0.5, D + 1, THATCH_B), box(0, H + 0.9, 0, W - 1, 0.5, D - 1, THATCH_A), box(0, H + 1.3, 0, W - 3.5, 0.4, D - 3, THATCH_B));
  b.push(box(0, 0.45, -0.6, W - 2, 0.3, D - 2.6, HAY));
  // 入口の上の看板（クマの顔）
  b.push(box(0, H - 0.2, D / 2 + 0.05, 1.6, 1.0, 0.12, WOOD_LIGHT), box(-0.5, H + 0.25, D / 2 + 0.07, 0.35, 0.35, 0.1, '#2e2622'), box(0.5, H + 0.25, D / 2 + 0.07, 0.35, 0.35, 0.1, '#2e2622'), box(0, H - 0.25, D / 2 + 0.08, 0.7, 0.45, 0.1, '#2e2622'));
  return {
    label: 'クマの家',
    boxes: b,
    height: H + 1.6,
    footprint: { x0: -W / 2 - 0.3, x1: W / 2 + 0.3, z0: -D / 2 - 0.3, z1: D / 2 + 0.3 },
    spots: [{ x: 2.5, z: D / 2 + 2.2, fx: 0, fz: 0, jobs: ['料理人', '探検家'], label: 'クマの家' }],
  };
}

// ステージ（8日目〜）：木の野外ステージ。手前の左右に火の台（かがり火）。舞台の上で15分ごとに出し物（show.js）
function stage() {
  const b = [];
  const W = 9, D = 6, TOP = 1.05;
  b.push(box(0, 0.5, 0, W, 1, D, WOOD));
  for (let x = -4; x <= 4; x += 1) b.push(box(x, 1.02, 0, 0.9, 0.06, D, x % 2 ? WOOD_LIGHT : WOOD));
  b.push(box(0, 3.4, -2.8, W, 4.8, 0.4, WOOD_LIGHT), box(0, 5.9, -2.8, 9.6, 0.4, 0.6, WOOD_DARK));
  for (const x of [-4.4, 4.4]) b.push(box(x, 3, -2.8, 0.5, 6, 0.5, WOOD_DARK));
  b.push(box(0, 5.3, -2.55, 6, 0.9, 0.1, RED), box(0, 5.3, -2.5, 4.6, 0.3, 0.1, '#f0c040'));
  for (const x of [-1.2, 0, 1.2]) b.push(box(x, 0.25, 3.4, 0.9, 0.5, 0.9, WOOD_LIGHT));
  b.push(box(0, 0.25, 3.9, 2.8, 0.5, 0.6, WOOD));
  // かがり火の台（石の台に鉄のかご）
  for (const x of [-4.9, 4.9]) b.push(box(x, 0.6, 3.2, 1.0, 1.2, 1.0, '#8d8f97'), box(x, 1.45, 3.2, 1.2, 0.5, 1.2, '#4b4f58'));
  return {
    label: 'ステージ',
    boxes: b,
    height: 6.2,
    footprint: { x0: -W / 2 - 0.9, x1: W / 2 + 0.9, z0: -D / 2 - 0.2, z1: D / 2 + 1.4 },
    fires: [{ x: -4.9, y: 1.75, z: 3.2 }, { x: 4.9, y: 1.75, z: 3.2 }],
    stageTop: TOP,
    stageSpots: [[0, 0.4], [-1.6, 0.2], [1.6, 0.2], [-3.0, -0.2], [3.0, -0.2], [0, -1.4]], // 舞台の上の立ち位置（ローカル）
    spots: [
      { x: 0, z: D / 2 + 7, fx: 0, fz: 0, jobs: ['料理人', '大工', '漁師', '農家', '探検家', '島民'], label: 'ステージの客席', spread: 5, audience: true },
    ],
  };
}

export const BUILDING_TYPES = { hut, field, pier, watchtower, still, ruins, workshop, bigcrate, bigfield, bearhouse, stage };
export const BUILDING_LABELS = { hut: '小屋', field: '畑', pier: '桟橋', watchtower: '見張り台', still: '蒸留装置', ruins: '昔の住人の跡', workshop: '石の作業場', bigcrate: '大きな木箱', bigfield: '大きな畑', bearhouse: 'クマの家', stage: 'ステージ' };

// 広場のたき火（建物データではなく、島に最初からある）
export function campfireBoxes() {
  const STONE = '#8d8f98';
  const STONE_D = '#6f7079';
  const b = [];
  const ring = [
    [-0.9, 0],
    [0.9, 0],
    [0, -0.9],
    [0, 0.9],
    [-0.65, -0.65],
    [0.65, -0.65],
    [-0.65, 0.65],
    [0.65, 0.65],
  ];
  ring.forEach(([x, z], n) => b.push(box(x, 0.2, z, 0.5, 0.4, 0.5, n % 2 ? STONE : STONE_D)));
  b.push(box(0, 0.25, 0, 1.2, 0.25, 0.3, WOOD_DARK));
  b.push(box(0, 0.3, 0, 0.3, 0.25, 1.2, WOOD));
  // 丸太のいす
  b.push(box(-3.0, 0.3, 0.6, 0.7, 0.6, 2.2, WOOD));
  b.push(box(2.9, 0.3, -0.8, 0.7, 0.6, 2.2, WOOD));
  b.push(box(0.4, 0.3, 3.1, 2.2, 0.6, 0.7, WOOD));
  return b;
}

const rad = (deg) => (deg * Math.PI) / 180;

// state.json の buildings を解決する。
// 戻り値：{ list, blocked:Set, reserved:Set, decks:Map }
export function resolveBuildings(defs, terrain) {
  const { idx, cellOf, cellCenter, inGrid, h } = terrain;
  const list = [];
  const blocked = new Set();
  const reserved = new Set();
  const decks = new Map();

  (defs || []).forEach((src, n) => {
    const make = BUILDING_TYPES[src.type] || signpost;
    const def = make(src);
    let x = Number(src.x) || 0;
    let z = Number(src.z) || 0;
    const rot = Number(src.rot) || 0;
    if (def.snapToCell) {
      const c = cellOf(x, z);
      const cc = cellCenter(c.i, c.j);
      x = cc.x;
      z = cc.z;
    }
    const sin = Math.sin(rad(rot));
    const cos = Math.cos(rad(rot));
    const toWorld = (lx, lz) => ({ x: x + lx * cos + lz * sin, z: z - lx * sin + lz * cos });
    const toLocal = (wx, wz) => {
      const dx = wx - x;
      const dz = wz - z;
      return { x: dx * cos - dz * sin, z: dx * sin + dz * cos };
    };

    // 周辺のマスを走査して、敷地・床・地面の高さを求める
    const c0 = cellOf(x, z);
    const R = 14;
    let baseY = -Infinity;
    const foot = [];
    for (let dj = -R; dj <= R; dj++) {
      for (let di = -R; di <= R; di++) {
        const i = c0.i + di;
        const j = c0.j + dj;
        if (!inGrid(i, j)) continue;
        const cc = cellCenter(i, j);
        const l = toLocal(cc.x, cc.z);
        const k = idx(i, j);
        const f = def.footprint;
        if (f) {
          if (l.x >= f.x0 && l.x <= f.x1 && l.z >= f.z0 && l.z <= f.z1) {
            blocked.add(k);
            foot.push(k);
            baseY = Math.max(baseY, h[k]);
          }
          const m = 2.2; // 木や岩を置かない余白
          if (l.x >= f.x0 - m && l.x <= f.x1 + m && l.z >= f.z0 - m && l.z <= f.z1 + m + 2.5) reserved.add(k);
        }
        const d = def.deck;
        if (d) {
          if (l.x >= d.x0 && l.x <= d.x1 && l.z >= d.z0 && l.z <= d.z1) {
            if (h[k] < d.y + 0.5) decks.set(k, d.y);
          }
          if (l.x >= d.x0 - 4 && l.x <= d.x1 + 5 && l.z >= d.z0 - 3 && l.z <= d.z1 + 3) reserved.add(k);
        }
      }
    }
    if (def.absoluteY) {
      baseY = 0;
    } else if (!foot.length) {
      baseY = Math.max(1, h[idx(c0.i, c0.j)]);
    } else {
      // 敷地は整地する（高さの中央値にそろえる）。開拓で地面がならされる、という扱い。
      const hs = foot.map((k) => h[k]).sort((a, b) => a - b);
      baseY = Math.max(1, hs[Math.floor((hs.length - 1) / 2)]);
      for (const k of foot) h[k] = baseY;
    }

    const spots = def.spots.map((s) => {
      const p = toWorld(s.x, s.z);
      const f = toWorld(s.fx, s.fz);
      return { x: p.x, z: p.z, fx: f.x, fz: f.z, jobs: s.jobs, label: src.name || s.label, spread: s.spread ?? 0.9, building: src.id || `b${n}`, audience: !!s.audience };
    });

    list.push({
      id: src.id || `b${n}`,
      type: BUILDING_TYPES[src.type] ? src.type : 'unknown',
      typeLabel: def.label,
      name: src.name || def.label,
      builtDay: src.builtDay ?? null,
      note: src.note || '',
      x,
      z,
      y: baseY,
      rot,
      height: def.height,
      boxes: def.boxes,
      foundation: !def.absoluteY, // 斜面でも浮かないよう、土台を下へ伸ばす
      footprintLocal: def.footprint || null,
      spots,
      fires: (def.fires || []).map((f) => ({ ...toWorld(f.x, f.z), y: baseY + f.y })),
      stageSpots: def.stageSpots ? def.stageSpots.map(([lx, lz]) => ({ ...toWorld(lx, lz), y: baseY + def.stageTop, f: toWorld(lx, lz + 6) })) : null,
    });
  });

  return { list, blocked, reserved, decks };
}

export { N, CELL };
