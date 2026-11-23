// ステージの出し物（PWA）：30分ごとに出演者が代わる。仲良しがいる人は、仲良しも一緒に上がる。
// 時刻と名簿だけで決まる（どの端末でも同じ人が出ている）。
import { hashStr } from './rng.js';

export const SLOT_MIN = 30;
const ACTS = { sing: '歌', dance: 'ダンス', cook: '料理ショー', talk: 'トーク' };
const JST = 9 * 3600 * 1000;

// 出演の順番：その日ごとに名簿を並べ替える（同じ日は同じ順）
function orderOf(islanders, day) {
  return islanders.map((p, i) => ({ i, h: hashStr(`${p.id}:show:${day}`) })).sort((a, b) => a.h - b.h || a.i - b.i).map((x) => x.i);
}

// tMs の時刻の出し物：{ slot, start, end, lead, members:[index…], act, label }
export function showAt(islanders, day, tMs, offset = 0) {
  if (!islanders.length) return null;
  const idx = new Map(islanders.map((p, i) => [String(p.id), i]));
  const slot = Math.floor((tMs + JST) / (SLOT_MIN * 60000)) + offset;
  const order = orderOf(islanders, day);
  const lead = order[((slot % order.length) + order.length) % order.length];
  const p = islanders[lead];
  const friends = (p.relationships || []).filter((r) => r.type === 'friend').map((r) => idx.get(String(r.id))).filter((j) => j !== undefined && j !== lead);
  const members = [lead, ...friends].slice(0, 6);
  const keys = Object.keys(ACTS);
  const act = p.job === '料理人' && hashStr(`${p.id}:act`) % 2 === 0 ? 'cook' : keys[hashStr(`${p.id}:act:${day}`) % 4];
  const start = slot * SLOT_MIN * 60000 - JST;
  return { slot, start, end: start + SLOT_MIN * 60000, lead, members, act, label: ACTS[act] };
}

export function showLabel(islanders, s) {
  const p = islanders[s.lead];
  const n = s.members.length - 1;
  return `${p.displayName}さん${n ? `と仲良し${n}人` : ''}（${s.label}）`;
}
