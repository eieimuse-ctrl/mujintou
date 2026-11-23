// 画面のDOM部分：ヘッダー、タブ、島民検索・ランキング（と漂流中の人）、年表、投票カード、詳細パネル。
// データ由来の文字列はすべて textContent で入れる（HTMLとして解釈させない）。

import { showAt, showLabel, upcomingMap, nextShowOf, setShowRequests } from './show.js';
import { INSTAGRAM_URL, INSTAGRAM_HANDLE, RELATION_TYPES, DEFAULT_RELATION } from './config.js';
import { iconCanvas, islanderPortrait, hydrateIcons } from './pixelart.js';
import { rankIslanders } from './data.js';
import { LANDING } from './terrain.js';

// 子要素に null / undefined / false が来たら飛ばす。
const present = (c) => c !== null && c !== undefined && c !== false;

function el(tag, props = {}, children = []) {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(props)) {
    if (v === undefined || v === null || v === false) continue;
    if (k === 'class') node.className = v;
    else if (k === 'text') node.textContent = v;
    else if (k === 'on') for (const [ev, fn] of Object.entries(v)) node.addEventListener(ev, fn);
    else if (k === 'data') Object.assign(node.dataset, v);
    else node.setAttribute(k, v === true ? '' : v);
  }
  for (const c of [].concat(children)) if (c) node.append(c);
  return node;
}

// 中身をまとめて入れ替える。DOM の append / replaceChildren に null を渡すと
// 文字列 "null" が描かれてしまうので、条件つきの子要素は必ず el() かこれを通す。
function fill(node, children) {
  node.replaceChildren(...[].concat(children).filter(present));
}

const $ = (id) => document.getElementById(id);

function formatDeadline(date) {
  try {
    const f = new Intl.DateTimeFormat('ja-JP', { month: 'numeric', day: 'numeric', weekday: 'short', hour: '2-digit', minute: '2-digit', hour12: false, timeZone: 'Asia/Tokyo' });
    return `${f.format(date)}（日本時間）`;
  } catch {
    return date.toISOString();
  }
}

function formatRemaining(ms) {
  if (ms <= 0) return '';
  const min = Math.floor(ms / 60000);
  const d = Math.floor(min / 1440);
  const h = Math.floor((min % 1440) / 60);
  const m = min % 60;
  if (d > 0) return `あと${d}日${h}時間`;
  if (h > 0) return `あと${h}時間${m}分`;
  return `あと${Math.max(1, m)}分`;
}

// "2026-11-17" → "11/17"
const monthDay = (ymd) => {
  const m = /^\d{4}-(\d{2})-(\d{2})$/.exec(ymd || '');
  return m ? `${Number(m[1])}/${Number(m[2])}` : '';
};

export function createUI({ onSelectIslander, onSelectDrifter, onCloseDetail, onSheetChange, onRecenter, onLabels, now = () => Date.now() }) {
  const body = document.body;
  const panel = $('panel');
  const sheet = $('sheet');
  const views = {
    islanders: $('view-islanders'),
    chronicle: $('view-chronicle'),
    vote: $('view-vote'),
    detail: $('view-detail'),
  };
  const tabs = [...document.querySelectorAll('#tabs [data-tab]')];
  const desktop = window.matchMedia('(min-width: 900px)');

  let state = null;
  let islanders = [];
  let ranked = [];
  let drifters = []; // 漂流中の人（まだ漂着していない）
  let portraitFor = (p) => islanderPortrait(p);
  let drifterPortraitFor = (p) => islanderPortrait(p);
  let currentView = 'islanders';
  let returnView = null; // 詳細を閉じたときに戻る先（null ならシートを閉じる）
  let selected = -1;
  let selectedDrifter = -1;
  let nowLine = null;
  let nowKey = '';
  let voteTimer = null;

  hydrateIcons();

  // ---- シートとタブ ----------------------------------------------------------
  function isSheetOpen() {
    return desktop.matches || body.dataset.sheet === 'open';
  }

  function setSheet(open) {
    const before = body.dataset.sheet;
    body.dataset.sheet = open ? 'open' : 'closed';
    if (before !== body.dataset.sheet) onSheetChange?.();
  }

  function setView(name, { open = true } = {}) {
    currentView = name;
    panel.dataset.view = name;
    for (const [k, v] of Object.entries(views)) v.hidden = k !== name;
    const tabName = name === 'detail' ? 'islanders' : name;
    for (const t of tabs) {
      const active = open || desktop.matches ? t.dataset.tab === tabName : t.dataset.tab === 'island';
      t.setAttribute('aria-selected', active ? 'true' : 'false');
    }
    setSheet(open);
    sheet.scrollTop = 0;
  }

  for (const t of tabs) {
    t.addEventListener('click', () => {
      const name = t.dataset.tab;
      if (name === 'island') {
        setView(currentView === 'detail' ? 'islanders' : currentView, { open: false });
        if (selected >= 0 || selectedDrifter >= 0) closeDetail(true);
        return;
      }
      if (currentView === 'detail' && (selected >= 0 || selectedDrifter >= 0)) {
        selected = -1;
        selectedDrifter = -1;
        onCloseDetail?.();
      }
      setView(name);
    });
  }
  desktop.addEventListener?.('change', () => {
    setView(currentView, { open: body.dataset.sheet === 'open' });
    onSheetChange?.();
  });

  $('recenter').addEventListener('click', () => onRecenter?.());
  // 名札の表示／非表示（端末に覚えておく。保存できない環境でも動くように）
  const LABELS_KEY = 'mujintou.labels';
  let labelsOn = true;
  try { labelsOn = localStorage.getItem(LABELS_KEY) !== 'off'; } catch { /* 保存できない環境 */ }
  const labelsBtn = $('labels-toggle');
  const applyLabels = () => {
    labelsBtn.setAttribute('aria-pressed', String(labelsOn));
    onLabels?.(labelsOn);
  };
  labelsBtn.addEventListener('click', () => {
    labelsOn = !labelsOn;
    try { localStorage.setItem(LABELS_KEY, labelsOn ? 'on' : 'off'); } catch { /* 保存できない環境 */ }
    applyLabels();
    toast(labelsOn ? '名札を表示します' : '名札を消しました（タップした人の名札は出ます）');
  });
  queueMicrotask(applyLabels);
  $('vote-chip').addEventListener('click', () => setView('vote'));

  // ---- ヘッダー --------------------------------------------------------------
  function renderHeader() {
    $('island-name').textContent = state.islandName;
    document.title = state.islandName;
    $('day-chip').textContent = `${state.day}日目`;
    $('pop-chip').textContent = `島民 ${islanders.length}人`;
    // 漂流中の人がいるときだけ（投票のチップと同じ段の右はし）
    const driftChip = $('drift-chip');
    driftChip.hidden = !drifters.length;
    driftChip.textContent = `漂流中 ${drifters.length}人`;
    body.classList.toggle('has-drifters', drifters.length > 0);
    renderLikes();
  }

  // 島のいいね合計（全投稿）。節目（goals）に目盛り。タップで、次のごほうびまでの数
  function renderLikes() {
    const L = state.likes;
    const bar = $('like-bar');
    bar.hidden = !L;
    if (!L) return;
    bar.querySelector('.like-fill').style.width = `${Math.min(100, (L.total / L.max) * 100)}%`;
    bar.querySelector('.like-num').textContent = `${L.total} / ${L.max}`;
    bar.querySelector('.like-ticks').replaceChildren(...L.goals.filter((g) => g.at < L.max).map((g) => {
      const t = el('span', { class: `like-tick${L.total >= g.at ? ' is-done' : ''}` });
      t.style.left = `calc(${(g.at / L.max) * 100}% - 1px)`;
      return t;
    }));
  }
  $('like-bar').addEventListener('click', () => {
    const L = state.likes;
    if (!L) return;
    const next = L.goals.find((g) => L.total < g.at);
    const done = L.goals.filter((g) => L.total >= g.at).map((g) => g.label);
    toast(next ? `島のいいね合計 ${L.total}。あと${next.at - L.total}で「${next.label}」！（全投稿のいいねの合計）` : `島のいいね合計 ${L.total}。ごほうびは全部達成！`, 5000);
    if (done.length && next) setTimeout(() => toast(`達成：${done.join('、')}`, 3500), 5100);
  });

  // ---- 島民：検索とランキング（上に「漂流中」の人） ----------------------------------
  const searchInput = $('search');
  const listEl = $('islander-list');
  const listMeta = $('list-meta'); // 検索したときの件数（島民と漂流者をあわせて）
  const islanderMeta = $('islander-meta'); // ランキングの見出し
  const driftGroup = $('drifter-group');
  const driftMeta = $('drifter-meta');
  const driftList = $('drifter-list');

  function matches(p, q) {
    if (!q) return true;
    const hay = p.anonymous ? p.displayName : `${p.name}\n${p.id}\n${p.job || ''}`;
    return hay.toLowerCase().includes(q);
  }

  const query = () => searchInput.value.trim().toLowerCase().replace(/^@/, '');

  // 漂流中の人（名前＋「漂流中」チップ＋漂流開始日）。押すと海の上のその人へ寄る
  function renderDrifters(q) {
    const rows = drifters.map((p, index) => ({ p, index })).filter((e) => matches(e.p, q));
    driftGroup.hidden = !rows.length;
    driftList.replaceChildren();
    if (!rows.length) return rows;
    driftMeta.textContent = `漂流中 ${rows.length}人・次の動画で島に漂着します`;
    for (const { p, index } of rows) {
      const since = monthDay(p.since);
      const row = el(
        'button',
        { class: 'islander-row drifter-row', type: 'button', 'aria-label': `${p.displayName}、漂流中${since ? `、${since}から` : ''}。海で探す`, on: { click: () => onSelectDrifter?.(index, { fromList: true }) } },
        [
          el('span', { class: 'portrait-wrap portrait-sea' }, drifterPortraitFor(p, index)),
          el('span', { class: 'who' }, [
            el('span', { class: 'who-name' }, [el('span', { text: p.displayName }), el('span', { class: 'tag tag-drift', text: '漂流中' }), p.sample ? el('span', { class: 'tag tag-sample', text: 'サンプル' }) : null]),
            el('span', { class: 'who-sub', text: p.anonymous ? '沖をただよっている' : `@${p.id}` }),
          ]),
          since ? el('span', { class: 'drift-since' }, [el('span', { text: '漂流開始' }), el('b', { text: since })]) : el('span'),
        ],
      );
      driftList.append(el('li', {}, row));
    }
    return rows;
  }

  // ステージの出演予定（24時間以内）。ステージが建っているときだけ
  const hasStage = () => (state?.buildings || []).some((b) => b.type === 'stage');
  function hmDay(ms) {
    const d = new Date(ms + 9 * 3600000), n = new Date(now() + 9 * 3600000);
    const hm = `${String(d.getUTCHours()).padStart(2, '0')}:${String(d.getUTCMinutes()).padStart(2, '0')}`;
    return d.getUTCDate() === n.getUTCDate() ? hm : `あした ${hm}`;
  }
  function stageNote(s) {
    if (!s) return '';
    return s.start <= now() ? `いまステージに出演中（${s.label}）` : `ステージ出演 ${hmDay(s.start)}〜（${s.label}）`;
  }
  let upCache = { slot: null, map: null };
  function upcoming() {
    const t = now(), slot = Math.floor(t / 900000);
    if (upCache.slot !== slot || upCache.n !== islanders.length) upCache = { slot, n: islanders.length, map: upcomingMap(islanders, state.day, t, 24) };
    return upCache.map;
  }

  function renderList() {
    const q = query();
    const drifting = renderDrifters(q);
    const rows = ranked.filter((e) => matches(e.p, q));
    listEl.replaceChildren();
    listMeta.textContent = q ? `「${searchInput.value.trim()}」の検索結果：${rows.length + drifting.length}人` : '';
    listMeta.hidden = !q;
    // ランキングの見出し。検索中は、漂流者もヒットしたときだけ「島民 N人」で区切る
    islanderMeta.textContent = q ? (drifting.length && rows.length ? `島民 ${rows.length}人` : '') : islanders.length ? `在住日数ランキング（全${islanders.length}人）` : '';
    if (!rows.length) {
      if (q && drifting.length) return; // 漂流者だけヒットした
      const notFound = q && islanders.length + drifters.length > 0;
      listEl.append(
        el('li', { class: 'empty' }, [
          el('p', { class: 'empty-title', text: notFound ? (drifters.length ? 'その名前の島民・漂流者は見つかりませんでした' : 'その名前の島民は見つかりませんでした') : 'まだ島民はいません' }),
          el('p', {
            text: notFound
              ? `まだ島に届いていないのかもしれません。Instagram（@${INSTAGRAM_HANDLE}）をフォローした人は、まず島の沖を漂流し、動画の更新にあわせてこの島に漂着します。`
              : `Instagram（@${INSTAGRAM_HANDLE}）をフォローすると、この島に漂着します。名簿は動画の更新にあわせて反映されます。`,
          }),
        ]),
      );
      return;
    }
    const up = q && hasStage() ? upcoming() : null; // 名前で探したとき：24時間以内の出演予定
    for (const e of rows) {
      const p = e.p;
      const rank = el('span', { class: `rank rank-${Math.min(e.rank, 4)}` }, [e.rank <= 3 ? iconCanvas('crown', e.rank === 2 ? { C: '#c3c8d4', L: '#ffffff' } : e.rank === 3 ? { C: '#d08a4e', L: '#f3c9a0' } : undefined) : null, el('span', { text: `${e.rank}位` })]);
      const row = el(
        'button',
        { class: 'islander-row', type: 'button', 'aria-label': `${p.displayName}、${p.job}、在住${p.days}日、${e.rank}位。島で探す`, on: { click: () => onSelectIslander?.(e.index, { fromList: true }) } },
        [
          rank,
          el('span', { class: 'portrait-wrap' }, portraitFor(p, e.index)),
          el('span', { class: 'who' }, [
            el('span', { class: 'who-name' }, [el('span', { text: p.displayName }), p.sample ? el('span', { class: 'tag tag-sample', text: 'サンプル' }) : null]),
            el('span', { class: 'who-sub', text: p.anonymous ? p.job : `@${p.id}・${p.job}` }),
            up && up.has(e.index) ? el('span', { class: 'who-stage', text: `🎤 ${stageNote(up.get(e.index))}` }) : null,
          ]),
          el('span', { class: 'days' }, [el('b', { text: String(p.days) }), el('span', { text: '日' })]),
        ],
      );
      listEl.append(el('li', {}, row));
    }
  }

  searchInput.addEventListener('input', renderList);
  $('search-form').addEventListener('submit', (ev) => {
    ev.preventDefault();
    const q = query();
    if (!q) return;
    // 一覧の上から順に（漂流中の人 → 島民）
    const d = drifters.findIndex((p) => matches(p, q));
    const hit = d < 0 ? ranked.find((e) => matches(e.p, q)) : null;
    if (d >= 0 || hit) searchInput.blur();
    if (d >= 0) onSelectDrifter?.(d, { fromList: true });
    else if (hit) onSelectIslander?.(hit.index, { fromList: true });
  });

  // ---- 島のいま（拠点と、島民の行動範囲） ----------------------------------------
  // 行動範囲は運営が開け閉めするものではなく、住民の投票で広がるもの。範囲の外は「自然の障壁」として説明する。
  const districtName = (id) => state.districts.find((d) => d.id === id)?.name || id;

  function renderIslandNow() {
    const inside = state.districts.filter((d) => d.inRange);
    const outside = state.districts.filter((d) => !d.inRange);
    const b = state.base;
    fill($('island-now'), [
      el('h3', { class: 'now-title', text: '島のいま' }),
      el('dl', { class: 'now-list' }, [
        el('div', {}, [
          el('dt', { text: '拠点' }),
          el('dd', {}, b ? [el('b', { text: b.name }), b.decidedDay ? el('span', { text: `（${b.decidedDay}日目に住民の投票で決定）` }) : null] : [el('b', { text: 'まだ決まっていない' }), el('span', { text: `（いまは${LANDING.name}が集まり場）` })]),
        ]),
        el('div', {}, [
          el('dt', { text: '行動範囲' }),
          el('dd', {}, [el('b', { text: inside.map((d) => d.name).join('・') || '—' }), ...inside.filter((d) => d.expandedDay).map((d) => el('span', { class: 'now-expanded', text: `${d.name}は${d.expandedDay}日目から` }))]),
        ]),
        state.forestRoad
          ? el('div', {}, [
              el('dt', { text: '森の道づくり' }),
              el('dd', {}, [
                state.forestRoad.open
                  ? el('b', { text: `${state.forestRoad.label}まで開通` })
                  : el('b', { text: `${Math.min(state.forestRoad.count, state.forestRoad.need)}／${state.forestRoad.need}人` }),
                el('span', { text: state.forestRoad.open ? '（松明を持って、みんなで森へ入った。火の番は交代で道を守っている）' : state.forestRoad.count >= state.forestRoad.need ? `（${state.forestRoad.label}まで道がつながった）` : `（${state.forestRoad.label}まで、木が${state.forestRoad.need}本。島民1人が1本ずつ切りひらく。あと${state.forestRoad.need - state.forestRoad.count}人）` }),
              ]),
            ])
          : null,
        outside.length
          ? el('div', {}, [
              el('dt', { text: '範囲の外' }),
              el(
                'dd',
                {},
                el(
                  'ul',
                  { class: 'now-barriers' },
                  outside.map((d) => el('li', {}, [el('b', { text: d.name }), el('span', { text: d.barrier })])),
                ),
              ),
            ])
          : null,
      ]),
      el('p', { class: 'now-note', text: outside.length ? `${outside.map((d) => d.name).join('や')}へ行くかどうかは、住民の投票で決まります。` : '島じゅうが、島民の行動範囲になりました。' }),
    ]);
  }

  // ---- 年表 ------------------------------------------------------------------
  function renderChronicle() {
    const root = $('chronicle-list');
    root.replaceChildren();
    if (!state.chronicle.length) {
      root.append(el('li', { class: 'empty' }, el('p', { text: 'まだ出来事がありません。島の出来事は、動画の更新にあわせてここに記録されます。' })));
      return;
    }
    for (const c of state.chronicle) {
      root.append(
        el('li', { class: `chron${c.expands.length ? ' chron-expand' : ''}` }, [
          el('div', { class: 'chron-head' }, [el('span', { class: 'chip chip-day', text: `${c.day}日目` }), c.date ? el('time', { datetime: c.date, text: c.date.replaceAll('-', '/') }) : null]),
          el('h3', { text: c.title }),
          c.text ? el('p', { text: c.text }) : null,
          c.expands.length ? el('p', { class: 'chron-range' }, [el('span', { class: 'chron-range-label', text: '行動範囲が広がった' }), el('b', { text: c.expands.map(districtName).join('・') })]) : null,
          c.vote && (c.vote.question || c.vote.adopted)
            ? el('div', { class: 'chron-vote' }, [
                el('span', { class: 'chron-vote-label' }, [iconCanvas('vote'), el('span', { text: '採用された投票結果' })]),
                c.vote.question ? el('span', { class: 'chron-vote-q', text: c.vote.question }) : null,
                el('strong', { text: c.vote.adopted ? `→ ${c.vote.adopted}` : '' }),
                c.vote.note ? el('span', { class: 'chron-vote-note', text: c.vote.note }) : null,
              ])
            : null,
        ]),
      );
    }
  }

  // ---- 投票カード ------------------------------------------------------------
  function voteStatus(v) {
    const passed = v.deadline && now() > v.deadline.getTime();
    if (v.status === 'closed') return { key: 'closed', label: '終了' };
    if (v.status === 'counting' || passed) return { key: 'counting', label: '集計中' };
    return { key: 'open', label: '受付中' };
  }

  function renderVote() {
    const root = $('vote-card');
    const chip = $('vote-chip');
    root.replaceChildren();
    const v = state.currentVote;
    const dot = document.querySelector('#tabs [data-tab="vote"] .tab-dot');
    if (!v) {
      chip.hidden = true;
      if (dot) dot.hidden = true;
      root.append(el('div', { class: 'empty' }, [el('p', { class: 'empty-title', text: 'いま受付中の投票はありません' }), el('p', { text: '次のお題は、次の動画で発表されます。' })]));
      return;
    }
    const st = voteStatus(v);
    chip.hidden = st.key !== 'open';
    if (dot) dot.hidden = st.key !== 'open';
    $('vote-chip-text').textContent = v.question;

    const remaining = v.deadline ? formatRemaining(v.deadline.getTime() - now()) : '';
    const url = v.postUrl || INSTAGRAM_URL;
    const free = !v.options.length; // 選択肢のないお題＝自由コメント
    // 結果メモ・説明・締切は無いことがあるので fill() で入れる（append だと null が "null" と描かれる）
    fill(root, [
      el('div', { class: 'vote-head' }, [el('span', { class: `chip chip-${st.key}`, text: st.label }), el('span', { class: 'vote-kicker', text: '現在の投票お題' })]),
      el('h3', { class: 'vote-q', text: v.question }),
      v.description ? el('p', { class: 'vote-desc', text: v.description }) : null,
      free ? null : el(
        'ol',
        { class: 'vote-options' },
        v.options.map((o) =>
          el('li', { class: v.result && v.result.key === o.key ? 'is-adopted' : '' }, [
            el('span', { class: 'opt-key', text: o.key }),
            el('span', { class: 'opt-body' }, [el('b', { text: o.label }), o.note ? el('span', { text: o.note }) : null]),
            v.result && v.result.key === o.key ? el('span', { class: 'tag tag-adopted', text: '採用' }) : null,
          ]),
        ),
      ),
      v.deadline
        ? el('p', { class: 'vote-deadline' }, [
            el('span', { class: 'vote-deadline-label', text: '締切' }),
            el('time', { datetime: v.deadline.toISOString(), text: formatDeadline(v.deadline) }),
            st.key === 'open' && remaining ? el('b', { class: 'vote-remaining', text: remaining }) : null,
            st.key === 'counting' ? el('b', { class: 'vote-remaining', text: '締め切りました。結果は次の動画で発表' }) : null,
          ])
        : null,
      v.result?.note ? el('p', { class: 'vote-result-note', text: v.result.note }) : null,
      el('div', { class: 'vote-how' }, [
        el('p', { class: 'vote-how-title', text: '投票はInstagramのコメントで' }),
        el('p', { text: 'このアプリの中では投票できません。次の手順で参加してください。' }),
        // 選択肢あり＝コメントの件数が一番多い案を採用／選択肢なし（自由コメント）＝いいねが一番多いコメントを採用
        el('ol', {}, free
          ? [el('li', { text: `Instagram（@${INSTAGRAM_HANDLE}）の最新の投稿をひらく` }), el('li', { text: '自由に案をコメントする' }), el('li', { text: 'いいなと思うコメントに、いいねする' }), el('li', { text: 'いいねが一番多いコメントが採用されます（同じ数なら、先に書かれたもの）' })]
          : [el('li', { text: `Instagram（@${INSTAGRAM_HANDLE}）の最新の投稿をひらく` }), el('li', { text: `えらんだ案（${v.options.map((o) => o.key).join('・')}）をコメントする` }), el('li', { text: 'コメントが一番多い案が採用されます' })]),
        st.key === 'open' ? el('a', { class: 'btn btn-primary', href: url, target: '_blank', rel: 'noopener noreferrer', text: 'Instagramで投票する' }) : el('a', { class: 'btn', href: url, target: '_blank', rel: 'noopener noreferrer', text: 'Instagramをひらく' }),
      ]),
    ]);
  }

  // ---- 詳細パネル ------------------------------------------------------------
  function detailHeader(titleNode) {
    return el('div', { class: 'detail-head' }, [
      returnView ? el('button', { class: 'btn btn-small', type: 'button', text: '‹ 一覧へ', on: { click: () => closeDetail() } }) : el('span'),
      titleNode,
      el('button', { class: 'icon-btn', type: 'button', 'aria-label': '閉じる', on: { click: () => closeDetail(true) } }, iconCanvas('close')),
    ]);
  }

  function showIslander(index, { fromList = false } = {}) {
    const p = islanders[index];
    if (!p) return;
    if (currentView !== 'detail') returnView = fromList || isSheetOpen() ? (currentView === 'detail' ? 'islanders' : currentView) : null;
    selected = index;
    selectedDrifter = -1;
    const root = views.detail;
    nowLine = el('div', { class: 'now-line', 'aria-live': 'polite' });
    nowKey = '';

    const byId = new Map(islanders.map((q, i) => [q.id, i]));
    const rels = p.relationships
      .map((r) => ({ r, j: byId.get(r.id) }))
      .filter((x) => x.j !== undefined)
      .sort((a, b) => b.r.affinity - a.r.affinity);

    fill(root, [
      detailHeader(el('span', { class: 'detail-kicker', text: '島民' })),
      el('div', { class: 'profile' }, [
        el('span', { class: 'portrait-wrap portrait-big' }, portraitFor(p, index)),
        el('div', { class: 'profile-main' }, [
          el('h3', {}, [el('span', { text: p.displayName }), p.sample ? el('span', { class: 'tag tag-sample', text: 'サンプル' }) : null]),
          p.anonymous ? null : el('p', { class: 'profile-id', text: `@${p.id}` }),
          nowLine,
        ]),
      ]),
      el('dl', { class: 'facts' }, [
        el('div', {}, [el('dt', { text: '在住' }), el('dd', {}, [el('b', { text: String(p.days) }), el('span', { text: '日' })])]),
        el('div', {}, [el('dt', { text: '仕事' }), el('dd', { text: p.job })]),
        p.torchNo ? el('div', {}, [el('dt', { text: '火の番' }), el('dd', {}, [el('span', { text: '森の道の' }), el('b', { text: String(p.torchNo) }), el('span', { text: '本目' })])]) : null,
      ]),
      p.since ? el('p', { class: 'since', text: `在住の起点：${p.since.replaceAll('-', '/')}` }) : null,
      hasStage() && nextShowOf(islanders, state.day, index, now(), 24) ? el('p', { class: 'stage-next', text: `🎤 ${stageNote(nextShowOf(islanders, state.day, index, now(), 24))}` }) : null,
      el('h4', { class: 'section-title', text: '関係' }),
      rels.length
        ? el(
            'ul',
            { class: 'rel-list' },
            rels.map(({ r, j }) => {
              const type = RELATION_TYPES[r.type] || DEFAULT_RELATION;
              const q = islanders[j];
              return el(
                'li',
                {},
                el('button', { class: 'rel-row', type: 'button', 'aria-label': `${q.displayName}、${type.label}、好感度${r.affinity}。この島民を見る`, on: { click: () => onSelectIslander?.(j, { fromList: returnView !== null }) } }, [
                  el('span', { class: 'portrait-wrap portrait-small' }, portraitFor(q, j)),
                  el('span', { class: 'rel-main' }, [
                    el('span', { class: 'rel-name', text: q.displayName }),
                    el('span', { class: `rel-type rel-${r.type}` }, [iconCanvas(type.icon), el('span', { text: type.label })]),
                  ]),
                  el('span', { class: 'meter', role: 'img', 'aria-label': `好感度 ${r.affinity}` }, [
                    el('span', { class: 'meter-bar' }, el('span', { class: 'meter-fill', style: `width:${r.affinity}%` })),
                    el('span', { class: 'meter-num', text: String(r.affinity) }),
                  ]),
                ]),
              );
            }),
          )
        : el('p', { class: 'muted', text: 'まだ特別な関係はありません。これから育っていきます。' }),
    ]);
    setView('detail');
  }

  // 漂流者の詳細：まだ漂着していないので、在住日数や関係は出さない
  function showDrifter(index, { fromList = false } = {}) {
    const p = drifters[index];
    if (!p) return;
    if (currentView !== 'detail') returnView = fromList || isSheetOpen() ? currentView : null;
    selected = -1;
    selectedDrifter = index;
    nowLine = null;
    fill(views.detail, [
      detailHeader(el('span', { class: 'detail-kicker', text: '漂流者' })),
      el('div', { class: 'profile' }, [
        el('span', { class: 'portrait-wrap portrait-big portrait-sea' }, drifterPortraitFor(p, index)),
        el('div', { class: 'profile-main' }, [
          el('h3', {}, [el('span', { text: p.displayName }), p.sample ? el('span', { class: 'tag tag-sample', text: 'サンプル' }) : null]),
          p.anonymous ? null : el('p', { class: 'profile-id', text: `@${p.id}` }),
          el('div', { class: 'now-line is-drift' }, [el('span', { class: 'now-tag', text: '🌊 漂流中' }), el('p', { class: 'now-text', text: 'まだ漂着していません。次の動画で島に流れ着きます。' })]),
        ]),
      ]),
      el('dl', { class: 'facts' }, [el('div', {}, [el('dt', { text: '漂流開始' }), el('dd', { text: p.since ? p.since.replaceAll('-', '/') : '—' })])]),
    ]);
    setView('detail');
  }

  function showBuilding(b) {
    if (currentView !== 'detail') returnView = isSheetOpen() ? currentView : null;
    selected = -1;
    selectedDrifter = -1;
    nowLine = null;
    const root = views.detail;
    fill(root, [
      detailHeader(el('span', { class: 'detail-kicker', text: '建物' })),
      el('div', { class: 'profile' }, [
        el('span', { class: 'portrait-wrap portrait-big portrait-building' }, iconCanvas('home')),
        el('div', { class: 'profile-main' }, [el('h3', { text: b.name }), el('p', { class: 'profile-id', text: b.typeLabel })]),
      ]),
      el('dl', { class: 'facts' }, [el('div', {}, [el('dt', { text: b.type === 'bigcrate' ? '流れ着いた' : '完成' }), el('dd', { text: b.builtDay ? `${b.builtDay}日目` : '—' })]), el('div', {}, [el('dt', { text: '種類' }), el('dd', { text: b.typeLabel })])]),
      b.note ? el('p', { text: b.note }) : null,
      b.type === 'stage' ? stageTimetable() : null,
    ]);
    setView('detail');
  }

  // ステージの時間割：いまの出し物と、このあと
  function stageTimetable() {
    const t = now();
    const hm = (ms) => { const d = new Date(ms + 9 * 3600000); return `${String(d.getUTCHours()).padStart(2, '0')}:${String(d.getUTCMinutes()).padStart(2, '0')}`; };
    const rows = [];
    for (let k = 0; k < 8; k++) {
      const s = showAt(islanders, state.day, t, k);
      if (!s) break;
      rows.push(el('li', { class: k === 0 ? 'is-now' : '' }, [el('b', { text: k === 0 ? 'いま' : hm(s.start) }), el('span', { text: showLabel(islanders, s) })]));
    }
    return el('div', { class: 'timetable' }, [el('h4', { class: 'section-title', text: 'ステージの時間割（15分ごと）' }), el('ul', {}, rows)]);
  }

  // ---- 鑑賞モード：ステージをタップ → 客席から舞台を見る。いまの出し物と時間割 ----
  let stageView = null;
  function hmOf(ms) { const d = new Date(ms + 9 * 3600000); return `${String(d.getUTCHours()).padStart(2, '0')}:${String(d.getUTCMinutes()).padStart(2, '0')}`; }
  function enterStageView(b, { onExit, onShow } = {}) {
    exitStageView(true);
    const root = el('div', { id: 'stage-view', role: 'dialog', 'aria-label': `${b.name}を鑑賞中` });
    const close = el('button', { class: 'sv-close', type: 'button', 'aria-label': '鑑賞をやめる', text: '×', on: { click: () => exitStageView() } });
    const top = el('div', { class: 'sv-top' }, [el('span', { class: 'sv-badge', text: '鑑賞中' }), el('span', { class: 'sv-name', text: b.name }), close]);
    const now_ = el('div', { class: 'sv-now' });
    const list = el('ul', { class: 'sv-list' });
    list.hidden = true;
    const toggle = el('button', { class: 'sv-toggle', type: 'button', 'aria-expanded': 'false', text: '時間割をひらく' });
    toggle.addEventListener('click', () => {
      const open = list.hidden;
      list.hidden = !open;
      toggle.setAttribute('aria-expanded', String(open));
      toggle.textContent = open ? '時間割をとじる' : '時間割をひらく';
    });
    const card = el('div', { class: 'sv-card' }, [now_, toggle, list]);
    root.append(top, card);
    document.getElementById('stage').append(root);
    document.body.dataset.mode = 'stage';
    let slot = null;
    const tick = () => {
      const t = now();
      const s = showAt(islanders, state.day, t);
      if (!s) return;
      const left = Math.max(0, Math.ceil((s.end - t) / 60000));
      if (s.slot !== slot) {
        slot = s.slot;
        const names = s.members.map((i) => islanders[i]?.displayName).filter(Boolean);
        fill(now_, [
          el('p', { class: 'sv-when' }, [el('b', { text: 'いま' }), el('span', { text: `${hmOf(s.start)}〜${hmOf(s.end)}` }), el('span', { class: 'sv-left' })]),
          el('h3', { class: 'sv-title', text: showLabel(islanders, s) }),
          names.length > 1 ? el('p', { class: 'sv-members', text: `出演：${names.map((n) => `${n}さん`).join('・')}` }) : null,
        ]);
        const rows = [];
        for (let k = 1; k < 8; k++) {
          const n = showAt(islanders, state.day, t, k);
          if (n) rows.push(el('li', {}, [el('b', { text: hmOf(n.start) }), el('span', { text: showLabel(islanders, n) })]));
        }
        fill(list, rows);
        onShow?.(s);
      }
      const l = now_.querySelector('.sv-left');
      if (l) l.textContent = `あと${left}分`;
    };
    tick();
    const timer = setInterval(tick, 1000);
    stageView = { root, timer, onExit };
  }
  function exitStageView(silent = false) {
    if (!stageView) return;
    const v = stageView;
    stageView = null;
    clearInterval(v.timer);
    v.root.remove();
    delete document.body.dataset.mode;
    if (!silent) v.onExit?.();
  }

  function closeDetail(forceClose = false) {
    selected = -1;
    selectedDrifter = -1;
    nowLine = null;
    if (currentView === 'detail') {
      if (returnView && !forceClose) setView(returnView);
      else setView(returnView || 'islanders', { open: false });
    }
    returnView = null;
    onCloseDetail?.();
  }

  // ---- そのほか --------------------------------------------------------------
  let toastTimer = null;
  function toast(message, ms = 2600) {
    const t = $('toast');
    t.textContent = message;
    t.classList.add('is-on');
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => t.classList.remove('is-on'), ms);
  }

  function setLoading(text) {
    const l = $('loading');
    if (!text) {
      l.hidden = true;
      return;
    }
    l.hidden = false;
    l.querySelector('.loading-text').textContent = text;
  }

  function showStageError(message) {
    const l = $('loading');
    l.hidden = false;
    l.classList.add('is-error');
    l.querySelector('.loading-text').textContent = message;
  }

  function renderData(data, opts = {}) {
    state = data.state;
    setShowRequests(state.stageRequests);
    islanders = data.islanders;
    drifters = data.drifters || [];
    ranked = rankIslanders(islanders);
    if (opts.portraitFor) portraitFor = opts.portraitFor;
    if (opts.drifterPortraitFor) drifterPortraitFor = opts.drifterPortraitFor;
    renderHeader();
    renderList();
    renderIslandNow();
    renderChronicle();
    renderVote();
    $('sample-note').hidden = !(state.sample || islanders.some((p) => p.sample) || drifters.some((p) => p.sample));
    $('updated').textContent = state.updatedAt ? `データ更新：${state.updatedAt.replaceAll('-', '/')}` : '';
    clearInterval(voteTimer);
    voteTimer = setInterval(renderVote, 60000);
  }

  setView('islanders', { open: false });

  return {
    renderData,
    showIslander,
    showDrifter,
    showBuilding,
    enterStageView,
    exitStageView,
    inStageView: () => !!stageView,
    closeDetail,
    setView,
    toast,
    setLoading,
    showStageError,
    isSheetOpen,
    isDesktop: () => desktop.matches,
    selectedIndex: () => selected,
    // 詳細の「いま」：タグ（いま・仕事中）、文、このあとの予定。st は sim.status() の結果
    setNow: (st) => {
      if (!nowLine || !st) return;
      const key = `${st.label}|${st.text}|${st.next}`;
      if (key === nowKey) return;
      nowKey = key;
      nowLine.classList.toggle('is-missing', !!st.missing);
      fill(nowLine, [
        el('span', { class: 'now-tag', text: st.label ? `いま・${st.label}` : 'いま' }),
        el('p', { class: 'now-text', text: st.text }),
        st.next ? el('p', { class: 'now-next', text: `このあと：${st.next}` }) : null,
      ]);
    },
    // シート＋タブがステージに重なっている高さ（スマホのみ）
    overlapHeight: () => {
      if (desktop.matches) return 0;
      return window.innerHeight - panel.getBoundingClientRect().top;
    },
    expectedOverlap: () => {
      if (desktop.matches) return 0;
      const tabsH = $('tabs').getBoundingClientRect().height;
      return body.dataset.sheet === 'open' ? tabsH + Math.round(window.innerHeight * 0.5) : tabsH;
    },
  };
}
