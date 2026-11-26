#!/usr/bin/env python3
"""10日目の台本（約56秒）。カメラは激しく（標準）。
  python3 video-tools/ep10/build_story.py
入力：ep10/input/comments.json（9日目「次に作るのは？」）・ep10/input/islanders.json（無いときは ep9 の名簿で代用。漂着の人数は 0 になる）
流れ
  島のいいね1000 → もこもこのひつじが海を泳いで流れ着く → 漂着・リンク
  → 前回いいねが多かったコメント → 投票 A みんなの宿舎 → Rinoさんの案で広場のそばに、じんさん・Kaoriさんたちが建てる → その夜は屋根の下で
  → ゆらさんのギターにクマが聴きいる（ステージの予約：ヘロルトさんのファイヤーショー、みはかさんのライブ）
  → 謎：コタつむりさんが手記を2枚 → 夕暮れの島全体「残りの手記も、島のどこかに」
  → 次の問い（自由）「みんなの家ができた。次は、どんな島にしたい？」
"""
import json, os, re, math, random, sys
HERE = os.path.dirname(os.path.abspath(__file__))
os.makedirs(os.path.join(HERE, 'story'), exist_ok=True)
C = json.load(open(os.environ.get('COMMENTS') or os.path.join(HERE, 'input', 'comments.json'), encoding='utf-8'))
ROSTER_PATH = os.environ.get('ROSTER') or os.path.join(HERE, 'input', 'islanders.json')
if not os.path.exists(ROSTER_PATH):
    print('!! ep10/input/islanders.json が無いので、ep9 の名簿で代用（漂着は 0 人）', file=sys.stderr)
    ROSTER_PATH = os.path.join(HERE, '..', 'ep9', 'input', 'islanders.json')
ROSTER_PATH = os.path.abspath(ROSTER_PATH)
ROSTER_REL = os.path.relpath(ROSTER_PATH, os.path.join(HERE, 'story'))
R = json.load(open(ROSTER_PATH, encoding='utf-8'))
ROSTER = {p['id']: p for p in R['islanders']}
DAY = 10
inr = lambda i: bool(i) and i in ROSTER
LIKES = int(C['post'].get('likesTotal') or 0)
rnd = random.Random(10)

OPTS = {'A': 'みんなの宿舎（雨や嵐が来る前に）', 'B': '自分のお店が並ぶ通り', 'C': 'スポーツ広場', 'D': '自由に提案'}
VOTE_RE = re.compile(r'(?<![A-Za-zＡ-Ｚａ-ｚ])([ABCDabcdＡＢＣＤａｂｃｄ])(?![A-Za-zＡ-Ｚａ-ｚ])')
Z2H = {'Ａ': 'A', 'Ｂ': 'B', 'Ｃ': 'C', 'Ｄ': 'D', 'ａ': 'A', 'ｂ': 'B', 'ｃ': 'C', 'ｄ': 'D'}
def vote_of(text):
    m = VOTE_RE.search(re.sub(r'@[\w.]+', ' ', text or ''))
    return (Z2H.get(m.group(1)) or m.group(1).upper()) if m else None
cm = [c for c in C['comments'] if c.get('userId') and c.get('status') != 'none']
people = {}
for c in sorted(cm, key=lambda c: c.get('at') or ''):
    prev = people.get(c['userId'])
    people[c['userId']] = {**c, 'vote': c.get('vote') or vote_of(c.get('text')) or (prev or {}).get('vote')}
tally = {k: 0 for k in OPTS}
for p in people.values():
    if p['vote'] in tally: tally[p['vote']] += 1
winner = max(OPTS, key=lambda k: (tally[k], -list(OPTS).index(k)))
def name_of(i):
    n = (people.get(i, {}).get('name') or '').strip() or ROSTER.get(i, {}).get('name') or i
    ok = sum(1 for ch in n if ch.isascii() and ch.isalnum() or '぀' <= ch <= 'ヿ' or '一' <= ch <= '鿿')
    return n if ok >= max(1, len(n) // 2) else i
commenters = {i: (p['vote'] or '-') for i, p in people.items() if inr(i)}
top = sorted([c for c in cm if inr(c['userId'])], key=lambda c: (-(c.get('likeCount') or 0), c.get('at') or ''))
seen, TOP = set(), []
for c in top:
    if c['userId'] in seen or not (c.get('likeCount') or 0) or '合言葉' in (c.get('text') or ''): continue
    seen.add(c['userId']); TOP.append(c)
TOP = TOP[:3]

ZAF, JIN, KAORI, RINO, YURA, HERO, MIHA, KOTA = 'guernica.0712', 'jinsta129', 'onyankopunch', 'rino._.15', 'yuradayo0330', 'heroruto7', 'mihaka166', 'kota_chumuri'
REQ = [(YURA, 'ギターの弾き語り', 'sing'), (HERO, 'ファイヤーショー', 'dance'), (MIHA, 'ライブ', 'sing')]
REQ = [r for r in REQ if inr(r[0])]
arrivals = [p['id'] for p in R['islanders'] if int(p.get('joinedDay', 0)) == DAY]
n_arrive, n_all = len(arrivals), len(R['islanders'])
special = {ZAF, JIN, KAORI, RINO, YURA, HERO, MIHA, KOTA} | {c['userId'] for c in TOP}
older = [p for p in R['islanders'] if int(p.get('joinedDay', 0)) < DAY and p['id'] not in special]
carpenters = [p['id'] for p in older if p.get('job') == '大工'][:8]
rest = [p['id'] for p in older if p['id'] not in carpenters]
beachfolk = rest[:40]
audience = rest[40:80]
helpers = rest[80:104]

# ---- 場所（ワールド座標） ----
BC = [236.0, 124.0]                   # 漂着の浜
SEA = [262.0, 136.0]                  # ひつじが泳いでくる沖
DORM = [-24.0, 34.0]                  # みんなの宿舎（Rinoさんの案で、中央の広場のそば。正面は +z）
STAGE = [22.0, 34.0]
SEAT = [STAGE[0], STAGE[1] + 8.5]

BEACH = json.load(open(os.path.join(HERE, '..', 'ep7', 'beach_spots.json')))
spots = [list(b) for b in BEACH]
rnd.shuffle(spots)

groups = [
    {'name': 'south', 'type': 'line', 'spot': [0, 0], 'face': [0, 1], 'members': []},
    {'name': 'beach', 'type': 'ring', 'spot': [BC[0] - 8, BC[1] - 2], 'radius': 7, 'gap': 2.0, 'members': beachfolk},
    {'name': 'build', 'type': 'line', 'spot': [DORM[0], DORM[1] + 8.5], 'face': [0, -1], 'gap': 1.9, 'rows': 3, 'members': [x for x in [JIN, KAORI, RINO, ZAF] if inr(x)] + carpenters + helpers},
    {'name': 'seat', 'type': 'line', 'spot': [SEAT[0], SEAT[1] + 1.5], 'face': [0, -1], 'gap': 1.7, 'rows': 4, 'members': audience},
]
acts = [{'who': '*', 't': 0, 'anim': 'idle', 'face': 'front'}]
A = acts.append

# S0 ひつじ（0〜4.8）：浜の島民が海を見て、ひつじが泳いでくる
T1, T2 = 4.8, 7.0
A({'who': beachfolk, 't': 0, 'at': {'slot': 'beach'}, 'anim': 'idle', 'face': {'at': SEA}})
A({'who': beachfolk, 't': 1.6, 'anim': 'shock', 'pick': 0.5, 'seed': 1})
A({'who': beachfolk, 't': 3.0, 'anim': 'cheer', 'pick': 0.8, 'seed': 2})
A({'who': beachfolk, 't': T1, 'hide': True})
# S1 漂着（4.8〜7.0）
for k, i in enumerate(arrivals[:len(spots)]):
    x, z = spots[k]
    A({'who': i, 't': T1, 'at': [x, z], 'anim': 'sleep', 'face': 'front', 'hide': False})
    A({'who': i, 't': T1 + 0.6 + (k % 9) * 0.08, 'anim': 'sit' if k % 3 == 0 else 'cheer'})
    A({'who': i, 't': T2, 'hide': True})

# S4 宿舎づくり（16.2〜30.0）
T4, T5 = 16.2, 30.0
B = G_build = groups[2]['members']
A({'who': B, 't': T4, 'anim': 'work', 'face': {'at': DORM}})
A({'who': B, 't': T4 + 8.0, 'anim': 'cheer', 'face': 'front'})
# その夜：戸口へ歩いて、中へ
for k, i in enumerate(B):
    door = [DORM[0] + [-5.5, 0, 5.5][k % 3], DORM[1] + 4.2]
    A({'who': i, 't': T4 + 10.4 + (k % 8) * 0.18, 'to': door, 'dur': 1.6})
    A({'who': i, 't': T4 + 12.2 + (k % 8) * 0.18, 'hide': True})

# S5 ステージ：ゆらさんのギターに、クマが聴きいる（30.0〜35.6）
T6 = 35.6
A({'who': audience, 't': 0, 'at': {'slot': 'seat'}, 'anim': 'idle', 'face': {'at': STAGE}})
A({'who': audience, 't': T5 + 2.6, 'anim': 'cheer', 'pick': 0.5, 'seed': 4})
if inr(YURA):
    A({'who': YURA, 't': T5, 'at': {'xz': [STAGE[0] - 0.6, STAGE[1] + 0.6], 'up': 1.1}, 'anim': 'talk', 'face': 'front', 'hide': False})
    A({'who': YURA, 't': T6, 'hide': True})

# S6 謎（35.6〜41.6）：コタつむりさん → 夕暮れの島全体
T7, T8 = 35.6, 41.6
if inr(KOTA):
    A({'who': KOTA, 't': T7, 'at': [-2.0, 12.0], 'anim': 'cheer', 'face': 'front', 'hide': False})
    A({'who': KOTA, 't': T7 + 2.4, 'hide': True})

# ひつじの群れ：沖から泳いで浜へ（8頭）。ゆらさんの場面ではクマ
SHEEP = []
for k in range(8):
    sx, sz = SEA[0] + (k % 3) * 3.0 + rnd.uniform(-1, 1), SEA[1] - 6 + (k // 3) * 3.2 + rnd.uniform(-1, 1)
    ex, ez = BC[0] + 4 + (k % 4) * 2.4, BC[1] - 1 + (k // 4) * 2.6
    SHEEP.append({'type': 'beast', 'model': 'sheep', 'size': 0.9, 'at': [sx, sz], 'show': 0, 'hide': T1, 't0': 0, 't1': T1,
                  'path': [[0, round(sx, 2), round(sz, 2)], [0.4 + k * 0.1, round(sx, 2), round(sz, 2)], [3.4 + k * 0.08, round(ex, 2), round(ez, 2)], [T1, round(ex + 0.6, 2), round(ez + 0.4, 2)]]})
BEAR = {'type': 'beast', 'at': [STAGE[0] + 3.4, STAGE[1] + 0.4], 'lift': 1.05, 'size': 0.8, 'path': [[0, STAGE[0] + 3.45, STAGE[1] + 0.4], [60, STAGE[0] + 3.35, STAGE[1] + 0.4]], 'show': T5, 'hide': T6, 't0': 0, 't1': 60}  # 舞台の上、ゆらさんの横で聴く

DUR = 56.0
W = lambda look, dist, az, pol, up, t, fov=42: {'t': t, 'look': look, 'dist': dist, 'az': az, 'pol': pol, 'up': up, 'frame': 'south', 'fov': fov}
SH = [BC[0] + 10, BC[1] + 2]
camera = [
    # ひつじ：海面すれすれから、泳いでくる群れを追って浜へ
    {'from': 0, 'to': T1, 'hour': 8.0, 'shake': [[3.2, 3.8, 0.8]], 'keys': [W([SEA[0], SEA[1] - 2], 26, 1.4, 1.3, 1, 0, 46), W([SEA[0] - 8, SEA[1] - 3], 18, 0.6, 1.25, 1.5, 2.0, 42), W([BC[0] + 6, BC[1] + 1], 20, -0.4, 1.15, 2, 3.6, 42), W([BC[0], BC[1]], 46, -1.0, 0.9, 2, T1, 46)]},
    {'from': T1, 'to': T2, 'hour': 9.0, 'keys': [W(BC, 90, 0.3, 0.6, 0, T1, 48), W(BC, 34, 1.1, 1.1, 1.5, T2, 42)]},
    {'from': T2, 'to': 9.0, 'hour': 11, 'keys': [W([15, 40], 950, 0.0, 0.6, 0, T2), W([15, 40], 620, 1.0, 0.9, 0, 9.0)]},
    {'from': 9.0, 'to': 13.4, 'hour': 12, 'keys': [W(DORM, 90, -0.6, 0.7, 0, 9.0, 44), W(DORM, 60, 0.4, 0.85, 0, 13.4, 44)]},
    {'from': 13.4, 'to': T4, 'hour': 12, 'keys': [W([0, 15], 420, 0.3, 0.55, 0, 13.4), W([0, 15], 300, -0.3, 0.8, 0, T4)]},
    # 宿舎：まわりを高速で回りこみ → 完成で引き → 夜、戸口へ
    {'from': T4, 'to': T4 + 8.0, 'hour': 14.5, 'shake': [[T4 + 7.4, T4 + 8.0, 0.8]], 'keys': [W([DORM[0], DORM[1] + 6], 22, -1.6, 1.1, 2, T4, 46), W(DORM, 30, -0.4, 0.95, 3, T4 + 3.0, 44), W(DORM, 26, 1.0, 1.0, 3, T4 + 6.0, 44), W(DORM, 40, 0.3, 0.85, 2, T4 + 8.0, 46)]},
    {'from': T4 + 8.0, 'to': T5, 'hour': 20.4, 'keys': [W([DORM[0], DORM[1] + 4], 34, 0.2, 1.05, 2, T4 + 8.0, 44), W([DORM[0], DORM[1] + 4], 26, -0.2, 1.12, 2, T5, 40)]},
    # ステージ：客席の頭ごし → ゆらさんとクマ
    {'from': T5, 'to': T6, 'hour': 18.6, 'keys': [W([STAGE[0], STAGE[1] + 9], 34, -0.5, 0.85, 2.5, T5, 48), W([STAGE[0] + 1.6, STAGE[1] + 1.5], 20, 0.15, 1.05, 3, T5 + 2.6, 42), W([STAGE[0] + 1.6, STAGE[1] + 1.5], 16, -0.15, 1.1, 3, T6, 38)]},
    # 謎：コタつむりさん → 夕暮れの島全体
    {'from': T7, 'to': T7 + 2.4, 'hour': 17.6, 'keys': [W([-2, 12], 24, -0.8, 1.0, 1.6, T7, 44), W([-2, 12], 12, -0.1, 1.26, 1.6, T7 + 2.4, 36)]},
    {'from': T7 + 2.4, 'to': T8, 'hour': 18.0, 'keys': [W([0, 0], 1750, 2.0, 0.5, 0, T7 + 2.4, 40), W([0, 0], 1600, 2.4, 0.55, 0, T8, 40)]},
    # 次の問い
    {'from': T8, 'to': 52.0, 'hour': 9.5, 'keys': [W([15, 20], 300, -1.6, 0.6, 0, T8, 46), W([15, 20], 520, -0.2, 0.8, 0, 47.0, 44), W([15, 20], 700, 1.0, 0.85, 0, 52.0, 42)]},
    {'from': 52.0, 'to': DUR, 'hour': 18.5, 'keys': [W([15, 40], 700, 0.8, 0.85, 0, 52.0), W([15, 40], 780, 1.0, 0.85, 0, DUR)]},
]

props = [{'type': 'heart', 'from': {'xz': [BC[0] + 6 + k * 3, BC[1]], 'up': 3.4}, 'to': {'xz': [BC[0] + 6 + k * 3, BC[1]], 'up': 4.6}, 't0': 3.6 + k * 0.2, 't1': T1, 't2': T1, 'size': 1.3, 'phase': k} for k in range(3)]
if inr(YURA):
    props.append({'type': 'guitar', 'from': {'xz': [STAGE[0] - 0.6, STAGE[1] + 0.9], 'up': 2.2}, 't0': T5, 't1': T5 + 0.01, 't2': T6, 'size': 1.6})
props.append({'type': 'heart', 'from': {'xz': [STAGE[0] + 3.4, STAGE[1] + 0.4], 'up': 5.6}, 'to': {'xz': [STAGE[0] + 3.4, STAGE[1] + 0.4], 'up': 6.6}, 't0': T5 + 3.0, 't1': T6, 't2': T6, 'size': 1.8})

props3d = [
    *SHEEP,
    {'type': 'build', 'kind': 'dorm', 'at': DORM, 'rot': 0, 't0': T4 + 0.6, 't1': T4 + 7.4, 'show': T4},
    BEAR,
]

def star(i, a, b, text):
    return {'who': i, 'from': a, 'to': b, 'bubble': text} if inr(i) else None
stars = [x for x in [
    star(JIN, T4 + 0.4, T4 + 2.8, '俺が建物作るで！'),
    star(KAORI, T4 + 3.0, T4 + 5.4, '大工の私が、本気出す！'),
    star(YURA, T5 + 0.4, T5 + 2.8, '熊さんに、ギターを聞かせたい'),
    star(KOTA, T7 + 0.3, T7 + 2.4, '手記、2枚見つけた👀'),
] if x]
TOPROWS = [{'name': name_of(c['userId']), 'text': re.sub(r'\s+', ' ', c.get('text') or ''), 'likes': c.get('likeCount') or 0} for c in TOP]
ROWS = [{'key': k, 'label': OPTS[k], 'count': tally[k]} for k in OPTS]
LB = {'total': LIKES, 'max': 1000, 'goals': [{'at': 600, 'label': '畑が一晩で実る'}, {'at': 750, 'label': '灯台が建つ'}, {'at': 1000, 'label': 'もこもこのひつじが流れ着く'}]}
overlay = {
    'banner': 'コメントで動く無人島　10日目',
    'bannerOff': [[0, 9.0], [13.4, T4], [T7 + 2.4, DUR]],
    'commenters': commenters,
    'names': {**{i: name_of(i) for i in people}, **{i: name_of(i) for i in [ZAF, JIN, KAORI, RINO, YURA, KOTA]}},
    'titles': [{'text': '10日目', 'from': 0.1, 'to': 2.4}],
    'tagAll': ([[T1 + 0.6, T2, 0.03]] if arrivals else []),
    'stars': stars,
    'ranking': {'from': 9.0, 'to': 13.4, 'title': '前回、いいねが多かったコメント', 'rows': TOPROWS, 'winnerAt': 99},
    'tally': {'from': 13.4, 'to': T4, 'title': '昨日の質問　次に作るのは？', 'grow': [13.6, 14.6], 'winner': winner, 'winnerAt': 14.9, 'rows': ROWS},
    'likebars': [{**LB, 'from': 0.3, 'to': 2.4, 'from0': 900, 'y': 1180}, {**LB, 'from': 52.1, 'to': DUR, 'from0': LIKES, 'y': 380}],
    'images': [
        {'file': 'profile.png', 'from': T2, 'to': 9.0, 'w': 900, 'y': 600, 'tap': [0.24, 0.905], 'tapLabel': 'フォロー＆いいねで…'},
        {'file': 'profile.png', 'from': 52.1, 'to': DUR, 'w': 900, 'y': 980, 'tap': [0.37, 0.78], 'tapLabel': 'ここから'},
    ],
    'captions': [
        {'text': '島のいいねが、1000を超えた！', 'from': 0.3, 'to': 2.4, 'y': 340, 'size': 60, 'color': [255, 214, 74]},
        {'text': 'もこもこのひつじが、', 'from': 2.5, 'to': T1, 'y': 300, 'size': 66},
        {'text': '流れ着いた！', 'from': 2.8, 'to': T1, 'y': 400, 'size': 84, 'color': [255, 214, 74]},
        *([{'text': f'{n_arrive}人も、流れ着いた！', 'from': T1 + 0.1, 'to': T1 + 1.2, 'y': 1290, 'size': 66}] if arrivals else []),
        {'text': f'島民、{n_all}人に！', 'from': T1 + (1.2 if arrivals else 0.1), 'to': T2, 'y': 1290, 'size': 70, 'color': [255, 214, 74]},
        {'text': 'あなたも、次の動画で流れ着きます', 'from': T2 + 0.1, 'to': 9.0, 'y': 1400, 'size': 50, 'color': [255, 214, 74]},
        {'text': 'Rinoさんの案で、場所は広場のそば', 'from': T4 + 0.1, 'to': T4 + 3.0, 'y': 1300, 'size': 44},
        {'text': 'みんなで、宿舎を建てる！', 'from': T4 + 0.1, 'to': T4 + 7.4, 'y': 330, 'size': 60, 'color': [255, 214, 74]},
        {'text': 'みんなの宿舎が、できた！', 'from': T4 + 7.4, 'to': T4 + 8.0, 'y': 330, 'size': 66, 'color': [255, 214, 74]},
        {'text': 'その夜は、みんな屋根の下で', 'from': T4 + 8.1, 'to': T5, 'y': 360, 'size': 56},
        {'text': 'ゆらさんのギターに、クマが聴きいる', 'from': T5 + 2.8, 'to': T6, 'y': 330, 'size': 48, 'color': [255, 214, 74]},
        {'text': 'ヘロルトさんのファイヤーショー、みはかさんのライブも予約', 'from': T5 + 2.8, 'to': T6, 'y': 1300, 'size': 36},
        {'text': 'コタつむりさんは、手記を2枚も', 'from': T7 + 0.1, 'to': T7 + 2.4, 'y': 360, 'size': 54, 'color': [255, 214, 74]},
        {'text': '残りの手記も、', 'from': T7 + 2.5, 'to': T8, 'y': 440, 'size': 56},
        {'text': '島のどこかに', 'from': T7 + 2.9, 'to': T8, 'y': 530, 'size': 56, 'color': [255, 214, 74]},
        {'text': '次の質問', 'from': T8 + 0.1, 'to': 52.0, 'y': 300, 'size': 64, 'color': [255, 214, 74]},
        {'text': 'みんなの家ができた。', 'from': T8 + 0.2, 'to': 52.0, 'y': 430, 'size': 60},
        {'text': '次は、どんな島にしたい？', 'from': T8 + 0.2, 'to': 52.0, 'y': 530, 'size': 70},
        {'text': 'なんでもOK。コメントで教えてね', 'from': T8 + 1.2, 'to': 52.0, 'y': 700, 'size': 50},
        {'text': 'いいねが集まった案ほど、形になりやすい…かも', 'from': T8 + 2.4, 'to': 52.0, 'y': 810, 'size': 40, 'color': [220, 230, 255]},
        {'text': '一緒にやりたい人は @ で誘ってね', 'from': T8 + 3.6, 'to': 52.0, 'y': 1180, 'size': 48, 'color': [255, 214, 74]},
        {'text': 'ステージでやりたいことも募集中', 'from': T8 + 4.6, 'to': 52.0, 'y': 1280, 'size': 46},
        {'text': '島のいいね1000、ありがとう！', 'from': 52.2, 'to': DUR, 'y': 720, 'size': 46, 'color': [255, 214, 74]},
    ],
    'smallTagsMax': 5,
}
narr = [
    {'at': 0.3, 'until': 2.4, 'text': '島のいいねが、1000を超えた！'},
    {'at': 2.5, 'until': T1, 'text': 'もこもこのひつじが、流れ着いた！'},
    {'at': T1 + 0.1, 'until': T2, 'text': f'{n_arrive}人も流れ着いて、島民は{n_all}人！' if arrivals else f'島民は、{n_all}人！'},
    {'at': T2 + 0.1, 'until': 9.0, 'text': 'フォローといいねで、あなたも。'},
    {'at': 9.1, 'until': 13.4, 'text': '前回、いいねが多かったコメント。'},
    {'at': 13.5, 'until': T4, 'text': '昨日の一番人気は、みんなの宿舎！'},
    {'at': T4 + 0.1, 'until': T4 + 7.4, 'text': 'Rinoさんの案で、広場のそばに。みんなで宿舎を建てる！'},
    {'at': T4 + 7.4, 'until': T4 + 8.0, 'text': 'できた！'},
    {'at': T4 + 8.1, 'until': T5, 'text': 'その夜は、みんな屋根の下で。'},
    {'at': T5 + 0.1, 'until': T6, 'text': 'ゆらさんのギターに、クマが聴きいる。'},
    {'at': T7 + 0.1, 'until': T8, 'text': 'コタつむりさんは、手記を2枚も。残りの手記も、島のどこかに。'},
    {'at': T8 + 0.2, 'until': 52.0, 'text': '次は、どんな島にしたい？なんでもいいよ、コメントで教えてね。いいねが集まると、形になるかも。'},
    {'at': 52.2, 'until': DUR, 'text': 'いいね1000、ありがとう！'},
]
EXIST = [
    {'id': 'ruins-1', 'type': 'ruins', 'name': '昔の住人の跡', 'x': -44.7, 'z': -12.7, 'rot': 0, 'builtDay': 1},
    {'id': 'hut-1', 'type': 'hut', 'name': 'はじまりの小屋', 'x': -20, 'z': -5, 'rot': 20, 'builtDay': 4},
    {'id': 'workshop-1', 'type': 'workshop', 'name': '石の作業場', 'x': -40.3, 'z': -9.0, 'rot': 10, 'builtDay': 5},
    {'id': 'bigfield-1', 'type': 'bigfield', 'name': '巨大な畑', 'x': -36.67, 'z': -17.0, 'rot': 0, 'builtDay': 6},
    {'id': 'bearhouse-1', 'type': 'bearhouse', 'name': 'クマの家', 'x': -29.33, 'z': -12.0, 'rot': 0, 'builtDay': 7},
    {'id': 'stage-1', 'type': 'stage', 'name': 'みんなのステージ', 'x': 7.33, 'z': 11.33, 'rot': 0, 'builtDay': 8},
    {'id': 'lighthouse-1', 'type': 'lighthouse', 'name': '灯台', 'x': 85.33, 'z': 30.0, 'rot': 0, 'builtDay': 9},
    {'id': 'cave-1', 'type': 'cave', 'name': '洞窟', 'x': 30.67, 'z': -52.0, 'rot': 0, 'builtDay': 9},
]
story = {
    'title': '10日目', 'roster': ROSTER_REL, 'day': DAY, 'fps': 24, 'duration': DUR, 'hour': 10,
    'baseTime': '2026-11-26T09:00:00+09:00', 'base': {'name': '中央の広場', 'x': 0, 'z': 5, 'decidedDay': 2},
    'forestRoad': {'points': [[-74, -22], [-128, -34]], 'need': 300, 'startDay': 4, 'label': '光の場所', 'open': True},
    'toolAge': 'stone', 'clearings': [{'x0': -132, 'x1': -86, 'z0': -62, 'z1': 22, 'day': 6}], 'buildings': EXIST,
    'cast': list(dict.fromkeys(arrivals[:len(spots)] + beachfolk + groups[2]['members'] + audience + [x for x in [YURA, KOTA] if inr(x)])),
    'groups': groups, 'acts': acts, 'props': props, 'props3d': props3d, 'camera': camera,
    'overlay': overlay, 'override': {}, 'cutaway': {'radius': 1.6},
    'audio': {'narration': narr, 'bgm': {'volume': 0.18}, 'speed': 1.15},
    'cover': {'at': 3.4, 'day': f'{DAY}日目', 'lines': ['もこもこのひつじが', '流れ着いた！']},
}
json.dump(story, open(os.path.join(HERE, 'story', 'ep10.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

today = []
def td(i, spot, anim, text, tool=None):
    if inr(i): today.append({'id': i, 'spot': spot, 'anim': anim, 'text': text, **({'tool': tool} if tool else {})})
td(JIN, 'plaza', 'work', '自分で建てたみんなの宿舎の、仕上げをしている', 'hammer')
td(KAORI, 'plaza', 'work', '大工の本気で、宿舎の屋根をなおしている', 'hammer')
td(RINO, 'plaza', 'cheer', '自分の案の場所に宿舎が建って、うれしそう')
pwa = {'day': DAY, 'roster': ROSTER_REL, 'today': today, 'missing': {}}
json.dump(pwa, open(os.path.join(HERE, 'story', 'ep10_pwa.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
state = {
    'day': DAY,
    'likes': {'total': LIKES},
    'sheep': {'day': DAY, 'x': 55.0, 'z': -15.0, 'r': 14, 'count': 8, 'text': '島のいいね1000で流れ着いた、もこもこのひつじ。広場の東の草地で、のんびり草を食べている。'},
    'buildings_add': [{'id': 'dorm-1', 'type': 'dorm', 'name': 'みんなの宿舎', 'x': round(DORM[0] / 3, 2), 'z': round(DORM[1] / 3, 2), 'rot': 0, 'builtDay': DAY,
                       'note': 'みんなの投票（A 17票）で建てた宿舎。場所はRinoさんの案で、中央の広場のそば。雨や嵐の夜も、みんなで屋根の下に。'}],
    'stageRequests_add': [{'id': i, 'text': t, 'kind': k, 'after': '2026-11-26T18:30:00+09:00'} for i, t, k in REQ],
    'chronicle_add': {'day': DAY, 'title': 'ひつじが流れ着き、みんなの宿舎ができた',
                      'text': f'島のいいねが1000を超えて、もこもこのひつじが流れ着いた。島民は{n_all}人に。みんなの投票で、広場のそばに宿舎を建てた。ゆらさんのギターに、クマが聴きいった。',
                      'vote': {'question': '島民1154人。次に作るのは？', 'adopted': OPTS[winner], 'note': '　'.join(f'{k} {tally[k]}件' for k in OPTS)}},
    'currentVote': {'id': 'vote-010-free', 'status': 'open', 'question': 'みんなの家ができた。次は、どんな島にしたい？',
                    'description': 'なんでもOK。コメントで教えてね。いいねが集まった案ほど、形になりやすい。一緒にやりたい人は @ で誘ってね', 'options': []},
}
json.dump(state, open(os.path.join(HERE, 'story', 'ep10_state.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(json.dumps({'arrivals': n_arrive, 'all': n_all, 'likes': LIKES, 'tally': tally, 'winner': winner, 'top': [(r['name'], r['likes']) for r in TOPROWS], 'req': [name_of(r[0]) for r in REQ], 'cast': len(story['cast'])}, ensure_ascii=False))
