// 島民の表示：ドット絵スプライト、足もとの影、吹き出し、頭上の名前ラベル（DOM）。
// 吹き出しはアイコン（会話・ハート・音符・いなずま）がスプライト、セリフ（文字）が名前ラベルの上の DOM。
// 名前ラベルとセリフは、カメラの距離に応じて出し分ける（zoom.js）。
// 漂流者（drift.js）も同じスプライトで、沖の海に腰から下を沈めて描く（名前ラベルの出し方と上限は島民と共通）。

import * as THREE from '../lib/three.module.js';
import { islanderAtlas, bubbleCanvas, FRAME_W, FRAME_H, FRAME_COUNT, FRAMES, BUBBLE_W, BUBBLE_H } from './pixelart.js';
import { hashStr } from './rng.js';
import { MAX_LABELS } from './config.js';
import { nameLabelLook } from './zoom.js';
import { SEA_Y } from './terrain.js';
import { driftPose } from './drift.js';

const SPRITE_H = 3.9; // スプライト1コマの高さ（ワールド単位）
const SPRITE_W = (SPRITE_H * FRAME_W) / FRAME_H;
const MIN_PX = 30; // 引いて見ても、これより小さくはしない（画面上の高さ）
const WATERLINE = 0.4; // 漂流者のスプライトは、下からこの割合が水面の下
const DRIFT_VISIBLE = 1 - WATERLINE;

// 「？」の吹き出し（白地・濃い枠のドット絵）
function questionCanvas() {
  const rows = [
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
  ];
  const c = document.createElement('canvas');
  c.width = rows[0].length;
  c.height = rows.length;
  const g = c.getContext('2d');
  rows.forEach((r, y) => [...r].forEach((ch, x) => {
    if (ch === '.') return;
    g.fillStyle = ch === 'k' ? '#231d36' : '#ffffff';
    g.fillRect(x, y, 1, 1);
  }));
  return c;
}

function pixelTexture(canvas) {
  const t = new THREE.CanvasTexture(canvas);
  t.magFilter = THREE.NearestFilter;
  t.minFilter = THREE.NearestFilter;
  t.generateMipmaps = false;
  t.colorSpace = THREE.SRGBColorSpace;
  return t;
}

// drifters: 漂流者（data.js の正規化済み）、drifts: その場所と揺れ方（drift.js の layoutDrifters。drifters と同じ並び）
export function createActors({ scene, islanders, sim, labelLayer, drifters = [], drifts = [], heightAt = null }) {
  const bubbleTex = {};
  for (const icon of ['talk', 'heart', 'note', 'bolt']) bubbleTex[icon] = pixelTexture(bubbleCanvas(icon));

  const shadowGeo = new THREE.CircleGeometry(0.85, 10);
  shadowGeo.rotateX(-Math.PI / 2);
  const shadowMat = new THREE.MeshBasicMaterial({ color: '#1b1630', transparent: true, opacity: 0.26, depthWrite: false });
  const ringGeo = new THREE.RingGeometry(1.25, 1.6, 20);
  ringGeo.rotateX(-Math.PI / 2);
  const ring = new THREE.Mesh(ringGeo, new THREE.MeshBasicMaterial({ color: '#ffe14a', transparent: true, opacity: 0.95, depthWrite: false, fog: false }));
  ring.visible = false;
  ring.renderOrder = 4;
  scene.add(ring);

  const actors = islanders.map((person, i) => {
    const atlas = islanderAtlas(person);
    const tex = pixelTexture(atlas);
    tex.repeat.set(1 / FRAME_COUNT, 0.5);
    const sprite = new THREE.Sprite(new THREE.SpriteMaterial({ map: tex, alphaTest: 0.5, transparent: false }));
    sprite.center.set(0.5, 1 / FRAME_H);
    sprite.scale.set(SPRITE_W, SPRITE_H, 1);
    sprite.renderOrder = 1;

    const shadow = new THREE.Mesh(shadowGeo, shadowMat);
    shadow.renderOrder = 3;

    const bubble = new THREE.Sprite(new THREE.SpriteMaterial({ map: bubbleTex.talk, alphaTest: 0.5, transparent: false, depthTest: false }));
    bubble.center.set(0.35, 0);
    bubble.visible = false;
    bubble.renderOrder = 5;

    scene.add(shadow, sprite, bubble);

    const label = document.createElement('div');
    label.className = 'label';
    label.style.display = 'none';
    const name = document.createElement('span');
    name.textContent = person.displayName;
    label.appendChild(name);
    labelLayer.appendChild(label);

    return {
      person,
      index: i,
      atlas,
      tex,
      sprite,
      shadow,
      bubble,
      label,
      speech: null, // セリフの吹き出し（初めて話すときに作る）
      speechText: '',
      line: '',
      seed: hashStr(String(person.id)),
      pos: new THREE.Vector3(),
      y: null,
      facing: 1,
      scale: 1,
      screen: { x: 0, y: 0, r: 0, visible: false },
      look: { show: false, opacity: 0, size: 0 },
      labelShown: false,
      labelSize: 0,
      labelOpacity: -1,
    };
  });

  // ---- 漂流者：沖の海にただよう（腰から下は水の中。まわりに白い波紋） ----------------
  const rippleGeo = new THREE.RingGeometry(1.15, 1.55, 20);
  rippleGeo.rotateX(-Math.PI / 2);
  const rippleMat = new THREE.MeshBasicMaterial({ color: '#ffffff', transparent: true, opacity: 0.55, depthWrite: false });
  const castaways = drifters.map((person, j) => {
    const atlas = islanderAtlas({ id: person.id, color: person.color, job: '' });
    const tex = pixelTexture(atlas);
    tex.repeat.set(1 / FRAME_COUNT, 0.5);
    const sprite = new THREE.Sprite(new THREE.SpriteMaterial({ map: tex, alphaTest: 0.5, transparent: false }));
    sprite.center.set(0.5, WATERLINE); // 水面の線をスプライトの基準点にする
    sprite.scale.set(SPRITE_W, SPRITE_H, 1);
    sprite.renderOrder = 1;
    const ripple = new THREE.Mesh(rippleGeo, rippleMat);
    ripple.renderOrder = 3;
    sprite.visible = ripple.visible = !!drifts[j];
    scene.add(sprite, ripple);

    const label = document.createElement('div');
    label.className = 'label is-drifter';
    label.style.display = 'none';
    const name = document.createElement('span');
    name.textContent = person.displayName;
    label.appendChild(name);
    labelLayer.appendChild(label);

    return {
      drifter: true,
      person,
      index: j,
      drift: drifts[j],
      pose: {},
      atlas,
      tex,
      sprite,
      ripple,
      label,
      seed: hashStr(String(person.id)),
      pos: new THREE.Vector3(),
      facing: 1,
      scale: 1,
      screen: { x: 0, y: 0, r: 0, visible: false },
      look: { show: false, opacity: 0, size: 0 },
      labelShown: false,
      labelSize: 0,
      labelOpacity: -1,
    };
  });
  const everyone = [...actors, ...castaways];

  // ---- 行方不明（data.js の missing）：森の奥に浮かぶ「？」と、そこへ続く足跡 ----
  const groundAt = (x, z) => Math.max(0.45, (heightAt && heightAt(x, z)) || 0);
  const qTex = pixelTexture(questionCanvas());
  const stepGeo = new THREE.CircleGeometry(0.42, 8);
  stepGeo.rotateX(-Math.PI / 2);
  const stepMat = new THREE.MeshBasicMaterial({ color: '#3a2a1c', transparent: true, opacity: 0.55, depthWrite: false });
  const missingMarks = [];
  for (const a of actors) {
    const m = a.person.missing;
    if (!m) continue;
    const q = new THREE.Sprite(new THREE.SpriteMaterial({ map: qTex, alphaTest: 0.5, transparent: false, depthTest: false, fog: false }));
    q.center.set(0.5, 0);
    q.renderOrder = 6;
    const gy = groundAt(m.x, m.z);
    scene.add(q);
    // 足跡：森の入口から奥へ（左右交互）
    const sx = m.x + 46, sz = m.z + 8;
    const steps = [];
    for (let k = 0; k < 14; k++) {
      const u = k / 13;
      const x = sx + (m.x - sx) * u, z = sz + (m.z - sz) * u;
      const len = Math.hypot(m.x - sx, m.z - sz) || 1;
      const side = k % 2 ? 0.5 : -0.5;
      const fx = x + (-(m.z - sz) / len) * side, fz = z + ((m.x - sx) / len) * side;
      const st = new THREE.Mesh(stepGeo, stepMat);
      st.position.set(fx, groundAt(fx, fz) + 0.06, fz);
      st.scale.set(0.7, 1, 1.15);
      st.renderOrder = 3;
      scene.add(st);
      steps.push(st);
    }
    missingMarks.push({ a, q, gy, m });
  }


  // きょうの行動：その場所でその動きを続ける（ときどき向きを変える程度）
  const todayState = {};
  function todayPose(a, td) {
    todayState.x = td.x;
    todayState.z = td.z;
    todayState.y = groundAt(td.x, td.z);
    todayState.dx = td.dx;
    todayState.dz = td.dz;
    todayState.anim = td.anim;
    todayState.frame = null;
    todayState.bubble = null;
    todayState.line = '';
    return todayState;
  }

  const right = new THREE.Vector3();
  const v = new THREE.Vector3();
  const order = [];

  // viewport: { w, h }（CSSピクセル）、zoomDist: カメラから注視点までの距離（ラベルの段階表示に使う）
  // selected: 選択中の島民の番号、selectedDrifter: 選択中の漂流者の番号（どちらも無ければ -1）
  function update(tMs, dt, camera, viewport, selected, zoomDist, selectedDrifter = -1) {
    right.setFromMatrixColumn(camera.matrixWorld, 0);
    const pxPerUnitAt1 = viewport.h / (2 * Math.tan((camera.fov * Math.PI) / 360));
    const t = tMs / 1000;
    for (const a of actors) a.selected = a.index === selected;
    for (const a of castaways) a.selected = a.index === selectedDrifter;

    // 動画の録画用：globalThis.__stagePose(i, tMs) があれば、その演技（台本）で動かす。null を返した人はふだんの暮らし。
    const stagePose = typeof globalThis.__stagePose === 'function' ? globalThis.__stagePose : null;
    const stageDrift = typeof globalThis.__stageDrift === 'function' ? globalThis.__stageDrift : null;
    for (const a of actors) {
      if (a.person.missing && !stagePose) {
        // 姿は消して、選んだときのカメラは森の奥の「？」へ
        const m = a.person.missing;
        a.sprite.visible = a.shadow.visible = a.bubble.visible = false;
        a.pos.set(m.x, groundAt(m.x, m.z) + 9, m.z); // カメラは「？」の少し下を見る
        a.screen.visible = false;
        a.line = '';
        continue;
      }
      a.sprite.visible = a.shadow.visible = true;
      const td = !stagePose && a.person.today;
      const s = (stagePose && stagePose(a.index, tMs)) || (td ? todayPose(a, td) : sim.stateAt(a.index, tMs));

      // 高さは段差でカクッとしないよう、少しなめらかに追いかける
      if (a.y === null || Math.abs(a.y - s.y) > 3) a.y = s.y;
      else a.y += (s.y - a.y) * Math.min(1, dt * 14);

      // 画面上の左右どちらを向くか
      const side = s.dx * right.x + s.dz * right.z;
      if (Math.abs(side) > 0.05 * Math.hypot(s.dx, s.dz)) a.facing = side > 0 ? 1 : -1;

      // コマ選び
      let frame = FRAMES.idle;
      let hop = 0;
      const ph = t + (a.seed % 1000) / 500;
      if (s.anim === 'walk') {
        frame = [FRAMES.walkA, FRAMES.idle, FRAMES.walkB, FRAMES.idle][Math.floor(ph * 7) % 4];
        hop = Math.floor(ph * 7) % 2 === 0 ? 0.12 : 0;
      } else if (s.anim === 'work') {
        frame = Math.floor(ph * 2.4) % 2 ? FRAMES.workB : FRAMES.workA;
      } else if (s.anim === 'cheer') {
        const c = Math.floor(ph * 2.6) % 3;
        frame = c === 0 ? FRAMES.cheer : FRAMES.idle;
        hop = c === 0 ? 0.3 : 0;
      } else if (s.anim === 'talk') {
        hop = s.bubble && Math.floor(ph * 4) % 2 ? 0.14 : 0;
      } else if (s.anim === 'sit') {
        frame = FRAMES.sit;
      } else if (s.anim === 'shock') {
        frame = FRAMES.shock;
        hop = Math.floor(ph * 6) % 2 ? 0.18 : 0;
      } else if (s.anim === 'eat') {
        frame = Math.floor(ph * 2) % 2 ? FRAMES.eat : FRAMES.idle;
      } else if (s.anim === 'run') {
        frame = [FRAMES.walkA, FRAMES.walkB][Math.floor(ph * 12) % 2];
        hop = Math.floor(ph * 12) % 2 ? 0.2 : 0;
      }
      if (s.frame != null && FRAMES[s.frame] != null) frame = FRAMES[s.frame];
      a.tex.offset.set(frame / FRAME_COUNT, a.facing > 0 ? 0.5 : 0);

      a.pos.set(s.x, a.y, s.z);
      const dist = camera.position.distanceTo(a.pos);
      const pxPerUnit = pxPerUnitAt1 / Math.max(1, dist);
      const minPx = a.index === selected ? MIN_PX + 8 : MIN_PX;
      const k = Math.max(1, minPx / (SPRITE_H * pxPerUnit));
      a.scale = k;

      a.sprite.position.set(s.x, a.y + hop * k, s.z);
      a.sprite.scale.set(SPRITE_W * k, SPRITE_H * k, 1);
      a.shadow.position.set(s.x, a.y + 0.07, s.z);
      a.shadow.scale.setScalar(k);

      // セリフ（'line'）は DOM の吹き出しで、名前ラベルの上に出す。それ以外はアイコンのスプライト。
      const iconBubble = s.bubble && s.bubble !== 'line';
      a.line = s.bubble === 'line' ? s.line : '';
      if (iconBubble) {
        a.bubble.visible = true;
        a.bubble.material.map = bubbleTex[s.bubble] || bubbleTex.talk;
        const bh = 2.3 * k;
        a.bubble.scale.set((bh * BUBBLE_W) / BUBBLE_H, bh, 1);
        a.bubble.position.set(s.x, a.y + (SPRITE_H + 0.2) * k, s.z);
      } else {
        a.bubble.visible = false;
      }

      // 画面座標（タップ判定とラベル用）
      v.set(s.x, a.y + SPRITE_H * k * 0.5, s.z).project(camera);
      const onScreen = v.z > -1 && v.z < 1 && Math.abs(v.x) < 1.15 && Math.abs(v.y) < 1.15;
      a.screen.visible = onScreen;
      a.screen.x = (v.x * 0.5 + 0.5) * viewport.w;
      a.screen.y = (-v.y * 0.5 + 0.5) * viewport.h;
      a.screen.r = Math.max(20, SPRITE_H * k * pxPerUnit * 0.6);
      a.screen.dist = dist;
      a.screen.top = a.screen.y - SPRITE_H * k * pxPerUnit * (iconBubble ? 1.15 : 0.56);
    }

    // 漂流者：位置と揺れは drift.js（データ × 時刻の純関数）。ときどき島に向かって手をふる
    for (const a of castaways) {
      if (!a.drift && !stageDrift) continue;
      const staged = stageDrift && stageDrift(a.index, tMs, a.drift);
      if (!staged && !a.drift) continue;
      const s = staged || driftPose(a.drift, tMs, a.pose);
      if (staged) a.sprite.visible = a.ripple.visible = !s.hide;
      const side = s.dx * right.x + s.dz * right.z;
      if (Math.abs(side) > 0.05 * Math.hypot(s.dx, s.dz)) a.facing = side > 0 ? 1 : -1;
      const frame = s.wave && Math.floor((t + (a.seed % 1000) / 500) * 2.6) % 2 === 0 ? FRAMES.cheer : FRAMES.idle;
      a.tex.offset.set(frame / FRAME_COUNT, a.facing > 0 ? 0.5 : 0);

      a.pos.set(s.x, s.y, s.z);
      const dist = camera.position.distanceTo(a.pos);
      const pxPerUnit = pxPerUnitAt1 / Math.max(1, dist);
      const minPx = a.selected ? MIN_PX + 8 : MIN_PX;
      // 引いたときの大きさは島民とほぼ同じ（下が水に沈むぶん、少しだけ大きめ）
      const k = Math.max(1, minPx / (SPRITE_H * 0.8 * pxPerUnit));
      a.scale = k;
      // 波の上下は、引いて大きく描いているときも見えるように大きさに合わせる（島民の跳ねと同じ扱い）
      const waterline = SEA_Y + (s.y - SEA_Y) * k;
      a.sprite.position.set(s.x, waterline, s.z);
      a.sprite.scale.set(SPRITE_W * k, SPRITE_H * k, 1);
      a.ripple.position.set(s.x, SEA_Y + 0.04, s.z);
      a.ripple.scale.setScalar(k * (1 + 0.08 * Math.sin(t * (a.drift?.bobSpeed ?? 1.3) + (a.drift?.bobPhase ?? a.seed % 7))));

      const above = SPRITE_H * k * DRIFT_VISIBLE; // 水の上に出ている高さ
      v.set(s.x, waterline + above * 0.5, s.z).project(camera);
      a.screen.visible = v.z > -1 && v.z < 1 && Math.abs(v.x) < 1.15 && Math.abs(v.y) < 1.15;
      a.screen.x = (v.x * 0.5 + 0.5) * viewport.w;
      a.screen.y = (-v.y * 0.5 + 0.5) * viewport.h;
      a.screen.r = Math.max(20, above * pxPerUnit * 0.6);
      a.screen.dist = dist;
      a.screen.top = a.screen.y - above * pxPerUnit * 0.56;
    }

    for (const mk of missingMarks) {
      const dist = camera.position.distanceTo(mk.a.pos);
      const k = Math.max(1, (MIN_PX + 10) / ((SPRITE_H * pxPerUnitAt1) / Math.max(1, dist)));
      mk.q.visible = !stagePose;
      mk.q.position.set(mk.m.x, mk.gy + 10.5 + Math.sin(t * 2.2) * 0.4 * k, mk.m.z);
      mk.q.scale.set(2.2 * k * 0.86, 2.2 * k, 1);
    }

    // ラベル：ズームの段階で出し分け（引きの全体表示では出さない）、
    // 出すものが多いときはカメラに近い順に上限（MAX_LABELS）まで（島民と漂流者をあわせて数える）
    order.length = 0;
    for (const a of everyone) {
      nameLabelLook(zoomDist ?? a.screen.dist, a.screen.dist, viewport.h, a.selected, a.look);
      if (a.screen.visible && a.look.show) order.push(a);
    }
    let allowed = null;
    if (order.length > MAX_LABELS) {
      order.sort((p, q) => p.screen.dist - q.screen.dist);
      allowed = new Set(order.slice(0, MAX_LABELS));
    }
    for (const a of everyone) {
      const show = a.screen.visible && a.look.show && (a.selected || !allowed || allowed.has(a));
      if (show !== a.labelShown) {
        a.label.style.display = show ? '' : 'none';
        a.labelShown = show;
      }
      if (!show) continue;
      if (a.labelSize !== a.look.size) {
        a.label.style.fontSize = `${a.look.size}px`;
        a.labelSize = a.look.size;
      }
      if (a.labelOpacity !== a.look.opacity) {
        a.label.style.opacity = String(a.look.opacity);
        a.labelOpacity = a.look.opacity;
      }
      a.label.style.transform = `translate(${Math.round(a.screen.x)}px, ${Math.round(a.screen.top)}px) translate(-50%, -100%)`;
      a.label.classList.toggle('is-selected', a.selected);

      // セリフの吹き出し（名前ラベルの上）
      if (a.line) {
        if (!a.speech) {
          a.speech = document.createElement('span');
          a.speech.className = 'speech';
          a.speech.hidden = true;
          a.label.appendChild(a.speech);
        }
        if (a.speechText !== a.line) {
          a.speech.textContent = a.line;
          a.speechText = a.line;
        }
      }
      if (a.speech && a.speech.hidden !== !a.line) {
        a.speech.hidden = !a.line;
        a.label.classList.toggle('is-talking', !!a.line);
      }
    }

    // 選択中の足もとの輪（漂流者は水面に）
    const sel = actors[selected] || (castaways[selectedDrifter]?.drift ? castaways[selectedDrifter] : null);
    if (sel) {
      ring.visible = true;
      const pulse = 1 + 0.12 * Math.sin(t * 5);
      ring.position.set(sel.pos.x, sel.drifter ? SEA_Y + 0.08 : sel.pos.y + 0.1, sel.pos.z);
      ring.scale.setScalar(sel.scale * pulse);
    } else {
      ring.visible = false;
    }
  }

  // タップ位置（ステージ内のCSSピクセル）にいちばん近い人。戻り値：{ kind: 'islander' | 'drifter', index } か null
  function pick(x, y) {
    let best = null;
    let bestD = Infinity;
    for (const a of everyone) {
      if (!a.screen.visible || (a.drifter && !a.drift && !a.sprite.visible)) continue;
      const d = Math.hypot(a.screen.x - x, a.screen.y - y);
      if (d <= a.screen.r + 8 && d < bestD) {
        bestD = d;
        best = a;
      }
    }
    return best ? { kind: best.drifter ? 'drifter' : 'islander', index: best.index } : null;
  }

  // タップ位置に近い島民の番号（漂流者は含めない。以前からの呼び出し口）
  function pickAt(x, y) {
    let best = -1;
    let bestD = Infinity;
    for (const a of actors) {
      if (!a.screen.visible) continue;
      const d = Math.hypot(a.screen.x - x, a.screen.y - y);
      if (d <= a.screen.r + 8 && d < bestD) {
        bestD = d;
        best = a.index;
      }
    }
    return best;
  }

  return {
    actors,
    castaways,
    update,
    pick,
    pickAt,
    positionOf: (i) => actors[i]?.pos,
    atlasOf: (i) => actors[i]?.atlas,
    drifterPositionOf: (j) => castaways[j]?.pos,
    drifterAtlasOf: (j) => castaways[j]?.atlas,
  };
}
