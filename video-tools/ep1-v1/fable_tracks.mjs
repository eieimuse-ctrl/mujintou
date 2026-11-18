// Screen-space tracks of POINTS for every film frame (no rendering) -> build/tracks.json
import fs from 'node:fs';
import { openIsland, BASE_T } from './fable_rig.mjs';
import { SHOTS, POINTS, FPS, poseAt, frameCount } from './fable_timeline.mjs';
const { browser, page } = await openIsland({ w: 270, h: 480, dsf: 1 });
const names = Object.keys(POINTS);
const pts = [];
for (const n of names) {
  const [x, y, z] = POINTS[n];
  pts.push([x, typeof y === 'string' ? (await page.evaluate((x, z) => window.__ground(x, z), x, z)) + Number(y.slice(2)) : y, z]);
}
const out = { names, world: pts, fps: FPS, shots: {} };
for (const shot of Object.keys(SHOTS)) {
  const N = frameCount(shot);
  const poses = Array.from({ length: N }, (_, i) => ({ ...poseAt(shot, SHOTS[shot].from + i / FPS), simT: BASE_T, pts }));
  const res = await page.evaluate((ps) => ps.map((p) => { const m = window.__pose(p); return { pts: m.pts, hour: p.hour, dist: p.dist }; }), poses);
  out.shots[shot] = { from: SHOTS[shot].from, frames: res };
  console.log(shot, N);
}
fs.writeFileSync(process.env.HOME + '/workspace/mujintou/video/build/tracks.json', JSON.stringify(out));
await browser.close();
