#!/usr/bin/env python3
"""9日目の台本（約56秒）。カメラは激しく（標準）。
  python3 video-tools/ep9/build_story.py
入力：ep9/input/comments.json（8日目「この島で、何をする？」の自由コメント。likeCount つき）・ep9/input/islanders.json
流れ
  101人の漂着 → リンク → 島のいいね750達成で灯台が建つ（夕方、灯がともる）→ 次は1000でひつじ
  → 前回いいねが多かったコメント → 採用1：ざーふさんとクマのショー（ステージ）／Rino×sykyu_77 の仲良し
  → 採用2：さくさくぱんだ「自然パーク」→ 高原のクマの家族のまわりから
  → ステージの出し物の予約（コメントから）→ 謎：手記を見つけた人が現れた／「洞窟を見つけました」…？
  → 次の問い「次に作るのは？」A みんなの宿舎／B 自分のお店が並ぶ通り／C スポーツ広場／D 自由
"""
import json, os, re, math, random
HERE = os.path.dirname(os.path.abspath(__file__))
os.makedirs(os.path.join(HERE, 'story'), exist_ok=True)
C = json.load(open(os.environ.get('COMMENTS') or os.path.join(HERE, 'input', 'comments.json'), encoding='utf-8'))
ROSTER_PATH = os.path.abspath(os.environ.get('ROSTER') or os.path.join(HERE, 'input', 'islanders.json'))
ROSTER_REL = os.path.relpath(ROSTER_PATH, os.path.join(HERE, 'story'))
R = json.load(open(ROSTER_PATH, encoding='utf-8'))
ROSTER = {p['id']: p for p in R['islanders']}
DAY = 9
inr = lambda i: bool(i) and i in ROSTER
LIKES = int(C['post'].get('likesTotal') or 0)
GOALS = [{'at': 600, 'label': '畑が一晩で実る'}, {'at': 750, 'label': '灯台が建つ'}, {'at': 1000, 'label': 'もこもこのひつじが流れ着く'}]
NEXT = next((g for g in GOALS if LIKES < g['at']), None)
rnd = random.Random(9)

cm = [c for c in C['comments'] if c.get('userId') and c.get('status') != 'none']
people = {c['userId']: c for c in sorted(cm, key=lambda c: c.get('at') or '')}
def name_of(i):
    n = (people.get(i, {}).get('name') or '').strip() or ROSTER.get(i, {}).get('name') or i
    ok = sum(1 for ch in n if ch.isascii() and ch.isalnum() or '぀' <= ch <= 'ヿ' or '一' <= ch <= '鿿')
    return n if ok >= max(1, len(n) // 2) else i
commenters = {i: '-' for i in people if inr(i)}
top = sorted([c for c in cm if inr(c['userId'])], key=lambda c: (-(c.get('likeCount') or 0), c.get('at') or ''))
seen, TOP = set(), []
for c in top:
    if c['userId'] in seen or not (c.get('likeCount') or 0): continue
    seen.add(c['userId']); TOP.append(c)
TOP = TOP[:3]

ZAF, SAKU, TSUKI, RINO, SYK, YURI, RUNE = 'guernica.0712', 'sakusaku_ss0420', 'tsuki5747', 'rino._.15', 'sykyu_77', 'yuridazo68', 'nn1k2n'
# ステージの出し物の予約（コメントから。PWA では state.stageRequests、今夜の投稿から順に）
REQ = [(TSUKI, 'ギターの弾き語り', 'sing'), ('jinsta129', 'ドームライブ', 'sing'), ('endst520', '歌って踊る', 'dance'), ('moose.85881582', 'ファッションショー', 'dance'),
       ('hokura_masao', 'ギター演奏', 'sing'), ('0112riku', '弾き語り', 'sing'), ('squirrel.39516326', 'イラストの展示', 'talk'), ('ry0t0_nk', '料理ショー', 'cook')]
REQ = [r for r in REQ if inr(r[0])]
ZF = sorted({r['id'] for r in (ROSTER.get(ZAF, {}).get('relationships') or []) if r.get('type') == 'friend' and inr(r.get('id'))})
arrivals = [p['id'] for p in R['islanders'] if int(p.get('joinedDay', 0)) == DAY]
n_arrive, n_all = len(arrivals), len(R['islanders'])
special = {ZAF, SAKU, TSUKI, RINO, SYK, YURI, RUNE} | set(ZF) | {c['userId'] for c in TOP} | {r[0] for r in REQ}
older = [p for p in R['islanders'] if int(p.get('joinedDay', 0)) < DAY and p['id'] not in special]
audience = [p['id'] for p in older][:44]
watchers = [p['id'] for p in older][44:70]
beachfolk = [p['id'] for p in older][70:110]

# ---- 場所（ワールド座標） ----
STAGE = [22.0, 34.0]                  # みんなのステージ（正面は +z）
SEAT = [STAGE[0], STAGE[1] + 8.5]
LIGHT = [256.0, 90.0]                 # 灯台（漂着の浜の先）
BC = [236.0, 124.0]                   # 漂着の浜
FAM = [84.0, -146.0]                  # 高原のクマの家族
KIDS = [[FAM[0] - 3.2, FAM[1] + 1.0], [FAM[0] + 2.6, FAM[1] + 1.8]]
MOM = [76.0, -138.0]
CAVE = [92.0, -156.0]                 # 洞窟（クマの家族の奥。正面は +z）

BEACH = json.load(open(os.path.join(HERE, '..', 'ep7', 'beach_spots.json')))
spots = [list(b) for b in BEACH]
rnd.shuffle(spots)

groups = [
    {'name': 'south', 'type': 'line', 'spot': [0, 0], 'face': [0, 1], 'members': []},
    {'name': 'seat', 'type': 'line', 'spot': [SEAT[0], SEAT[1] + 1.5], 'face': [0, -1], 'gap': 1.7, 'rows': 4, 'members': audience},
    {'name': 'watch', 'type': 'line', 'spot': [MOM[0] - 2, MOM[1] + 12], 'face': [0, -1], 'gap': 1.8, 'rows': 3, 'members': watchers},
    {'name': 'lbeach', 'type': 'ring', 'spot': [LIGHT[0] - 14, LIGHT[1] + 14], 'radius': 6, 'gap': 2.2, 'members': beachfolk},
]
acts = [{'who': '*', 't': 0, 'anim': 'idle', 'face': 'front'}]
A = acts.append

# S0 漂着（0〜4.4）：浜に寝ている → 起きる → 海からも走って上がる
for k, i in enumerate(arrivals[:len(spots)]):
    x, z = spots[k]
    if k % 4 == 0:
        A({'who': i, 't': 0, 'at': [x + 13, z + rnd.uniform(-2, 2)], 'anim': 'idle', 'face': {'at': [x - 20, z]}, 'hide': False})
        A({'who': i, 't': 0.3 + (k % 7) * 0.16, 'to': [x, z], 'dur': 1.5, 'run': True})
        A({'who': i, 't': 2.3, 'anim': 'cheer', 'face': 'front'})
    else:
        A({'who': i, 't': 0, 'at': [x, z], 'anim': 'sleep', 'face': 'front', 'hide': False})
        A({'who': i, 't': 1.1 + (k % 11) * 0.09, 'anim': 'sit' if k % 3 == 0 else 'sleep'})
        A({'who': i, 't': 2.2 + (k % 13) * 0.07, 'anim': 'cheer' if k % 2 else 'idle'})
    A({'who': i, 't': 4.4, 'hide': True})

# S2 灯台（6.4〜13.0）：浜の島民が見上げる
A({'who': beachfolk, 't': 0, 'at': {'slot': 'lbeach'}, 'anim': 'idle', 'face': {'at': LIGHT}})
A({'who': beachfolk, 't': 10.6, 'anim': 'cheer', 'pick': 0.7, 'seed': 2})

# S4 ざーふさんとクマのショー（17.4〜27.0）
T4, T5 = 17.4, 27.0
A({'who': audience, 't': T4, 'anim': 'idle', 'face': {'at': STAGE}})
A({'who': audience, 't': T4 + 3.0, 'anim': 'shock', 'pick': 0.4, 'seed': 5})
A({'who': audience, 't': T4 + 4.6, 'anim': 'cheer', 'pick': 0.8, 'seed': 6})
if inr(ZAF):
    A({'who': ZAF, 't': T4, 'at': {'xz': [STAGE[0] - 2.6, STAGE[1] + 0.8], 'up': 1.1}, 'anim': 'talk', 'face': 'front', 'hide': False})
    A({'who': ZAF, 't': T4 + 2.8, 'anim': 'cheer'})
    A({'who': ZAF, 't': T5, 'hide': True})
PAIR = [x for x in [RINO, SYK] if inr(x)]
for k, i in enumerate(PAIR):
    A({'who': i, 't': T4, 'at': [SEAT[0] + 6.5 + k * 1.8, SEAT[1] - 1.2], 'anim': 'cheer', 'face': {'at': STAGE}, 'hide': False})
    A({'who': i, 't': T5, 'hide': True})

# S5 自然パーク（27.0〜32.6）：高原のクマの家族を、少し離れて見守る
TC, T6 = 32.6, 36.0                   # TC〜T6：洞窟を見つける
A({'who': watchers, 't': 0, 'at': {'slot': 'watch'}, 'anim': 'idle', 'face': {'at': FAM}})
A({'who': watchers, 't': T5 + 2.0, 'anim': 'cheer', 'pick': 0.5, 'seed': 3})
A({'who': watchers, 't': TC + 0.6, 'anim': 'shock', 'face': {'at': CAVE}})
if inr(SAKU):
    A({'who': SAKU, 't': T5, 'at': [MOM[0] + 3, MOM[1] + 8], 'anim': 'cheer', 'face': {'at': FAM}, 'hide': False})
    A({'who': SAKU, 't': T6, 'hide': True})

# S7 謎（37.8〜42.0）：ゆりさん
T7, T8 = 41.2, 45.4
if inr(YURI):
    A({'who': YURI, 't': T7, 'at': [-2.0, 12.0], 'anim': 'cheer', 'face': 'front', 'hide': False})
    A({'who': YURI, 't': T8, 'hide': True})

# クマ：ステージの上でショー（立ち上がる）→ 高原ではいつもの場所
BPATH = [[0, STAGE[0] + 3.0, STAGE[1] + 2.4], [T4 + 1.6, STAGE[0] + 3.0, STAGE[1] + 2.4], [T4 + 2.6, STAGE[0] + 0.6, STAGE[1] + 1.2], [T4 + 5.2, STAGE[0] + 0.6, STAGE[1] + 1.2], [T4 + 6.4, STAGE[0] + 3.4, STAGE[1] + 0.4], [T5, STAGE[0] + 3.4, STAGE[1] + 0.4]]

DUR = 59.4
W = lambda look, dist, az, pol, up, t, fov=42: {'t': t, 'look': look, 'dist': dist, 'az': az, 'pol': pol, 'up': up, 'frame': 'south', 'fov': fov}
camera = [
    # 漂着：海の上から浜へ突っこむ
    {'from': 0, 'to': 4.4, 'hour': 7.4, 'shake': [[1.4, 2.2, 1.4]], 'keys': [W([BC[0] + 30, BC[1]], 160, 1.6, 0.45, 0, 0, 50), W(BC, 46, 1.2, 0.95, 1, 1.6, 46), W([BC[0] - 6, BC[1] + 4], 20, 0.4, 1.22, 2, 3.0, 40), W([BC[0] - 10, BC[1] - 8], 38, -0.8, 1.0, 2, 4.4, 46)]},
    {'from': 4.4, 'to': 6.4, 'hour': 11, 'keys': [W([15, 40], 950, 0.0, 0.6, 0, 4.4), W([15, 40], 620, 1.0, 0.9, 0, 6.4)]},
    # 灯台：根元から見上げて、塔のまわりをらせんに上がる → 灯がともる
    {'from': 6.4, 'to': 13.0, 'hour': 18.2, 'shake': [[8.6, 9.2, 0.6]], 'keys': [W(LIGHT, 22, 2.2, 1.25, 2, 6.4, 50), W(LIGHT, 26, 3.4, 1.2, 8, 8.4, 48), W(LIGHT, 30, 4.6, 1.15, 15, 10.4, 44), W(LIGHT, 40, 5.4, 1.1, 16, 12.0, 44), W(LIGHT, 70, 5.9, 1.0, 10, 13.0, 46)]},
    {'from': 13.0, 'to': T4, 'hour': 13, 'keys': [W(STAGE, 70, -0.6, 0.8, 0, 13.0, 44), W(STAGE, 50, 0.4, 0.9, 0, T4, 44)]},
    # ショー：客席から舞台へ突っこみ、クマが立つ瞬間に寄る
    {'from': T4, 'to': T5, 'hour': 18.8, 'shake': [[T4 + 3.0, T4 + 3.8, 1.0]], 'keys': [W([STAGE[0], STAGE[1] + 8], 38, -0.6, 0.85, 2.5, T4, 50), W([STAGE[0], STAGE[1] + 1.5], 24, 0.15, 0.98, 3.5, T4 + 2.6, 44), W([STAGE[0] + 1, STAGE[1] + 1], 19, -0.2, 1.05, 4.0, T4 + 4.0, 40), W([STAGE[0], STAGE[1] + 3], 18, 0.5, 1.0, 3.5, T4 + 6.6, 40), W([STAGE[0] + 6, STAGE[1] + 8], 26, 0.9, 0.95, 2.5, T5, 46)]},
    # 自然パーク：高原を上から → クマの家族へ降りる
    {'from': T5, 'to': T6, 'hour': 15.5, 'keys': [W([FAM[0] - 10, FAM[1] + 10], 200, -0.4, 0.5, 0, T5, 46), W([MOM[0] + 2, MOM[1]], 30, 0.3, 1.0, 2, T5 + 3.0, 42), W([MOM[0] + 2, MOM[1] + 2], 22, 0.8, 1.1, 2, TC, 40), W([CAVE[0] - 2, CAVE[1] + 8], 30, 0.5, 1.05, 3, TC + 1.4, 44), W([CAVE[0], CAVE[1] + 4], 18, 0.05, 1.18, 3, T6, 38)]},
    # 出し物の予約：夜のステージをゆっくり
    {'from': T6, 'to': T7, 'hour': 20.0, 'keys': [W(STAGE, 40, -0.8, 0.9, 2, T6, 44), W(STAGE, 30, 0.6, 1.0, 2.5, T7, 44)]},
    # 謎：ゆりさんにぐっと寄る
    # 謎（夕暮れ）：ゆりさんに寄る → 夕暮れの島をゆっくり引きで（8日目の謎と同じ雰囲気）
    {'from': T7, 'to': T7 + 2.0, 'hour': 17.6, 'keys': [W([-2, 12], 24, -0.8, 1.0, 1.6, T7, 44), W([-2, 12], 12, -0.1, 1.26, 1.6, T7 + 2.0, 36)]},
    {'from': T7 + 2.0, 'to': T8, 'hour': 18.0, 'keys': [W([20, -20], 640, 2.0, 0.7, 0, T7 + 2.0, 40), W([20, -20], 560, 2.5, 0.75, 0, T8, 40)]},
    # 次の問い
    {'from': T8, 'to': 55.8, 'hour': 9.5, 'keys': [W([15, 20], 300, -1.6, 0.6, 0, T8, 46), W([15, 20], 520, -0.2, 0.8, 0, 50.4, 44), W([15, 20], 700, 1.0, 0.85, 0, 55.8, 42)]},
    {'from': 55.8, 'to': DUR, 'hour': 18.5, 'keys': [W([15, 40], 700, 0.8, 0.85, 0, 55.8), W([15, 40], 780, 1.0, 0.85, 0, DUR)]},
]

props = [{'type': 'zzz', 'from': {'rel': i, 'up': 1.6}, 't0': 0, 't1': 0.01, 't2': 2.0, 'size': 0.9, 'phase': k * 0.3} for k, i in enumerate(arrivals[1:30:4])]
props.append({'type': 'flame', 'from': {'xz': LIGHT, 'up': 17.1}, 't0': 10.4, 't1': 10.41, 't2': 13.0, 'size': 2.6})  # 灯がともる
if len(PAIR) == 2:
    props.append({'type': 'heart', 'from': {'xz': [SEAT[0] + 7.4, SEAT[1] - 1.2], 'up': 3.6}, 'to': {'xz': [SEAT[0] + 7.4, SEAT[1] - 1.2], 'up': 4.4}, 't0': T4 + 6.4, 't1': T5, 't2': T5, 'size': 1.5})
for k, kd in enumerate(KIDS):
    props.append({'type': 'heart', 'from': {'xz': kd, 'up': 3.2}, 'to': {'xz': kd, 'up': 4.2}, 't0': T5 + 3.0 + k * 0.3, 't1': T6, 't2': T6, 'size': 1.4, 'phase': k})

props3d = [
    {'type': 'build', 'kind': 'lighthouse', 'at': LIGHT, 'rot': 0, 't0': 6.6, 't1': 10.2, 'show': 6.4},
    {'type': 'beast', 'at': BPATH[0][1:], 'path': BPATH, 'lift': 1.05, 'show': T4, 'hide': T5, 't0': 0, 't1': T5, 'rear': [[T4 + 3.0, T4 + 4.4], [T4 + 7.0, T4 + 8.2]]},
    {'type': 'beast', 'at': MOM, 'path': [[0, MOM[0], MOM[1]], [60, MOM[0], MOM[1]]], 'show': T5, 'hide': T6, 't0': 0, 't1': 60},
    *[{'type': 'beast', 'at': kd, 'path': [[0, kd[0], kd[1]], [60, kd[0], kd[1]]], 'size': 0.55, 'show': T5, 'hide': T6, 't0': 0, 't1': 60} for kd in KIDS],
]

def star(i, a, b, text):
    return {'who': i, 'from': a, 'to': b, 'bubble': text} if inr(i) else None
stars = [x for x in [
    star(ZAF, T4 + 0.4, T4 + 2.8, 'クマとショー、やってみた！'),
    star(SAKU, T5 + 3.0, TC, 'この島の自然を、守りたい！'),
    star(YURI, T7 + 0.4, T7 + 2.0, '合言葉　ふね'),
] if x]
TOPROWS = [{'name': name_of(c['userId']), 'text': re.sub(r'\s+', ' ', c.get('text') or ''), 'likes': c.get('likeCount') or 0} for c in TOP]
LB = {'total': LIKES, 'max': 1000, 'goals': GOALS}
OPTS = {'A': 'みんなの宿舎（雨や嵐が来る前に）', 'B': '自分のお店が並ぶ通り', 'C': 'スポーツ広場', 'D': '自由に提案'}
overlay = {
    'banner': 'コメントで動く無人島　9日目',
    'bannerOff': [[0, 6.4], [13.0, T4], [T7 + 2.0, DUR]],
    'commenters': commenters,
    'names': {**{i: name_of(i) for i in people}, **{i: name_of(i) for i in [ZAF, SAKU, RINO, SYK, YURI]}},
    'titles': [{'text': '9日目', 'from': 0.1, 'to': 2.6}],
    'tagAll': [[2.4, 4.4, 0.03]],
    'tagOnly': ([{'from': T4 + 6.4, 'to': T5, 'who': PAIR, 'join': True, 'size': 36}] if len(PAIR) == 2 else []),
    'stars': stars,
    'ranking': {'from': 13.0, 'to': T4, 'title': '前回、いいねが多かったコメント', 'rows': TOPROWS, 'winnerAt': 99},
    'wall': {'from': T6, 'to': T7, 'title': 'ステージの出し物、予約が入った', 'step': 0.18, 'items': [{'name': name_of(i), 'text': t} for i, t, _ in REQ]},
    'likebars': [{**LB, 'from': 11.0, 'to': 13.0, 'from0': 700, 'y': 1180}, {**LB, 'from': 52.5, 'to': DUR, 'from0': LIKES, 'y': 380}],
    'images': [
        {'file': 'profile.png', 'from': 4.4, 'to': 6.4, 'w': 900, 'y': 600, 'tap': [0.24, 0.905], 'tapLabel': 'フォロー＆いいねで…'},
        {'file': 'profile.png', 'from': 52.5, 'to': DUR, 'w': 900, 'y': 980, 'tap': [0.37, 0.78], 'tapLabel': 'ここから'},
    ],
    'captions': [
        {'text': f'{n_arrive}人が、流れ着いた！', 'from': 0.4, 'to': 2.3, 'y': 1290, 'size': 72},
        {'text': f'島民、{n_all}人に！', 'from': 2.4, 'to': 4.4, 'y': 1290, 'size': 72, 'color': [255, 214, 74]},
        {'text': 'あなたも、次の動画で流れ着きます', 'from': 4.5, 'to': 6.4, 'y': 1400, 'size': 50, 'color': [255, 214, 74]},
        {'text': '島のいいねが、750を超えた！', 'from': 6.5, 'to': 8.6, 'y': 340, 'size': 60, 'color': [255, 214, 74]},
        {'text': '灯台が、建った！', 'from': 8.7, 'to': 11.0, 'y': 340, 'size': 80, 'color': [255, 214, 74]},
        *([{'text': f'次は{NEXT["at"]}で、{NEXT["label"]}', 'from': 11.1, 'to': 13.0, 'y': 340, 'size': 50}] if NEXT else []),
        {'text': 'ざーふさん「クマとショーをやってみたい」', 'from': T4 + 0.1, 'to': T4 + 2.9, 'y': 330, 'size': 44, 'color': [255, 214, 74]},
        {'text': 'クマが、立った！', 'from': T4 + 3.0, 'to': T4 + 6.2, 'y': 330, 'size': 80, 'color': [255, 214, 74]},
        *([{'text': 'Rinoさんと仲良しが、@で誘いあった', 'from': T4 + 6.4, 'to': T5, 'y': 330, 'size': 46}] if len(PAIR) == 2 else []),
        {'text': 'さくさくぱんださんの「自然パーク」', 'from': T5 + 0.1, 'to': T5 + 3.0, 'y': 340, 'size': 50, 'color': [255, 214, 74]},
        {'text': 'まずは、高原のクマの家族を見守るところから', 'from': T5 + 3.0, 'to': TC, 'y': 340, 'size': 44},
        {'text': 'クマの家族の奥に…', 'from': TC + 0.1, 'to': TC + 1.5, 'y': 340, 'size': 60},
        {'text': '洞窟！？', 'from': TC + 1.5, 'to': T6, 'y': 340, 'size': 90, 'color': [255, 214, 74]},
        {'text': 'るねさんの「島で洞窟を見つけました」は、本当だった', 'from': TC + 1.7, 'to': T6, 'y': 1300, 'size': 40},
        {'text': '今夜から、順番にステージへ', 'from': T6 + 1.6, 'to': T7, 'y': 1560, 'size': 46, 'color': [255, 214, 74]},
        {'text': '手記を見つけた人が、現れた…', 'from': T7 + 0.1, 'to': T7 + 2.0, 'y': 360, 'size': 56, 'color': [255, 214, 74]},
        {'text': '昔の住人の手記は、', 'from': T7 + 2.1, 'to': T8, 'y': 440, 'size': 56},
        {'text': '島のどこかにあるらしい', 'from': T7 + 2.5, 'to': T8, 'y': 530, 'size': 56, 'color': [255, 214, 74]},
        {'text': '次の質問', 'from': T8 + 0.1, 'to': 55.8, 'y': 300, 'size': 64, 'color': [255, 214, 74]},
        {'text': f'島民{n_all}人。次に作るのは？', 'from': T8 + 0.2, 'to': 55.8, 'y': 430, 'size': 62},
        {'text': f'A {OPTS["A"]}', 'from': T8 + 1.0, 'to': 55.8, 'y': 640, 'size': 46},
        {'text': f'B {OPTS["B"]}', 'from': T8 + 1.6, 'to': 55.8, 'y': 740, 'size': 46},
        {'text': f'C {OPTS["C"]}', 'from': T8 + 2.2, 'to': 55.8, 'y': 840, 'size': 46},
        {'text': f'D {OPTS["D"]}', 'from': T8 + 2.8, 'to': 55.8, 'y': 940, 'size': 46},
        {'text': 'A・B・C・Dでコメントしてね', 'from': T8 + 3.6, 'to': 55.8, 'y': 1180, 'size': 50, 'color': [255, 214, 74]},
        {'text': 'いいと思ったコメントには♥を', 'from': T8 + 4.6, 'to': 55.8, 'y': 1280, 'size': 44},
        {'text': 'いいねは全部の投稿で数えます', 'from': 52.6, 'to': DUR, 'y': 720, 'size': 42},
    ],
    'smallTagsMax': 5,
}
narr = [
    {'at': 0.3, 'until': 2.3, 'text': f'{n_arrive}人が、流れ着いた！'},
    {'at': 2.4, 'until': 4.4, 'text': f'島民は、{n_all}人に！'},
    {'at': 4.5, 'until': 6.4, 'text': 'フォローといいねで、あなたも。'},
    {'at': 6.5, 'until': 8.6, 'text': '島のいいねが、750を超えた！'},
    {'at': 8.7, 'until': 11.0, 'text': 'みんなのいいねで、灯台が建った！'},
    {'at': 11.1, 'until': 13.0, 'text': f'次は{NEXT["at"]}で、ひつじ！' if NEXT else 'いいね、ありがとう！'},
    {'at': 13.1, 'until': T4, 'text': '前回、いいねが多かったコメント。'},
    {'at': T4 + 0.1, 'until': T4 + 2.9, 'text': 'ざーふさんと、クマのショー！'},
    {'at': T4 + 3.0, 'until': T4 + 6.2, 'text': 'クマが、立った！'},
    {'at': T4 + 6.4, 'until': T5, 'text': 'アットで誘いあって、仲良しに。'},
    {'at': T5 + 0.1, 'until': TC, 'text': '自然パークづくり、まずはクマの家族を見守るところから。'},
    {'at': TC + 0.1, 'until': T6, 'text': 'その奥に、洞窟！？'},
    {'at': T6 + 0.1, 'until': T7, 'text': 'ステージの出し物にも、予約が入った！今夜から、順番に登場！'},
    {'at': T7 + 0.1, 'until': T8, 'text': '手記を見つけた人が、現れた…。昔の住人の手記は、島のどこかにあるらしい。'},
    {'at': T8 + 0.2, 'until': 55.8, 'text': '次に作るのは？エー、ビー、シー、ディーでコメントしてね。いいと思ったコメントには、いいねを。'},
    {'at': 52.6, 'until': DUR, 'text': 'いいねで、島が変わるよ。'},
]
EXIST = [
    {'id': 'ruins-1', 'type': 'ruins', 'name': '昔の住人の跡', 'x': -44.7, 'z': -12.7, 'rot': 0, 'builtDay': 1},
    {'id': 'hut-1', 'type': 'hut', 'name': 'はじまりの小屋', 'x': -20, 'z': -5, 'rot': 20, 'builtDay': 4},
    {'id': 'workshop-1', 'type': 'workshop', 'name': '石の作業場', 'x': -40.3, 'z': -9.0, 'rot': 10, 'builtDay': 5},
    {'id': 'bigfield-1', 'type': 'bigfield', 'name': '巨大な畑', 'x': -36.67, 'z': -17.0, 'rot': 0, 'builtDay': 6},
    {'id': 'bearhouse-1', 'type': 'bearhouse', 'name': 'クマの家', 'x': -29.33, 'z': -12.0, 'rot': 0, 'builtDay': 7},
    {'id': 'stage-1', 'type': 'stage', 'name': 'みんなのステージ', 'x': 7.33, 'z': 11.33, 'rot': 0, 'builtDay': 8},
    {'id': 'cave-1', 'type': 'cave', 'name': '洞窟', 'x': round(CAVE[0] / 3, 2), 'z': round(CAVE[1] / 3, 2), 'rot': 0, 'builtDay': 9},
]
story = {
    'title': '9日目', 'roster': ROSTER_REL, 'day': DAY, 'fps': 24, 'duration': DUR, 'hour': 10,
    'baseTime': '2026-11-25T09:00:00+09:00', 'base': {'name': '中央の広場', 'x': 0, 'z': 5, 'decidedDay': 2},
    'forestRoad': {'points': [[-74, -22], [-128, -34]], 'need': 300, 'startDay': 4, 'label': '光の場所', 'open': True},
    'toolAge': 'stone', 'clearings': [{'x0': -132, 'x1': -86, 'z0': -62, 'z1': 22, 'day': 6}], 'buildings': EXIST,
    'cast': list(dict.fromkeys(arrivals[:len(spots)] + audience + watchers + beachfolk + PAIR + [x for x in [ZAF, SAKU, YURI] if inr(x)])),
    'groups': groups, 'acts': acts, 'props': props, 'props3d': props3d, 'camera': camera,
    'overlay': overlay, 'override': {}, 'cutaway': {'radius': 1.6},
    'audio': {'narration': narr, 'bgm': {'volume': 0.18}, 'speed': 1.15},
    'cover': {'at': 21.0, 'day': f'{DAY}日目', 'lines': ['クマが、', 'ステージに立った！']},
}
json.dump(story, open(os.path.join(HERE, 'story', 'ep9.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

today = []
def td(i, spot, anim, text, tool=None):
    if inr(i): today.append({'id': i, 'spot': spot, 'anim': anim, 'text': text, **({'tool': tool} if tool else {})})
td(ZAF, 'plaza', 'cheer', 'クマとのショーを終えて、次の演目を考えている')
td(SAKU, 'forestEdge', 'idle', '自然パークの計画を練っている。まずはクマの家族を見守るところから')
pwa = {'day': DAY, 'roster': ROSTER_REL, 'today': today, 'missing': {}}
json.dump(pwa, open(os.path.join(HERE, 'story', 'ep9_pwa.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
state = {
    'day': DAY,
    'likes': {'total': LIKES},
    'buildings_add': [{'id': 'lighthouse-1', 'type': 'lighthouse', 'name': '灯台', 'x': round(LIGHT[0] / 3, 2), 'z': round(LIGHT[1] / 3, 2), 'rot': 0, 'builtDay': DAY,
                       'note': '島のいいねが750を超えて建った灯台。漂着の浜の先に立ち、夜は灯がともる。'},
                      {'id': 'cave-1', 'type': 'cave', 'name': '洞窟', 'x': round(CAVE[0] / 3, 2), 'z': round(CAVE[1] / 3, 2), 'rot': 0, 'builtDay': DAY,
                       'note': '自然パークの観察中に見つけた洞窟。高原の奥、クマの家族のすみかの先にある。るねさんの「島で洞窟を見つけました」は本当だった。'}],
    'stageRequests_add': [{'id': i, 'text': t, 'kind': k, 'after': '2026-11-25T18:30:00+09:00'} for i, t, k in REQ],
    'chronicle_add': {'day': DAY, 'title': '灯台が建ち、クマがステージへ',
                      'text': f'{n_arrive}人が流れ着き、島民は{n_all}人に。島のいいねが750を超えて灯台が建った。ざーふさんとクマのショーで、クマがステージに立った。さくさくぱんださんの「自然パーク」づくりが始まり、観察中に高原の奥で洞窟を見つけた。',
                      'vote': {'question': 'この島で、何をする？', 'adopted': 'ざーふさん「クマとショー」・さくさくぱんださん「自然パーク」（いいね順）', 'note': '自由コメント'}},
    'currentVote': {'id': 'vote-009-build', 'status': 'open', 'question': f'島民{n_all}人。次に作るのは？',
                    'description': 'A・B・C・D でコメントしてね。コメントが一番多い案を採用します（Dはいいねが多い案から）',
                    'options': [{'key': k, 'label': v} for k, v in OPTS.items()]},
}
json.dump(state, open(os.path.join(HERE, 'story', 'ep9_state.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(json.dumps({'arrivals': n_arrive, 'all': n_all, 'likes': LIKES, 'top': [(r['name'], r['likes']) for r in TOPROWS], 'req': [name_of(r[0]) for r in REQ], 'pair': PAIR, 'cast': len(story['cast'])}, ensure_ascii=False))
