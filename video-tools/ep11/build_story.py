#!/usr/bin/env python3
"""11日目の台本（約52秒）。カメラは激しく（標準）。
  python3 video-tools/ep11/build_story.py
入力：ep11/input/comments.json（10日目「次は、どんな島にしたい？」の自由コメント）・ep11/input/islanders.json（無いときは ep10 の名簿で代用。漂着は 0 人）
流れ
  漂着 → リンク → いちばん人気は牧場（同じ人の採用は3日に1回 → コタつむりさんの案）
  → みんなで牧場をつくり、ひつじを柵の中へ → 🐸ま🐸さんたちが「ほかの動物」を探しに → 洞窟の奥に光る目…？
  → 手記を見つけた人が増えた（ibu13さん・さらさん）
  → 次の問い「洞窟の奥に、光る目。どうする？」A 松明を持って、みんなで入る／B クマに先に行ってもらう／C 入口に柵をして、様子を見る／D 自由
"""
import json, os, re, math, random, sys
HERE = os.path.dirname(os.path.abspath(__file__))
os.makedirs(os.path.join(HERE, 'story'), exist_ok=True)
C = json.load(open(os.environ.get('COMMENTS') or os.path.join(HERE, 'input', 'comments.json'), encoding='utf-8'))
ROSTER_PATH = os.environ.get('ROSTER') or os.path.join(HERE, 'input', 'islanders.json')
if not os.path.exists(ROSTER_PATH):
    print('!! ep11/input/islanders.json が無いので、ep10 の名簿で代用（漂着は 0 人）', file=sys.stderr)
    ROSTER_PATH = os.path.join(HERE, '..', 'ep10', 'input', 'islanders.json')
ROSTER_PATH = os.path.abspath(ROSTER_PATH)
ROSTER_REL = os.path.relpath(ROSTER_PATH, os.path.join(HERE, 'story'))
R = json.load(open(ROSTER_PATH, encoding='utf-8'))
ROSTER = {p['id']: p for p in R['islanders']}
DAY = 11
inr = lambda i: bool(i) and i in ROSTER
LIKES = int(C['post'].get('likesTotal') or 0)
rnd = random.Random(11)

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
    t = c.get('text') or ''
    if c['userId'] in seen or not (c.get('likeCount') or 0) or '合言葉' in t or '手記' in t: continue
    seen.add(c['userId']); TOP.append(c)
TOP = TOP[:3]

ZAF, KOTA, MARU, IBU, SARA, TSUKI = 'guernica.0712', 'kota_chumuri', 'marumegane4', 'ibu131313', 'sajuyu19', 'tsuki5747'
arrivals = [p['id'] for p in R['islanders'] if int(p.get('joinedDay', 0)) == DAY]
n_arrive, n_all = len(arrivals), len(R['islanders'])
special = {ZAF, KOTA, MARU, IBU, SARA, TSUKI} | {c['userId'] for c in TOP}
older = [p for p in R['islanders'] if int(p.get('joinedDay', 0)) < DAY and p['id'] not in special]
farmers = [p['id'] for p in older if p.get('job') in ('農家', '大工')][:16]
explorers = [p['id'] for p in older if p.get('job') == '探検家' and p['id'] not in farmers][:10]

# ---- 場所（ワールド座標） ----
BC = [236.0, 124.0]
RANCH = [48.0, -12.0]                 # 牧場（ひつじの草地。入口は +z）
CAVE = [92.0, -156.0]                 # 洞窟（入口は +z）
COVE = [-20.0, 150.0]                 # 入り江（ibu13さんが釣りをしていた）

BEACH = json.load(open(os.path.join(HERE, '..', 'ep7', 'beach_spots.json')))
spots = [list(b) for b in BEACH]
rnd.shuffle(spots)

groups = [
    {'name': 'south', 'type': 'line', 'spot': [0, 0], 'face': [0, 1], 'members': []},
    {'name': 'farm', 'type': 'line', 'spot': [RANCH[0] + 3, RANCH[1] + 9], 'face': [0, -1], 'gap': 2.2, 'rows': 2, 'members': [x for x in [KOTA] if inr(x)] + farmers},
    {'name': 'explore', 'type': 'line', 'spot': [CAVE[0], CAVE[1] + 12], 'face': [0, -1], 'gap': 1.7, 'rows': 2, 'members': [x for x in [MARU, TSUKI] if inr(x)] + explorers},
]
acts = [{'who': '*', 't': 0, 'anim': 'idle', 'face': 'front'}]
A = acts.append

# S0 漂着（0〜4.4）
T1, T2 = 4.4, 6.4
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
    A({'who': i, 't': T1, 'hide': True})

# S3 牧場づくり（11.0〜24.0）
T3, T4 = 11.0, 24.0
FB = groups[1]['members']
A({'who': FB, 't': T3, 'anim': 'work', 'face': {'at': RANCH}})
A({'who': FB, 't': T3 + 7.4, 'anim': 'idle', 'face': {'at': RANCH}})
A({'who': FB, 't': T3 + 10.2, 'anim': 'cheer', 'face': 'front'})
A({'who': FB, 't': T4, 'hide': True})

# S4 ほかの動物を探しに → 洞窟の奥に光る目（24.0〜32.0）
T5 = 32.0
EX = groups[2]['members']
A({'who': EX, 't': 0, 'hide': True})
A({'who': EX, 't': T4, 'hide': False, 'anim': 'idle', 'face': {'at': CAVE}})
A({'who': EX, 't': T4 + 4.4, 'anim': 'shock', 'face': {'at': CAVE}})
A({'who': EX, 't': T5, 'hide': True})

# S5 手記（32.0〜36.0）：ibu13さん（入り江で釣り）
T6 = 36.0
if inr(IBU):
    A({'who': IBU, 't': T5, 'at': COVE, 'anim': 'cheer', 'face': 'front', 'hide': False})
    A({'who': IBU, 't': T6, 'hide': True})

# ひつじ：牧場の外の草地 → 島民に連れられて柵の中へ
SHEEP = []
for k in range(8):
    sx, sz = RANCH[0] - 10 + (k % 4) * 4.5 + rnd.uniform(-1, 1), RANCH[1] + 24 + (k // 4) * 3 + rnd.uniform(-1, 1)
    ex, ez = RANCH[0] - 9 + (k % 4) * 5.5 + rnd.uniform(-1, 1), RANCH[1] - 5 + (k // 4) * 7 + rnd.uniform(-1, 1)
    gx, gz = RANCH[0] + rnd.uniform(-1.5, 1.5), RANCH[1] + 14.5
    SHEEP.append({'type': 'beast', 'model': 'sheep', 'size': 0.9, 'at': [sx, sz], 'show': T3, 'hide': T4, 't0': 0, 't1': 60,
                  'path': [[0, round(sx, 2), round(sz, 2)], [T3 + 7.6 + k * 0.15, round(sx, 2), round(sz, 2)], [T3 + 8.8 + k * 0.15, round(gx, 2), round(gz, 2)],
                           [T3 + 10.4 + k * 0.12, round(ex, 2), round(ez, 2)], [60, round(ex + 0.3, 2), round(ez, 2)]]})

DUR = 52.0
W = lambda look, dist, az, pol, up, t, fov=42: {'t': t, 'look': look, 'dist': dist, 'az': az, 'pol': pol, 'up': up, 'frame': 'south', 'fov': fov}
camera = [
    {'from': 0, 'to': T1, 'hour': 7.4, 'shake': [[1.4, 2.2, 1.4]], 'keys': [W([BC[0] + 30, BC[1]], 160, 1.6, 0.45, 0, 0, 50), W(BC, 46, 1.2, 0.95, 1, 1.6, 46), W([BC[0] - 6, BC[1] + 4], 20, 0.4, 1.22, 2, 3.0, 40), W([BC[0] - 10, BC[1] - 8], 38, -0.8, 1.0, 2, T1, 46)]},
    {'from': T1, 'to': T2, 'hour': 11, 'keys': [W([15, 40], 950, 0.0, 0.6, 0, T1), W([15, 40], 620, 1.0, 0.9, 0, T2)]},
    {'from': T2, 'to': T3, 'hour': 12, 'keys': [W(RANCH, 160, -0.6, 0.55, 0, T2, 44), W(RANCH, 110, 0.4, 0.7, 0, T3, 44)]},
    # 牧場：柵のまわりを高速で回りこむ → ひつじが入口から入る → 真上から
    {'from': T3, 'to': T4, 'hour': 15.0, 'shake': [[T3 + 7.2, T3 + 7.8, 0.7]], 'keys': [
        W([RANCH[0], RANCH[1] + 14], 22, -1.4, 1.1, 2, T3, 46), W(RANCH, 44, -0.2, 0.85, 2, T3 + 3.4, 46), W(RANCH, 46, 1.2, 0.8, 2, T3 + 6.8, 46),
        W([RANCH[0], RANCH[1] + 14], 20, 0.3, 1.15, 2, T3 + 9.0, 42), W(RANCH, 70, 0.0, 0.4, 0, T4, 46)]},
    # 洞窟：探検隊の頭ごし → 入口へ突っこむ → 光る目
    {'from': T4, 'to': T5, 'hour': 18.4, 'shake': [[T4 + 4.4, T4 + 5.2, 1.2]], 'keys': [W([CAVE[0], CAVE[1] + 14], 30, -0.6, 1.0, 2, T4, 46), W([CAVE[0], CAVE[1] + 6], 18, 0.0, 1.18, 2.5, T4 + 3.0, 40), W([CAVE[0], CAVE[1] + 3], 13, 0.0, 1.22, 2.2, T4 + 5.0, 34), W([CAVE[0], CAVE[1] + 3], 16, 0.15, 1.2, 2.2, T5, 36)]},
    # 手記：入り江のibu13さん → 夕暮れの島
    {'from': T5, 'to': T6, 'hour': 17.6, 'keys': [W(COVE, 26, -0.8, 1.0, 1.6, T5, 44), W(COVE, 12, -0.1, 1.26, 1.6, T6, 36)]},
    # 次の問い：洞窟の前から引いていく
    {'from': T6, 'to': 48.0, 'hour': 19.6, 'keys': [W([CAVE[0], CAVE[1] + 4], 30, 0.3, 1.1, 3, T6, 44), W([CAVE[0], CAVE[1] + 4], 80, -0.2, 0.9, 3, 42.0, 46), W([CAVE[0], CAVE[1]], 240, -0.6, 0.7, 0, 48.0, 46)]},
    {'from': 48.0, 'to': DUR, 'hour': 18.5, 'keys': [W([15, 40], 700, 0.8, 0.85, 0, 48.0), W([15, 40], 780, 1.0, 0.85, 0, DUR)]},
]

props = [{'type': 'zzz', 'from': {'rel': i, 'up': 1.6}, 't0': 0, 't1': 0.01, 't2': 2.0, 'size': 0.9, 'phase': k * 0.3} for k, i in enumerate(arrivals[1:20:4])]
for k in range(4):
    props.append({'type': 'heart', 'from': {'xz': [RANCH[0] - 8 + k * 5, RANCH[1] - 2], 'up': 3.0}, 'to': {'xz': [RANCH[0] - 8 + k * 5, RANCH[1] - 2], 'up': 4.2}, 't0': T3 + 10.6 + k * 0.2, 't1': T4, 't2': T4, 'size': 1.4, 'phase': k})
# 洞窟の奥の光る目（まばたき：2回出たり消えたり）
for a, b in [(T4 + 4.4, T4 + 6.0), (T4 + 6.3, T5), (T6, 44.0)]:
    props.append({'type': 'eyes', 'from': {'xz': [CAVE[0], CAVE[1] + 2.4], 'up': 1.7}, 't0': a, 't1': a + 0.01, 't2': b, 'size': 0.9})

props3d = [
    *SHEEP,
    {'type': 'build', 'kind': 'ranch', 'at': RANCH, 'rot': 0, 't0': T3 + 0.4, 't1': T3 + 7.0, 'show': T3, 'hide': T4},
]

def star(i, a, b, text):
    return {'who': i, 'from': a, 'to': b, 'bubble': text} if inr(i) else None
stars = [x for x in [
    star(KOTA, T3 + 0.4, T3 + 3.2, 'ヒツジさんの為に、牧場つくりたい！'),
    star(MARU, T4 + 0.4, T4 + 3.0, 'ほかにも動物、いないかな？'),
    star(IBU, T5 + 0.3, T6, '釣りをしてたら、手記を見つけた！'),
] if x]
TOPROWS = [{'name': name_of(c['userId']), 'text': re.sub(r'\s+', ' ', c.get('text') or ''), 'likes': c.get('likeCount') or 0} for c in TOP]
OPTS = {'A': '松明を持って、みんなで入る', 'B': 'クマに先に行ってもらう', 'C': '入口に柵をして、様子を見る', 'D': '自由に提案'}
overlay = {
    'banner': 'コメントで動く無人島　11日目',
    'bannerOff': [[0, T2], [T6, DUR]],
    'commenters': commenters,
    'names': {**{i: name_of(i) for i in people}, **{i: name_of(i) for i in [KOTA, MARU, IBU]}},
    'titles': [{'text': '11日目', 'from': 0.1, 'to': 2.6}],
    'tagAll': ([[2.4, T1, 0.03]] if arrivals else []),
    'tagOnly': [{'from': T4 + 0.4, 'to': T4 + 4.2, 'who': [x for x in EX[:6]], 'below': True, 'size': 30}],
    'stars': stars,
    'ranking': {'from': T2, 'to': T3, 'title': '前回、いいねが多かったコメント', 'rows': TOPROWS, 'winnerAt': 99},
    'images': [
        {'file': 'profile.png', 'from': T1, 'to': T2, 'w': 900, 'y': 600, 'tap': [0.24, 0.905], 'tapLabel': 'フォロー＆いいねで…'},
        {'file': 'profile.png', 'from': 48.1, 'to': DUR, 'w': 900, 'y': 980, 'tap': [0.37, 0.78], 'tapLabel': 'ここから'},
    ],
    'captions': [
        *([{'text': f'{n_arrive}人が、流れ着いた！', 'from': 0.4, 'to': 2.3, 'y': 1290, 'size': 72}] if arrivals else []),
        {'text': f'島民、{n_all}人に！', 'from': 2.4 if arrivals else 0.4, 'to': T1, 'y': 1290, 'size': 72, 'color': [255, 214, 74]},
        {'text': 'あなたも、次の動画で流れ着きます', 'from': T1 + 0.1, 'to': T2, 'y': 1400, 'size': 50, 'color': [255, 214, 74]},
        {'text': 'いちばん人気は、牧場！', 'from': T2 + 2.4, 'to': T3, 'y': 1560, 'size': 56, 'color': [255, 214, 74]},
        {'text': '同じ人の採用は3日に1回なので、コタつむりさんの案で', 'from': T3 + 0.1, 'to': T3 + 3.2, 'y': 1300, 'size': 36},
        {'text': 'みんなで、牧場をつくる！', 'from': T3 + 0.1, 'to': T3 + 7.2, 'y': 330, 'size': 60, 'color': [255, 214, 74]},
        {'text': 'ひつじを、柵の中へ', 'from': T3 + 7.3, 'to': T3 + 10.4, 'y': 330, 'size': 60},
        {'text': '牧場が、できた！', 'from': T3 + 10.5, 'to': T4, 'y': 330, 'size': 72, 'color': [255, 214, 74]},
        {'text': '🐸ま🐸さんたちは、ほかの動物を探しに', 'from': T4 + 0.1, 'to': T4 + 4.2, 'y': 330, 'size': 46},
        {'text': '洞窟の奥に…', 'from': T4 + 3.0, 'to': T4 + 4.4, 'y': 420, 'size': 60},
        {'text': '光る目！？', 'from': T4 + 4.4, 'to': T5, 'y': 420, 'size': 90, 'color': [255, 214, 74]},
        {'text': 'さらさんも、手記を見つけた', 'from': T5 + 1.6, 'to': T6, 'y': 1300, 'size': 44},
        {'text': '次の質問', 'from': T6 + 0.1, 'to': 48.0, 'y': 300, 'size': 64, 'color': [255, 214, 74]},
        {'text': '洞窟の奥に、光る目。どうする？', 'from': T6 + 0.2, 'to': 48.0, 'y': 430, 'size': 60},
        {'text': f'A {OPTS["A"]}', 'from': T6 + 1.0, 'to': 48.0, 'y': 640, 'size': 46},
        {'text': f'B {OPTS["B"]}', 'from': T6 + 1.6, 'to': 48.0, 'y': 740, 'size': 46},
        {'text': f'C {OPTS["C"]}', 'from': T6 + 2.2, 'to': 48.0, 'y': 840, 'size': 46},
        {'text': f'D {OPTS["D"]}', 'from': T6 + 2.8, 'to': 48.0, 'y': 940, 'size': 46},
        {'text': 'A・B・C・Dでコメントしてね', 'from': T6 + 3.6, 'to': 48.0, 'y': 1180, 'size': 50, 'color': [255, 214, 74]},
        {'text': 'いいと思ったコメントには♥を', 'from': T6 + 4.6, 'to': 48.0, 'y': 1280, 'size': 44},
        {'text': 'いいねは全部の投稿で数えます', 'from': 48.2, 'to': DUR, 'y': 720, 'size': 42},
    ],
    'smallTagsMax': 5,
}
narr = [
    {'at': 0.3, 'until': T1, 'text': f'{n_arrive}人が流れ着いて、島民は{n_all}人！' if arrivals else f'島民は、{n_all}人！'},
    {'at': T1 + 0.1, 'until': T2, 'text': 'フォローといいねで、あなたも。'},
    {'at': T2 + 0.1, 'until': T3, 'text': '前回のいちばん人気は、牧場！'},
    {'at': T3 + 0.1, 'until': T3 + 7.2, 'text': 'コタつむりさんの案で、みんなで牧場をつくる！'},
    {'at': T3 + 7.3, 'until': T3 + 10.4, 'text': 'ひつじを、柵の中へ。'},
    {'at': T3 + 10.5, 'until': T4, 'text': '牧場が、できた！'},
    {'at': T4 + 0.1, 'until': T4 + 4.2, 'text': 'ほかの動物を探しに、洞窟へ。'},
    {'at': T4 + 4.4, 'until': T5, 'text': '奥に、光る目！？'},
    {'at': T5 + 0.1, 'until': T6, 'text': 'ibu13さんと、さらさんも、手記を見つけた。'},
    {'at': T6 + 0.2, 'until': 48.0, 'text': '洞窟の奥に、光る目。どうする？エー、ビー、シー、ディーでコメントしてね。'},
    {'at': 48.2, 'until': DUR, 'text': 'いいねで、島が変わるよ。'},
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
    {'id': 'dorm-1', 'type': 'dorm', 'name': 'みんなの宿舎', 'x': -8.0, 'z': 11.33, 'rot': 0, 'builtDay': 10},
]
story = {
    'title': '11日目', 'roster': ROSTER_REL, 'day': DAY, 'fps': 24, 'duration': DUR, 'hour': 10,
    'baseTime': '2026-11-27T09:00:00+09:00', 'base': {'name': '中央の広場', 'x': 0, 'z': 5, 'decidedDay': 2},
    'forestRoad': {'points': [[-74, -22], [-128, -34]], 'need': 300, 'startDay': 4, 'label': '光の場所', 'open': True},
    'toolAge': 'stone', 'clearings': [{'x0': -132, 'x1': -86, 'z0': -62, 'z1': 22, 'day': 6}, {'x0': RANCH[0] - 19, 'x1': RANCH[0] + 19, 'z0': RANCH[1] - 16, 'z1': RANCH[1] + 20, 'day': DAY}], 'buildings': EXIST,
    'cast': list(dict.fromkeys(arrivals[:len(spots)] + FB + EX + [x for x in [IBU] if inr(x)])),
    'groups': groups, 'acts': acts, 'props': props, 'props3d': props3d, 'camera': camera,
    'overlay': overlay, 'override': {}, 'cutaway': {'radius': 1.6},
    'audio': {'narration': narr, 'bgm': {'volume': 0.18}, 'speed': 1.15},
    'cover': {'at': 29.0, 'day': f'{DAY}日目', 'lines': ['洞窟の奥に、', '光る目…！？']},
}
json.dump(story, open(os.path.join(HERE, 'story', 'ep11.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

today = []
def td(i, spot, anim, text, tool=None):
    if inr(i): today.append({'id': i, 'spot': spot, 'anim': anim, 'text': text, **({'tool': tool} if tool else {})})
td(KOTA, 'plaza', 'cheer', '自分の案でできた牧場で、ひつじの世話をしている')
td(MARU, 'forestEdge', 'idle', '洞窟の奥の光る目が気になって、入口の前で考えこんでいる')
pwa = {'day': DAY, 'roster': ROSTER_REL, 'today': today, 'missing': {}}
json.dump(pwa, open(os.path.join(HERE, 'story', 'ep11_pwa.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
state = {
    'day': DAY,
    'likes': {'total': LIKES},
    'sheep': {'day': 10, 'x': RANCH[0], 'z': RANCH[1], 'r': 11, 'count': 8, 'text': 'コタつむりさんの案でできた牧場で、もこもこのひつじがのんびり草を食べている。'},
    'buildings_add': [{'id': 'ranch-1', 'type': 'ranch', 'name': '牧場', 'x': round(RANCH[0] / 3, 2), 'z': round(RANCH[1] / 3, 2), 'rot': 0, 'builtDay': DAY,
                       'note': 'コタつむりさんの「ヒツジさんの為に牧場つくりたい」から、みんなでつくった牧場。いちばん人気の案だった。'}],
    'chronicle_add': {'day': DAY, 'title': '牧場ができ、洞窟の奥に光る目',
                      'text': f'島民は{n_all}人に。いちばん人気の「牧場」をコタつむりさんの案でつくり、ひつじを柵の中へ。ほかの動物を探しに行った🐸ま🐸さんたちは、洞窟の奥に光る目を見た。',
                      'vote': {'question': '次は、どんな島にしたい？', 'adopted': 'コタつむりさん「ヒツジさんの為に牧場つくりたい」（いいね順・同じ人の採用は3日に1回）', 'note': '自由コメント'}},
    'currentVote': {'id': 'vote-011-cave', 'status': 'open', 'question': '洞窟の奥に、光る目。どうする？',
                    'description': 'A・B・C・D でコメントしてね。コメントが一番多い案を採用します（Dはいいねが多い案から）',
                    'options': [{'key': k, 'label': v} for k, v in OPTS.items()]},
}
json.dump(state, open(os.path.join(HERE, 'story', 'ep11_state.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(json.dumps({'arrivals': n_arrive, 'all': n_all, 'likes': LIKES, 'top': [(r['name'], r['likes']) for r in TOPROWS], 'cast': len(story['cast'])}, ensure_ascii=False))
