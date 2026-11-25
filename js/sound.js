// 島の音（Web Audio）：島のBGM（昼・夜を混ぜる）と、ステージの出し物の音（近いほど大きい）。
// ブラウザは、人が画面を押すまで音を出せない。「音」ボタンで始め、設定は端末に覚えておく。
// 音源はすべて Muse の自作（audio/CREDITS.md）。
const FILES = {
  day: './audio/bgm_day.mp3', night: './audio/bgm_night.mp3',
  sing: './audio/stage_sing.mp3', dance: './audio/stage_dance.mp3', cook: './audio/stage_cook.mp3', talk: './audio/stage_talk.mp3',
  guitar: './audio/stage_guitar.mp3', // ギターの弾き語り・演奏（無いときは歌の音）
  applause: './audio/applause.mp3',
};
const BGM_VOL = 0.38, STAGE_VOL = 0.75, NEAR = 40, FAR = 260; // ステージの音：NEAR まで最大、FAR で聞こえない

export function createSound() {
  let ctx = null, master = null, on = false;
  const buf = {}, loading = {}, failed = {};
  const loops = {}; // name → { src, gain }
  let stageAct = null, stageSlot = null;

  function load(name) {
    if (buf[name] || loading[name]) return loading[name];
    loading[name] = fetch(FILES[name]).then((r) => r.arrayBuffer()).then((a) => ctx.decodeAudioData(a)).then((b) => { buf[name] = b; return b; }).catch(() => { failed[name] = true; return null; });
    return loading[name];
  }
  // ループの音：最初は無音で鳴らしておき、音量だけ上げ下げする
  function loop(name) {
    if (loops[name]) return loops[name];
    const gain = ctx.createGain();
    gain.gain.value = 0;
    gain.connect(master);
    loops[name] = { gain, src: null };
    load(name).then((b) => {
      if (!b || !loops[name] || loops[name].src) return;
      const src = ctx.createBufferSource();
      src.buffer = b;
      src.loop = true;
      src.connect(gain);
      src.start();
      loops[name].src = src;
    });
    return loops[name];
  }
  function setVol(name, v) {
    const L = loop(name);
    L.gain.gain.setTargetAtTime(v, ctx.currentTime, 0.6);
  }
  function oneShot(name, v = 0.8) {
    load(name).then((b) => {
      if (!b || !on) return;
      const g = ctx.createGain();
      g.gain.value = v;
      g.connect(master);
      const s = ctx.createBufferSource();
      s.buffer = b;
      s.connect(g);
      s.start();
    });
  }

  function enable() {
    if (!ctx) {
      const AC = window.AudioContext || window.webkitAudioContext;
      if (!AC) return false;
      ctx = new AC();
      master = ctx.createGain();
      master.connect(ctx.destination);
    }
    ctx.resume?.();
    on = true;
    master.gain.setTargetAtTime(1, ctx.currentTime, 0.2);
    return true;
  }
  function disable() {
    on = false;
    if (ctx) master.gain.setTargetAtTime(0, ctx.currentTime, 0.15);
  }

  // 毎フレーム：night 0〜1、show（いまの出し物）、stageDist（カメラの注視点からステージまで）、viewing（鑑賞モード）
  function update({ night = 0, show = null, stageDist = Infinity, viewing = false }) {
    if (!on || !ctx) return;
    const near = viewing ? 1 : Math.max(0, Math.min(1, (FAR - stageDist) / (FAR - NEAR)));
    const stageV = show ? STAGE_VOL * near * near : 0;
    const duck = 1 - 0.75 * Math.min(1, stageV / STAGE_VOL); // ステージが聞こえるほど、島のBGMは下げる
    setVol('day', BGM_VOL * (1 - night) * duck);
    setVol('night', BGM_VOL * night * duck);
    let act = show ? show.act : null;
    if (act === 'sing' && /ギター|弾き語り/.test(show.label || '')) { if (!loading.guitar) load('guitar'); if (!failed.guitar) act = 'guitar'; }
    for (const a of ['sing', 'dance', 'cook', 'talk', 'guitar']) if (a === act || loops[a]) setVol(a, a === act ? stageV : 0);
    if (show && stageSlot !== null && show.slot !== stageSlot && stageV > 0.05) oneShot('applause', 0.9 * near);
    stageSlot = show ? show.slot : null;
    stageAct = act;
  }

  // 画面を離れたら止める（裏で鳴り続けないように）
  document.addEventListener('visibilitychange', () => {
    if (!ctx) return;
    if (document.hidden) ctx.suspend?.();
    else if (on) ctx.resume?.();
  });

  return { enable, disable, update, isOn: () => on };
}
