// 起動処理：データ読み込み → 島の生成 → 描画ループ。

import { loadData } from './data.js';
import { createUI } from './ui.js';
import { generateTerrain, generateDeco, buildNav, DISTRICT_INDEX, DISTRICTS, HALF, TERRAIN_SEED } from './terrain.js';
import { resolveBuildings } from './buildings.js';
import { createPathfinder } from './pathfind.js';
import { createSim, resolveHub } from './sim.js';
import { showDistrictLabels } from './zoom.js';
import { layoutDrifters } from './drift.js';

const params = new URLSearchParams(location.search);
const DEBUG = params.has('debug');
const DEMO = params.has('demo'); // ?demo … data/demo/ の「育った島」のデモデータを表示

// 時計。?t=（エポックms か ISO日時）で開始時刻を、?freeze で停止を指定できる（確認用）。
const clock = (() => {
  let offset = 0;
  const frozen = params.has('freeze');
  if (params.has('t')) {
    const raw = params.get('t');
    const t = /^\d+$/.test(raw) ? Number(raw) : Date.parse(raw);
    if (Number.isFinite(t)) offset = t - Date.now();
  }
  const start = Date.now();
  return { now: () => (frozen ? start + offset : Date.now() + offset) };
})();

const ui = createUI({
  now: clock.now,
  onSelectIslander: (index, opts) => selectIslander(index, opts),
  onSelectDrifter: (index, opts) => selectDrifter(index, opts),
  onCloseDetail: () => deselect(),
  onSheetChange: () => syncViewShift(),
  onRecenter: () => {
    ui.closeDetail(true);
    app?.orbit.overview();
  },
});

let app = null; // 3D一式（生成に失敗しても一覧・年表・投票は使える）
let selected = -1; // 選択中の島民
let selectedDrifter = -1; // 選択中の漂流者

function selectIslander(index, opts = {}) {
  selected = index;
  selectedDrifter = -1;
  ui.showIslander(index, opts);
  if (app) {
    app.orbit.followTarget(() => app.actors.positionOf(index), 46);
    syncViewShift();
  }
}

function selectDrifter(index, opts = {}) {
  selected = -1;
  selectedDrifter = index;
  ui.showDrifter(index, opts);
  if (app) {
    app.orbit.followTarget(() => app.actors.drifterPositionOf(index), 46);
    syncViewShift();
  }
}

function deselect() {
  selected = -1;
  selectedDrifter = -1;
  app?.orbit.stopFollow();
  syncViewShift();
}

function syncViewShift() {
  if (!app) return;
  // シートが下から重なるぶん、島の中心を上へずらす
  requestAnimationFrame(() => {
    const overlap = ui.expectedOverlap();
    const hud = document.getElementById('hud').getBoundingClientRect().height;
    app.orbit.setViewShift(Math.max(0, (overlap - hud) / 2));
  });
}

async function boot() {
  ui.setLoading('島を読み込み中…');
  let data;
  try {
    data = await loadData({ demo: DEMO });
  } catch (err) {
    console.error(err);
    ui.showStageError('島のデータを読み込めませんでした。通信状況を確認して、もう一度ひらいてください。');
    return;
  }
  ui.renderData(data);

  try {
    app = await buildIsland(data);
  } catch (err) {
    console.error(err);
    ui.showStageError('この端末では島の3D表示を開始できませんでした。島民・年表・投票は下のタブから見られます。');
    return;
  }
  // 3D側で作ったスプライトを一覧のアイコンにも使い回す
  const portraitOf = (atlas) => {
    const c = document.createElement('canvas');
    c.width = 18;
    c.height = 24;
    c.className = 'portrait';
    if (atlas) c.getContext('2d').drawImage(atlas, 0, 0, 18, 24, 0, 0, 18, 24);
    return c;
  };
  ui.renderData(data, {
    portraitFor: (p, index) => portraitOf(app.actors.atlasOf(index)),
    drifterPortraitFor: (p, index) => portraitOf(app.actors.drifterAtlasOf(index)),
  });
  ui.setLoading('');
  syncViewShift();
  if (params.has('who')) {
    // 島民でも漂流者でも、その人を選んだ状態で開く
    const who = params.get('who');
    const i = data.islanders.findIndex((p) => p.id === who);
    const j = data.drifters.findIndex((p) => p.id === who);
    if (i >= 0) selectIslander(i, { fromList: false });
    else if (j >= 0) selectDrifter(j, { fromList: false });
  }
}

async function buildIsland({ state, islanders, drifters = [] }) {
  const THREE = await import('../lib/three.module.js');
  const { createWorld } = await import('./world.js');
  const { createActors } = await import('./actors.js');
  const { createOrbit } = await import('./camera.js');

  const stage = document.getElementById('stage');
  const canvas = document.getElementById('scene');
  const labelLayer = document.getElementById('labels');

  // 島の生成（すべて決定的）。拠点（広場）は最初の投票で決まるまで無い。
  let base = state.base;
  let terrain = generateTerrain(TERRAIN_SEED, { base });
  if (base && terrain.heightAt(base.x, base.z) < 1) {
    console.warn('state.json の base が島の外（海）を指しているので、拠点は未決定として表示します。', base);
    base = null;
    terrain = generateTerrain();
  }
  // 島民の集まり場：拠点が決まっていれば拠点、まだなら漂着した砂浜
  const hub = resolveHub(base);
  const built = resolveBuildings(state.buildings, terrain);
  const hubCell = terrain.cellOf(hub.x, hub.z);
  for (let dj = -2; dj <= 2; dj++) {
    for (let di = -2; di <= 2; di++) if (terrain.inGrid(hubCell.i + di, hubCell.j + dj)) built.reserved.add(terrain.idx(hubCell.i + di, hubCell.j + dj));
  }
  if (hub.isBase) built.blocked.add(terrain.idx(hubCell.i, hubCell.j)); // たき火のマス
  const roadCells = forestRoadCells(state.forestRoad, terrain);
  for (const k of roadCells) built.reserved.add(k);
  const deco = generateDeco(terrain, (i, j) => built.reserved.has(terrain.idx(i, j)));
  // 島民の行動範囲の外（森・高原などの自然の障壁の向こう）。集まり場のある地区は必ず範囲に入れる。
  const hubDistrict = terrain.district[terrain.idx(hubCell.i, hubCell.j)];
  const outOfRange = new Set(
    state.districts
      .filter((d) => !d.inRange)
      .map((d) => DISTRICT_INDEX[d.id])
      .filter((n) => n !== hubDistrict),
  );
  const nav = buildNav(terrain, { blocked: built.blocked, decks: built.decks, outOfRange, deco, origin: { x: hub.x, z: hub.z } });
  const pathfinder = createPathfinder(terrain, nav);
  const sim = createSim({ terrain, nav, pathfinder, islanders, buildings: built.list, hub, outOfRange });

  // 漂流者は漂着地点の沖の海に（sim とは別。浅瀬の岩はよける）
  const drifts = layoutDrifters(drifters, terrain, { avoid: deco.filter((d) => d.kind === 'searock') });

  const trailCells = sim.trails();
  for (const k of roadCells) trailCells.add(k);
  const world = createWorld({ canvas, terrain, deco, buildings: built.list, hub, trailCells });
  const actors = createActors({ scene: world.scene, islanders, sim, labelLayer, drifters, drifts, heightAt: (x, z) => terrain.heightAt(x, z) });

  // 地区ラベル。拠点が決まったら、拠点のある地区は拠点の名前を拠点の位置に出す。
  const districtLabels = world.districtAnchors.map((a) => {
    const info = state.districts.find((d) => d.id === a.id);
    const node = document.createElement('div');
    node.className = 'dlabel';
    let pos = a.pos;
    let name = info?.name || a.name;
    let lift = false;
    if (hub.isBase && a.index === hubDistrict) {
      name = hub.label;
      pos = new THREE.Vector3(hub.x, Math.max(1, terrain.heightAt(hub.x, hub.z)) + 4, hub.z);
      lift = true; // 拠点の真上に浮かべる（広場に集まった島民を隠さない）
    } else if (a.id === 'beach' && drifts.length) {
      lift = true; // 沖の漂流者を隠さないよう、砂浜の地区名は上に浮かべる
    }
    node.textContent = name;
    labelLayer.append(node);
    return { node, pos, lift, shown: null };
  });

  let viewport = { w: 1, h: 1 };
  const orbit = createOrbit({
    camera: world.camera,
    dom: canvas,
    islandRadius: HALF * 0.8,
    onTap: (x, y) => handleTap(x, y),
  });

  function handleTap(x, y) {
    const hit = actors.pick(x, y);
    if (hit) {
      if (hit.kind === 'drifter') selectDrifter(hit.index, { fromList: false });
      else selectIslander(hit.index, { fromList: false });
      return;
    }
    const nx = (x / viewport.w) * 2 - 1;
    const ny = -(y / viewport.h) * 2 + 1;
    const p = world.pick(nx, ny);
    if (!p) return;
    if (p.type === 'building') {
      selected = -1;
      selectedDrifter = -1;
      ui.showBuilding(p.building);
      orbit.focus({ x: p.building.x, y: p.building.y + 2, z: p.building.z }, 58);
      syncViewShift();
      return;
    }
    if (ui.selectedIndex() >= 0 || document.getElementById('panel').dataset.view === 'detail') ui.closeDetail();
    if (p.point.y > 0.6) orbit.focus({ x: p.point.x, y: Math.max(1, p.point.y), z: p.point.z }, Math.min(orbit.goal.dist, 90));
    if (DEBUG) {
      const c = terrain.cellOf(p.point.x, p.point.z);
      const k = terrain.idx(c.i, c.j);
      const d = terrain.district[k];
      ui.toast(`x: ${Math.round(p.point.x)} / z: ${Math.round(p.point.z)} / 高さ: ${terrain.h[k]} / ${d < DISTRICTS.length ? DISTRICTS[d].name : '海'}`, 6000);
    }
  }

  function resize() {
    const r = stage.getBoundingClientRect();
    viewport = { w: Math.max(1, Math.round(r.width)), h: Math.max(1, Math.round(r.height)) };
    world.resize(viewport.w, viewport.h);
    orbit.setSize(viewport.w, viewport.h);
  }
  resize();
  new ResizeObserver(resize).observe(stage);
  orbit.overview(true);

  // 時刻に合わせた空（?hour=12 のように固定もできる）
  const fixedHour = params.has('hour') ? Number(params.get('hour')) : null;
  const applySky = () => {
    const d = new Date(clock.now());
    const hour = Number.isFinite(fixedHour) && fixedHour !== null ? fixedHour : d.getHours() + d.getMinutes() / 60;
    const sky = world.setTimeOfDay(hour);
    document.documentElement.style.setProperty('--sky', `#${sky.getHexString()}`);
  };
  applySky();
  setInterval(applySky, 60000);

  const v = new THREE.Vector3();
  let last = performance.now();
  let lastNow = 0;
  function frame(nowPerf) {
    const dt = Math.min(0.1, (nowPerf - last) / 1000);
    last = nowPerf;
    const t = clock.now();

    orbit.update(dt);
    world.update(t);
    actors.update(t, dt, world.camera, viewport, selected, orbit.state.dist, selectedDrifter);

    // 地区名は引いたときだけ、島民名は寄ったときだけ（段階は zoom.js）
    const far = showDistrictLabels(orbit.state.dist, viewport.h);
    for (const d of districtLabels) {
      v.copy(d.pos).project(world.camera);
      const show = far && v.z < 1 && Math.abs(v.x) < 1 && Math.abs(v.y) < 1;
      if (show !== d.shown) {
        d.node.classList.toggle('is-on', show);
        d.shown = show;
      }
      if (show) d.node.style.transform = `translate(${Math.round((v.x * 0.5 + 0.5) * viewport.w)}px, ${Math.round((-v.y * 0.5 + 0.5) * viewport.h)}px) translate(-50%, ${d.lift ? 'calc(-100% - 12px)' : '-50%'})`;
    }

    if (selected >= 0 && nowPerf - lastNow > 500) {
      lastNow = nowPerf;
      const lost = islanders[selected]?.missing;
      const td = islanders[selected]?.today;
      ui.setNow(lost ? { label: '行方不明', text: lost.text, next: '', missing: true } : td ? { label: 'きょうの行動', text: td.text, next: '次の動画まで続けています' } : sim.status(selected, t));
    }

    world.render();
    requestAnimationFrame(frame);
  }
  requestAnimationFrame(frame);

  const api = { world, actors, orbit, sim, terrain, nav, clock, hub, drifts };
  if (DEBUG) window.__island = api;
  return api;
}

// 森の道づくり：森の入口から光の場所へ、島民の数 ÷ need の長さだけ道を切りひらく（その幅のマスは木が無く、道の色になる）
function forestRoadCells(road, terrain) {
  const cells = new Set();
  if (!road) return cells;
  const pts = road.points;
  const seg = [];
  let total = 0;
  for (let n = 0; n < pts.length - 1; n++) {
    const len = Math.hypot(pts[n + 1][0] - pts[n][0], pts[n + 1][1] - pts[n][1]);
    seg.push(len);
    total += len;
  }
  const reach = total * Math.min(1, road.count / road.need);
  const half = road.width / 2;
  let walked = 0;
  for (let n = 0; n < seg.length && walked < reach; n++) {
    const [x0, z0] = pts[n];
    const [x1, z1] = pts[n + 1];
    for (let s = 0; s <= seg[n] && walked + s <= reach; s += 0.5) {
      const u = s / seg[n];
      const x = x0 + (x1 - x0) * u;
      const z = z0 + (z1 - z0) * u;
      const c = terrain.cellOf(x, z);
      for (let dj = -2; dj <= 2; dj++) {
        for (let di = -2; di <= 2; di++) {
          if (!terrain.inGrid(c.i + di, c.j + dj)) continue;
          const cc = terrain.cellCenter(c.i + di, c.j + dj);
          if (Math.hypot(cc.x - x, cc.z - z) <= half) cells.add(terrain.idx(c.i + di, c.j + dj));
        }
      }
    }
    walked += seg[n];
  }
  return cells;
}

boot();

// Service Worker（http/https で配信されているときだけ）
if ('serviceWorker' in navigator && /^https?:$/.test(location.protocol) && !params.has('nosw')) {
  window.addEventListener('load', () => {
    navigator.serviceWorker
      .register('./sw.js')
      .then(applyUpdatesWhenHidden)
      .catch((err) => console.warn('Service Worker を登録できませんでした', err));
  });
}

// 新しい版のプログラムが届いていたら、画面が裏に回ったとき（アプリを閉じた・切り替えた）に
// 入れ替えて読み直す。島を見ている最中に勝手に読み直すことはしない。
function applyUpdatesWhenHidden(reg) {
  let reloading = false;
  let lastCheck = Date.now();
  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'visible') {
      // 開きっぱなしの端末でも、ときどき新しい版を確かめる
      if (Date.now() - lastCheck > 3600 * 1000) {
        lastCheck = Date.now();
        reg.update().catch(() => {});
      }
      return;
    }
    if (reg.waiting && navigator.serviceWorker.controller) {
      reloading = true;
      reg.waiting.postMessage('skipWaiting');
    }
  });
  navigator.serviceWorker.addEventListener('controllerchange', () => {
    if (reloading) location.reload();
  });
}
