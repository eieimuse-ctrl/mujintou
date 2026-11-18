// Shared capture rig for the ep1 revision.
// The app's own rAF loop is stopped; every frame is posed and rendered by hand, so a
// frame is a pure function of its pose (resumable, ~0.75 s per 1080x1920 frame here).
import puppeteer from 'puppeteer-core';

const EXE = process.env.HOME + '/.cache/puppeteer/chrome-headless-shell/linux-157.0.8103.50/chrome-headless-shell-linux64/chrome-headless-shell';
export const BASE_T = Date.parse('2026-11-17T10:00:00+09:00');

export async function openIsland({ w = 540, h = 960, dsf = 2 } = {}) {
  const browser = await puppeteer.launch({
    executablePath: EXE,
    args: ['--no-sandbox', '--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'],
    protocolTimeout: 180000,
  });
  const page = await browser.newPage();
  await page.setViewport({ width: w, height: h, deviceScaleFactor: dsf });
  page.on('pageerror', (e) => console.log('pageerror:', String(e).slice(0, 200)));
  // no ?demo: the real day-1 island, zero islanders
  await page.goto(`http://127.0.0.1:8773/index.html?debug&nosw&freeze&t=${BASE_T}`, { waitUntil: 'networkidle0', timeout: 60000 });
  await page.waitForFunction(() => window.__island, { timeout: 30000 });
  const info = await page.evaluate(() => {
    window.requestAnimationFrame = () => 0;
    const a = window.__island;
    const src = a.world.renderer.domElement;
    const c = document.createElement('canvas');
    c.width = src.width; c.height = src.height;
    const V = a.world.camera.position.constructor;
    window.__cap = { src, c, ctx: c.getContext('2d'), V, v: new V(), fov0: a.world.camera.fov };
    // pose: {tx,ty,tz,dist,az,pol,hour,fov,simT, pts:[[x,y,z],...]} -> projected pts + clearance
    window.__pose = (p) => {
      const cam = a.world.camera;
      const sp = Math.sin(p.pol);
      cam.position.set(p.tx + p.dist * sp * Math.sin(p.az), p.ty + p.dist * Math.cos(p.pol), p.tz + p.dist * sp * Math.cos(p.az));
      if (cam.view) cam.clearViewOffset();
      const fov = p.fov || window.__cap.fov0;
      if (cam.fov !== fov) { cam.fov = fov; cam.updateProjectionMatrix(); }
      cam.lookAt(p.tx, p.ty, p.tz);
      cam.updateMatrixWorld();
      a.world.update(p.simT);
      a.world.setTimeOfDay(p.hour);
      const v = window.__cap.v;
      const pts = (p.pts || []).map(([x, y, z]) => {
        v.set(x, y, z).project(cam);
        const d = Math.hypot(cam.position.x - x, cam.position.y - y, cam.position.z - z);
        return [+(v.x * 0.5 + 0.5).toFixed(5), +(-v.y * 0.5 + 0.5).toFixed(5), v.z < 1 ? +d.toFixed(2) : -1];
      });
      const ground = Math.max(0.45, a.terrain.heightAt(cam.position.x, cam.position.z) || 0);
      return { pts, clear: +(cam.position.y - ground).toFixed(2), cam: cam.position.toArray().map((n) => +n.toFixed(1)) };
    };
    // one output frame = average of n sub-poses (motion blur); returns meta of the centre pose
    window.__frame = async (centre, subs, q) => {
      const { src, c, ctx } = window.__cap;
      subs.forEach((p, k) => {
        window.__pose(p);
        a.world.render();
        ctx.globalAlpha = 1 / (k + 1);
        ctx.drawImage(src, 0, 0);
      });
      ctx.globalAlpha = 1;
      const meta = window.__pose(centre);
      const blob = await new Promise((r) => c.toBlob(r, 'image/jpeg', q));
      const buf = new Uint8Array(await blob.arrayBuffer());
      let bin = '';
      for (let k = 0; k < buf.length; k += 32768) bin += String.fromCharCode(...buf.subarray(k, k + 32768));
      return { meta, b64: btoa(bin) };
    };
    window.__ground = (x, z) => Math.max(0.45, a.terrain.heightAt(x, z) || 0);
    const actors = a.actors;
    return {
      cw: src.width, ch: src.height, fov: a.world.camera.fov,
      islanders: document.querySelectorAll('.islander-label, .name-tag').length,
      anchors: a.world.districtAnchors.map((d) => ({ id: d.id, x: d.pos.x, y: d.pos.y, z: d.pos.z, ground: a.terrain.heightAt(d.pos.x, d.pos.z) })),
      actorKeys: Object.keys(actors),
    };
  });
  return { browser, page, info };
}

export async function shoot(page, pose, q = 0.93, subs = null) {
  const r = await page.evaluate((c, s, q) => window.__frame(c, s, q), pose, subs || [pose], q);
  return { meta: r.meta, jpg: Buffer.from(r.b64, 'base64') };
}
