// 漂流者：フォローしてから、次の動画で「漂着」して島民になるまでの人。
// 東の砂浜（漂着地点 LANDING）の沖の海にただよっている。
//   ・場所：id のハッシュで決まる（漂着地点から岸に沿ったずれ ±DRIFT.along、岸からの距離 DRIFT.near〜far）
//   ・揺れ：時刻だけで決まる往復（上下に DRIFT.bob、前後左右に DRIFT.sway）。決して岸には着かない
//   → データ × 時刻の純関数なので、誰の端末でも同じ光景になる。
// 島民の sim とは完全に別もの（sim の状態・ハッシュ・経路には一切触れない）。
// Three.js に依存しない（Node で検証できる）。

import { LANDING, SEA_Y } from './terrain.js';
import { DRIFT, SHIRT_COLORS } from './config.js';
import { hashStr, hashMix, hash01 } from './rng.js';

const MIN_GAP = 7; // 漂流者どうしの間隔（これより近いと、別の場所を選びなおす）
const TRIES = 12; // 場所の選びなおしの回数
const ROCK_GAP = 4; // 浅瀬の岩からこれだけ離す
const WAVE_MS = 6000; // 島に手をふる周期
const WAVE_SHOW_MS = 1500; // 1回の手ふりの長さ

const idHash = (id) => hashStr(String(id));

// 服の色：id のハッシュで SHIRT_COLORS（デモの島民と同じ色）から決まる
export function drifterColor(id) {
  return SHIRT_COLORS[hashMix(idHash(id), 7) % SHIRT_COLORS.length];
}

// 沖の向き（島の中心から漂着地点へ）と、岸に沿った向き
export function driftAxes() {
  const len = Math.hypot(LANDING.x, LANDING.z) || 1;
  const nx = LANDING.x / len;
  const nz = LANDING.z / len;
  return { nx, nz, tx: -nz, tz: nx };
}

// 漂流者それぞれの、ただよう場所（揺れの中心）と揺れ方。
//   drifters: [{ id, … }]（並び順が早い人ほど、ハッシュで決まった最初の場所をそのまま使える）
//   terrain:  generateTerrain() の結果（海岸線を探すのに heightAt だけ使う。高さ1以上が陸）
//   avoid:    よけたい点 [{ x, z }]（浅瀬の岩など）
// 戻り値：[{ id, x, z, nx, nz, tx, tz, along, off, clearance, bobSpeed, bobPhase, swaySpeed, swayPhase, hash }]
//   along: 漂着地点から岸に沿ったずれ、off: 岸（その線上でいちばん沖にある陸）からの距離、
//   clearance: いちばん近い陸までのおおよその距離
export function layoutDrifters(drifters, terrain, { avoid = [] } = {}) {
  const { nx, nz, tx, tz } = driftAxes();
  const isLand = (x, z) => terrain.heightAt(x, z) >= 1;
  // まわり（半径 r）に陸が無いか
  const clearOf = (x, z, r) => {
    if (isLand(x, z)) return false;
    for (const rr of [r / 3, (2 * r) / 3, r]) {
      for (let a = 0; a < 24; a++) {
        const ang = (a / 24) * Math.PI * 2;
        if (isLand(x + Math.cos(ang) * rr, z + Math.sin(ang) * rr)) return false;
      }
    }
    return !avoid.some((p) => Math.hypot(p.x - x, p.z - z) < ROCK_GAP);
  };
  // 岸に沿って along ずれた線の上で、いちばん沖にある陸の先（漂着地点の線から沖へ測った距離）
  const coast = new Map();
  const coastAt = (along) => {
    const key = Math.round(along * 4);
    if (coast.has(key)) return coast.get(key);
    const bx = LANDING.x + tx * along;
    const bz = LANDING.z + tz * along;
    let last = null;
    for (let s = -60; s <= 240; s += 0.5) if (isLand(bx + nx * s, bz + nz * s)) last = s;
    const c = { bx, bz, s: last === null ? 0 : last + 0.5 };
    coast.set(key, c);
    return c;
  };
  // いちばん近い陸までの距離（1単位きざみの目安。検証用）
  const clearance = (x, z) => {
    for (let r = 1; r <= DRIFT.far * 2; r++) if (!clearOf(x, z, r)) return r - 1;
    return DRIFT.far * 2;
  };

  const placed = [];
  return drifters.map((d) => {
    const h = idHash(d.id);
    let best = null;
    for (let n = 0; n < TRIES; n++) {
      const along = (hash01(h, n, 1) * 2 - 1) * DRIFT.along;
      const off0 = DRIFT.near + hash01(h, n, 2) * (DRIFT.far - DRIFT.near);
      const c = coastAt(along);
      // 岸のすぐそば（DRIFT.near 以内）に陸や岩があれば、もう少し沖へ
      let off = off0;
      while (off < DRIFT.far * 2 && !clearOf(c.bx + nx * (c.s + off), c.bz + nz * (c.s + off), DRIFT.near)) off += 2;
      const x = c.bx + nx * (c.s + off);
      const z = c.bz + nz * (c.s + off);
      let gap = Infinity;
      for (const p of placed) gap = Math.min(gap, Math.hypot(p.x - x, p.z - z));
      if (!best || gap > best.gap) best = { x, z, along, off, gap };
      if (gap >= MIN_GAP) break;
    }
    placed.push(best);
    return {
      id: String(d.id),
      x: best.x,
      z: best.z,
      nx,
      nz,
      tx,
      tz,
      along: best.along,
      off: best.off,
      clearance: clearance(best.x, best.z),
      hash: h,
      bobSpeed: 1.1 + hash01(h, 11) * 0.7, // ラジアン／秒（周期 およそ3.5〜5.7秒）
      bobPhase: hash01(h, 12) * Math.PI * 2,
      swaySpeed: 0.35 + hash01(h, 13) * 0.3,
      swayPhase: hash01(h, 14) * Math.PI * 2,
    };
  });
}

// 時刻 tMs（エポックms）の姿。戻り値（out に書き込む）：{ x, y, z, dx, dz, wave }
//   y:      水面の高さ（波で上下する）。スプライトはこの高さを「水面の線」として描く
//   dx, dz: 向き（島のほう）
//   wave:   島に向かって手をふっているところか（ときどき）
export function driftPose(d, tMs, out = {}) {
  const t = tMs / 1000;
  const bob = Math.sin(t * d.bobSpeed + d.bobPhase) * DRIFT.bob;
  // 前後左右のゆれ：岸に沿った向きに大きめ、沖の向きにはごく小さく（岸には近づかない）
  const s1 = Math.sin(t * d.swaySpeed + d.swayPhase) * DRIFT.sway;
  const s2 = Math.sin(t * d.swaySpeed * 0.77 + d.swayPhase * 1.7) * DRIFT.sway * 0.5;
  out.x = d.x + d.tx * s1 + d.nx * s2;
  out.y = SEA_Y + bob;
  out.z = d.z + d.tz * s1 + d.nz * s2;
  out.dx = -d.nx;
  out.dz = -d.nz;
  const tt = tMs + (d.hash % WAVE_MS);
  const cyc = Math.floor(tt / WAVE_MS);
  out.wave = hashMix(d.hash, cyc, 3) % 3 === 0 && tt - cyc * WAVE_MS < WAVE_SHOW_MS;
  return out;
}
