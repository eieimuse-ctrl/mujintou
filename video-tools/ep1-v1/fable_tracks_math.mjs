// Screen-space tracks of POINTS for every film frame, computed without a browser
// (same projection as fable_rig.__pose; verified against the recorder's track.jsonl).
//   node fable_tracks_math.mjs          -> build/tracks.json
import fs from 'node:fs';
import { SHOTS, FPS, poseAt, frameCount } from './fable_timeline.mjs';
const V = process.env.HOME + '/workspace/mujintou/video/build';
const P = JSON.parse(fs.readFileSync(`${V}/rec/points.json`, 'utf8'));
const ASPECT = P.w / P.h;
const sub = (a, b) => [a[0] - b[0], a[1] - b[1], a[2] - b[2]];
const dot = (a, b) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
const cross = (a, b) => [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]];
const norm = (a) => { const l = Math.hypot(...a); return a.map((v) => v / l); };
function project(p) {
  const sp = Math.sin(p.pol);
  const C = [p.tx + p.dist * sp * Math.sin(p.az), p.ty + p.dist * Math.cos(p.pol), p.tz + p.dist * sp * Math.cos(p.az)];
  const f = norm(sub([p.tx, p.ty, p.tz], C)), r = norm(cross(f, [0, 1, 0])), u = cross(r, f);
  const th = Math.tan((p.fov * Math.PI) / 360);
  return P.world.map((w) => {
    const d = sub(w, C), z = dot(d, f);
    if (z <= 0.1) return [0, 0, -1];
    return [+(dot(d, r) / (z * th * ASPECT) * 0.5 + 0.5).toFixed(5), +(-dot(d, u) / (z * th) * 0.5 + 0.5).toFixed(5), +Math.hypot(...d).toFixed(2)];
  });
}
const out = { names: P.names, world: P.world, fps: FPS, shots: {} };
for (const shot of Object.keys(SHOTS)) {
  const N = frameCount(shot);
  const frames = [];
  for (let i = 0; i < N; i++) { const p = poseAt(shot, SHOTS[shot].from + i / FPS); frames.push({ pts: project(p), hour: p.hour, dist: p.dist }); }
  out.shots[shot] = { from: SHOTS[shot].from, frames };
  // verify against what the recorder measured in the real scene
  const tj = `${V}/rec/${shot}/track.jsonl`;
  let n = 0, maxErr = 0;
  if (fs.existsSync(tj)) for (const line of fs.readFileSync(tj, 'utf8').trim().split('\n')) {
    const r = JSON.parse(line); const m = frames[r.i].pts;
    r.pts.forEach((q, k) => { if (q[2] > 0 && m[k][2] > 0) { maxErr = Math.max(maxErr, Math.abs(q[0] - m[k][0]) * P.w, Math.abs(q[1] - m[k][1]) * P.h); n++; } else if ((q[2] > 0) !== (m[k][2] > 0)) console.log('visibility mismatch', shot, r.i, P.names[k], q, m[k]); });
  }
  console.log(shot, N, 'frames; checked', n, 'points against track.jsonl, max error', maxErr.toFixed(3), 'px');
}
fs.writeFileSync(`${V}/tracks.json`, JSON.stringify(out));
