// v3: screen-space tracks + camera of every frame of every take (a, b2, c, d, p), computed without a browser
// (same projection as fable_rig.__pose; checked against the recorder's own track.jsonl).
// compose_fable_v3.py projects arbitrary world points with the exported camera (the lying castaway).
//   node fable_tracks_v3.mjs   -> build/tracks_v3.json
import fs from 'node:fs';
import { SHOTS, FPS, poseAt, frameCount } from './fable_timeline_v3.mjs';
const V = process.env.HOME + '/workspace/mujintou/video/build';
const P = JSON.parse(fs.readFileSync(`${V}/rec3/points.json`, 'utf8'));
const ASPECT = P.w / P.h; // 1080/1920 = 540/960 (take p is recorded at half size, same aspect)
const sub = (a, b) => [a[0] - b[0], a[1] - b[1], a[2] - b[2]];
const dot = (a, b) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
const cross = (a, b) => [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]];
const norm = (a) => { const l = Math.hypot(...a); return a.map((v) => v / l); };
function camOf(p) {
  const sp = Math.sin(p.pol);
  const C = [p.tx + p.dist * sp * Math.sin(p.az), p.ty + p.dist * Math.cos(p.pol), p.tz + p.dist * sp * Math.cos(p.az)];
  const f = norm(sub([p.tx, p.ty, p.tz], C)), r = norm(cross(f, [0, 1, 0])), u = cross(r, f);
  return { C, f, r, u, th: Math.tan((p.fov * Math.PI) / 360) };
}
function project(c, w) {
  const d = sub(w, c.C), z = dot(d, c.f);
  if (z <= 0.1) return [0, 0, -1];
  return [+(dot(d, c.r) / (z * c.th * ASPECT) * 0.5 + 0.5).toFixed(5), +(-dot(d, c.u) / (z * c.th) * 0.5 + 0.5).toFixed(5), +Math.hypot(...d).toFixed(2)];
}
const out = { names: P.names, world: P.world, fps: FPS, aspect: ASPECT, shots: {} };
let worst = 0;
for (const shot of ['a', 'b2', 'c', 'd', 'p']) {
  const N = frameCount(shot);
  const frames = [];
  for (let i = 0; i < N; i++) {
    const p = poseAt(shot, SHOTS[shot].from + i / FPS); const c = camOf(p);
    frames.push({ pts: P.world.map((w) => project(c, w)), hour: p.hour, dist: p.dist, cam: [...c.C, ...c.f, ...c.r, ...c.u, c.th].map((v) => +v.toFixed(6)) });
  }
  out.shots[shot] = { from: SHOTS[shot].from, n: N, frames };
  const tj = `${V}/${shot === 'p' ? 'rec3h' : 'rec3'}/${shot}/track.jsonl`;
  let n = 0, maxErr = 0, lines = 0;
  if (fs.existsSync(tj)) for (const line of fs.readFileSync(tj, 'utf8').trim().split('\n')) {
    const r = JSON.parse(line); const m = frames[r.i].pts; lines++;
    r.pts.forEach((q, k) => {
      const onScreen = q[2] > 0 && q[0] > -0.2 && q[0] < 1.2 && q[1] > -0.2 && q[1] < 1.2;
      if (onScreen && m[k][2] > 0) { maxErr = Math.max(maxErr, Math.abs(q[0] - m[k][0]) * P.w, Math.abs(q[1] - m[k][1]) * P.h); n++; }
    });
  }
  worst = Math.max(worst, maxErr);
  console.log(shot, N, 'frames; track.jsonl lines', lines, '; checked', n, 'on-screen points, max error', maxErr.toFixed(3), 'px (1080x1920 scale)');
}
fs.writeFileSync(`${V}/tracks_v3.json`, JSON.stringify(out));
console.log(worst < 1 ? 'TRACKS OK' : 'TRACKS MISMATCH');
