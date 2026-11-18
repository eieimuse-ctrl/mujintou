// v3 recorder (enlarged island): same method as fable_rec.mjs, takes from fable_timeline_v3.mjs -> build/rec3/ (--half: build/rec3h/).
//   node fable_rec.mjs --preview [shots]   540x960, every 3rd frame, no blur  -> build/prev/<shot>/
//   node fable_rec.mjs [shots]             1080x1920, every frame, motion blur -> build/rec/<shot>/
// Resumable: frames already on disk are skipped; tracks are appended to track.jsonl.
import fs from 'node:fs';
import { openIsland, shoot, BASE_T } from './fable_rig.mjs';
import { SHOTS, POINTS, FPS, poseAt, frameCount } from './fable_timeline_v3.mjs';

const args = process.argv.slice(2);
const PREVIEW = args.includes('--preview');
const HALF = args.includes('--half'); // 540x960, every frame (take p: only shown inside the phone)
const shots = args.filter((a) => !a.startsWith('--'));
const names = shots.length ? shots : Object.keys(SHOTS);
const ROOT = process.env.HOME + '/workspace/mujintou/video/build/' + (PREVIEW ? 'prev3' : HALF ? 'rec3h' : 'rec3');
const STEP = PREVIEW ? 3 : 1;
const SIM_SPEED = 2.2; // sea/cloud animation speed relative to film time
const SHUTTER = 0.5 / FPS; // 180-degree shutter

const { browser, page, info } = await openIsland(PREVIEW || HALF ? { w: 540, h: 960, dsf: 1 } : { w: 540, h: 960, dsf: 2 });
console.log('canvas', info.cw, info.ch, 'islander labels', info.islanders);
const W = info.cw, H = info.ch;

const ptNames = Object.keys(POINTS);
const pts = [];
for (const n of ptNames) {
  const [x, y, z] = POINTS[n];
  const yy = typeof y === 'string' ? (await page.evaluate((x, z) => window.__ground(x, z), x, z)) + Number(y.slice(2)) : y;
  pts.push([x, yy, z]);
}
fs.mkdirSync(ROOT, { recursive: true });
fs.writeFileSync(`${ROOT}/points.json`, JSON.stringify({ names: ptNames, world: pts, w: W, h: H, fps: FPS, step: STEP }));

const full = (shot, t) => ({ ...poseAt(shot, t), simT: BASE_T + t * 1000 * SIM_SPEED, pts });

for (const shot of names) {
  const dir = `${ROOT}/${shot}`;
  fs.mkdirSync(dir, { recursive: true });
  const N = frameCount(shot);
  const t0 = Date.now();
  let done = 0, minClear = 1e9, maxSub = 0;
  for (let i = 0; i < N; i += STEP) {
    const file = `${dir}/f${String(i).padStart(5, '0')}.jpg`;
    if (fs.existsSync(file) && fs.statSync(file).size > 1000) continue;
    const t = SHOTS[shot].from + i / FPS;
    const centre = full(shot, t);
    let subs = null;
    if (!PREVIEW) {
      // how far does the picture move during the shutter? -> number of sub-samples
      const a = await page.evaluate((p) => window.__pose(p), full(shot, t - SHUTTER / 2));
      const b = await page.evaluate((p) => window.__pose(p), full(shot, t + SHUTTER / 2));
      let disp = 0;
      a.pts.forEach((pa, k) => { const pb = b.pts[k]; if (pa[2] > 0 && pb[2] > 0 && pa[0] > -0.5 && pa[0] < 1.5 && pa[1] > -0.5 && pa[1] < 1.5) disp = Math.max(disp, Math.hypot((pa[0] - pb[0]) * W, (pa[1] - pb[1]) * H)); });
      const n = Math.max(1, Math.min(6, Math.ceil(disp / 5)));
      maxSub = Math.max(maxSub, n);
      if (n > 1) subs = Array.from({ length: n }, (_, j) => full(shot, t + ((j + 0.5) / n - 0.5) * SHUTTER));
    }
    const { meta, jpg } = await shoot(page, centre, PREVIEW ? 0.82 : 0.94, subs);
    fs.writeFileSync(file + '.tmp', jpg);
    fs.renameSync(file + '.tmp', file);
    fs.appendFileSync(`${dir}/track.jsonl`, JSON.stringify({ i, t: +t.toFixed(4), n: subs ? subs.length : 1, clear: meta.clear, cam: meta.cam, pts: meta.pts }) + '\n');
    minClear = Math.min(minClear, meta.clear);
    done++;
    if (done % 48 === 0) console.log(shot, i, '/', N, ((Date.now() - t0) / 1000).toFixed(0) + 's', new Date().toISOString());
  }
  console.log(shot, 'done:', done, 'new frames of', N, 'in', ((Date.now() - t0) / 1000).toFixed(0) + 's', 'minClear', minClear, 'maxSub', maxSub);
}
await browser.close();
console.log('ALL DONE');
