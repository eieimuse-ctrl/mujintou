// ep3 録画用：ページの中で台本（story JSON）を解釈して、島民・小道具・カメラを1コマずつ決める。
// rig.mjs が page.evaluate でこのファイルの中身を流し込む。サイトのコードには手を入れない（actors.js の __stagePose フックだけ使う）。
// すべてのコマは「台本 × フィルム時刻」の純関数（途中で止めても同じコマから再開できる）。
(() => {
  const a = window.__island;
  const T = a.terrain;
  const cam = a.world.camera;
  const yAt = (x, z) => Math.max(0.45, T.heightAt(x, z) || 0);
  const V3 = cam.position.constructor;
  const tmp = new V3();

  // ---- 補間（カメラは ep2 と同じ pchip） ----
  function pchip(ts, ys, t) {
    const n = ts.length;
    if (n === 1 || t <= ts[0]) return ys[0];
    if (t >= ts[n - 1]) return ys[n - 1];
    const h = [], d = [];
    for (let i = 0; i < n - 1; i++) { h.push(ts[i + 1] - ts[i]); d.push((ys[i + 1] - ys[i]) / h[i]); }
    const m = new Array(n).fill(0);
    for (let i = 1; i < n - 1; i++) {
      if (d[i - 1] * d[i] > 0) { const w1 = 2 * h[i] + h[i - 1], w2 = h[i] + 2 * h[i - 1]; m[i] = (w1 + w2) / (w1 / d[i - 1] + w2 / d[i]); }
    }
    let i = 0;
    while (t > ts[i + 1]) i++;
    const s = (t - ts[i]) / h[i], s2 = s * s, s3 = s2 * s;
    return (2 * s3 - 3 * s2 + 1) * ys[i] + (s3 - 2 * s2 + s) * h[i] * m[i] + (-2 * s3 + 3 * s2) * ys[i + 1] + (s3 - s2) * h[i] * m[i + 1];
  }
  const ease = (u) => { u = Math.max(0, Math.min(1, u)); return u * u * (3 - 2 * u); };
  const hash01 = (s, k) => { let h = 2166136261 ^ k; for (let i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 16777619); } return ((h >>> 0) % 100000) / 100000; };

  let S = null; // 解釈ずみの台本

  function setup(story) {
    const people = a.actors.actors.map((x) => x.person);
    const idx = new Map(people.map((p, i) => [p.id, i]));
    const cast = story.cast.filter((id) => idx.has(id));

    // ---- 場所：岸に沿って並ぶ（shore） ----
    const pl = story.place;
    const sp = { x: pl.spot[0], z: pl.spot[1] };
    let wx = 0, wz = 0;
    for (let k = 0; k < 72; k++) { const g = (k / 72) * Math.PI * 2, cx = Math.sin(g), cz = Math.cos(g); if (T.heightAt(sp.x + cx * 8, sp.z + cz * 8) < 1) { wx += cx; wz += cz; } }
    const wl = Math.hypot(wx, wz) || 1;
    const W = { x: wx / wl, z: wz / wl }; // 海の向き
    const Tg = { x: -W.z, z: W.x }; // 岸に沿う向き
    const coast = (al) => {
      const bx = sp.x + Tg.x * al, bz = sp.z + Tg.z * al;
      let last = -30;
      for (let s = -30; s <= 30; s += 0.25) if (T.heightAt(bx + W.x * s, bz + W.z * s) >= 1) last = s;
      return { x: bx + W.x * (last - (pl.back ?? 1.4)), z: bz + W.z * (last - (pl.back ?? 1.4)) };
    };
    // 並び：cast[0] が真ん中、あとは左右交互
    const slot = new Map();
    const gap = pl.gap ?? 2.4;
    cast.forEach((id, k) => {
      const side = k === 0 ? 0 : (k % 2 ? 1 : -1) * Math.ceil(k / 2);
      const jitter = (hash01(id, 3) - 0.5) * (pl.jitter ?? 0.5);
      slot.set(id, coast(side * gap + jitter));
    });

    // 相対位置 {rel: id|'line', t: 岸沿い, n: 陸の奥へ(+)／海へ(-), up}
    const resolve = (r) => {
      if (!r) return null;
      const base = r.rel === 'line' || !slot.has(r.rel) ? sp : slot.get(r.rel);
      const x = base.x + Tg.x * (r.t || 0) - W.x * (r.n || 0);
      const z = base.z + Tg.z * (r.t || 0) - W.z * (r.n || 0);
      return { x, z, y: yAt(x, z) + (r.up || 0) };
    };

    // ---- 島民の台本：人ごとのキーを時刻順に ----
    const keys = new Map(cast.map((id) => [id, []]));
    const whoList = (w, act) => {
      let list = w === '*' ? cast.slice() : Array.isArray(w) ? w : [w];
      if (act.except) list = list.filter((id) => !act.except.includes(id));
      if (act.pick != null) list = list.filter((id) => hash01(id, act.seed || 7) < act.pick);
      return list.filter((id) => keys.has(id));
    };
    for (const act of story.acts) for (const id of whoList(act.who, act)) keys.get(id).push(act);
    for (const [, ks] of keys) ks.sort((p, q) => p.t - q.t);

    // 人ごとの状態（その時刻までのキーを積み上げる）
    const stateOf = (id, t) => {
      const st = { pos: slot.get(id), anim: 'idle', frame: null, hide: false, face: 'water', move: null };
      for (const k of keys.get(id)) {
        if (k.t > t) break;
        if (k.at) st.pos = resolve(k.at);
        if (k.to) st.move = { from: st.pos, to: resolve(k.to), t0: k.t, t1: k.t + (k.dur || 1) };
        if (k.anim) { st.anim = k.anim; st.frame = null; }
        if (k.frame !== undefined) st.frame = k.frame;
        if (k.hide !== undefined) st.hide = k.hide;
        if (k.face) st.face = k.face;
      }
      let p = st.pos, walking = false;
      if (st.move) {
        const u = (t - st.move.t0) / (st.move.t1 - st.move.t0);
        if (u < 1) { const e = Math.max(0, u); p = { x: st.move.from.x + (st.move.to.x - st.move.from.x) * e, z: st.move.from.z + (st.move.to.z - st.move.from.z) * e }; walking = true; }
        else p = st.move.to;
      }
      let dx = W.x, dz = W.z;
      if (walking) { dx = st.move.to.x - st.move.from.x; dz = st.move.to.z - st.move.from.z; }
      else if (st.face === 'land') { dx = -W.x; dz = -W.z; }
      else if (st.face && st.face.to && slot.has(st.face.to)) { const q = posAt(st.face.to, t); dx = q.x - p.x; dz = q.z - p.z; }
      else if (st.face === 'left') { dx = -Tg.x; dz = -Tg.z; }
      else if (st.face === 'right') { dx = Tg.x; dz = Tg.z; }
      return { x: p.x, z: p.z, dx, dz, anim: walking ? 'walk' : st.anim, frame: walking ? null : st.frame, hide: st.hide };
    };
    const posAt = (id, t) => { const s = stateOf(id, t); return { x: s.x, z: s.z }; };

    // ---- 小道具（ドット絵のスプライト） ----
    const proto = a.actors.actors[0].sprite;
    const SpriteC = proto.constructor, MatC = proto.material.constructor, TexC = proto.material.map.constructor;
    const scene = a.world.scene;
    const pixel = (rows, pal) => {
      const c = document.createElement('canvas'); c.width = rows[0].length; c.height = rows.length;
      const g = c.getContext('2d');
      rows.forEach((r, y) => [...r].forEach((ch, x) => { if (pal[ch]) { g.fillStyle = pal[ch]; g.fillRect(x, y, 1, 1); } }));
      const t = new TexC(c); t.magFilter = t.minFilter = 1003; t.generateMipmaps = false; t.colorSpace = 'srgb';
      return { tex: t, w: c.width, h: c.height };
    };
    const ART = {
      fish: pixel([
        '....kkkk....',
        '..kkbbbbk.kk',
        '.kbbwbbbbkbk',
        'kbkbbbbbbbbk',
        '.kbbbbbbbkbk',
        '..kkbbbbk.kk',
        '....kkkk....',
      ], { k: '#231d36', b: '#7fb7e0', w: '#ffffff' }),
      splash: pixel([
        '.w...w...w.',
        '..w.www.w..',
        'w..wwwww..w',
        '.wwwwwwwww.',
      ], { w: '#ffffff' }),
    };
    const props = (story.props || []).map((pr) => {
      const art = ART[pr.type];
      const sp2 = new SpriteC(new MatC({ map: art.tex, alphaTest: 0.5, transparent: false, depthTest: pr.type !== 'splash' }));
      const hgt = pr.size || 1.4;
      sp2.scale.set((hgt * art.w) / art.h, hgt, 1);
      sp2.center.set(0.5, 0);
      sp2.renderOrder = 6;
      sp2.visible = false;
      scene.add(sp2);
      return { pr, sp: sp2 };
    });
    const propAt = (P, t) => {
      const pr = P.pr;
      if (t < pr.t0 || t > (pr.t2 ?? pr.t1)) { P.sp.visible = false; return null; }
      const A = resolve(pr.from), B = resolve(pr.to || pr.from);
      const u = ease((t - pr.t0) / Math.max(0.01, pr.t1 - pr.t0));
      const arc = (pr.arc || 0) * 4 * u * (1 - u);
      const x = A.x + (B.x - A.x) * u, z = A.z + (B.z - A.z) * u, y = A.y + (B.y - A.y) * u + arc;
      const wob = pr.type === 'fish' ? Math.sin(t * 30) * 0.08 : 0;
      P.sp.position.set(x, y + wob, z);
      P.sp.visible = true;
      return { x, y, z };
    };

    // ---- カメラ：ショットごとにキー（look は相対位置）。az は「海側から見る」を0にした角度 ----
    const baseAz = Math.atan2(W.x, W.z);
    const shots = story.camera.map((sh) => ({
      from: sh.from, to: sh.to, hour: sh.hour ?? story.hour ?? 10,
      keys: sh.keys.map((k) => { const L = resolve(k.look); return { t: k.t, tx: L.x, ty: L.y + (k.up ?? 2), tz: L.z, dist: Math.log(k.dist), az: baseAz + (k.az || 0), pol: k.pol ?? 1.28, fov: k.fov ?? 40 }; }),
    }));
    const camAt = (t) => {
      const sh = shots.find((s) => t >= s.from && t < s.to) || shots[shots.length - 1];
      const ts = sh.keys.map((k) => k.t), o = { hour: sh.hour };
      for (const f of ['tx', 'ty', 'tz', 'dist', 'az', 'pol', 'fov']) o[f] = pchip(ts, sh.keys.map((k) => k[f]), t);
      o.dist = Math.exp(o.dist);
      return o;
    };

    S = { cast, idx, stateOf, props, propAt, camAt, story, W, Tg };
    globalThis.__stagePose = (i) => {
      const id = people[i].id;
      if (!keys.has(id)) return { x: 0, y: -80, z: 0, dx: 0, dz: 1, anim: 'idle' };
      const s = stateOf(id, window.__filmT || 0);
      if (s.hide) return { x: s.x, y: -80, z: s.z, dx: 0, dz: 1, anim: 'idle' };
      return { x: s.x, y: yAt(s.x, s.z), z: s.z, dx: s.dx, dz: s.dz, anim: s.anim, frame: s.frame, bubble: null, line: '' };
    };
    return { cast, missing: story.cast.filter((id) => !idx.has(id)), sea: W, n: cast.length };
  }

  // 1コマ：カメラを置き、島民と小道具を動かして描く。名札用に各人の頭と足の画面位置を返す
  async function frame(t, vw, vh, q) {
    window.__filmT = t;
    const c = S.camAt(t);
    const sp = Math.sin(c.pol);
    cam.position.set(c.tx + c.dist * sp * Math.sin(c.az), c.ty + c.dist * Math.cos(c.pol), c.tz + c.dist * sp * Math.cos(c.az));
    if (cam.fov !== c.fov) { cam.fov = c.fov; cam.updateProjectionMatrix(); }
    cam.lookAt(c.tx, c.ty, c.tz);
    cam.updateMatrixWorld();
    const tMs = window.__BASE_T + t * 1000;
    a.world.update(tMs);
    a.world.setTimeOfDay(c.hour);
    for (const x of a.actors.actors) x.y = null;
    a.actors.update(tMs, 1 / 24, cam, { w: vw, h: vh }, -1, c.dist, -1);
    for (const P of S.props) S.propAt(P, t);
    a.world.render();
    const proj = (x, y, z) => { tmp.set(x, y, z).project(cam); return [+(tmp.x * 0.5 + 0.5).toFixed(4), +(-tmp.y * 0.5 + 0.5).toFixed(4), tmp.z < 1]; };
    const people = {};
    for (const x of a.actors.actors) {
      const id = x.person.id;
      if (!S.cast.includes(id)) continue;
      const q2 = x.sprite.position, k = x.scale || 1;
      if (q2.y < -50) continue;
      const hd = proj(q2.x, q2.y + 3.9 * k, q2.z), ft = proj(q2.x, q2.y, q2.z);
      const on = hd[2] && ft[0] > -0.05 && ft[0] < 1.05 && hd[1] < 1.05 && ft[1] > -0.05;
      if (on) people[id] = { hx: hd[0], hy: hd[1], fx: ft[0], fy: ft[1], d: +cam.position.distanceTo(q2).toFixed(1) };
    }
    const src = a.world.renderer.domElement;
    if (!window.__cv) { window.__cv = document.createElement('canvas'); window.__cv.width = src.width; window.__cv.height = src.height; }
    const cv = window.__cv;
    cv.getContext('2d').drawImage(src, 0, 0);
    const blob = await new Promise((r) => cv.toBlob(r, 'image/jpeg', q));
    const buf = new Uint8Array(await blob.arrayBuffer());
    let bin = '';
    for (let k = 0; k < buf.length; k += 32768) bin += String.fromCharCode(...buf.subarray(k, k + 32768));
    return { b64: btoa(bin), people };
  }

  window.__ep3 = { setup, frame };
})();
