#!/usr/bin/env python3
"""8日目の台本（約58秒）。カメラは激しく（これからの標準）。
  python3 video-tools/ep8/build_story.py
入力：ep8/input/comments.json（7日目の投稿のコメント。likeCount つき）・ep8/input/islanders.json
流れ（2026-11-24 本人と確定）
  375人の大漂着（浜を埋めつくす）→ リンク → いいねバー（灯台まであと53）
  → ステージ：さかさんの「娯楽が欲しい」→ アンケートで広場のそば → 大工が建てる → かがり火、AK24さんの料理ショー → 15分交代・名前で出番
  → 前回のコメントから（いいね順）→ 投票 A 高原 → クマを先頭に高原へ（ざーふさんは背中に）→ 高原の奥にクマの家族
  → 謎（何かを見つけた人がいるらしい）→ 次の問い「この島で、何をする？」（自由。賛同が集まると形になりやすい）
"""
import json, os, re, math, random
HERE = os.path.dirname(os.path.abspath(__file__))
os.makedirs(os.path.join(HERE, 'story'), exist_ok=True)
C = json.load(open(os.environ.get('COMMENTS') or os.path.join(HERE, 'input', 'comments.json'), encoding='utf-8'))
ROSTER_PATH = os.path.abspath(os.environ.get('ROSTER') or os.path.join(HERE, 'input', 'islanders.json'))
ROSTER_REL = os.path.relpath(ROSTER_PATH, os.path.join(HERE, 'story'))
R = json.load(open(ROSTER_PATH, encoding='utf-8'))
ROSTER = {p['id']: p for p in R['islanders']}
DAY = 8
inr = lambda i: bool(i) and i in ROSTER
LIKES = int(C['post'].get('likesTotal') or 0)
GOALS = [{'at': 600, 'label': '畑が一晩で実る'}, {'at': 750, 'label': '灯台が建つ'}, {'at': 1000, 'label': 'もこもこのひつじが流れ着く'}]
NEXT = next((g for g in GOALS if LIKES < g['at']), None)
rnd = random.Random(8)

OPTS = {'A': '高原（クマが道を知っている）', 'B': '昔の住人の跡を、もっと掘る', 'C': '浜の先の岬（木箱が来た方角）', 'D': '自由に提案'}
VOTE_RE = re.compile(r'(?<![A-Za-zＡ-Ｚａ-ｚ])([ABCDabcdＡＢＣＤａｂｃｄ])(?![A-Za-zＡ-Ｚａ-ｚ])')
Z2H = {'Ａ': 'A', 'Ｂ': 'B', 'Ｃ': 'C', 'Ｄ': 'D', 'ａ': 'A', 'ｂ': 'B', 'ｃ': 'C', 'ｄ': 'D'}
def vote_of(text):
    m = VOTE_RE.search(re.sub(r'@[\w.]+', ' ', text or ''))
    return (Z2H.get(m.group(1)) or m.group(1).upper()) if m else None
cm = [c for c in C['comments'] if c.get('userId') and c.get('status') != 'none']
people = {}
for c in sorted(cm, key=lambda c: c.get('at') or ''):
    prev = people.get(c['userId'])
    people[c['userId']] = {**c, 'vote': vote_of(c.get('text')) or (prev or {}).get('vote')}
tally = {k: 0 for k in OPTS}
for p in people.values():
    if p['vote'] in tally: tally[p['vote']] += 1
winner = max(OPTS, key=lambda k: (tally[k], -list(OPTS).index(k)))
def name_of(i):
    n = (people.get(i, {}).get('name') or '').strip() or ROSTER.get(i, {}).get('name') or i
    ok = sum(1 for ch in n if ch.isascii() and ch.isalnum() or '぀' <= ch <= 'ヿ' or '一' <= ch <= '鿿')
    return n if ok >= max(1, len(n) // 2) else i
commenters = {i: (p['vote'] or '-') for i, p in people.items() if inr(i)}
# いいねの多いコメント（前回のコメントから）
top = sorted([c for c in cm if inr(c['userId'])], key=lambda c: (-(c.get('likeCount') or 0), c.get('at') or ''))
seen, TOP = set(), []
for c in top:
    if c['userId'] in seen or not (c.get('likeCount') or 0): continue
    seen.add(c['userId']); TOP.append(c)
TOP = TOP[:3]

SAKA, AK, ZAF, RINO, CHUN, ONO, IBU, MARU = 'sakasaka_1482', 'akrfjmt417', 'guernica.0712', 'rino._.15', 'chun0327', 'onoka0703', 'ibu131313', 'marumegane4'
ZF = sorted({r['id'] for r in (ROSTER.get(ZAF, {}).get('relationships') or []) if r.get('type') == 'friend' and inr(r.get('id'))})
arrivals = [p['id'] for p in R['islanders'] if int(p.get('joinedDay', 0)) == DAY]
n_arrive, n_all = len(arrivals), len(R['islanders'])
special = {SAKA, AK, ZAF, RINO, CHUN, ONO, IBU, MARU} | set(ZF) | {c['userId'] for c in TOP}
older = [p for p in R['islanders'] if int(p.get('joinedDay', 0)) < DAY and p['id'] not in special]
builders = [x for x in [SAKA] if inr(x)] + [p['id'] for p in older if p.get('job') == '大工'][:5]
audience = [p['id'] for p in older if p['id'] not in builders][:46]
hikers = [p['id'] for p in older if p['id'] not in builders and p['id'] not in audience][:30]

# ---- 場所（ワールド座標） ----
HUT = [-60.0, -15.0]                  # 拠点（はじまりの小屋）
STAGE = [22.0, 34.0]                  # みんなのステージ（中央の広場のそば。正面は +z）
SEAT = [STAGE[0], STAGE[1] + 8.5]    # 客席
FIRES = [[STAGE[0] - 4.9, STAGE[1] + 3.2], [STAGE[0] + 4.9, STAGE[1] + 3.2]]
HWAY = [[2.0, -4.0], [40.0, -70.0], [65.0, -120.0], [76.0, -134.0]]  # 高原へ
FAM = [84.0, -146.0]                  # クマの家族
KIDS = [[FAM[0] - 3.2, FAM[1] + 1.0], [FAM[0] + 2.6, FAM[1] + 1.8]]
MID = [(HWAY[-1][0] + FAM[0]) / 2, (HWAY[-1][1] + FAM[1]) / 2 + 3]

BEACH = json.load(open(os.path.join(HERE, '..', 'ep7', 'beach_spots.json')))
spots = [list(b) for b in BEACH]
for layer in range(3):  # 浜を埋めつくす：まわりにずらして3重に
    for b in BEACH:
        spots.append([round(b[0] + rnd.uniform(-3.2, 3.2), 1), round(b[1] + rnd.uniform(-3.2, 3.2), 1)])
rnd.shuffle(spots)

groups = [
    {'name': 'south', 'type': 'line', 'spot': [0, 0], 'face': [0, 1], 'members': []},
    {'name': 'beach', 'type': 'ring', 'spot': [236.0, 124.0], 'radius': 3.2, 'gap': 2.6, 'members': []},
    {'name': 'seat', 'type': 'line', 'spot': [SEAT[0], SEAT[1] + 1.5], 'face': [0, -1], 'gap': 1.7, 'rows': 4, 'members': audience},
    {'name': 'build', 'type': 'line', 'spot': [STAGE[0], STAGE[1] + 7.5], 'face': [0, -1], 'gap': 2.6, 'members': builders},
]
acts = [{'who': '*', 't': 0, 'anim': 'idle', 'face': 'front'}]
A = acts.append

# S0 大漂着（0〜4.6）：浜いっぱいに寝ている → 起きて → 海からもまだ流れ着く
sleepers = arrivals[:len(spots)]
for k, i in enumerate(sleepers):
    x, z = spots[k]
    if k % 5 == 0:  # 5人に1人は、海から走って上がってくる
        A({'who': i, 't': 0, 'at': [x + 14, z + rnd.uniform(-2, 2)], 'anim': 'idle', 'face': {'at': [x - 20, z]}, 'hide': False})
        A({'who': i, 't': 0.4 + (k % 7) * 0.18, 'to': [x, z], 'dur': 1.6, 'run': True})
        A({'who': i, 't': 2.6, 'anim': 'cheer', 'face': 'front'})
    else:
        A({'who': i, 't': 0, 'at': [x, z], 'anim': 'sleep', 'face': 'front', 'hide': False})
        A({'who': i, 't': 1.2 + (k % 11) * 0.09, 'anim': 'sit' if k % 3 == 0 else 'sleep'})
        A({'who': i, 't': 2.4 + (k % 13) * 0.07, 'anim': 'cheer' if k % 2 else 'idle'})
    A({'who': i, 't': 4.6, 'hide': True})

# S3 ステージ（9.6〜20.4）
if inr(SAKA): A({'who': SAKA, 't': 9.6, 'at': [HUT[0] + 2, HUT[1] + 8], 'anim': 'idle', 'face': 'front', 'hide': False})
A({'who': builders, 't': 12.0, 'at': {'slot': 'build'}, 'anim': 'work', 'face': {'at': STAGE}})
A({'who': builders, 't': 14.4, 'anim': 'cheer', 'face': 'front'})
A({'who': builders, 't': 15.0, 'hide': True})
A({'who': audience, 't': 15.0, 'at': {'slot': 'seat'}, 'anim': 'idle', 'face': {'at': STAGE}})
A({'who': audience, 't': 16.4, 'anim': 'cheer', 'pick': 0.6, 'seed': 4})
cast_on = [x for x in [AK] if inr(x)]
for k, i in enumerate(cast_on):
    A({'who': i, 't': 15.0, 'at': {'xz': [STAGE[0], STAGE[1] + 0.6], 'up': 1.1}, 'anim': 'work', 'face': 'front', 'hide': False})
    A({'who': i, 't': 18.6, 'anim': 'cheer'})
A({'who': audience, 't': 20.4, 'hide': True})
for i in cast_on: A({'who': i, 't': 20.4, 'hide': True})

# S4 前回のコメントから（20.4〜24.8）：上位の3人が広場に並ぶ
TOPI = [c['userId'] for c in TOP]
for k, i in enumerate(TOPI):
    A({'who': i, 't': 20.4, 'at': [-4 + k * 4, 12], 'anim': 'cheer' if k == 0 else 'idle', 'face': 'front', 'hide': False})
    A({'who': i, 't': 24.8, 'hide': True})

# S6 高原へ（27.6〜38.6）：クマが先頭、ざーふさんは背中、みんなが走ってついていく
def lerp_path(P, u):
    seg = [math.dist(a, b) for a, b in zip(P, P[1:])]; L = sum(seg); d = u * L
    for (a, b), s in zip(zip(P, P[1:]), seg):
        if d <= s: w = d / s; return [a[0] + (b[0] - a[0]) * w, a[1] + (b[1] - a[1]) * w]
        d -= s
    return list(P[-1])
T6, T7 = 27.6, 38.6
RUN = [T6 + 0.4, T6 + 9.2]
def bear_at(t):
    if t <= RUN[0]: return lerp_path(HWAY, 0)
    if t >= RUN[1]: return lerp_path(HWAY, 1)
    u = (t - RUN[0]) / (RUN[1] - RUN[0]); return lerp_path(HWAY, u * u * (3 - 2 * u))
if inr(ZAF):
    A({'who': ZAF, 't': T6, 'ride': True, 'anim': 'cheer', 'hide': False})
    A({'who': ZAF, 't': T7, 'ride': False, 'hide': True})
followers = ZF + [x for x in [RINO, CHUN, ONO] if inr(x)] + hikers
for k, i in enumerate(followers):
    lag = 0.25 + (k % 10) * 0.16 + (k // 10) * 0.5
    side = ((k % 5) - 2) * 1.6
    p0 = HWAY[0]
    A({'who': i, 't': T6, 'at': [p0[0] + side, p0[1] + 4 + (k // 5) * 1.8], 'anim': 'cheer', 'face': {'at': HWAY[1]}, 'hide': False})
    end = lerp_path(HWAY, 0.93)
    A({'who': i, 't': RUN[0] + lag, 'to': [MID[0] + side * 1.3 + (k // 5 % 2) * 0.8, MID[1] + 7 + (k // 5) * 1.5], 'dur': RUN[1] - RUN[0], 'run': True})
    A({'who': i, 't': RUN[1] + lag + 0.2, 'anim': 'shock', 'face': {'at': FAM}})
    A({'who': i, 't': T7 + 1.2, 'anim': 'cheer', 'pick': 0.7, 'seed': k})
    A({'who': i, 't': T7 + 3.4, 'hide': True})

# クマ（母グマ＝いつものクマ）の道すじ：高原の奥で止まり、家族と並ぶ
BPATH = []
t = 0.0
while t <= T7 + 3.5:
    p = bear_at(t); BPATH.append([round(t, 2), round(p[0], 2), round(p[1], 2)]); t = round(t + 0.1, 2)

# カメラ（激しく：寄り引き・回りこみ・手ぶれ・画角を大きく動かす）
DUR = 58.0
W = lambda look, dist, az, pol, up, t, fov=42: {'t': t, 'look': look, 'dist': dist, 'az': az, 'pol': pol, 'up': up, 'frame': 'south', 'fov': fov}
BC = [236.0, 124.0]
camera = [
    # 大漂着：真上の引きから一気に急降下して、浜の人の波をなめる
    {'from': 0, 'to': 4.6, 'hour': 7.4, 'shake': [[1.5, 2.3, 1.6]], 'keys': [W(BC, 230, -1.2, 0.25, 0, 0, 50), W([BC[0] - 4, BC[1]], 70, 0.2, 0.75, 1, 1.5, 48), W([BC[0] - 8, BC[1] + 6], 22, 1.1, 1.22, 2, 3.0, 40), W([BC[0] - 14, BC[1] - 10], 40, 2.4, 1.0, 2, 4.6, 46)]},
    {'from': 4.6, 'to': 6.6, 'hour': 11, 'keys': [W([15, 40], 950, 0.0, 0.6, 0, 4.6), W([15, 40], 620, 1.0, 0.9, 0, 6.6)]},
    {'from': 6.6, 'to': 9.6, 'hour': 12, 'keys': [W([0, 0], 520, -0.8, 0.5, 0, 6.6), W([0, 0], 380, 0.6, 0.85, 0, 9.6)]},
    # さかさんのつぶやき：ぐっと寄る
    {'from': 9.6, 'to': 12.0, 'hour': 17.4, 'keys': [W([HUT[0] + 2, HUT[1] + 8], 34, -1.0, 0.9, 1.6, 9.6, 46), W([HUT[0] + 2, HUT[1] + 8], 11, -0.1, 1.3, 1.6, 12.0, 34)]},
    # 建てる：まわりを高速で一周
    {'from': 12.0, 'to': 15.0, 'hour': 16.8, 'shake': [[14.2, 14.8, 0.8]], 'keys': [W(STAGE, 30, -2.2, 0.85, 2, 12.0, 46), W(STAGE, 24, -0.6, 1.0, 2.5, 13.5, 44), W(STAGE, 30, 0.9, 1.05, 2.5, 15.0, 44)]},
    # かがり火と料理ショー：客席の頭ごしから舞台へ突っこむ
    {'from': 15.0, 'to': 20.4, 'hour': 18.6, 'keys': [W([STAGE[0], STAGE[1] + 8], 40, -0.5, 0.8, 2.5, 15.0, 50), W([STAGE[0], STAGE[1] + 2], 24, 0.2, 0.95, 3.5, 17.0, 42), W([STAGE[0], STAGE[1] + 1], 15, -0.25, 1.05, 3.5, 18.6, 36), W([STAGE[0], STAGE[1] + 6], 38, 0.9, 0.8, 2, 20.4, 46)]},
    {'from': 20.4, 'to': 24.8, 'hour': 13, 'keys': [W([0, 12], 26, -0.5, 1.15, 2, 20.4, 44), W([0, 12], 18, 0.4, 1.25, 2, 24.8, 40)]},
    {'from': 24.8, 'to': 27.6, 'hour': 12, 'keys': [W([60, -110], 420, 0.3, 0.55, 0, 24.8), W([60, -110], 300, -0.3, 0.8, 0, 27.6)]},
    # 高原へ：クマの横を並走 → 前から → 真後ろから坂を見上げる
    {'from': T6, 'to': T7, 'hour': 15.5, 'shake': [[T6 + 0.4, T6 + 1.4, 1.2]], 'keys': [
        W(bear_at(T6), 16, 1.5, 1.15, 3.5, T6, 46), W(bear_at(T6 + 2.6), 13, 1.2, 1.2, 3.5, T6 + 2.6, 44),
        W(bear_at(T6 + 5.0), 18, 2.9, 1.15, 3.5, T6 + 5.0, 46), W(bear_at(T6 + 7.6), 20, 0.4, 1.05, 4, T6 + 7.6, 48),
        W(bear_at(T7), 30, 0.2, 1.0, 3, T7, 44)]},
    # クマの家族：子グマに寄って、ふわっと引く
    {'from': T7, 'to': T7 + 4.0, 'hour': 16.2, 'keys': [W(KIDS[0], 10, 0.6, 1.25, 1.5, T7, 36), W(MID, 26, 0.25, 1.0, 2, T7 + 1.6, 42), W(MID, 44, -0.3, 0.9, 2, T7 + 4.0, 46)]},
    # 謎：夜の島をゆっくり（一瞬止まる）
    {'from': T7 + 4.0, 'to': 46.6, 'hour': 22.5, 'keys': [W([20, -20], 640, 2.0, 0.7, 0, T7 + 4.0, 40), W([20, -20], 560, 2.6, 0.75, 0, 46.6, 40)]},
    # 次の問い：島の上をぐるっと
    {'from': 46.6, 'to': 55.6, 'hour': 9.5, 'keys': [W([15, 20], 300, -1.6, 0.6, 0, 46.6, 46), W([15, 20], 520, -0.2, 0.8, 0, 51.0, 44), W([15, 20], 700, 1.0, 0.85, 0, 55.6, 42)]},
    {'from': 55.6, 'to': DUR, 'hour': 18.5, 'keys': [W([15, 40], 700, 0.8, 0.85, 0, 55.6), W([15, 40], 780, 1.0, 0.85, 0, DUR)]},
]

props = [{'type': 'zzz', 'from': {'rel': i, 'up': 1.6}, 't0': 0, 't1': 0.01, 't2': 2.2, 'size': 0.9, 'phase': k * 0.3} for k, i in enumerate(sleepers[1:40:5])]
# かがり火（ステージができてから）
for k, f in enumerate(FIRES):
    props.append({'type': 'flame', 'from': {'xz': f, 'up': 2.2}, 't0': 15.0, 't1': 15.01, 't2': 20.4, 'size': 1.5})
# 料理ショー：鍋から湯気のかわりに、魚と木の実が客席へ飛ぶ
for k in range(6):
    props.append({'type': 'fish' if k % 2 else 'fruit', 'from': {'xz': [STAGE[0], STAGE[1] + 1], 'up': 3}, 'to': [SEAT[0] - 5 + k * 2, SEAT[1] - 1], 't0': 17.0 + k * 0.25, 't1': 17.9 + k * 0.25, 't2': 18.5 + k * 0.25, 'arc': 4, 'size': 0.9})
props.append({'type': 'question', 'from': {'xz': FAM, 'up': 0}, 't0': T7 - 0.4, 't1': T7 - 0.39, 't2': T7 + 1.0, 'size': 3})
for k, kd in enumerate(KIDS):
    props.append({'type': 'heart', 'from': {'xz': kd, 'up': 3.2}, 'to': {'xz': kd, 'up': 4.2}, 't0': T7 + 1.4 + k * 0.3, 't1': T7 + 3.6, 't2': T7 + 3.6, 'size': 1.4, 'phase': k})

props3d = [
    {'type': 'build', 'kind': 'stage', 'at': STAGE, 'rot': 0, 't0': 12.2, 't1': 14.4, 'show': 12.0, 'hide': 20.4},
    {'type': 'beast', 'at': HWAY[0], 'path': BPATH, 'show': T6, 'hide': T7 + 4.0, 't0': 0, 't1': T7 + 3.5},
    *[{'type': 'beast', 'at': kd, 'path': [[0, kd[0], kd[1]], [60, kd[0], kd[1]]], 'size': 0.55, 'show': T7 - 1.0, 'hide': T7 + 4.0, 't0': 0, 't1': 60} for kd in KIDS],
]

def star(i, a, b, text):
    return {'who': i, 'from': a, 'to': b, 'bubble': text} if inr(i) else None
stars = [x for x in [
    star(SAKA, 10.2, 12.0, '娯楽が欲しい…'),
    star(AK, 16.0, 18.5, '料理長のうまい料理、振る舞うよ！'),
    star(RINO, 31.0, 33.6, 'クマさんの毛で、暖かい服を着てレッツゴ〜！'),
    star(CHUN, T7 + 1.6, T7 + 3.8, '熊の家族と遊びたい！'),
] if x]
ROWS = [{'key': k, 'label': OPTS[k], 'count': tally[k]} for k in OPTS]
LB = {'total': LIKES, 'max': 1000, 'goals': GOALS}
TOPROWS = [{'name': name_of(c['userId']), 'text': re.sub(r'\s+', ' ', c.get('text') or ''), 'likes': c.get('likeCount') or 0} for c in TOP]
overlay = {
    'banner': 'コメントで動く無人島　8日目',
    'bannerOff': [[0, 6.6], [24.8, 27.6], [T7 + 4.0, DUR]],
    'commenters': commenters,
    'names': {**{i: name_of(i) for i in people}, **{i: name_of(i) for i in [SAKA, AK, ZAF, RINO, CHUN]}},
    'titles': [{'text': '8日目', 'from': 0.1, 'to': 2.8}],
    'tagAll': [[2.6, 4.6, 0.02]],
    'tagOnly': [{'from': 12.4, 'to': 14.8, 'who': builders, 'below': True, 'size': 30}] + ([{'from': T6 + 0.4, 'to': T6 + 3.0, 'who': [ZAF], 'size': 34}] if inr(ZAF) else []),
    'tagCycle': [{'from': 15.0, 'to': 20.4, 'n': 4, 'step': 1.6, 'size': 24, 'alpha': 0.62}, {'from': T6 + 3.0, 'to': T7, 'n': 4, 'step': 1.6, 'size': 24, 'alpha': 0.62}],
    'stars': stars,
    'ranking': {'from': 20.4, 'to': 24.8, 'title': '前回、いいねが多かったコメント', 'rows': TOPROWS, 'winnerAt': 99},
    'tally': {'from': 24.8, 'to': 27.6, 'title': '昨日の質問　次は島のどこを調べる？', 'grow': [25.0, 26.0], 'winner': winner, 'winnerAt': 26.3, 'rows': ROWS},
    'likebars': [{**LB, 'from': 6.6, 'to': 9.6, 'from0': max(0, LIKES - 105), 'y': 640}, {**LB, 'from': 55.7, 'to': DUR, 'from0': LIKES, 'y': 380}],
    'images': [
        {'file': 'profile.png', 'from': 4.6, 'to': 6.6, 'w': 900, 'y': 600, 'tap': [0.24, 0.905], 'tapLabel': 'フォロー＆いいねで…'},
        {'file': 'profile.png', 'from': 55.7, 'to': DUR, 'w': 900, 'y': 980, 'tap': [0.37, 0.78], 'tapLabel': 'ここから'},
    ],
    'captions': [
        {'text': f'{n_arrive}人が、流れ着いた！', 'from': 0.4, 'to': 2.6, 'y': 1290, 'size': 72},
        {'text': f'島民、{n_all}人に！', 'from': 2.7, 'to': 4.6, 'y': 1290, 'size': 72, 'color': [255, 214, 74]},
        {'text': 'あなたも、次の動画で流れ着きます', 'from': 4.7, 'to': 6.6, 'y': 1400, 'size': 50, 'color': [255, 214, 74]},
        *([{'text': f'あと{NEXT["at"] - LIKES}で、{NEXT["label"]}！', 'from': 7.2, 'to': 9.6, 'y': 1000, 'size': 58, 'color': [255, 214, 74]}] if NEXT else []),
        {'text': 'いいねは全部の投稿で数えます', 'from': 7.8, 'to': 9.6, 'y': 1090, 'size': 40},
        {'text': '6日目、さかさんのつぶやき', 'from': 9.7, 'to': 12.0, 'y': 360, 'size': 56},
        {'text': 'ストーリーのアンケートで、場所は広場のそばに', 'from': 12.1, 'to': 15.0, 'y': 330, 'size': 46},
        {'text': 'ステージが、できた！', 'from': 14.4, 'to': 15.0, 'y': 420, 'size': 70, 'color': [255, 214, 74]},
        {'text': 'こけら落としは、AK24さんの料理ショー', 'from': 15.1, 'to': 18.4, 'y': 330, 'size': 50, 'color': [255, 214, 74]},
        {'text': '15分ごとに、島民が交代で出し物', 'from': 18.5, 'to': 20.4, 'y': 330, 'size': 52, 'color': [255, 214, 74]},
        {'text': '島で自分の名前を検索すると、出番がわかる', 'from': 18.7, 'to': 20.4, 'y': 1300, 'size': 44},
        {'text': '高原へ、出発！', 'from': T6 + 0.1, 'to': T6 + 2.8, 'y': 360, 'size': 72, 'color': [255, 214, 74]},
        {'text': 'クマが、道を知っている', 'from': T6 + 3.0, 'to': T6 + 6.0, 'y': 360, 'size': 58},
        {'text': '高原の奥に…', 'from': T7 - 1.6, 'to': T7, 'y': 360, 'size': 64},
        {'text': 'クマの家族がいた！', 'from': T7 + 0.1, 'to': T7 + 4.0, 'y': 360, 'size': 70, 'color': [255, 214, 74]},
        {'text': 'その夜…', 'from': T7 + 4.1, 'to': 44.4, 'y': 420, 'size': 60},
        {'text': '島のどこかで、何かを見つけた人がいるらしい', 'from': 43.0, 'to': 46.6, 'y': 520, 'size': 46, 'color': [255, 214, 74]},
        {'text': '次の質問', 'from': 46.7, 'to': 55.6, 'y': 330, 'size': 64, 'color': [255, 214, 74]},
        {'text': 'この島で、何をする？', 'from': 46.8, 'to': 55.6, 'y': 470, 'size': 84},
        {'text': 'なんでもOK。コメントで教えてね', 'from': 47.8, 'to': 55.6, 'y': 640, 'size': 52},
        {'text': 'いいねが集まった案ほど、形になりやすい…かも', 'from': 49.2, 'to': 55.6, 'y': 760, 'size': 40, 'color': [220, 230, 255]},
        {'text': '一緒にやりたい人は @ で誘ってね', 'from': 50.4, 'to': 55.6, 'y': 1180, 'size': 48, 'color': [255, 214, 74]},
        {'text': 'ステージでやりたいことも募集中', 'from': 51.4, 'to': 55.6, 'y': 1280, 'size': 46},
        {'text': 'いいねは全部の投稿で数えます', 'from': 55.8, 'to': DUR, 'y': 720, 'size': 42},
    ],
    'smallTagsMax': 5,
}
narr = [
    {'at': 0.3, 'until': 2.6, 'text': f'{n_arrive}人が、流れ着いた！'},
    {'at': 2.7, 'until': 4.6, 'text': f'島民は、{n_all}人に！'},
    {'at': 4.7, 'until': 6.6, 'text': 'フォローといいねで、あなたも。'},
    {'at': 6.7, 'until': 9.6, 'text': f'いいね、あと{NEXT["at"] - LIKES}で、{NEXT["label"]}！' if NEXT else 'いいね、ありがとう！'},
    {'at': 9.7, 'until': 12.0, 'text': 'さかさんの、娯楽が欲しい、から。'},
    {'at': 12.1, 'until': 15.0, 'text': 'みんなで選んだ場所に、ステージができた！'},
    {'at': 15.1, 'until': 18.4, 'text': 'こけら落としは、AK24さんの料理ショー！'},
    {'at': 18.5, 'until': 20.4, 'text': '島で名前を検索すると、出番がわかるよ。'},
    {'at': 20.5, 'until': 24.8, 'text': '前回、いいねが多かったコメント。'},
    {'at': 24.9, 'until': 27.6, 'text': '昨日の一番人気は、高原！'},
    {'at': T6 + 0.1, 'until': T6 + 2.8, 'text': 'クマを先頭に、高原へ出発！'},
    {'at': T6 + 3.0, 'until': T6 + 6.0, 'text': 'クマが、道を知っている。'},
    {'at': T7 - 1.6, 'until': T7, 'text': '高原の奥に…'},
    {'at': T7 + 0.1, 'until': T7 + 4.0, 'text': 'クマの家族がいた！'},
    {'at': T7 + 4.1, 'until': 46.6, 'text': 'その夜。島のどこかで、何かを見つけた人がいるらしい。'},
    {'at': 46.8, 'until': 55.6, 'text': 'この島で、何をする？なんでもいいよ、コメントで教えてね。いいねが集まると、形になるかも。'},
    {'at': 55.8, 'until': DUR, 'text': 'いいねで、島が変わるよ。'},
]
EXIST = [
    {'id': 'ruins-1', 'type': 'ruins', 'name': '昔の住人の跡', 'x': -44.7, 'z': -12.7, 'rot': 0, 'builtDay': 1},
    {'id': 'hut-1', 'type': 'hut', 'name': 'はじまりの小屋', 'x': -20, 'z': -5, 'rot': 20, 'builtDay': 4},
    {'id': 'workshop-1', 'type': 'workshop', 'name': '石の作業場', 'x': -40.3, 'z': -9.0, 'rot': 10, 'builtDay': 5},
    {'id': 'bigfield-1', 'type': 'bigfield', 'name': '巨大な畑', 'x': -36.67, 'z': -17.0, 'rot': 0, 'builtDay': 6},
    {'id': 'bearhouse-1', 'type': 'bearhouse', 'name': 'クマの家', 'x': -29.33, 'z': -12.0, 'rot': 0, 'builtDay': 7},
]
story = {
    'title': '8日目', 'roster': ROSTER_REL, 'day': DAY, 'fps': 24, 'duration': DUR, 'hour': 10,
    'baseTime': '2026-11-24T09:00:00+09:00', 'base': {'name': '中央の広場', 'x': 0, 'z': 5, 'decidedDay': 2},
    'forestRoad': {'points': [[-74, -22], [-128, -34]], 'need': 300, 'startDay': 4, 'label': '光の場所', 'open': True},
    'toolAge': 'stone', 'clearings': [{'x0': -132, 'x1': -86, 'z0': -62, 'z1': 22, 'day': 6}], 'buildings': EXIST,
    'cast': list(dict.fromkeys(sleepers + builders + audience + cast_on + TOPI + followers + [x for x in [SAKA, ZAF] if inr(x)])),
    'groups': groups, 'acts': acts, 'props': props, 'props3d': props3d, 'camera': camera,
    'overlay': overlay, 'override': {}, 'cutaway': {'radius': 1.6},
    'audio': {'narration': narr, 'bgm': {'volume': 0.18}, 'speed': 1.15},
    'cover': {'at': 2.0, 'day': f'{DAY}日目', 'lines': [f'{n_arrive}人が', '流れ着いた！']},
}
json.dump(story, open(os.path.join(HERE, 'story', 'ep8.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

today = []
def td(i, spot, anim, text, tool=None):
    if inr(i): today.append({'id': i, 'spot': spot, 'anim': anim, 'text': text, **({'tool': tool} if tool else {})})
td(ZAF, 'forestEdge', 'cheer', 'クマの背中に乗って高原へ。クマの家族に会えて、うれしそう')
td(SAKA, 'plaza', 'cheer', '自分の「娯楽が欲しい」から生まれたステージを、満足そうに眺めている')
pwa = {'day': DAY, 'roster': ROSTER_REL, 'today': today, 'missing': {}}
json.dump(pwa, open(os.path.join(HERE, 'story', 'ep8_pwa.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
state = {
    'day': DAY,
    'likes': {'total': LIKES},
    'chronicle_add': {'day': DAY, 'title': 'ステージができ、高原へ',
                      'text': f'{n_arrive}人が流れ着き、島民は{n_all}人に。さかさんの「娯楽が欲しい」から、広場のそばにステージができた（こけら落としはAK24さんの料理ショー）。クマを先頭に高原へ登り、奥でクマの家族に出会った。',
                      'vote': {'question': '次は島のどこを調べる？', 'adopted': OPTS[winner], 'note': '　'.join(f'{k} {tally[k]}件' for k in OPTS)}},
    'currentVote': {'id': 'vote-008-free', 'status': 'open', 'question': 'この島で、何をする？',
                    'description': 'なんでもOK。コメントで教えてね。いいねが集まった案ほど、形になりやすい。一緒にやりたい人は @ で誘ってね',
                    'options': []},
}
json.dump(state, open(os.path.join(HERE, 'story', 'ep8_state.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(json.dumps({'arrivals': n_arrive, 'all': n_all, 'likes': LIKES, 'tally': tally, 'winner': winner, 'top': [(r['name'], r['likes']) for r in TOPROWS], 'cast': len(story['cast'])}, ensure_ascii=False))
