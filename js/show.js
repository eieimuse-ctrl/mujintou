// ステージの出し物（PWA）：15分ごとに出演者が代わる。仲良しがいる人は、仲良しも一緒に上がる。
// 時刻と名簿だけで決まる（どの端末でも同じ人が出ている）。
// コメントで募集した「やりたいこと」（state.stageRequests）は、after の時刻からの枠に順に入り、
// ふだんの順番はそのぶん後ろへずれる（after を「いまから24時間後」にすれば、見えている時間割は変わらない）。
import { hashStr } from './rng.js';

export const SLOT_MIN = 15;
const SLOT_MS = SLOT_MIN * 60000;
const ACTS = { sing: '歌', dance: 'ダンス', cook: '料理ショー', talk: 'トーク' };
const JST = 9 * 3600 * 1000;

let requests = []; // [{ id, text, kind, after(ms) }]
// state.stageRequests: [{ "id": "インスタID", "text": "ギター弾き語り", "kind": "sing|dance|cook|talk", "after": "2026-11-25T21:00:00+09:00" }]
export function setShowRequests(list) {
  requests = (Array.isArray(list) ? list : [])
    .map((r, n) => ({ id: String(r?.id || '').replace(/^@/, ''), text: String(r?.text || '').slice(0, 30), kind: ACTS[r?.kind] ? r.kind : 'talk', after: Date.parse(r?.after), n }))
    .filter((r) => r.id && r.text && Number.isFinite(r.after))
    .sort((a, b) => a.after - b.after || a.n - b.n);
  cache.key = null;
}

const slotOf = (tMs) => Math.floor((tMs + JST) / SLOT_MS);

// 出演の順番：その日ごとに名簿を並べ替える（同じ日は同じ順）
const cache = { key: null, order: null, idx: null, req: null };
function prep(islanders, day) {
  const key = `${day}:${islanders.length}`;
  if (cache.key === key && cache.islanders === islanders) return cache;
  cache.key = key;
  cache.islanders = islanders;
  cache.order = islanders.map((p, i) => ({ i, h: hashStr(`${p.id}:show:${day}`) })).sort((a, b) => a.h - b.h || a.i - b.i).map((x) => x.i);
  cache.idx = new Map(islanders.map((p, i) => [String(p.id), i]));
  // 募集の枠：after のあとの、空いている最初の枠へ順に
  cache.req = new Map();
  let last = -Infinity;
  for (const r of requests) {
    const i = cache.idx.get(r.id);
    if (i === undefined) continue;
    const s = Math.max(slotOf(r.after - 1) + 1, last + 1);
    cache.req.set(s, { ...r, i });
    last = s;
  }
  cache.reqSlots = [...cache.req.keys()].sort((a, b) => a - b);
  return cache;
}

// tMs の時刻の出し物：{ slot, start, end, lead, members:[index…], act, label }
export function showAt(islanders, day, tMs, offset = 0) {
  if (!islanders.length) return null;
  const C = prep(islanders, day);
  const slot = slotOf(tMs) + offset;
  const rq = C.req.get(slot);
  let lead, act, label;
  if (rq) {
    lead = rq.i;
    act = rq.kind;
    label = rq.text;
  } else {
    let before = 0; // この枠より前に入った募集の数だけ、ふだんの順番を後ろへずらす
    for (const s of C.reqSlots) if (s < slot) before++;
    const k = slot - before;
    lead = C.order[((k % C.order.length) + C.order.length) % C.order.length];
    const p = islanders[lead];
    const keys = Object.keys(ACTS);
    act = p.job === '料理人' && hashStr(`${p.id}:act`) % 2 === 0 ? 'cook' : keys[hashStr(`${p.id}:act:${day}`) % 4];
    label = ACTS[act];
  }
  const p = islanders[lead];
  const friends = (p.relationships || []).filter((r) => r.type === 'friend').map((r) => C.idx.get(String(r.id))).filter((j) => j !== undefined && j !== lead);
  const members = [lead, ...friends].slice(0, 6);
  const start = slot * SLOT_MS - JST;
  return { slot, start, end: start + SLOT_MS, lead, members, act, label, request: !!rq };
}

export function showLabel(islanders, s) {
  const p = islanders[s.lead];
  const n = s.members.length - 1;
  return `${p.displayName}さん${n ? `と仲良し${n}人` : ''}（${s.label}）`;
}

// この人が出る、いちばん近い出し物（いま出ていれば、いまの枠）。hours 時間先まで探す
export function nextShowOf(islanders, day, index, tMs, hours = 24) {
  const n = Math.ceil((hours * 60) / SLOT_MIN);
  for (let k = 0; k <= n; k++) {
    const s = showAt(islanders, day, tMs, k);
    if (s && s.members.includes(index)) return s;
  }
  return null;
}

// hours 時間先までの出演予定：Map(index → いちばん近い出し物)
export function upcomingMap(islanders, day, tMs, hours = 24) {
  const out = new Map();
  const n = Math.ceil((hours * 60) / SLOT_MIN);
  for (let k = 0; k <= n; k++) {
    const s = showAt(islanders, day, tMs, k);
    if (s) for (const i of s.members) if (!out.has(i)) out.set(i, s);
  }
  return out;
}
