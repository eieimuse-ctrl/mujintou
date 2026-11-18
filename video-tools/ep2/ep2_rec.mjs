// ep2 recorder: node ep2_rec.mjs [shots]  -> build/ep2/rec/<shot>/f%05d.jpg + track.jsonl  (needs stage2 on :8774)
// Resumable: frames on disk are skipped. Every frame is a pure function of film time (camera + islander script).
import fs from 'node:fs';
import { openStage, shoot, BASE_T } from './ep2_rig.mjs';
import { SHOTS, FPS, poseAt, frameCount, LANDING, NX, NZ } from './ep2_timeline.mjs';

const TEST = !!process.env.TEST; // TEST=1: 3 frames per shot at 540x960 -> build/ep2/test/
const ROOT = process.env.HOME + '/workspace/mujintou/video/build/ep2/' + (TEST ? 'test' : 'rec');
const SIM_SPEED = 2.2;
const args = process.argv.slice(2);
const names = args.length ? args : ['L', 'B', 'P', 'H', 'QB', 'QC', 'QD', 'QE', 'E', 'p2'];

// in-page: the film script for the 52 islanders (day-2 set). Returns env anchors for the camera keys.
function setupScript(L, NX, NZ) {
  const a = window.__island, T = a.terrain, nav = a.nav;
  const isl = a.actors.actors.map((x) => x.person);
  const n = isl.length;
  const h01 = (i, k) => { let x = Math.sin((i + 1) * 12.9898 + k * 78.233) * 43758.5453; return x - Math.floor(x); };
  const yAt = (x, z) => (nav.yAt ? nav.yAt(x, z) : Math.max(0.45, T.heightAt(x, z)));
  const fire = a.sim.fireSpot || a.hub;
  const C = { x: fire.x, z: fire.z };
  const az = 0.45; // the gathering camera
  const toCam = { x: Math.sin(az), z: Math.cos(az) }, right = { x: Math.cos(az), z: -Math.sin(az) };
  const saka = Math.max(0, isl.findIndex((p) => p.id === 'sakasaka_1482'));
  // plaza rings around the fire
  const rings = [[6.5, 13], [10, 19], [13.5, 20]];
  const slots = [];
  for (const [r, m] of rings) for (let k = 0; k < m; k++) { const ph = az + (2 * Math.PI * k) / m + (r === 10 ? Math.PI / m : 0); slots.push({ x: C.x + r * Math.sin(ph), z: C.z + r * Math.cos(ph) }); }
  const order = [...Array(n).keys()].filter((i) => i !== saka).sort((p, q) => h01(p, 1) - h01(q, 1));
  const slotOf = new Array(n);
  slotOf[saka] = slots[0];
  order.forEach((i, k) => { slotOf[i] = slots[k + 1]; });
  // beach: along the coast near LANDING
  const tx = -NZ, tz = NX;
  const coastS = (al) => { let last = 0; for (let s = -40; s <= 120; s += 0.5) if (T.heightAt(L.x + tx * al + NX * s, L.z + tz * al + NZ * s) >= 1) last = s; return last; };
  const beach = new Array(n);
  [...Array(n).keys()].sort((p, q) => h01(p, 2) - h01(q, 2)).forEach((i, k) => {
    const al = -26 + (52 * (k + 0.5)) / n + (h01(i, 3) - 0.5) * 1.5;
    const s = coastS(al) - (1.6 + h01(i, 4) * 7.5);
    beach[i] = { x: L.x + tx * al + NX * s, z: L.z + tz * al + NZ * s };
  });
  const s0 = coastS(0);
  // walk-in: from the left/right of the gathering camera
  const start = new Array(n), arrive = new Array(n);
  for (let i = 0; i < n; i++) {
    const side = h01(i, 5) < 0.5 ? -1 : 1;
    let dx = side * right.x * 0.88 + toCam.x * 0.45, dz = side * right.z * 0.88 + toCam.z * 0.45;
    const l = Math.hypot(dx, dz); dx /= l; dz /= l;
    const d = 34 + h01(i, 6) * 14, lat = (h01(i, 7) - 0.5) * 12;
    start[i] = { x: slotOf[i].x + dx * d - dz * lat, z: slotOf[i].z + dz * d + dx * lat };
    arrive[i] = i === saka ? 22.8 : 22.5 + h01(i, 8) * 2.3;
  }
  // option scenes: workers by job
  const pickJob = (job, k, used) => { const out = []; for (let i = 0; i < n && out.length < k; i++) if (isl[i].job === job && !used.has(i)) out.push(i); for (let i = 0; i < n && out.length < k; i++) if (!used.has(i) && !out.includes(i) && i !== saka) out.push(i); out.forEach((i) => used.add(i)); return out; };
  const used = new Set([saka]);
  const fishers = pickJob('漁師', 3, used), farmers = pickJob('農家', 3, used), explorers = pickJob('探検家', 3, used);
  const waterDir = (p) => { let wx = 0, wz = 0; for (let k = 0; k < 36; k++) { const ang = (k / 36) * Math.PI * 2, cx = Math.sin(ang), cz = Math.cos(ang); if (T.heightAt(p.x + cx * 7, p.z + cz * 7) < 1) { wx += cx; wz += cz; } } const l = Math.hypot(wx, wz) || 1; return { x: wx / l, z: wz / l }; };
  const fishSpot = { x: -9, z: 189 }, w = waterDir(fishSpot);
  const farmSpot = { x: -7, z: 99 };
  const woodSpot = { x: -83, z: -25 }, toWood = { x: -0.98, z: -0.2 };
  const place = (spot, k, m, fx, fz, gap = 3.2) => ({ x: spot.x + (k - (m - 1) / 2) * gap * -fz, z: spot.z + (k - (m - 1) / 2) * gap * fx });
  const sm = (u) => { u = Math.max(0, Math.min(1, u)); return u * u * (3 - 2 * u); };
  const HIDE = { y: -80 };
  globalThis.__stagePose = (i) => {
    const t = window.__filmT ?? 0;
    const st = (x, z, anim, dx, dz) => ({ x, y: yAt(x, z), z, dx, dz, anim, bubble: null, line: '' });
    const s = slotOf[i];
    const face = (p, q) => { const dx = q.x - p.x, dz = q.z - p.z, l = Math.hypot(dx, dz) || 1; return [dx / l, dz / l]; };
    if (t >= 32.0 && t < 39.6) {
      const job = t < 34.7 ? fishers : t < 36.95 ? farmers : explorers;
      const k = job.indexOf(i);
      if (k >= 0) {
        if (t < 34.7) { const p = place({ x: fishSpot.x + w.x * 1.5, z: fishSpot.z + w.z * 1.5 }, k, 3, w.x, w.z); return st(p.x, p.z, 'work', w.x, w.z); }
        if (t < 36.95) { const p = place(farmSpot, k, 3, 0.6, 0.8, 4); return st(p.x, p.z, 'work', k % 2 ? 1 : -1, 0.2); }
        const p = place(woodSpot, k, 3, toWood.x, toWood.z, 3.6); return st(p.x, p.z, k === 1 ? 'work' : 'idle', toWood.x, toWood.z);
      }
    }
    if (t < 15.4) return { ...st(s.x, s.z, 'idle', 0, 1), ...HIDE };
    if (t < 17.25) { const b = beach[i]; return st(b.x, b.z, h01(i, 9) < 0.65 ? 'cheer' : 'idle', -NX, -NZ); }
    if (t < 20.6) return { ...st(s.x, s.z, 'idle', 0, 1), ...HIDE };
    if (t < arrive[i]) {
      const u = (t - 20.6) / (arrive[i] - 20.6);
      const e = 1 - (1 - u) * (1 - u) * 0.35 - (1 - u) * 0.65; // mostly linear, eases at the end
      const p0 = start[i], x = p0.x + (s.x - p0.x) * e, z = p0.z + (s.z - p0.z) * e;
      const [dx, dz] = face(p0, s);
      return st(x, z, 'walk', dx, dz);
    }
    const [fx, fz] = face(s, C);
    if (i === saka && t >= 24.55 && t < 26.1) return st(s.x, s.z, 'cheer', -toCam.z, toCam.x);
    if (t < arrive[i] + 1.0 && t < 27.0) return st(s.x, s.z, 'cheer', fx, fz);
    return st(s.x, s.z, 'idle', fx, fz);
  };
  const hung = { x: C.x + 10 * Math.sin(0.95), z: C.z + 10 * Math.cos(0.95) };
  const fishT = { x: fishSpot.x + w.x * 3, z: fishSpot.z + w.z * 3 };
  const fishAz = Math.atan2(-w.x, -w.z) + 0.5;
  const woodAz = Math.atan2(-toWood.x, -toWood.z) + 0.25;
  return {
    Cx: C.x, Cz: C.z, sakaX: slotOf[saka].x, sakaZ: slotOf[saka].z, saka,
    beachX: L.x + NX * (s0 - 4), beachZ: L.z + NZ * (s0 - 4), hungX: hung.x, hungZ: hung.z,
    fishX: fishT.x, fishZ: fishT.z, fishAz, fishAz2: fishAz + 0.15, farmX: farmSpot.x, farmZ: farmSpot.z,
    woodX: woodSpot.x + 2, woodZ: woodSpot.z, woodAz, woodAz2: woodAz + 0.15,
    fishers, farmers, explorers, water: w, s0, names: isl.map((p) => p.name), ids: isl.map((p) => p.id),
  };
}

async function run(group, shots) {
  const half = shots.some((s) => SHOTS[s].half);
  const set = SHOTS[shots[0]].set || '';
  const { browser, page, info } = await openStage(half || TEST ? { w: 540, h: 960, dsf: 1, set } : { w: 540, h: 960, dsf: 2, set });
  console.log(group, 'canvas', info.cw, info.ch, 'islanders', info.nIsl, 'drifters', info.nDrift, new Date().toISOString());
  const env = set === 'landing' ? {} : await page.evaluate(setupScript, LANDING, NX, NZ);
  if (set !== 'landing') {
    fs.mkdirSync(ROOT, { recursive: true });
    fs.writeFileSync(`${ROOT}/env.json`, JSON.stringify(env));
    console.log('env', JSON.stringify({ ...env, names: undefined, ids: undefined }));
  }
  const ground = async (x, z) => page.evaluate((x, z) => window.__ground(x, z), x, z);
  for (const shot of shots) {
    const S = SHOTS[shot];
    const keys = [];
    for (const k of S.keys) {
      const r = { ...k };
      for (const f of ['tx', 'tz', 'az']) if (typeof r[f] === 'string') r[f] = env[r[f]];
      if (typeof r.ty === 'string') r.ty = (await ground(r.tx, r.tz)) + Number(r.ty.slice(2));
      keys.push(r);
    }
    const dir = `${ROOT}/${shot}`;
    fs.mkdirSync(dir, { recursive: true });
    fs.writeFileSync(`${dir}/keys.json`, JSON.stringify(keys));
    const N = frameCount(shot);
    const t0 = Date.now();
    let done = 0;
    const list = TEST ? (process.env.TEST_AT ? process.env.TEST_AT.split(',').map(Number).filter((x) => x >= S.from && x < S.to).map((x) => Math.round((x - S.from) * FPS)) : [0, Math.floor(N / 2), N - 1]) : [...Array(N).keys()];
    for (const i of list) {
      const file = `${dir}/f${String(i).padStart(5, '0')}.jpg`;
      if (fs.existsSync(file) && fs.statSync(file).size > 1000) continue;
      const t = S.from + i / FPS;
      const pose = { ...poseAt(keys, t), filmT: t, simT: BASE_T + t * 1000 * SIM_SPEED, actT: BASE_T + t * 1000, pts: [] };
      if (set === 'landing') pose.landing = { t: Math.max(0, t - 12.7), dur: 2.1, spread: 0.7, stop: 2.5 };
      const { meta, jpg } = await shoot(page, pose, 0.92);
      fs.writeFileSync(file + '.tmp', jpg);
      fs.renameSync(file + '.tmp', file);
      fs.appendFileSync(`${dir}/track.jsonl`, JSON.stringify({ i, t: +t.toFixed(4), cam: meta.cam, heads: meta.heads }) + '\n');
      done++;
      if (done % 24 === 0) console.log(shot, i, '/', N, ((Date.now() - t0) / 1000).toFixed(0) + 's', new Date().toISOString());
    }
    console.log(shot, 'done', done, 'new of', N, ((Date.now() - t0) / 1000).toFixed(0) + 's');
  }
  await browser.close();
}

const groups = [
  ['landing', names.filter((s) => SHOTS[s].set === 'landing')],
  ['day2', names.filter((s) => !SHOTS[s].set && !SHOTS[s].half)],
  ['half', names.filter((s) => SHOTS[s].half)],
];
for (const [g, s] of groups) if (s.length) await run(g, s);
console.log('ALL DONE');
