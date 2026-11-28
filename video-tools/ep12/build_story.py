#!/usr/bin/env python3
"""12日目の台本（約56秒）。カメラは激しく（標準）。
  python3 video-tools/ep12/build_story.py
入力：ep12/input/comments.json・ep12/input/islanders.json（無いときは ep11 の名簿で代用。漂着は 0 人）
流れ
  フック：松明の明かりが、洞窟の光る目に近づく →「光る目の正体は…」
  漂着 → リンク → お待たせ：きのこの山さんのカフェ（BGMははるまきさん）
  → 投票 A 松明を持って、みんなで入る → 松明の行列が洞窟へ → 光る目の正体は「金」（あおすけさんの予想）
  → さらに奥の壁に、昔の住人の絵 →「文明を発見！」（無人島プロジェクト大統領さん）。絵には海の向こうの島と舟
  → 手記：コタつむりさんは4枚目、残りは1枚
  → 次の問い「壁の絵には、海の向こうの島。どうする？」A 舟をつくって、海の向こうへ／B 洞窟をもっと奥まで調べる／C 金で、島にお店を開く／D 自由
"""
import json, os, re, math, random, sys
HERE = os.path.dirname(os.path.abspath(__file__))
os.makedirs(os.path.join(HERE, 'story'), exist_ok=True)
C = json.load(open(os.environ.get('COMMENTS') or os.path.join(HERE, 'input', 'comments.json'), encoding='utf-8'))
ROSTER_PATH = os.environ.get('ROSTER') or os.path.join(HERE, 'input', 'islanders.json')
if not os.path.exists(ROSTER_PATH):
    print('!! ep12/input/islanders.json が無いので、ep11 の名簿で代用（漂着は 0 人）', file=sys.stderr)
    ROSTER_PATH = os.path.join(HERE, '..', 'ep11', 'input', 'islanders.json')
ROSTER_PATH = os.path.abspath(ROSTER_PATH)
ROSTER_REL = os.path.relpath(ROSTER_PATH, os.path.join(HERE, 'story'))
R = json.load(open(ROSTER_PATH, encoding='utf-8'))
ROSTER = {p['id']: p for p in R['islanders']}
DAY = 12
inr = lambda i: bool(i) and i in ROSTER
LIKES = int(C['post'].get('likesTotal') or 0)
rnd = random.Random(12)

OPTS0 = {'A': '松明を持って、みんなで入る', 'B': 'クマに先に行ってもらう', 'C': '入口に柵をして、様子を見る', 'D': '自由に（なんの目だと思う？）'}
cm = [c for c in C['comments'] if c.get('userId') and c.get('status') != 'none']
people = {}
for c in sorted(cm, key=lambda c: c.get('at') or ''):
    prev = people.get(c['userId'])
    people[c['userId']] = {**c, 'vote': c.get('vote') or (prev or {}).get('vote')}
TALLY = {'A': 13, 'B': 3, 'C': 4, 'D': 2}  # tally.md（スクショ補完後・2026-11-28 16:35）
def name_of(i):
    n = (people.get(i, {}).get('name') or '').strip() or ROSTER.get(i, {}).get('name') or i
    ok = sum(1 for ch in n if ch.isascii() and ch.isalnum() or '぀' <= ch <= 'ヿ' or '一' <= ch <= '鿿')
    return n if ok >= max(1, len(n) // 2) else i
commenters = {i: (p.get('vote') or '-') for i, p in people.items() if inr(i)}

KINOKO, HARU, AOSUKE, DAITO, KOTA, ZAF, SAKU = 'chocolatecookie1212', 'harumakigohan3', 'aosuke_0308', 'mujintoudaitouryou', 'kota_chumuri', 'guernica.0712', 'moose.85881582'
arrivals = [p['id'] for p in R['islanders'] if int(p.get('joinedDay', 0)) == DAY]
n_arrive, n_all = len(arrivals), len(R['islanders'])
special = {KINOKO, HARU, AOSUKE, DAITO, KOTA, ZAF, SAKU}
older = [p for p in R['islanders'] if int(p.get('joinedDay', 0)) < DAY and p['id'] not in special]
cafe_crowd = [p['id'] for p in older][:18]
torchers = [x for x in [ZAF, SAKU, AOSUKE, DAITO] if inr(x)] + [p['id'] for p in older][18:42]

# ---- 場所（ワールド座標） ----
BC = [236.0, 124.0]
CAFE = [0.0, 42.0]                    # カフェ（広場の南。正面は +z）
CAVE = [92.0, -156.0]                 # 洞窟（入口は +z）
IN = [CAVE[0], CAVE[1] + 3.2]         # 入口の暗がり
ROOM = [60.0, -150.0]                 # 洞窟の中（撮影用のセット。奥の壁は z-10、正面 +z が開いている）
BACK = [ROOM[0], ROOM[1] - 8.6]       # 奥の壁の前

BEACH = json.load(open(os.path.join(HERE, '..', 'ep7', 'beach_spots.json')))
spots = [list(b) for b in BEACH]
rnd.shuffle(spots)

groups = [
    {'name': 'south', 'type': 'line', 'spot': [0, 0], 'face': [0, 1], 'members': []},
    {'name': 'cafe', 'type': 'ring', 'spot': [CAFE[0], CAFE[1] + 9], 'radius': 4.2, 'gap': 1.9, 'members': cafe_crowd},
]
acts = [{'who': '*', 't': 0, 'anim': 'idle', 'face': 'front'}]
A = acts.append

HOOK = 2.4
# S0 漂着（2.4〜6.4）
T1, T2 = 6.4, 8.4
for k, i in enumerate(arrivals[:len(spots)]):
    x, z = spots[k]
    A({'who': i, 't': 0, 'hide': True})
    A({'who': i, 't': HOOK, 'at': [x, z], 'anim': 'sleep', 'face': 'front', 'hide': False})
    A({'who': i, 't': HOOK + 1.0 + (k % 11) * 0.09, 'anim': 'sit' if k % 3 == 0 else 'cheer'})
    A({'who': i, 't': T1, 'hide': True})

# S2 カフェ（8.4〜16.0）
T3 = 16.0
A({'who': cafe_crowd, 't': 0, 'hide': True})
A({'who': cafe_crowd, 't': T2, 'hide': False, 'at': {'slot': 'cafe'}, 'anim': 'cheer', 'face': {'at': CAFE}, 'pick': 0.6, 'seed': 3})
A({'who': cafe_crowd, 't': T3, 'hide': True})
for k, i in enumerate([x for x in [KINOKO, HARU] if inr(x)]):
    A({'who': i, 't': T2, 'at': [CAFE[0] - 1.6 + k * 3.2, CAFE[1] + 4.6], 'anim': 'cheer' if k == 0 else 'talk', 'face': 'front', 'hide': False})
    A({'who': i, 't': T3, 'hide': True})

# S3 投票（16.0〜18.8）→ S4 洞窟へ（18.8〜36.0）
T4, T5, T6 = 18.8, 28.6, 36.0
for k, i in enumerate(torchers):
    lane, row = (k % 3) - 1, k // 3
    A({'who': i, 't': 0, 'hide': True})
    A({'who': i, 't': T4, 'hide': False, 'at': [CAVE[0] + lane * 1.8, CAVE[1] + 26 + row * 2.2], 'anim': 'idle', 'face': {'at': CAVE}, 'torch': True})
    A({'who': i, 't': T4 + 0.3 + row * 0.12, 'to': [CAVE[0] + lane * 1.8, CAVE[1] + 8 + row * 1.7], 'dur': 3.6})
    # 中へ：入口から奥の壁へ、松明を持って進む
    A({'who': i, 't': T4 + 4.4, 'at': [ROOM[0] + lane * 3.4, ROOM[1] + 9 + row * 1.4], 'anim': 'walk', 'face': {'at': BACK}, 'torch': True})
    A({'who': i, 't': T4 + 4.45, 'to': [ROOM[0] + (1 if k % 2 else -1) * (2.0 + (k // 2 % 3) * 0.9), ROOM[1] - 2.5 + (k // 6) * 1.6], 'dur': 2.6})
    A({'who': i, 't': T4 + 7.2, 'anim': 'idle', 'face': {'at': BACK}})
    A({'who': i, 't': T4 + 7.6, 'anim': 'shock', 'pick': 0.6, 'seed': k})
    A({'who': i, 't': T5 + 0.4, 'anim': 'cheer', 'pick': 0.7, 'seed': k + 3})
    A({'who': i, 't': T6, 'hide': True})

# S5 手記（36.0〜40.0）：コタつむりさん
T7 = 40.0
if inr(KOTA):
    A({'who': KOTA, 't': 0, 'hide': True})
    A({'who': KOTA, 't': T6, 'at': [-2.0, 12.0], 'anim': 'cheer', 'face': 'front', 'hide': False})
    A({'who': KOTA, 't': T7, 'hide': True})

DUR = 56.0
W = lambda look, dist, az, pol, up, t, fov=42: {'t': t, 'look': look, 'dist': dist, 'az': az, 'pol': pol, 'up': up, 'frame': 'south', 'fov': fov}
camera = [
    # フック：松明の明かりが、暗がりの目へ近づく
    {'from': 0, 'to': HOOK, 'hour': 21.2, 'keys': [W(IN, 20, -0.4, 1.18, 2.2, 0, 40), W(IN, 11, 0.0, 1.24, 2.0, HOOK, 32)]},
    {'from': HOOK, 'to': T1, 'hour': 7.4, 'shake': [[HOOK + 1.2, HOOK + 1.8, 1.2]], 'keys': [W([BC[0] + 30, BC[1]], 160, 1.6, 0.45, 0, HOOK, 50), W(BC, 46, 1.2, 0.95, 1, HOOK + 1.6, 46), W([BC[0] - 8, BC[1] - 6], 30, -0.4, 1.05, 2, T1, 44)]},
    {'from': T1, 'to': T2, 'hour': 11, 'keys': [W([15, 40], 950, 0.0, 0.6, 0, T1), W([15, 40], 620, 1.0, 0.9, 0, T2)]},
    # カフェ：上から急降下 → 店先へ
    {'from': T2, 'to': T3, 'hour': 15.5, 'keys': [W(CAFE, 70, -1.0, 0.6, 2, T2, 48), W([CAFE[0], CAFE[1] + 4], 22, -0.3, 1.1, 2.5, T2 + 2.6, 42), W([CAFE[0], CAFE[1] + 5], 16, 0.4, 1.15, 2.5, T2 + 5.0, 38), W([CAFE[0], CAFE[1] + 6], 30, 0.9, 0.95, 2, T3, 44)]},
    {'from': T3, 'to': T4, 'hour': 12, 'keys': [W([60, -110], 420, 0.3, 0.55, 0, T3), W([60, -110], 300, -0.3, 0.8, 0, T4)]},
    # 松明の行列 → 入口 → 目に近づく → 金！
    {'from': T4, 'to': T4 + 4.4, 'hour': 20.4, 'keys': [W([CAVE[0], CAVE[1] + 24], 26, 2.6, 1.15, 2, T4, 46), W([CAVE[0], CAVE[1] + 14], 30, 0.8, 1.05, 2.5, T4 + 3.2, 44), W(IN, 12, 0.0, 1.22, 2.2, T4 + 4.4, 34)]},
    {'from': T4 + 4.4, 'to': T5, 'hour': 18.7, 'shake': [[T4 + 7.6, T4 + 8.2, 0.9]], 'keys': [W([ROOM[0], ROOM[1] + 1], 18, 0.0, 1.12, 4.0, T4 + 4.4, 48), W([ROOM[0], ROOM[1] - 5], 14, 0.1, 1.15, 3.2, T4 + 7.6, 44), W([BACK[0], BACK[1] + 1.5], 10, -0.05, 1.2, 2.2, T5, 38)]},
    # さらに奥：壁の絵
    {'from': T5, 'to': T6, 'hour': 18.7, 'keys': [W([BACK[0], BACK[1] + 2], 14, 0.0, 1.25, 4.4, T5, 44), W([BACK[0], BACK[1] + 1], 11, 0.0, 1.3, 4.8, T5 + 3.0, 40), W([ROOM[0], ROOM[1] - 2], 17, 0.15, 1.22, 4.0, T6, 46)]},
    # 手記
    {'from': T6, 'to': T7, 'hour': 17.6, 'keys': [W([-2, 12], 24, -0.8, 1.0, 1.6, T6, 44), W([-2, 12], 12, -0.1, 1.26, 1.6, T6 + 2.0, 36)]},
    {'from': T6 + 2.0, 'to': T7, 'hour': 18.0, 'keys': [W([0, 0], 1750, 2.0, 0.5, 0, T6 + 2.0, 40), W([0, 0], 1600, 2.4, 0.55, 0, T7, 40)]},
    # 次の問い：海の向こうを見る
    {'from': T7, 'to': 52.0, 'hour': 18.2, 'keys': [W([150, 60], 200, 1.2, 0.95, 0, T7, 48), W([200, 80], 420, 1.6, 1.05, 0, 46.0, 48), W([0, 0], 1500, 2.0, 0.55, 0, 52.0, 40)]},
    {'from': 52.0, 'to': DUR, 'hour': 18.5, 'keys': [W([15, 40], 700, 0.8, 0.85, 0, 52.0), W([15, 40], 780, 1.0, 0.85, 0, DUR)]},
]

props = []
# フックと洞窟：暗がりの目（金の照り返し）
props.append({'type': 'eyes', 'from': {'xz': IN, 'up': 1.7}, 't0': 0, 't1': 0.01, 't2': HOOK, 'size': 0.9})
props.append({'type': 'eyes', 'from': {'xz': BACK, 'up': 2.2}, 't0': T4 + 4.4, 't1': T4 + 4.41, 't2': T4 + 7.6, 'size': 1.1})
for k, (dx, up) in enumerate([(-0.9, 1.6), (0.9, 1.6), (0.0, 1.0), (-0.4, 0.6), (0.6, 0.7)]):
    props.append({'type': 'gold', 'from': {'xz': [BACK[0] + dx * 1.4, BACK[1] + 1.2], 'up': up * 0.6 + 0.5}, 't0': T4 + 7.6 + k * 0.08, 't1': T4 + 7.61 + k * 0.08, 't2': T6, 'size': 0.7})
props.append({'type': 'mural', 'from': {'xz': [BACK[0], BACK[1]], 'up': 5.0}, 't0': T5 + 0.3, 't1': T5 + 0.31, 't2': T6, 'size': 3.4})
# フックの松明の明かり（目に近づく）
props.append({'type': 'flame', 'from': {'xz': [IN[0] + 1.6, IN[1] + 3.5], 'up': 2.4}, 'to': {'xz': [IN[0] + 0.8, IN[1] + 1.4], 'up': 2.2}, 't0': 0, 't1': HOOK, 't2': HOOK, 'size': 1.1})
# カフェの音楽（はるまきさん）
for k in range(4):
    props.append({'type': 'heart', 'from': {'xz': [CAFE[0] - 3 + k * 2, CAFE[1] + 6], 'up': 3.4}, 'to': {'xz': [CAFE[0] - 3 + k * 2, CAFE[1] + 6], 'up': 4.6}, 't0': T2 + 4.0 + k * 0.2, 't1': T3, 't2': T3, 'size': 1.3, 'phase': k})

props3d = [{'type': 'build', 'kind': 'cafe', 'at': CAFE, 'rot': 0, 't0': T2 + 0.2, 't1': T2 + 3.4, 'show': T2, 'hide': T3},
           {'type': 'build', 'kind': 'caveroom', 'at': ROOM, 'rot': 0, 't0': 0, 't1': 0.01, 'show': T4 + 4.3, 'hide': T6}]

def star(i, a, b, text):
    return {'who': i, 'from': a, 'to': b, 'bubble': text} if inr(i) else None
stars = [x for x in [
    star(KINOKO, T2 + 3.6, T2 + 5.6, 'カフェ、オープン！'),
    star(HARU, T2 + 5.6, T3, '店内BGMは、うちに任せな👍'),
    star(KOTA, T6 + 0.3, T6 + 2.0, '手記、4枚目！'),
] if x]
ROWS = [{'key': k, 'label': OPTS0[k], 'count': TALLY[k]} for k in OPTS0]
OPTS = {'A': '舟をつくって、海の向こうの島へ', 'B': '洞窟を掘りすすめて、島の地下へ', 'C': '金で、お店が並ぶ通りをつくる', 'D': '自由に提案'}
overlay = {
    'banner': 'コメントで動く無人島　12日目',
    'bannerOff': [[0, T2], [T3, T4], [T6 + 2.0, DUR]],
    'commenters': commenters,
    'names': {**{i: name_of(i) for i in people}, **{i: name_of(i) for i in [KINOKO, HARU, AOSUKE, DAITO, KOTA, ZAF]}},
    'titles': [{'text': '12日目', 'from': HOOK + 0.1, 'to': HOOK + 2.4}],
    'tagAll': ([[HOOK + 1.6, T1, 0.03]] if arrivals else []),
    'tagOnly': [{'from': T4 + 0.6, 'to': T4 + 4.0, 'who': torchers[:4], 'below': True, 'size': 30}],
    'stars': stars,
    'tally': {'from': T3, 'to': T4, 'title': '昨日の質問　洞窟の光る目、どうする？', 'grow': [T3 + 0.2, T3 + 1.2], 'winner': 'A', 'winnerAt': T3 + 1.5, 'rows': ROWS},
    'images': [
        {'file': 'profile.png', 'from': T1, 'to': T2, 'w': 900, 'y': 600, 'tap': [0.24, 0.905], 'tapLabel': 'フォロー＆いいねで…'},
        {'file': 'profile.png', 'from': 52.1, 'to': DUR, 'w': 900, 'y': 980, 'tap': [0.37, 0.78], 'tapLabel': 'ここから'},
    ],
    'captions': [
        {'text': '光る目の正体は…', 'from': 0.05, 'to': HOOK, 'y': 420, 'size': 76, 'color': [255, 225, 74]},
        *([{'text': f'{n_arrive}人が、流れ着いた！', 'from': HOOK + 0.3, 'to': HOOK + 2.0, 'y': 1290, 'size': 72}] if arrivals else []),
        {'text': f'島民、{n_all}人に！', 'from': HOOK + (2.0 if arrivals else 0.3), 'to': T1, 'y': 1290, 'size': 72, 'color': [255, 214, 74]},
        {'text': 'あなたも、次の動画で流れ着きます', 'from': T1 + 0.1, 'to': T2, 'y': 1400, 'size': 50, 'color': [255, 214, 74]},
        {'text': 'お待たせしました！', 'from': T2 + 0.1, 'to': T2 + 2.0, 'y': 330, 'size': 66},
        {'text': '♥14の、きのこの山さんのカフェ', 'from': T2 + 2.0, 'to': T3, 'y': 330, 'size': 52, 'color': [255, 214, 74]},
        {'text': '店内BGMは、はるまきさん', 'from': T2 + 5.6, 'to': T3, 'y': 1300, 'size': 46},
        {'text': '松明を持って、みんなで洞窟へ', 'from': T4 + 0.1, 'to': T4 + 4.4, 'y': 330, 'size': 54, 'color': [255, 214, 74]},
        {'text': '洞窟の中へ…', 'from': T4 + 4.5, 'to': T4 + 6.0, 'y': 330, 'size': 60},
        {'text': '明かりを近づけると…', 'from': T4 + 6.0, 'to': T4 + 7.6, 'y': 330, 'size': 56},
        {'text': '金だった！', 'from': T4 + 7.6, 'to': T5, 'y': 330, 'size': 96, 'color': [255, 214, 74]},
        {'text': 'あおすけさんの予想が、当たった', 'from': T4 + 8.0, 'to': T5, 'y': 1300, 'size': 46},
        {'text': 'さらに奥の壁に…', 'from': T5 + 0.1, 'to': T5 + 2.0, 'y': 330, 'size': 60},
        {'text': '昔の住人の絵！', 'from': T5 + 2.0, 'to': T5 + 4.6, 'y': 330, 'size': 80, 'color': [255, 214, 74]},
        {'text': '「文明を発見！」大統領さん、正解かも', 'from': T5 + 2.4, 'to': T6, 'y': 1300, 'size': 42},
        {'text': '海の向こうに、島と舟…？', 'from': T5 + 4.6, 'to': T6, 'y': 330, 'size': 60},
        {'text': 'コタつむりさん、手記4枚目', 'from': T6 + 0.1, 'to': T6 + 2.0, 'y': 360, 'size': 58, 'color': [255, 214, 74]},
        {'text': '残りの手記は、', 'from': T6 + 2.1, 'to': T7, 'y': 440, 'size': 56},
        {'text': 'あと1枚', 'from': T6 + 2.5, 'to': T7, 'y': 540, 'size': 84, 'color': [255, 214, 74]},
        {'text': '次の質問', 'from': T7 + 0.1, 'to': 52.0, 'y': 300, 'size': 64, 'color': [255, 214, 74]},
        {'text': '壁の絵には、海の向こうの島。', 'from': T7 + 0.2, 'to': 52.0, 'y': 430, 'size': 56},
        {'text': 'どうする？', 'from': T7 + 0.2, 'to': 52.0, 'y': 525, 'size': 70},
        {'text': f'A {OPTS["A"]}', 'from': T7 + 1.0, 'to': 52.0, 'y': 700, 'size': 46},
        {'text': f'B {OPTS["B"]}', 'from': T7 + 1.6, 'to': 52.0, 'y': 800, 'size': 46},
        {'text': f'C {OPTS["C"]}', 'from': T7 + 2.2, 'to': 52.0, 'y': 900, 'size': 46},
        {'text': f'D {OPTS["D"]}', 'from': T7 + 2.8, 'to': 52.0, 'y': 1000, 'size': 46},
        {'text': 'A・B・C・Dでコメントしてね', 'from': T7 + 3.6, 'to': 52.0, 'y': 1180, 'size': 50, 'color': [255, 214, 74]},
        {'text': 'いいと思ったコメントには♥を', 'from': T7 + 4.6, 'to': 52.0, 'y': 1280, 'size': 44},
        {'text': 'いいねは全部の投稿で数えます', 'from': 52.2, 'to': DUR, 'y': 720, 'size': 42},
    ],
    'smallTagsMax': 5,
}
narr = [
    {'at': 0.1, 'until': HOOK, 'text': '光る目の、正体は…'},
    {'at': HOOK + 0.2, 'until': T1, 'text': f'{n_arrive}人が流れ着いて、島民は{n_all}人！' if arrivals else f'島民は、{n_all}人！'},
    {'at': T1 + 0.1, 'until': T2, 'text': 'フォローといいねで、あなたも。'},
    {'at': T2 + 0.1, 'until': T2 + 5.5, 'text': 'お待たせしました！きのこの山さんのカフェ、オープン！'},
    {'at': T2 + 5.6, 'until': T3, 'text': 'BGMは、はるまきさん。'},
    {'at': T3 + 0.1, 'until': T4, 'text': '昨日の一番人気は、みんなで入る！'},
    {'at': T4 + 0.1, 'until': T4 + 4.4, 'text': '松明を持って、みんなで洞窟へ。'},
    {'at': T4 + 4.5, 'until': T4 + 7.5, 'text': '中へ入って、明かりを近づけると…'},
    {'at': T4 + 7.6, 'until': T5, 'text': '金だった！あおすけさんの予想が、当たった！'},
    {'at': T5 + 0.1, 'until': T5 + 4.5, 'text': 'さらに奥の壁に、昔の住人の絵！'},
    {'at': T5 + 4.6, 'until': T6, 'text': '海の向こうに、島と舟？'},
    {'at': T6 + 0.1, 'until': T7, 'text': 'コタつむりさんは、手記を4枚。残りは、あと1枚。'},
    {'at': T7 + 0.2, 'until': 52.0, 'text': '壁の絵には、海の向こうの島。どうする？エー、ビー、シー、ディーでコメントしてね。'},
    {'at': 52.2, 'until': DUR, 'text': 'いいねで、島が変わるよ。'},
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
    {'id': 'ranch-1', 'type': 'ranch', 'name': '牧場', 'x': 16.0, 'z': -4.0, 'rot': 0, 'builtDay': 11},
]
story = {
    'title': '12日目', 'roster': ROSTER_REL, 'day': DAY, 'fps': 24, 'duration': DUR, 'hour': 10,
    'baseTime': '2026-11-28T09:00:00+09:00', 'base': {'name': '中央の広場', 'x': 0, 'z': 5, 'decidedDay': 2},
    'forestRoad': {'points': [[-74, -22], [-128, -34]], 'need': 300, 'startDay': 4, 'label': '光の場所', 'open': True},
    'toolAge': 'stone', 'clearings': [{'x0': -132, 'x1': -86, 'z0': -62, 'z1': 22, 'day': 6}, {'x0': 29, 'x1': 67, 'z0': -28, 'z1': 8, 'day': 11}], 'buildings': EXIST,
    'cast': list(dict.fromkeys(arrivals[:len(spots)] + cafe_crowd + torchers + [x for x in [KINOKO, HARU, KOTA] if inr(x)])),
    'groups': groups, 'acts': acts, 'props': props, 'props3d': props3d, 'camera': camera,
    'overlay': overlay, 'override': {}, 'cutaway': {'radius': 1.6},
    'audio': {'narration': narr, 'bgm': {'volume': 0.18}, 'speed': 1.15},
    'cover': {'at': T4 + 8.4, 'day': f'{DAY}日目', 'lines': ['光る目の正体は、', '金だった！']},
}
json.dump(story, open(os.path.join(HERE, 'story', 'ep12.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

today = []
def td(i, spot, anim, text, tool=None):
    if inr(i): today.append({'id': i, 'spot': spot, 'anim': anim, 'text': text, **({'tool': tool} if tool else {})})
td(KINOKO, 'plaza', 'work', '自分のカフェで、お客さんにコーヒーを出している', 'ladle')
td(HARU, 'plaza', 'talk', 'カフェの店内BGMを担当している')
td(AOSUKE, 'forestEdge', 'cheer', '洞窟の光る目の正体（金）を当てて、うれしそう')
pwa = {'day': DAY, 'roster': ROSTER_REL, 'today': today, 'missing': {}}
json.dump(pwa, open(os.path.join(HERE, 'story', 'ep12_pwa.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
state = {
    'day': DAY,
    'likes': {'total': LIKES},
    'buildings_add': [{'id': 'cafe-1', 'type': 'cafe', 'name': 'きのこの山カフェ', 'x': round(CAFE[0] / 3, 2), 'z': round(CAFE[1] / 3, 2), 'rot': 0, 'builtDay': DAY,
                       'note': 'きのこの山さんの案（♥14）でできたカフェ。店内BGMは、はるまきさん。'}],
    'cave_note': '洞窟の光る目の正体は、金の照り返しだった（あおすけさんの予想）。奥の壁には、昔の住人が描いた絵。海の向こうの島と舟が描かれている。',
    'chronicle_add': {'day': DAY, 'title': '光る目の正体は金、奥には昔の住人の絵',
                      'text': 'きのこの山さんのカフェがオープン（BGMは、はるまきさん）。松明を持ってみんなで洞窟に入ると、光る目の正体は金だった。さらに奥の壁には、昔の住人が描いた海の向こうの島と舟。',
                      'vote': {'question': '洞窟の奥に、光る目。どうする？', 'adopted': OPTS0['A'], 'note': '　'.join(f'{k} {TALLY[k]}件' for k in OPTS0)}},
    'currentVote': {'id': 'vote-012-sea', 'status': 'open', 'question': '壁の絵には、海の向こうの島。どうする？',
                    'description': 'A・B・C・D でコメントしてね。コメントが一番多い案を採用します（Dはいいねが多い案から）',
                    'options': [{'key': k, 'label': v} for k, v in OPTS.items()]},
}
json.dump(state, open(os.path.join(HERE, 'story', 'ep12_state.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(json.dumps({'arrivals': n_arrive, 'all': n_all, 'likes': LIKES, 'cast': len(story['cast'])}, ensure_ascii=False))
