// ep2 capture rig (2日目アニメーション): fable_rig.mjs + video/stage2 (port 8774) + actors.
// The app's rAF loop is stopped; each frame = pose camera -> world.update -> actors.update -> render.
// Islanders follow globalThis.__stagePose (the film script, set by ep2_rec.mjs); drifters follow __landing.
import puppeteer from 'puppeteer-core';

const EXE = process.env.HOME + '/.cache/puppeteer/chrome-headless-shell/linux-157.0.8103.50/chrome-headless-shell-linux64/chrome-headless-shell';
export const BASE_T = Date.parse('2026-11-18T09:00:00+09:00');

export async function openStage({ w = 540, h = 960, dsf = 2, set = '' } = {}) {
  const browser = await puppeteer.launch({
    executablePath: EXE,
    args: ['--no-sandbox', '--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--js-flags=--max-old-space-size=384'],
    protocolTimeout: 180000,
  });
  const page = await browser.newPage();
  await page.setViewport({ width: w, height: h, deviceScaleFactor: dsf });
  page.on('pageerror', (e) => console.log('pageerror:', String(e).slice(0, 200)));
  await page.goto(`http://127.0.0.1:8774/index.html?debug&nosw&freeze&t=${BASE_T}${set ? '&set=' + set : ''}`, { waitUntil: 'networkidle0', timeout: 90000 });
  await page.waitForFunction(() => window.__island, { timeout: 60000 });
  const info = await page.evaluate((vw, vh) => {
    window.requestAnimationFrame = () => 0;
    const a = window.__island;
    const src = a.world.renderer.domElement;
    const c = document.createElement('canvas');
    c.width = src.width; c.height = src.height;
    const V = a.world.camera.position.constructor;
    window.__cap = { src, c, ctx: c.getContext('2d'), V, v: new V(), fov0: a.world.camera.fov, vp: { w: vw, h: vh } };
    window.__ground = (x, z) => Math.max(0.45, a.terrain.heightAt(x, z) || 0);
    // pose: {tx,ty,tz,dist,az,pol,hour,fov,simT,actT,filmT,landing, pts:[[x,y,z],...]}
    window.__pose = (p) => {
      const cam = a.world.camera;
      const sp = Math.sin(p.pol);
      cam.position.set(p.tx + p.dist * sp * Math.sin(p.az), p.ty + p.dist * Math.cos(p.pol), p.tz + p.dist * sp * Math.cos(p.az));
      if (cam.view) cam.clearViewOffset();
      const fov = p.fov || window.__cap.fov0;
      if (cam.fov !== fov) { cam.fov = fov; cam.updateProjectionMatrix(); }
      cam.lookAt(p.tx, p.ty, p.tz);
      cam.updateMatrixWorld();
      window.__filmT = p.filmT;
      globalThis.__landing = p.landing || null;
      a.world.update(p.simT);
      a.world.setTimeOfDay(p.hour);
      for (const x of a.actors.actors) x.y = null; // no height smoothing: every frame is a pure function of its pose
      a.actors.update(p.actT, 1 / 24, cam, window.__cap.vp, -1, p.dist, -1);
      const v = window.__cap.v;
      const proj = (x, y, z) => {
        v.set(x, y, z).project(cam);
        const d = Math.hypot(cam.position.x - x, cam.position.y - y, cam.position.z - z);
        return [+(v.x * 0.5 + 0.5).toFixed(5), +(-v.y * 0.5 + 0.5).toFixed(5), v.z < 1 ? +d.toFixed(2) : -1];
      };
      const pts = (p.pts || []).map(([x, y, z]) => proj(x, y, z));
      // head (top of sprite) and feet of every islander on screen
      const heads = a.actors.actors.map((x) => { const q = x.sprite.position, k = x.scale || 1; const hd = proj(q.x, q.y + 3.9 * k, q.z); const ft = proj(q.x, q.y, q.z); return [hd[0], hd[1], ft[0], ft[1], hd[2]]; });
      const ground = Math.max(0.45, a.terrain.heightAt(cam.position.x, cam.position.z) || 0);
      return { pts, heads, clear: +(cam.position.y - ground).toFixed(2), cam: cam.position.toArray().map((n) => +n.toFixed(1)) };
    };
    window.__frame = async (pose, q) => {
      const { src, c, ctx } = window.__cap;
      const meta = window.__pose(pose);
      a.world.render();
      ctx.drawImage(src, 0, 0);
      const blob = await new Promise((r) => c.toBlob(r, 'image/jpeg', q));
      const buf = new Uint8Array(await blob.arrayBuffer());
      let bin = '';
      for (let k = 0; k < buf.length; k += 32768) bin += String.fromCharCode(...buf.subarray(k, k + 32768));
      return { meta, b64: btoa(bin) };
    };
    return { cw: src.width, ch: src.height, fov: a.world.camera.fov, hub: a.hub, nIsl: a.actors.actors.length, nDrift: a.actors.castaways.length };
  }, w, h);
  return { browser, page, info };
}

export async function shoot(page, pose, q = 0.93) {
  const r = await page.evaluate((p, q) => window.__frame(p, q), pose, q);
  return { meta: r.meta, jpg: Buffer.from(r.b64, 'base64') };
}
