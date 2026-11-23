#!/usr/bin/env python3
"""7日目の台本（約60秒）。第1幕の締め → 第2幕「島を知る」の入口。
  python3 video-tools/ep7/build_story.py
入力：ep7/input/comments.json（6日目の投稿のコメント。post.likesTotal＝全投稿のいいね合計）・ep7/input/islanders.json
流れ（2026-11-23 本人と確定。大筋：昔の住人の謎を背骨に、最後は1,000人で島ライブ）
  漂着 → リンク（フォローといいねで）→ 前回のクマ → いいねバー → 集計（C 食べ物を分けて仲良く）→ ざーふさん＋仲良し
  → ごちそうでクマと仲良く → クマの家（Rinoさんの案）→ 夜、クマが森の奥へ「ついて来い」→ 次の問い「次は島のどこを調べる？」
"""
import json, os, re, math
HERE = os.path.dirname(os.path.abspath(__file__))
os.makedirs(os.path.join(HERE, 'story'), exist_ok=True)
C = json.load(open(os.environ.get('COMMENTS') or os.path.join(HERE, 'input', 'comments.json'), encoding='utf-8'))
ROSTER_PATH = os.path.abspath(os.environ.get('ROSTER') or os.path.join(HERE, 'input', 'islanders.json'))
ROSTER_REL = os.path.relpath(ROSTER_PATH, os.path.join(HERE, 'story'))
R = json.load(open(ROSTER_PATH, encoding='utf-8'))
ROSTER = {p['id']: p for p in R['islanders']}
PREV = {p['id']: p for p in json.load(open(os.path.join(HERE, '..', 'ep6', 'input', 'islanders.json'), encoding='utf-8'))['islanders']}
DAY = 7
inr = lambda i: bool(i) and i in ROSTER
LIKES = int(C['post'].get('likesTotal') or 0)
GOALS = [{'at': 600, 'label': '畑が一晩で実る'}, {'at': 750, 'label': '灯台が建つ'}, {'at': 1000, 'label': 'もこもこのひつじが流れ着く'}]
NEXT = next((g for g in GOALS if LIKES < g['at']), None)

OPTS = {'A': '松明の火で追い払う', 'B': '柵と落とし穴で畑を守る', 'C': '食べ物を分けて、仲良くなる', 'D': '自由に提案'}
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

# 新しい仲良し（6日目の名簿に無い関係）
edges = set()
for p in R['islanders']:
    for r in p.get('relationships') or []:
        if r.get('type') != 'friend' or not inr(r.get('id')): continue
        a, b = sorted([p['id'], r['id']])
        if b not in {x.get('id') for x in (PREV.get(a, {}).get('relationships') or [])}: edges.add((a, b))
pairs = sorted(edges)[:2]

ZAF, YURI, RINO, KUBO, IBU, TSUKI, ABC = 'guernica.0712', 'yuridazo68', 'rino._.15', 'kubotto0505', 'ibu131313', 'tsuki5747', 'abc.man13'
arrivals = [p['id'] for p in R['islanders'] if int(p.get('joinedDay', 0)) == DAY]
n_arrive = len(arrivals)
ZAF = 'guernica.0712'
ZF = sorted({r['id'] for r in (ROSTER.get(ZAF, {}).get('relationships') or []) if r.get('type') == 'friend' and inr(r.get('id'))})  # ざーふさんの仲良し全員
pairs = [e for e in pairs if ZAF not in e]
special = {x for e in pairs for x in e} | {ZAF, YURI, RINO, KUBO, IBU, TSUKI, ABC} | set(ZF)
older = [p for p in R['islanders'] if int(p.get('joinedDay', 0)) < DAY and p['id'] not in special]
cooks = [x for x in [YURI, TSUKI, ABC] if inr(x)] + [p['id'] for p in older if p.get('job') == '料理人'][:3]
watchers = [p['id'] for p in older if p['id'] not in cooks][:34]
builders = [p['id'] for p in older if p.get('job') == '大工' and p['id'] not in watchers][:5]
crowd = watchers[:18]

LAND = [236.0, 124.0]
FIELD = [-110.0, -51.0]
FOOD = [-86.0, -60.0]          # ごちそうを置く所（畑の東、森のふち）
DEN = [-100.0, -74.0]          # クマが出てくる森
WATCH = [-74.0, -46.0]         # みんなが見守る所
HOUSE = [-88.0, -36.0]         # クマの家（畑のそば）
HIGH = [-60.0, -100.0]         # クマが歩いていく先（高原へ続く獣道の方）

groups = [
    {'name': 'beach', 'type': 'ring', 'spot': LAND, 'radius': 3.2, 'gap': 2.6, 'members': arrivals[:22]},
    {'name': 'zaf', 'type': 'line', 'spot': [15, 36], 'face': [0, 1], 'gap': 2.0, 'members': [x for x in [ZAF] if inr(x)] + ZF},
    *[{'name': f'pair{k}', 'type': 'line', 'spot': [5 + k * 6, 46], 'face': [0, 1], 'gap': 1.8, 'members': list(e)} for k, e in enumerate(pairs)],
    {'name': 'pairs', 'type': 'line', 'spot': [8, 46], 'face': [0, 1], 'members': []},
    {'name': 'plaza', 'type': 'ring', 'spot': [0, 15], 'radius': 7, 'gap': 2.8, 'members': crowd},
    {'name': 'watch', 'type': 'ring', 'spot': WATCH, 'radius': 6, 'gap': 2.0, 'members': watchers},
    {'name': 'cooks', 'type': 'line', 'spot': [FOOD[0] + 5, FOOD[1] + 6], 'face': [-0.6, -0.8], 'gap': 2.0, 'members': cooks},
    {'name': 'build', 'type': 'line', 'spot': [HOUSE[0], HOUSE[1] + 7], 'face': [0, -1], 'gap': 2.6, 'members': builders + [x for x in [RINO] if inr(x)]},
    {'name': 'south', 'type': 'line', 'spot': WATCH, 'face': [0, 1], 'members': []},
]
G = {g['name']: g for g in groups}
acts = [{'who': '*', 't': 0, 'anim': 'idle', 'face': 'front'}]
A = acts.append
# S0 漂着（浜いっぱい）
BEACH = json.load(open(os.path.join(HERE, 'beach_spots.json')))
sleepers = arrivals[:len(BEACH)]
for k, i in enumerate(sleepers[len(G['beach']['members']):]):
    A({'who': i, 't': 0, 'at': BEACH[len(G['beach']['members']) + k], 'anim': 'sleep', 'face': 'front', 'hide': False})
    A({'who': i, 't': 1.6 + (k % 9) * 0.1, 'anim': 'sit' if k % 3 == 0 else 'sleep'})
    A({'who': i, 't': 3.0, 'hide': True})
A({'who': G['beach']['members'], 't': 0, 'at': {'slot': 'beach'}, 'anim': 'sleep'})
A({'who': G['beach']['members'], 't': 1.4, 'anim': 'sit', 'pick': 0.35, 'seed': 6})
A({'who': G['beach']['members'], 't': 2.3, 'anim': 'cheer', 'pick': 0.25, 'seed': 2})
# S2 前回のクマ（5.5〜9）：たき火のあとで立ち上がる
A({'who': watchers[:12], 't': 5.5, 'at': {'slot': 'watch'}, 'anim': 'shock', 'face': {'at': DEN}})
# S5 ざーふさん＋仲良し（15〜19）
if inr(ZAF): A({'who': ZAF, 't': 15.0, 'at': [15, 36], 'anim': 'cheer', 'face': 'front'})
for k, f in enumerate(ZF):
    a = math.pi * (0.1 + 0.8 * k / max(1, len(ZF) - 1))
    A({'who': f, 't': 15.0, 'at': [15 + 3.4 * math.cos(a), 36 - 3.4 * math.sin(a) + 0.6], 'to': [15 + 2.4 * math.cos(a), 36 - 2.4 * math.sin(a) + 0.6], 'dur': 0.7, 'run': True})
    A({'who': f, 't': 15.8 + k * 0.12, 'anim': 'cheer', 'face': 'front'})
for k, e in enumerate(pairs): A({'who': list(e), 't': 17.2, 'at': {'slot': f'pair{k}'}, 'anim': 'cheer', 'face': 'front'})
A({'who': crowd, 't': 12.0, 'at': {'slot': 'plaza'}, 'anim': 'idle', 'face': {'at': [0, 15]}})
# S6 ごちそう（19〜34）
A({'who': cooks, 't': 19.0, 'at': {'slot': 'cooks'}, 'anim': 'work', 'face': {'at': FOOD}})
for k, i in enumerate(cooks):
    A({'who': i, 't': 21.6 + k * 0.1, 'to': [WATCH[0] - 4 + k * 1.6, WATCH[1] - 7.5], 'dur': 1.4, 'run': True})
    A({'who': i, 't': 23.2, 'anim': 'idle', 'face': {'at': FOOD}})
A({'who': watchers, 't': 19.0, 'at': {'slot': 'watch'}, 'anim': 'idle', 'face': {'at': FOOD}})
A({'who': watchers + cooks, 't': 24.2, 'anim': 'shock', 'face': {'at': FOOD}, 'pick': 0.5, 'seed': 3})
A({'who': watchers + cooks, 't': 28.4, 'anim': 'cheer', 'pick': 0.6, 'seed': 7})
if inr(ZAF):
    A({'who': ZAF, 't': 19.0, 'at': [WATCH[0] - 6, WATCH[1] - 6], 'anim': 'idle', 'face': {'at': FOOD}})
    A({'who': ZAF, 't': 28.6, 'to': [FOOD[0] + 4.2, FOOD[1] + 3.2], 'dur': 1.8})
    A({'who': ZAF, 't': 30.6, 'anim': 'cheer', 'face': {'at': FOOD}})
    # 金太郎みたいに、クマの背中に乗る（31.4〜34.6）
    A({'who': ZAF, 't': 31.4, 'ride': True, 'anim': 'sit'})
    A({'who': ZAF, 't': 32.4, 'anim': 'cheer'})
    A({'who': ZAF, 't': 34.6, 'ride': False, 'at': [HOUSE[0] + 4, HOUSE[1] + 5], 'anim': 'cheer', 'face': 'front'})
# 仲良したちがクマのまわりを走ってついていく
for k, f in enumerate(ZF):
    A({'who': f, 't': 31.4, 'at': [WATCH[0] - 3 + k * 1.8, WATCH[1] - 7], 'anim': 'cheer', 'face': {'at': FOOD}, 'hide': False})
    A({'who': f, 't': 32.0 + k * 0.1, 'to': [WATCH[0] - 1 + k * 1.6, WATCH[1] - 1.5 + (k % 2)], 'dur': 2.2, 'run': True})
    A({'who': f, 't': 34.4, 'anim': 'cheer', 'face': {'at': [WATCH[0] - 2, WATCH[1] - 5]}})
# S7 クマの家（34〜40）
A({'who': G['build']['members'], 't': 34.0, 'at': {'slot': 'build'}, 'anim': 'work', 'face': {'at': HOUSE}})
A({'who': G['build']['members'], 't': 38.4, 'anim': 'cheer', 'face': 'front'})
# S8 夜、クマが森の奥へ（40〜47）
A({'who': watchers[:16], 't': 40.0, 'at': {'slot': 'watch'}, 'anim': 'idle', 'face': {'at': HIGH}})
if inr(ZAF): A({'who': ZAF, 't': 40.0, 'at': [HOUSE[0] + 4, HOUSE[1] - 6], 'anim': 'idle', 'face': {'at': HIGH}})

# クマの道すじ
BWAY = [(0, DEN), (5.4, [WATCH[0] - 6, WATCH[1] - 10]), (9.0, [WATCH[0] - 6, WATCH[1] - 10]),
        (22.8, DEN), (24.0, DEN), (26.6, [FOOD[0] - 1.5, FOOD[1] - 2.5]), (28.6, [FOOD[0] - 1.5, FOOD[1] - 2.5]),
        (30.2, [FOOD[0] + 1.6, FOOD[1] + 0.6]), (31.6, [FOOD[0] + 1.6, FOOD[1] + 0.6]), (34.4, [WATCH[0] - 2, WATCH[1] - 5]),
        (35.0, [HOUSE[0] - 4, HOUSE[1] - 3]), (40.0, [HOUSE[0] - 4, HOUSE[1] - 3]),
        (41.6, [HOUSE[0] + 2, HOUSE[1] - 12]), (42.6, [HOUSE[0] + 2, HOUSE[1] - 12]), (44.2, [HOUSE[0] + 8, HOUSE[1] - 22]), (47.0, [HOUSE[0] + 8, HOUSE[1] - 22])]
def bear_at(t):
    if t <= BWAY[0][0]: return list(BWAY[0][1])
    for (ta, pa), (tb, pb) in zip(BWAY, BWAY[1:]):
        if t <= tb:
            u = (t - ta) / max(0.01, tb - ta); u = u * u * (3 - 2 * u)
            return [pa[0] + (pb[0] - pa[0]) * u, pa[1] + (pb[1] - pa[1]) * u]
    return list(BWAY[-1][1])
BPATH = []
t = 0.0
while t <= 47.0001:
    p = bear_at(t); BPATH.append([round(t, 2), round(p[0], 2), round(p[1], 2)]); t = round(t + 0.1, 2)
# 前回を思い出す場面（5.5〜9）は、クマが立ち上がる
def heading(t):
    a, b = bear_at(t - 0.2), bear_at(t)
    return math.atan2(b[0] - a[0], b[1] - a[1]) if (a != b) else 0.0

DUR = 60.0
camera = [
    {'from': 0, 'to': 3.0, 'hour': 7.5, 'keys': [{'t': 0, 'look': {'rel': 'g:beach'}, 'dist': 70, 'az': 0.4, 'pol': 0.35, 'up': 1.5, 'frame': 'beach'}, {'t': 1.6, 'look': {'rel': 'g:beach'}, 'dist': 34, 'az': 1.0, 'pol': 0.9, 'up': 1.5, 'frame': 'beach'}, {'t': 3.0, 'look': {'rel': 'g:beach'}, 'dist': 24, 'az': 1.35, 'pol': 1.15, 'up': 1.5, 'frame': 'beach'}]},
    {'from': 3.0, 'to': 5.5, 'hour': 11, 'keys': [{'t': 3.0, 'look': [15, 40], 'dist': 900, 'az': 0.2, 'pol': 0.7, 'up': 0, 'frame': 'beach'}, {'t': 5.5, 'look': [15, 40], 'dist': 640, 'az': 0.9, 'pol': 0.85, 'up': 0, 'frame': 'beach'}]},
    {'from': 5.5, 'to': 9.0, 'hour': 19.3, 'shake': [[6.4, 7.6, 1.0]], 'keys': [{'t': 5.5, 'look': bear_at(5.5), 'dist': 22, 'az': 0.2, 'pol': 1.2, 'up': 3, 'frame': 'south', 'fov': 44}, {'t': 9.0, 'look': bear_at(9.0), 'dist': 13, 'az': 0.0, 'pol': 1.32, 'up': 4, 'frame': 'south', 'fov': 32}]},
    {'from': 9.0, 'to': 12.0, 'hour': 12, 'keys': [{'t': 9.0, 'look': FIELD, 'dist': 60, 'az': 0.3, 'pol': 0.8, 'up': 0, 'frame': 'south'}, {'t': 12.0, 'look': FIELD, 'dist': 48, 'az': 0.8, 'pol': 0.85, 'up': 0, 'frame': 'south'}]},
    {'from': 12.0, 'to': 15.0, 'hour': 13, 'keys': [{'t': 12.0, 'look': [0, 15], 'dist': 60, 'az': 0.0, 'pol': 0.8, 'up': 0, 'frame': 'zaf'}, {'t': 15.0, 'look': [0, 15], 'dist': 80, 'az': 1.0, 'pol': 0.95, 'up': 0, 'frame': 'zaf'}]},
    {'from': 15.0, 'to': 17.2, 'hour': 13.5, 'keys': [{'t': 15.0, 'look': [15, 35.5], 'dist': 22, 'az': -1.3, 'pol': 0.45, 'up': 1.5, 'frame': 'zaf', 'fov': 50}, {'t': 16.2, 'look': [15, 35.5], 'dist': 15, 'az': -0.4, 'pol': 1.0, 'up': 2.0, 'frame': 'zaf', 'fov': 44}, {'t': 17.2, 'look': [15, 35.5], 'dist': 12, 'az': 0.3, 'pol': 1.28, 'up': 2.2, 'frame': 'zaf', 'fov': 40}]},
    {'from': 17.2, 'to': 19.0, 'hour': 13.5, 'keys': [{'t': 17.2, 'look': {'rel': 'g:pairs'}, 'dist': 26, 'az': 0.8, 'pol': 1.15, 'up': 2, 'frame': 'pairs'}, {'t': 19.0, 'look': {'rel': 'g:pairs'}, 'dist': 20, 'az': 0.0, 'pol': 1.25, 'up': 2, 'frame': 'pairs'}]},
    # ごちそう：置く → みんなで見守る（後ろ姿ごしに森）
    {'from': 19.0, 'to': 23.4, 'hour': 17.0, 'keys': [{'t': 19.0, 'look': FOOD, 'dist': 9, 'az': 1.6, 'pol': 1.35, 'up': 1.5, 'frame': 'south', 'fov': 46}, {'t': 21.0, 'look': FOOD, 'dist': 16, 'az': 0.8, 'pol': 1.0, 'up': 2, 'frame': 'south', 'fov': 42}, {'t': 23.4, 'look': [FOOD[0] + 4, FOOD[1] + 6], 'dist': 34, 'az': -0.2, 'pol': 0.8, 'up': 2, 'frame': 'south', 'fov': 42}]},
    {'from': 23.4, 'to': 28.6, 'hour': 17.3, 'keys': [{'t': 23.4, 'look': [FOOD[0], FOOD[1] - 4], 'dist': 30, 'az': 0.25, 'pol': 1.28, 'up': 2.5, 'frame': 'south', 'fov': 40}, {'t': 26.6, 'look': FOOD, 'dist': 18, 'az': 0.1, 'pol': 1.3, 'up': 2.5, 'frame': 'south', 'fov': 34}, {'t': 28.6, 'look': FOOD, 'dist': 11, 'az': 0.5, 'pol': 1.25, 'up': 3, 'frame': 'south', 'fov': 30}]},
    {'from': 28.6, 'to': 31.4, 'hour': 17.5, 'keys': [{'t': 28.6, 'look': [FOOD[0] + 2, FOOD[1] + 1.5], 'dist': 16, 'az': 1.4, 'pol': 1.2, 'up': 2.5, 'frame': 'south', 'fov': 40}, {'t': 30.0, 'look': [FOOD[0] + 2, FOOD[1] + 1.5], 'dist': 10, 'az': 0.6, 'pol': 1.3, 'up': 2.5, 'frame': 'south', 'fov': 34}, {'t': 31.4, 'look': [FOOD[0] + 2, FOOD[1] + 1.5], 'dist': 12, 'az': -0.2, 'pol': 1.25, 'up': 3.5, 'frame': 'south', 'fov': 36}]},
    # 金太郎：クマの横を一緒に走るように、ぐるっと回りこむ
    {'from': 31.4, 'to': 34.6, 'hour': 17.6, 'keys': [{'t': 31.4, 'look': bear_at(31.4), 'dist': 13, 'az': -0.6, 'pol': 1.2, 'up': 4.5, 'frame': 'south', 'fov': 40}, {'t': 32.8, 'look': bear_at(32.8), 'dist': 11, 'az': 0.6, 'pol': 1.3, 'up': 4.5, 'frame': 'south', 'fov': 38}, {'t': 34.6, 'look': bear_at(34.4), 'dist': 20, 'az': 1.6, 'pol': 1.05, 'up': 3.5, 'frame': 'south', 'fov': 42}]},
    {'from': 34.6, 'to': 40.0, 'hour': 11, 'keys': [{'t': 34.6, 'look': HOUSE, 'dist': 26, 'az': -0.6, 'pol': 1.1, 'up': 2, 'frame': 'south'}, {'t': 38.4, 'look': HOUSE, 'dist': 18, 'az': 0.4, 'pol': 1.15, 'up': 2.5, 'frame': 'south'}, {'t': 40.0, 'look': HOUSE, 'dist': 22, 'az': 0.8, 'pol': 1.1, 'up': 2.5, 'frame': 'south'}]},
    # 夜：クマが森の奥へ歩いては振り返る
    {'from': 40.0, 'to': 47.0, 'hour': 20.3, 'keys': [{'t': 40.0, 'look': bear_at(40.0), 'dist': 16, 'az': 0.3, 'pol': 1.3, 'up': 2.5, 'frame': 'south', 'fov': 40}, {'t': 42.6, 'look': bear_at(42.6), 'dist': 14, 'az': 0.0, 'pol': 1.3, 'up': 2.5, 'frame': 'south', 'fov': 36}, {'t': 47.0, 'look': bear_at(47.0), 'dist': 46, 'az': -0.3, 'pol': 0.8, 'up': 1, 'frame': 'south', 'fov': 40}]},
    {'from': 47.0, 'to': 57.0, 'hour': 20.0, 'keys': [{'t': 47.0, 'look': [HOUSE[0], HOUSE[1] - 20], 'dist': 60, 'az': -0.4, 'pol': 0.8, 'up': 0, 'frame': 'south'}, {'t': 57.0, 'look': [HOUSE[0], HOUSE[1] - 20], 'dist': 80, 'az': 0.4, 'pol': 0.75, 'up': 0, 'frame': 'south'}]},
    {'from': 57.0, 'to': DUR, 'hour': 18.5, 'keys': [{'t': 57.0, 'look': [15, 40], 'dist': 700, 'az': 0.8, 'pol': 0.85, 'up': 0, 'frame': 'beach'}, {'t': DUR, 'look': [15, 40], 'dist': 780, 'az': 1.0, 'pol': 0.85, 'up': 0, 'frame': 'beach'}]},
]

props = [{'type': 'zzz', 'from': {'rel': i, 'up': 1.6}, 't0': 0, 't1': 0.01, 't2': 2.2, 'size': 0.9, 'phase': k * 0.3} for k, i in enumerate(G['beach']['members'][:6])]
for k, f in enumerate(ZF):
    props.append({'type': 'heart', 'from': {'rel': f, 'up': 3.4}, 'to': {'rel': f, 'up': 3.4}, 't0': 15.9 + k * 0.15, 't1': 17.1, 't2': 17.1, 'size': 1.3, 'phase': k})
for k, e in enumerate(pairs):
    props.append({'type': 'heart', 'from': {'rel': e[0], 'up': 3.4, 't': 0.9}, 'to': {'rel': e[0], 'up': 3.4, 't': 0.9}, 't0': 17.4, 't1': 19.0, 't2': 19.0, 'size': 1.4, 'phase': k})
# ごちそう（魚と木の実）
for k in range(7):
    a = k * 0.9
    props.append({'type': 'fish' if k % 2 else 'fruit', 'from': {'xz': [FOOD[0] + 4.5, FOOD[1] + 5], 'up': 2}, 'to': [round(FOOD[0] + math.cos(a) * 1.2, 2), round(FOOD[1] + math.sin(a) * 0.9, 2)], 't0': 19.6 + k * 0.25, 't1': 20.4 + k * 0.25, 't2': 29.0, 'arc': 2.5, 'size': 0.9})
props.append({'type': 'heart', 'from': {'xz': [FOOD[0] + 2.2, FOOD[1] + 1.2], 'up': 5.5}, 'to': {'xz': [FOOD[0] + 2.2, FOOD[1] + 1.2], 'up': 7.0}, 't0': 30.6, 't1': 31.4, 't2': 31.4, 'size': 2.2})
props.append({'type': 'question', 'from': {'xz': bear_at(44.2), 'up': 0}, 't0': 44.4, 't1': 44.41, 't2': 47.0, 'size': 3})

props3d = [
    {'type': 'beast', 'at': DEN, 'path': BPATH, 'show': 5.4, 'hide': 47.0, 't0': 0, 't1': 47.0, 'rear': [[6.2, 7.8]]},
    {'type': 'build', 'kind': 'bearhouse', 'at': HOUSE, 'rot': 0, 't0': 34.4, 't1': 38.2, 'show': 34.0},
]

def star(i, a, b, text):
    return {'who': i, 'from': a, 'to': b, 'bubble': text} if inr(i) else None
stars = [x for x in [star(ZAF, 15.2, 17.1, '俺らで熊を手懐けよう🐻金太郎みたいに'), star(RINO, 34.8, 37.2, 'クマ専用エリアを作ったらいいかも！')] if x]
ROWS = [{'key': k, 'label': OPTS[k], 'count': tally[k]} for k in OPTS]
LB = {'total': LIKES, 'max': 1000, 'goals': GOALS}
overlay = {
    'banner': 'コメントで動く無人島　7日目',
    'bannerOff': [[0, 5.5], [9.0, 12.0], [47.0, DUR]],
    'commenters': commenters,
    'names': {**{i: name_of(i) for i in people}, **{x: name_of(x) for e in pairs for x in e}},
    'titles': [{'text': '7日目', 'from': 0.1, 'to': 3.0}],
    'tagAll': [[0.3, 3.0, 0.08]],
    'tagOnly': [{'from': 15.8, 'to': 17.1, 'who': ZF, 'below': True, 'size': 32}] + [{'from': 17.4, 'to': 19.0, 'who': list(e), 'join': True, 'size': 36} for e in pairs],
    'stars': stars,
    'tally': {'from': 12.0, 'to': 15.0, 'title': '昨日の質問　クマをどうする？', 'grow': [12.3, 13.5], 'winner': winner, 'winnerAt': 13.8, 'rows': ROWS},
    'likebars': [{**LB, 'from': 9.0, 'to': 12.0, 'from0': max(0, LIKES - 120), 'y': 640}, {**LB, 'from': 57.1, 'to': DUR, 'from0': LIKES, 'y': 380}],
    'images': [
        {'file': 'profile.png', 'from': 3.0, 'to': 4.3, 'w': 900, 'y': 600, 'tap': [0.24, 0.905], 'tapLabel': 'フォロー＆いいねで…'},
        {'file': 'profile.png', 'from': 4.3, 'to': 5.5, 'w': 900, 'y': 600, 'tap': [0.37, 0.78], 'tapLabel': '島のいまは、ここ'},
        {'file': 'profile.png', 'from': 57.1, 'to': DUR, 'w': 900, 'y': 980, 'tap': [0.37, 0.78], 'tapLabel': 'ここから'},
    ],
    'captions': [
        {'text': f'フォローした{n_arrive}人が、流れ着いた', 'from': 0.4, 'to': 3.0, 'y': 1290, 'size': 66},
        {'text': 'あなたも、次の動画で流れ着きます', 'from': 3.1, 'to': 4.3, 'y': 1400, 'size': 50, 'color': [255, 214, 74]},
        {'text': '前回、クマが現れた…！', 'from': 5.6, 'to': 9.0, 'y': 360, 'size': 60, 'color': [255, 120, 90]},
        *([{'text': f'あと{NEXT["at"] - LIKES}で、{NEXT["label"]}！', 'from': 9.6, 'to': 12.0, 'y': 1000, 'size': 58, 'color': [255, 214, 74]}] if NEXT else []),
        {'text': 'いいねは全部の投稿で数えます', 'from': 10.2, 'to': 12.0, 'y': 1090, 'size': 40},
        {'text': '食べ物を分けて、仲良くなる作戦', 'from': 19.1, 'to': 23.2, 'y': 360, 'size': 54, 'color': [255, 214, 74]},
        {'text': 'みんな、息をひそめて…', 'from': 23.4, 'to': 26.4, 'y': 360, 'size': 58},
        {'text': '食べた！', 'from': 28.6, 'to': 30.4, 'y': 360, 'size': 84, 'color': [255, 214, 74]},
        {'text': 'クマと、仲良くなった！', 'from': 30.6, 'to': 31.4, 'y': 360, 'size': 66, 'color': [255, 214, 74]},
        {'text': '金太郎みたいに、背中に乗った！', 'from': 31.5, 'to': 34.5, 'y': 360, 'size': 58, 'color': [255, 214, 74]},
        *([{'text': f'ざーふさん、仲良しが{len(ZF)}人に！', 'from': 15.6, 'to': 17.1, 'y': 420, 'size': 54}] if ZF else []),
        {'text': 'クマの家が、できた！', 'from': 38.4, 'to': 40.0, 'y': 360, 'size': 62, 'color': [255, 214, 74]},
        *([{'text': 'kubottoさん「住処を奪ったこちらにも非がある」', 'from': 36.0, 'to': 38.3, 'y': 1290, 'size': 38}] if inr(KUBO) else []),
        {'text': 'その夜、クマが森の奥へ…', 'from': 40.1, 'to': 42.6, 'y': 360, 'size': 56},
        {'text': '「ついて来い」って、言ってる？', 'from': 42.7, 'to': 47.0, 'y': 360, 'size': 56, 'color': [255, 214, 74]},
        {'text': '次の質問', 'from': 47.1, 'to': 57.0, 'y': 330, 'size': 64, 'color': [255, 214, 74]},
        {'text': 'クマと仲良くなった。', 'from': 47.2, 'to': 57.0, 'y': 450, 'size': 60},
        {'text': '次は島のどこを調べる？', 'from': 47.2, 'to': 57.0, 'y': 545, 'size': 60},
        {'text': 'A 高原（クマが道を知っている）', 'from': 48.0, 'to': 57.0, 'y': 760, 'size': 48},
        {'text': 'B 昔の住人の跡を、もっと掘る', 'from': 48.6, 'to': 57.0, 'y': 860, 'size': 48},
        {'text': 'C 浜の先の岬（木箱が来た方角）', 'from': 49.2, 'to': 57.0, 'y': 960, 'size': 48},
        {'text': 'D 自由に提案', 'from': 49.8, 'to': 57.0, 'y': 1060, 'size': 48},
        {'text': 'A・B・C・Dでコメントしてね', 'from': 50.6, 'to': 57.0, 'y': 1300, 'size': 50, 'color': [255, 214, 74]},
        {'text': 'いいねは全部の投稿で数えます', 'from': 57.2, 'to': DUR, 'y': 720, 'size': 42},
    ],
    'smallTagsMax': 5,
}
narr = [
    {'at': 0.3, 'until': 3.0, 'text': f'{n_arrive}人が、流れ着いた！'},
    {'at': 3.1, 'until': 4.3, 'text': 'フォローといいねで、あなたも。'},
    {'at': 4.4, 'until': 5.5, 'text': '島は、リンクから。'},
    {'at': 5.6, 'until': 9.0, 'text': '前回、クマが現れた！'},
    {'at': 9.1, 'until': 12.0, 'text': f'島のいいね、あと{NEXT["at"] - LIKES}で、{NEXT["label"]}！' if NEXT else 'いいね、ありがとう！'},
    {'at': 12.1, 'until': 15.0, 'text': '昨日の一番人気は、食べ物を分けて、仲良くなる！'},
    {'at': 15.1, 'until': 19.0, 'text': '俺らで熊を手懐けよう！'},
    {'at': 19.1, 'until': 23.2, 'text': '魚と木の実の、ごちそうを置いて。'},
    {'at': 23.4, 'until': 26.4, 'text': 'みんなで、そっと見守る…'},
    {'at': 28.6, 'until': 30.4, 'text': '食べた！'},
    {'at': 30.6, 'until': 31.4, 'text': '仲良くなった！'},
    {'at': 31.5, 'until': 34.5, 'text': '金太郎みたいに、背中に乗った！'},
    {'at': 34.1, 'until': 38.3, 'text': 'クマの家も、作ったよ。'},
    {'at': 40.1, 'until': 42.6, 'text': 'その夜、クマが森の奥へ。'},
    {'at': 42.7, 'until': 47.0, 'text': 'ついて来い、って言ってる？'},
    {'at': 47.2, 'until': 57.0, 'text': '次は島のどこを調べる？エー、ビー、シー、ディーでコメントしてね。'},
    {'at': 57.2, 'until': DUR, 'text': 'いいねで、島が変わるよ。'},
]
EXIST = [
    {'id': 'ruins-1', 'type': 'ruins', 'name': '昔の住人の跡', 'x': -44.7, 'z': -12.7, 'rot': 0, 'builtDay': 1},
    {'id': 'hut-1', 'type': 'hut', 'name': 'はじまりの小屋', 'x': -20, 'z': -5, 'rot': 20, 'builtDay': 4},
    {'id': 'workshop-1', 'type': 'workshop', 'name': '石の作業場', 'x': -40.3, 'z': -9.0, 'rot': 10, 'builtDay': 5},
    {'id': 'bigfield-1', 'type': 'bigfield', 'name': '巨大な畑', 'x': round(FIELD[0] / 3, 2), 'z': round(FIELD[1] / 3, 2), 'rot': 0, 'builtDay': 6},
]
story = {
    'title': '7日目', 'roster': ROSTER_REL, 'day': DAY, 'fps': 24, 'duration': DUR, 'hour': 10,
    'baseTime': '2026-11-23T09:00:00+09:00', 'base': {'name': '中央の広場', 'x': 0, 'z': 5, 'decidedDay': 2},
    'forestRoad': {'points': [[-74, -22], [-128, -34]], 'need': 300, 'startDay': 4, 'label': '光の場所', 'open': True},
    'toolAge': 'stone', 'clearings': [{'x0': -132, 'x1': -86, 'z0': -62, 'z1': 22, 'day': 6}], 'buildings': EXIST,
    'cast': list(dict.fromkeys(list(commenters) + [x for e in pairs for x in e] + crowd + watchers + cooks + builders + sleepers + [x for x in [ZAF, YURI, RINO] if inr(x)])),
    'groups': groups, 'acts': acts, 'props': props, 'props3d': props3d, 'camera': camera,
    'overlay': overlay, 'override': {}, 'cutaway': {'radius': 1.6},
    'audio': {'narration': narr, 'bgm': {'volume': 0.18}, 'speed': 1.15},
    'cover': {'at': 31.5, 'day': f'{DAY}日目', 'lines': ['クマと、', '仲良くなった！']},
}
json.dump(story, open(os.path.join(HERE, 'story', 'ep7.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

today = []
def td(i, spot, anim, text, tool=None):
    if inr(i): today.append({'id': i, 'spot': spot, 'anim': anim, 'text': text, **({'tool': tool} if tool else {})})
td(ZAF, 'forestEdge', 'cheer', 'クマと仲良くなった。クマの家のそばで、一緒に過ごしている')
td(YURI, 'forestEdge', 'work', 'クマのために、魚と木の実のごちそうを作っている', 'ladle')
td(RINO, 'cove', 'work', '副漁労長として、ibu13さんと漁をしている', 'rod')
td(IBU, 'cove', 'work', '漁労長として、Rinoさんと漁をしている', 'rod')
pwa = {'day': DAY, 'roster': ROSTER_REL, 'today': today, 'missing': {}}
json.dump(pwa, open(os.path.join(HERE, 'story', 'ep7_pwa.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
state = {
    'day': DAY,
    'likes': {'total': LIKES},
    'beast': {'day': 6, 'x': HOUSE[0], 'z': HOUSE[1], 'r': 10, 'friendly': True, 'text': 'みんなと仲良くなったクマ。クマの家のまわりで、のんびり過ごしている。ときどき、森の奥をじっと見ている…'},
    'buildings_add': [{'id': 'bearhouse-1', 'type': 'bearhouse', 'name': 'クマの家', 'x': round(HOUSE[0] / 3, 2), 'z': round(HOUSE[1] / 3, 2), 'rot': 0, 'builtDay': DAY, 'note': 'Rinoさんの案。森を切って住処を追われたクマのための家。'}],
    'chronicle_add': {'day': DAY, 'title': 'クマと仲良くなった', 'text': '魚と木の実のごちそうを分けて、クマと仲良くなった。畑のそばにクマの家を建てた。その夜、クマは森の奥へ歩いては振り返った。',
                      'vote': {'question': 'クマが現れた！どうする？', 'adopted': OPTS[winner], 'note': '　'.join(f'{k} {tally[k]}件' for k in OPTS)}},
    'currentVote': {'id': 'vote-007-explore', 'status': 'open', 'question': 'クマと仲良くなった。次は島のどこを調べる？',
                    'description': 'A・B・C・D でコメントしてね。コメントが一番多い案を採用します（Dが一番多いときは、Dの中でいいねが一番多い案）',
                    'options': [{'key': 'A', 'label': '高原（クマが道を知っている）'}, {'key': 'B', 'label': '昔の住人の跡を、もっと掘る'}, {'key': 'C', 'label': '浜の先の岬（木箱が来た方角）'}, {'key': 'D', 'label': '自由に提案'}]},
}
json.dump(state, open(os.path.join(HERE, 'story', 'ep7_state.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(json.dumps({'arrivals': n_arrive, 'likes': LIKES, 'tally': tally, 'winner': winner, 'pairs': [(name_of(a), name_of(b)) for a, b in pairs], 'cast': len(story['cast'])}, ensure_ascii=False))
