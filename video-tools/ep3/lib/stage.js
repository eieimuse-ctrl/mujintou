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
    const castAll = [...new Set([...(story.cast || []), ...(story.groups || []).flatMap((g) => g.members || [])])];
    const cast = castAll.filter((id) => idx.has(id));

    // ---- 置き場所（groups）：shore＝岸に沿って、line＝陸で横一列、ring＝輪になって ----
    // 互換：story.place（shore 1つ）だけなら、cast 全員をその1群に入れる
    const groupsIn = story.groups || [{ name: 'main', ...story.place, members: story.cast }];
    const seaDir = (x, z) => {
      let wx = 0, wz = 0;
      for (let k = 0; k < 72; k++) { const g = (k / 72) * Math.PI * 2, cx = Math.sin(g), cz = Math.cos(g); if (T.heightAt(x + cx * 8, z + cz * 8) < 1) { wx += cx; wz += cz; } }
      const l = Math.hypot(wx, wz) || 1;
      return { x: wx / l, z: wz / l };
    };
    const G = new Map();
    const slot = new Map(); // id → {x, z, g}（最初に入っている群＝その人の持ち場）
    const gslot = new Map(); // 群の名前 → (id → {x, z, g})：その群の中での各人の場所（集合のとき使う）
    for (const gi of groupsIn) {
      const sp = { x: gi.spot[0], z: gi.spot[1] };
      let F; // 群の「前」＝人が向く方向
      if (gi.type === 'shore' || !gi.type) F = seaDir(sp.x, sp.z);
      else if (Array.isArray(gi.face)) { const l = Math.hypot(gi.face[0], gi.face[1]) || 1; F = { x: gi.face[0] / l, z: gi.face[1] / l }; }
      else F = { x: 0, z: 1 };
      const Tg = { x: -F.z, z: F.x };
      const g = { name: gi.name, type: gi.type || 'shore', sp, F, Tg, gap: gi.gap ?? 2.4, back: gi.back ?? 1.4 };
      g.at = (al, n = 0) => {
        let bx = sp.x + Tg.x * al, bz = sp.z + Tg.z * al;
        if (g.type === 'shore') {
          let last = -30;
          for (let s2 = -30; s2 <= 30; s2 += 0.25) if (T.heightAt(bx + F.x * s2, bz + F.z * s2) >= 1) last = s2;
          bx += F.x * (last - g.back); bz += F.z * (last - g.back);
        }
        return { x: bx - F.x * n, z: bz - F.z * n };
      };
      G.set(g.name, g);
      const mem = (gi.members || []).filter((id) => idx.has(id));
      const gs = new Map(); gslot.set(g.name, gs);
      mem.forEach((id, k) => {
        const jitter = (hash01(id, 3) - 0.5) * (gi.jitter ?? 0.5);
        let p;
        if (g.type === 'ring') {
          // 輪：内側から 8, 14, 20 … 人ずつ
          let r = 0, cap = 8, kk = k, ring = 0;
          while (kk >= cap) { kk -= cap; ring++; cap += 6; }
          r = (gi.radius ?? 5) + ring * (gi.gap ?? 2.6);
          const ang = (2 * Math.PI * kk) / cap + ring * 0.4;
          p = { x: sp.x + Math.sin(ang) * r + jitter, z: sp.z + Math.cos(ang) * r };
        } else {
          const side = k === 0 ? 0 : (k % 2 ? 1 : -1) * Math.ceil(k / 2);
          const row = gi.rows ? Math.floor(Math.abs(side) / gi.rows) : 0;
          p = g.at(side * g.gap + jitter, row * (gi.rowGap ?? 2.2));
        }
        gs.set(id, { x: p.x, z: p.z, g });
        if (!slot.has(id)) slot.set(id, { x: p.x, z: p.z, g });
      });
    }
    const firstG = G.values().next().value;
    // 相対位置 {rel: ID か 'g:群の名前', t: 群の横方向, n: 群の奥(+)／前(-), up}
    // t を渡すと、rel の人の「その時刻にいる場所」を基準にする（場面ごとに持ち場が変わるため）
    const resolve = (r, t) => {
      if (!r) return null;
      if (Array.isArray(r)) return { x: r[0], z: r[1], y: yAt(r[0], r[1]) };
      let base, g;
      if (typeof r.rel === 'string' && r.rel.startsWith('g:')) { g = G.get(r.rel.slice(2)) || firstG; base = g.at(0); }
      else if (slot.has(r.rel) && t != null && keys.has(r.rel)) { const s2 = stateOf(r.rel, t); g = s2.g || firstG; base = s2; }
      else if (slot.has(r.rel)) { const s2 = slot.get(r.rel); g = s2.g; base = s2; }
      else { g = firstG; base = g.sp; }
      const x = base.x + g.Tg.x * (r.t || 0) - g.F.x * (r.n || 0);
      const z = base.z + g.Tg.z * (r.t || 0) - g.F.z * (r.n || 0);
      return { x, z, y: yAt(x, z) + (r.up || 0), g };
    };
    const groupOf = (r) => (r && r.rel && String(r.rel).startsWith('g:') ? G.get(String(r.rel).slice(2)) : slot.get(r?.rel)?.g) || firstG;

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
      const home = slot.get(id) || { x: 0, z: 0, g: firstG };
      const st = { pos: home, anim: 'idle', frame: null, hide: !slot.has(id), face: 'front', move: null, moveAnim: 'walk', g: home.g, torch: false };
      for (const k of keys.get(id)) {
        if (k.t > t) break;
        const at = k.at && k.at.slot ? gslot.get(k.at.slot)?.get(id) : null;
        const to = k.to && k.to.slot ? gslot.get(k.to.slot)?.get(id) : null;
        if (at) { st.pos = at; st.g = at.g; st.move = null; }
        else if (k.at) { const q = resolve(k.at, k.t); st.pos = q; st.g = q.g || groupOf(k.at); st.move = null; }
        if (to) { st.move = { from: moving(st, k.t), to, t0: k.t, t1: k.t + (k.dur || 1) }; st.g = to.g; st.moveAnim = k.run ? 'run' : 'walk'; }
        else if (k.to) { const q = resolve(k.to, k.t); st.move = { from: k.from ? resolve(k.from, k.t) : moving(st, k.t), to: q, t0: k.t, t1: k.t + (k.dur || 1) }; st.g = q.g || groupOf(k.to); st.moveAnim = k.run ? 'run' : 'walk'; }
        if (k.anim) { st.anim = k.anim; st.frame = null; }
        if (k.frame !== undefined) st.frame = k.frame;
        if (k.hide !== undefined) st.hide = k.hide;
        if (k.torch !== undefined) st.torch = k.torch;
        if (k.face) st.face = k.face;
      }
      let p = st.pos, walking = false;
      if (st.move) {
        const u = (t - st.move.t0) / (st.move.t1 - st.move.t0);
        if (u < 1) { const e = Math.max(0, u); p = { x: st.move.from.x + (st.move.to.x - st.move.from.x) * e, z: st.move.from.z + (st.move.to.z - st.move.from.z) * e }; walking = true; }
        else p = st.move.to;
      }
      const g = st.g || firstG;
      let dx = g.F.x, dz = g.F.z;
      if (walking) { dx = st.move.to.x - st.move.from.x; dz = st.move.to.z - st.move.from.z; }
      else if (st.face === 'back' || st.face === 'land') { dx = -g.F.x; dz = -g.F.z; }
      else if (st.face && st.face.to && slot.has(st.face.to)) { const q = posAt(st.face.to, t); dx = q.x - p.x; dz = q.z - p.z; }
      else if (st.face && st.face.at) { const q = resolve(st.face.at, t); dx = q.x - p.x; dz = q.z - p.z; }
      else if (st.face === 'left') { dx = -g.Tg.x; dz = -g.Tg.z; }
      else if (st.face === 'right') { dx = g.Tg.x; dz = g.Tg.z; }
      return { x: p.x, z: p.z, g, dx, dz, anim: walking ? st.moveAnim : st.anim, frame: walking ? null : st.frame, hide: st.hide, torch: st.torch };
    };
    const posAt = (id, t) => { const s = stateOf(id, t); return { x: s.x, z: s.z }; };
    function moving(st, t) {
      if (!st.move) return st.pos;
      const u = Math.min(1, Math.max(0, (t - st.move.t0) / (st.move.t1 - st.move.t0)));
      return { x: st.move.from.x + (st.move.to.x - st.move.from.x) * u, z: st.move.from.z + (st.move.to.z - st.move.from.z) * u };
    }

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
      fruit: pixel([
        '...gg...',
        '..gg....',
        '.rrrrr..',
        'rrwrrrr.',
        'rrrrrrr.',
        'rrrrrrr.',
        '.rrrrr..',
        '..rrr...',
      ], { g: '#3f8f3a', r: '#d94a5a', w: '#ffd0d6' }),
      crate: pixel([
        'kkkkkkkkkk',
        'kbbbbbbbbk',
        'kbkbbbbkbk',
        'kbbkbbkbbk',
        'kbbbkkbbbk',
        'kbbkbbkbbk',
        'kbkbbbbkbk',
        'kbbbbbbbbk',
        'kkkkkkkkkk',
      ], { k: '#4a2f1b', b: '#b07a44' }),
      question: pixel([
        '..kkkkkkkk..',
        '.kwwwwwwwwk.',
        'kwwwkkkkwwwk',
        'kwwkkwwkkwwk',
        'kwwwwwwkkwwk',
        'kwwwwwkkwwwk',
        'kwwwwkkwwwwk',
        'kwwwwkkwwwwk',
        'kwwwwwwwwwwk',
        'kwwwwkkwwwwk',
        '.kwwwkkwwwk.',
        '..kkkwwkkk..',
        '....kwk.....',
        '.....k......',
      ], { k: '#231d36', w: '#ffffff' }),
      flame: pixel([
        '...y....',
        '..yoy...',
        '.yoOoy..',
        'yoOOOoy.',
        'yoOOOoy.',
        '.ooOoo..',
        'kbkbkbk.',
      ], { y: '#ffd04a', o: '#ff8a1e', O: '#fff3b0', k: '#3a2a1c', b: '#7a4f2c' }),
      heart: pixel([
        '.kk.kk.',
        'kRRkRRk',
        'kRWRRRk',
        'kRRRRRk',
        '.kRRRk.',
        '..kRk..',
        '...k...',
      ], { k: '#5a1424', R: '#ff5a7a', W: '#ffd0da' }),
      zzz: pixel([
        'kkkkk....',
        '...k.....',
        '..k..kkkk',
        '.k.....k.',
        'kkkkk.k..',
        '.....kkkk',
      ], { k: '#ffffff' }),
      splash: pixel([
        '.w...w...w.',
        '..w.www.w..',
        'w..wwwww..w',
        '.wwwwwwwww.',
      ], { w: '#ffffff' }),
    };
    const props = (story.props || []).map((pr) => {
      const art = ART[pr.type];
      const sp2 = new SpriteC(new MatC({ map: art.tex, alphaTest: 0.5, transparent: false, depthTest: !['splash', 'question', 'zzz', 'heart'].includes(pr.type), fog: !['question', 'flame'].includes(pr.type) }));
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
      const A = P.A || (P.A = resolve(pr.from, pr.t0)), B = P.B || (P.B = resolve(pr.to || pr.from, pr.t0));
      const u = ease((t - pr.t0) / Math.max(0.01, pr.t1 - pr.t0));
      const arc = (pr.arc || 0) * 4 * u * (1 - u);
      const x = A.x + (B.x - A.x) * u, z = A.z + (B.z - A.z) * u, y = A.y + (B.y - A.y) * u + arc;
      const wob = pr.type === 'fish' ? Math.sin(t * 30) * 0.08 : pr.type === 'heart' ? Math.abs(Math.sin(t * 5 + (pr.phase || 0))) * 0.35 : pr.type === 'zzz' ? ((t * 0.8 + (pr.phase || 0)) % 1) * 1.2 : 0;
      if (pr.type === 'flame') P.sp.scale.set(P.sp.scale.x, (pr.size || 1.4) * (1 + 0.1 * Math.sin(t * 17)), 1);
      P.sp.position.set(x, y + wob, z);
      P.sp.visible = true;
      return { x, y, z };
    };

    // ---- カメラ：ショットごとにキー（look は相対位置）。az は「海側から見る」を0にした角度 ----
    const shots = story.camera.map((sh) => ({
      from: sh.from, to: sh.to, hour: sh.hour ?? story.hour ?? 10,
      keys: sh.keys.map((k) => {
        const L = resolve(k.look, k.t);
        const g = k.frame ? G.get(k.frame) : L.g || firstG;
        const baseAz = Math.atan2(g.F.x, g.F.z);
        return { t: k.t, tx: L.x, ty: L.y + (k.up ?? 2), tz: L.z, dist: Math.log(k.dist), az: baseAz + (k.az || 0), pol: k.pol ?? 1.28, fov: k.fov ?? 40 };
      }),
    }));
    const camAt = (t) => {
      const sh = shots.find((s) => t >= s.from && t < s.to) || shots[shots.length - 1];
      const ts = sh.keys.map((k) => k.t), o = { hour: sh.hour };
      for (const f of ['tx', 'ty', 'tz', 'dist', 'az', 'pol', 'fov']) o[f] = pchip(ts, sh.keys.map((k) => k[f]), t);
      o.dist = Math.exp(o.dist);
      return o;
    };

    // ---- 3D の小道具：tree（切られて倒れる木）・build（建物が下から組み上がる） ----
    let IM = null, GR = null;
    scene.traverse((o) => { if (!IM && o.isInstancedMesh) IM = o; if (!GR && o.isGroup) GR = o; });
    const BoxG = IM.geometry.constructor, LamM = IM.material.constructor, MeshC = Object.getPrototypeOf(IM.constructor.prototype).constructor, GroupC = GR.constructor;
    const unit = new BoxG(1, 1, 1);
    const mats = new Map();
    const mat = (c) => { if (!mats.has(c)) mats.set(c, new LamM({ color: c })); return mats.get(c); };
    const boxMesh = (x, y, z, w, h, d, c) => { const m = new MeshC(unit, mat(c)); m.position.set(x, y, z); m.scale.set(w, h, d); return m; };
    const solids = [];
    for (const pr of story.props3d || []) {
      const g = new GroupC();
      const P0 = resolve(pr.at, pr.t0 || 0);
      g.position.set(P0.x, yAt(P0.x, P0.z) - 0.1, P0.z);
      g.rotation.y = ((pr.rot || 0) * Math.PI) / 180;
      const parts = [];
      if (pr.type === 'tree') {
        const s0 = pr.size || 1.25;
        const pivot = new GroupC(); // 根元で倒す
        pivot.add(boxMesh(0, 1.1 * s0, 0, 0.7 * s0, 2.2 * s0, 0.7 * s0, '#7a4f2c'));
        pivot.add(boxMesh(0, 2.9 * s0, 0, 3.0 * s0, 1.7 * s0, 3.0 * s0, '#3a963a'));
        pivot.add(boxMesh(0.2 * s0, 4.2 * s0, -0.15 * s0, 2.0 * s0, 1.2 * s0, 2.0 * s0, '#5cbc4a'));
        g.add(pivot);
        const stump = boxMesh(0, 0.25 * s0, 0, 0.75 * s0, 0.5 * s0, 0.75 * s0, '#8a5a34');
        stump.visible = false;
        g.add(stump);
        parts.push(pivot, stump);
      } else if (pr.type === 'build') {
        const def = (window.__BUILD_DEFS || {})[pr.kind || 'hut'];
        const order = def.boxes.map((b, i) => ({ b, i })).sort((p, q) => p.b.p[1] - p.b.p[1] || p.i - q.i).sort((p, q) => p.b.p[1] - q.b.p[1]);
        for (const { b } of order) {
          const m = boxMesh(b.p[0], b.p[1], b.p[2], b.s[0], b.s[1], b.s[2], b.c);
          m.userData.full = [b.s[0], b.s[1], b.s[2]];
          m.visible = false;
          g.add(m);
          parts.push(m);
        }
      } else if (pr.type === 'float') {
        // 海から流れ着く物（建物の形をそのまま使う）。from（海）→ at（浜）へ t0〜t1 で寄ってくる
        const def = (window.__BUILD_DEFS || {})[pr.kind || 'bigcrate'];
        const inner = new GroupC();
        for (const b of def.boxes) inner.add(boxMesh(b.p[0], b.p[1], b.p[2], b.s[0], b.s[1], b.s[2], b.c));
        g.add(inner);
        parts.push(inner);
        const F = resolve(pr.from || pr.at, pr.t0 || 0); pr._f = [F.x, F.z]; pr._a = [P0.x, P0.z];
      } else if (pr.type === 'logs') {
        for (let k = 0; k < (pr.count || 3); k++) {
          const m = boxMesh(0, 0.35 + k * 0.62, (k % 2) * 0.3, 3.6, 0.6, 0.6, k % 2 ? '#8a5a34' : '#7a4f2c');
          m.visible = false; g.add(m); parts.push(m);
        }
      }
      scene.add(g);
      solids.push({ pr, g, parts });
    }
    const solidAt = (Q, t) => {
      const pr = Q.pr;
      Q.g.visible = t >= (pr.show ?? 0) && t <= (pr.hide ?? 1e9);
      if (pr.type === 'tree') {
        const [pivot, stump] = Q.parts;
        // 切る間は小刻みに揺れ、t0〜t1 で倒れ、そのあとは横たわる
        let ang = 0, shake = 0;
        if (t >= pr.t0 && t < pr.t1) { const u = (t - pr.t0) / (pr.t1 - pr.t0); ang = (Math.PI / 2) * u * u; }
        else if (t >= pr.t1) ang = Math.PI / 2 - 0.04 * Math.max(0, 1 - (t - pr.t1) * 4) * Math.sin((t - pr.t1) * 30);
        if (pr.chop != null && t >= pr.chop && t < pr.t0) shake = 0.05 * Math.sin(t * 40);
        pivot.rotation.z = -(ang + shake);
        stump.visible = t >= pr.t0;
        pivot.visible = t <= (pr.t2 ?? 1e9);
      } else if (pr.type === 'build') {
        const n = Q.parts.length, u = Math.max(0, Math.min(1, (t - pr.t0) / (pr.t1 - pr.t0)));
        Q.parts.forEach((m, k) => {
          const st = k / n, e = Math.max(0, Math.min(1, (u - st) * n / 2.5));
          m.visible = e > 0;
          const f = m.userData.full, pop = e < 1 ? 0.6 + 0.4 * e : 1;
          m.scale.set(f[0] * pop, f[1] * e, f[2] * pop);
        });
      } else if (pr.type === 'float') {
        const u = Math.max(0, Math.min(1, (t - pr.t0) / Math.max(0.01, pr.t1 - pr.t0)));
        const e = 1 - (1 - u) * (1 - u);
        const x = pr._f[0] + (pr._a[0] - pr._f[0]) * e, z = pr._f[1] + (pr._a[1] - pr._f[1]) * e;
        const wet = 1 - u; // 海の上では沈み、揺れる。浜に着くと止まる
        Q.g.position.set(x, yAt(x, z) - 0.1 - (pr.sink ?? 1.6) * wet + Math.sin(t * 2.2) * 0.35 * wet, z);
        Q.parts[0].rotation.z = Math.sin(t * 1.7) * 0.08 * wet;
        Q.parts[0].rotation.x = Math.sin(t * 1.3 + 1) * 0.06 * wet;
      } else if (pr.type === 'logs') {
        Q.parts.forEach((m, k) => { m.visible = t >= pr.t0 + k * ((pr.t1 - pr.t0) / Q.parts.length); });
      }
    };

    // ---- 手前の木を消す（カットアウェイ）：カメラと、映したい人（注視点・画面に入る島民）を結ぶ線のそばにある木や岩を、そのコマだけ見えなくする ----
    const deco = [];
    scene.traverse((o) => {
      if (!o.isInstancedMesh || o.count < 1) return;
      const arr = o.instanceMatrix.array;
      const pos = new Float32Array(o.count * 3);
      const ext = new Float32Array(o.count); // 箱の半径（いちばん長い辺の半分）。葉のような大きな箱も、ふちまで含めて判定する
      for (let i = 0; i < o.count; i++) {
        const b = i * 16;
        pos[i * 3] = arr[b + 12]; pos[i * 3 + 1] = arr[b + 13]; pos[i * 3 + 2] = arr[b + 14];
        const sx = Math.hypot(arr[b], arr[b + 1], arr[b + 2]), sy = Math.hypot(arr[b + 4], arr[b + 5], arr[b + 6]), sz = Math.hypot(arr[b + 8], arr[b + 9], arr[b + 10]);
        ext[i] = 0.5 * Math.hypot(sx, sy, sz);
      }
      deco.push({ o, orig: new Float32Array(arr), pos, ext, hidden: [] });
    });
    const CUT_R = story.cutaway?.radius ?? 1.6; // 線からの余白（箱の大きさは別に足す）
    const cutaway = (camPos, targets) => {
      if (story.cutaway === false) return;
      const segs = targets.map((q) => { const dx = q.x - camPos.x, dy = q.y - camPos.y, dz = q.z - camPos.z; const L = Math.hypot(dx, dy, dz) || 1; return { dx: dx / L, dy: dy / L, dz: dz / L, L }; });
      for (const D of deco) {
        const arr = D.o.instanceMatrix.array;
        let dirty = false;
        for (const i of D.hidden) { arr.set(D.orig.subarray(i * 16, i * 16 + 16), i * 16); dirty = true; }
        D.hidden = [];
        const P = D.pos, E = D.ext, n = D.o.count;
        for (let i = 0; i < n; i++) {
          const px = P[i * 3] - camPos.x, py = P[i * 3 + 1] - camPos.y, pz = P[i * 3 + 2] - camPos.z;
          const e = E[i];
          for (const g of segs) {
            const along = px * g.dx + py * g.dy + pz * g.dz;
            // 箱の手前のふちが人より手前にあれば対象（中心が少し後ろでも、ふちが顔にかぶるため）。完全に人の後ろの箱は残す
            if (along + e < 0.3 || along - e > g.L - 0.3) continue;
            const ox = px - g.dx * along, oy = py - g.dy * along, oz = pz - g.dz * along;
            const r = CUT_R + e;
            if (ox * ox + oy * oy + oz * oz < r * r) {
              for (let k = 0; k < 16; k++) arr[i * 16 + k] = 0;
              D.hidden.push(i); dirty = true; break;
            }
          }
        }
        if (dirty) D.o.instanceMatrix.needsUpdate = true;
      }
    };

    S = { cast, idx, stateOf, props, propAt, camAt, story, solids, solidAt, cutaway };
    globalThis.__stagePose = (i) => {
      const id = people[i].id;
      if (!keys.has(id)) return { x: 0, y: -80, z: 0, dx: 0, dz: 1, anim: 'idle' };
      const s = stateOf(id, window.__filmT || 0);
      if (s.hide) return { x: s.x, y: -80, z: s.z, dx: 0, dz: 1, anim: 'idle' };
      return { x: s.x, y: yAt(s.x, s.z), z: s.z, dx: s.dx, dz: s.dz, anim: s.anim, frame: s.frame, bubble: null, line: '', torch: s.torch };
    };
    return { cast, missing: castAll.filter((id) => !idx.has(id)), n: cast.length, groups: [...G.keys()] };
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
    for (const Q of S.solids) S.solidAt(Q, t);
    {
      const tg = [{ x: c.tx, y: c.ty, z: c.tz }];
      for (const x of a.actors.actors) {
        const q = x.sprite.position;
        if (q.y < -50 || !x.sprite.visible) continue;
        const k = x.scale || 1, hy = q.y + 3.0 * k;
        tmp.set(q.x, hy, q.z).project(cam);
        if (tmp.z < 1 && Math.abs(tmp.x) < 1.05 && Math.abs(tmp.y) < 1.05 && cam.position.distanceTo(q) < 60) { tg.push({ x: q.x, y: hy, z: q.z }); tg.push({ x: q.x, y: q.y + 1.2 * k, z: q.z }); }
        if (tg.length > 32) break;
      }
      S.cutaway(cam.position, tg);
    }
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
