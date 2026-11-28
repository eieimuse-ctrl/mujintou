// 洞窟の謎解き（12日目〜）：洞窟の奥をタップすると、洞窟の中に入って謎解きモードになる。
//   0 まっ暗 → 松明をともす
//   1 壁画の順番：謎の文のとおりに、4つの石を押す（朝日 → 人 → 波 → 舟）
//   2 石板を回す：4枚の石板を回して、舟の絵をそろえる
//   3 石室の地図：海の向こうの島のありか ＋ 合言葉（コメントで報告）
// 進み具合は端末に覚えておく（mujintou.cave）。ネタバレよけに、答えの文は少し変換して入れてある。
const STORE = 'mujintou.cave';
const load = () => { try { return Math.max(0, Math.min(3, Number(localStorage.getItem(STORE)) || 0)); } catch { return 0; } };
const save = (n) => { try { localStorage.setItem(STORE, String(n)); } catch { /* 保存できない環境 */ } };
const dec = (s) => [...s].map((c) => String.fromCharCode(c.charCodeAt(0) - 1)).join('');

// ドット絵（1文字＝1マス）
const PAL = { k: '#2a221b', y: '#ffd23a', o: '#e8902a', w: '#f4efe2', s: '#e8c39e', r: '#d9503f', b: '#5fb4dd', B: '#2f7fb8', t: '#c98a4a', T: '#7a4f2c', g: '#8d8f97' };
const ICONS = {
  sun: ['..y..y..', '...yy...', '.yyyyyy.', 'yyyooyyy', 'yyyooyyy', '.yyyyyy.', '...yy...', '..y..y..'],
  man: ['...ss...', '...ss...', '..rrrr..', '.s.rr.s.', '...rr...', '...TT...', '..T..T..', '..T..T..'],
  wave: ['........', '..bb....', '.b..b..b', 'b....bb.', '...bb...', '..b..b..', '.b....bb', 'b.......'],
  boat: ['....w...', '....ww..', '....www.', '....w...', 'tttttttt', '.tttttt.', '..tttt..', 'bbbbbbbb'],
};
const BOAT = [
  '....................', '.........w..........', '.........ww.........', '.........www........', '.........wwww.......', '.........wwwww......', '.........wwwwww.....', '.........wwwwwww....',
  '.........w..........', '.........w..........', '..tttttttttttttttt..', '...tttttttttttttt...', '....tttTttttTttt....', '.....tttttttttt.....', 'bbbbbbbbbbbbbbbbbbbb', 'BBbbBBbbBBbbBBbbBBbb',
  'bbBBbbBBbbBBbbBBbbBB', 'bbbbbbbbbbbbbbbbbbbb', 'BBBBBBBBBBBBBBBBBBBB', 'BBBBBBBBBBBBBBBBBBBB',
];
function pix(rows, scale) {
  const c = document.createElement('canvas');
  c.width = rows[0].length; c.height = rows.length;
  const g = c.getContext('2d');
  rows.forEach((r, y) => [...r].forEach((ch, x) => { if (PAL[ch]) { g.fillStyle = PAL[ch]; g.fillRect(x, y, 1, 1); } }));
  c.style.width = `${c.width * scale}px`; c.style.height = `${c.height * scale}px`; c.style.imageRendering = 'pixelated';
  return c;
}
function el(tag, cls, text) { const e = document.createElement(tag); if (cls) e.className = cls; if (text != null) e.textContent = text; return e; }

export function openCave({ onClose } = {}) {
  document.getElementById('cave-mode')?.remove();
  let step = load();
  const root = el('div'); root.id = 'cave-mode';
  root.setAttribute('role', 'dialog'); root.setAttribute('aria-label', '洞窟の中（謎解き）');
  const top = el('div', 'cv-top');
  const title = el('span', 'cv-title', '洞窟の中');
  const close = el('button', 'cv-close', '×'); close.type = 'button'; close.setAttribute('aria-label', '洞窟から出る');
  close.addEventListener('click', () => { root.remove(); onClose?.(); });
  top.append(title, close);
  const body = el('div', 'cv-body');
  root.append(top, body);
  document.getElementById('stage').append(root);

  const go = (n) => { step = Math.max(step, n); save(step); render(n); };
  function render(n) {
    body.replaceChildren();
    root.dataset.lit = n > 0 ? '1' : '0';
    if (n === 0) {
      body.append(el('p', 'cv-text', '洞窟の中は、まっ暗だ。'), el('p', 'cv-sub', '奥から、ひんやりした風が吹いてくる…'));
      const b = el('button', 'cv-btn', '🔥 松明をともす'); b.type = 'button';
      b.addEventListener('click', () => go(1));
      body.append(b);
    } else if (n === 1) {
      body.append(el('p', 'cv-kicker', 'その1　壁の石'));
      body.append(el('p', 'cv-text', '壁に、昔の住人の文字が刻まれている。'));
      body.append(el('p', 'cv-riddle', '「朝の光がのぼり　人は浜へおりる　波をこえて　舟はゆく」'));
      body.append(el('p', 'cv-sub', 'その下に、4つの石。押せそうだ。'));
      const order = ['sun', 'man', 'wave', 'boat'], shown = ['boat', 'sun', 'wave', 'man'];
      let got = [];
      const row = el('div', 'cv-stones');
      const msg = el('p', 'cv-msg', '');
      for (const key of shown) {
        const s = el('button', 'cv-stone'); s.type = 'button'; s.append(pix(ICONS[key], 6));
        s.addEventListener('click', () => {
          if (s.classList.contains('is-on')) return;
          if (key === order[got.length]) {
            got.push(key); s.classList.add('is-on');
            if (got.length === 4) { msg.textContent = 'ゴゴゴ……石の扉が、開いた！'; setTimeout(() => go(2), 1300); }
          } else {
            got = []; msg.textContent = 'ガコン……石が、もとにもどった。';
            row.querySelectorAll('.is-on').forEach((x) => x.classList.remove('is-on'));
            row.classList.remove('shake'); void row.offsetWidth; row.classList.add('shake');
          }
        });
        row.append(s);
      }
      body.append(row, msg);
    } else if (n === 2) {
      body.append(el('p', 'cv-kicker', 'その2　石板'));
      body.append(el('p', 'cv-text', '扉の奥に、4枚の石板。絵がばらばらの向きになっている。'));
      body.append(el('p', 'cv-sub', 'タップすると回る。絵をそろえよう。'));
      const big = pix(BOAT, 1);
      const grid = el('div', 'cv-tiles');
      const rot = [1, 3, 2, 1];
      const msg = el('p', 'cv-msg', '');
      const tiles = [];
      for (let k = 0; k < 4; k++) {
        const c = document.createElement('canvas'); c.width = 10; c.height = 10;
        c.getContext('2d').drawImage(big, (k % 2) * 10, Math.floor(k / 2) * 10, 10, 10, 0, 0, 10, 10);
        c.style.imageRendering = 'pixelated';
        const t = el('button', 'cv-tile'); t.type = 'button'; t.append(c);
        const set = () => { c.style.transform = `rotate(${rot[k] * 90}deg)`; };
        set();
        t.addEventListener('click', () => {
          if (msg.dataset.done) return;
          rot[k] = (rot[k] + 1) % 4; set();
          if (rot.every((r) => r === 0)) { msg.dataset.done = '1'; msg.textContent = 'カチリ。舟の絵がそろった！　奥の小部屋が、開いた。'; tiles.forEach((x) => x.classList.add('is-on')); setTimeout(() => go(3), 1500); }
        });
        tiles.push(t); grid.append(t);
      }
      body.append(grid, msg);
    } else {
      body.append(el('p', 'cv-kicker', 'その3　石室'));
      body.append(el('p', 'cv-text', '小部屋の床に、古い地図が刻まれていた。'));
      const map = document.createElement('canvas'); map.width = 280; map.height = 180; map.className = 'cv-map';
      const g = map.getContext('2d');
      g.fillStyle = '#3d342a'; g.fillRect(0, 0, 280, 180);
      g.fillStyle = '#6b5a44';
      g.beginPath(); g.ellipse(95, 110, 62, 46, -0.2, 0, Math.PI * 2); g.fill();
      g.beginPath(); g.ellipse(236, 34, 22, 14, 0.3, 0, Math.PI * 2); g.fill();
      g.strokeStyle = '#f2c230'; g.lineWidth = 3; g.setLineDash([6, 6]);
      g.beginPath(); g.moveTo(140, 92); g.quadraticCurveTo(190, 60, 220, 40); g.stroke(); g.setLineDash([]);
      g.fillStyle = '#f2c230'; g.font = 'bold 22px sans-serif'; g.fillText('？', 228, 42);
      g.fillStyle = '#ffd23a'; g.beginPath(); g.arc(250, 150, 12, 0, Math.PI * 2); g.fill();
      body.append(map);
      body.append(el('p', 'cv-riddle', dec('浸は吒ごぇは峷ば。灰叱はめごぇ。旦きはぽれ斺觓〃舠きぃろぱ。衍げれ')));
      const w = el('p', 'cv-word'); w.append(el('span', '', '合言葉'), el('b', '', dec('ぇむはめごぇ')));
      body.append(w, el('p', 'cv-sub', '解けたら、合言葉をコメントで教えてね（場所と答えはないしょ）'));
      const again = el('button', 'cv-btn cv-btn-soft', 'はじめから解き直す'); again.type = 'button';
      again.addEventListener('click', () => { save(0); step = 0; render(0); });
      body.append(again);
    }
  }
  render(step >= 3 ? 3 : step);
}
