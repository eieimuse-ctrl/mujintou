#!/usr/bin/env python3
"""5日目の台本を組み立てる（約57秒）。
  python3 video-tools/ep5/build_story.py
入力：ep5/input/comments.json（4日目の投稿のコメント）・ep5/input/islanders.json（名簿。5日目に漂着した人は joinedDay=5）
出力：ep5/story/ep5.json（台本）・ep5/story/ep5_pwa.json（PWA の続き）・ep5/story/ep5_state.json（Firebase の state に入れる差分）・ep5/story/ep5_tally.json

方針（2026-11-21 本人と確定）
- 冒頭で漂着（65人）→ リンク案内 → ゆらさん本人のコメント → @タグの仲良し → 集計（B 石の道具が採用）
- 本筋：昔の住人の跡をまねて石を割る → 石の作業場 → チームごとに石の道具を使って効果が出る
- 負けた案（A 拠点・C 行方探し）の人にも見せ場
- 夕方、海から大きな木箱が流れ着く。次の問い「中身はなんだろう？」（一番多い予想が中身になる）
  A 種と苗 / B 灯台 / C もこもこのひつじ / D 自由に予想
"""
import json, os, re

HERE = os.path.dirname(os.path.abspath(__file__))
C = json.load(open(os.path.join(HERE, 'input', 'comments.json'), encoding='utf-8'))
ROSTER_PATH = os.path.abspath(os.environ.get('ROSTER') or os.path.join(HERE, 'input', 'islanders.json'))
ROSTER_REL = os.path.relpath(ROSTER_PATH, os.path.join(HERE, 'story'))
R = json.load(open(ROSTER_PATH, encoding='utf-8'))
ROSTER = {p['id']: p for p in R['islanders']}
DAY = 5
inr = lambda i: bool(i) and i in ROSTER
os.makedirs(os.path.join(HERE, 'story'), exist_ok=True)

# ---- 集計：1人1票（最後のコメント）。A〜D の一文字で数える ----
OPTS = {'A': '跡を直して、森の拠点に', 'B': '石の道具をまねて作る', 'C': '昔の住人の行方を探す', 'D': '自由に提案'}
VOTE_RE = re.compile(r'(?<![A-Za-zＡ-Ｚａ-ｚ])([ABCDabcdＡＢＣＤａｂｃｄ])(?![A-Za-zＡ-Ｚａ-ｚ])')
Z2H = {'Ａ': 'A', 'Ｂ': 'B', 'Ｃ': 'C', 'Ｄ': 'D', 'ａ': 'A', 'ｂ': 'B', 'ｃ': 'C', 'ｄ': 'D'}
def vote_of(text):
    m = VOTE_RE.search(re.sub(r'@[\w.]+', ' ', text or ''))  # @タグ（@b1_… など）の文字は数えない
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
    n = (people.get(i, {}).get('name') or '').strip() or ROSTER.get(i, {}).get('name') or '名無し'
    # 読めない飾り文字だけの名前（字幕で□になる）は ID にする
    ok = sum(1 for ch in n if ch.isascii() and ch.isalnum() or '\u3040' <= ch <= '\u30ff' or '\u4e00' <= ch <= '\u9fff')
    return n if ok >= max(1, len(n) // 2) else i
said = {i: (p.get('text') or '').strip() for i, p in people.items()}
commenters = {i: (p['vote'] or '-') for i, p in people.items() if inr(i)}

YURA, TSUKI, DAN, NAKA, IBU, RINO, AYANE, SAKA, PESE, SYKYU = 'yuradayo0330', 'tsuki5747', 'bear.44190633', 'atsukidesu', 'ibu131313', 'rino._.15', 'analogayane', 'sakasaka_1482', 'b1_482000', 'sykyu_77'
pairs = []
for p in R['islanders']:
    for r in p.get('relationships') or []:
        if r.get('type') == 'friend' and inr(r.get('id')) and p['id'] < r['id']: pairs.append((p['id'], r['id']))
pairs = pairs[:2]
in_pair = {x for pr in pairs for x in pr}
arrivals = [p['id'] for p in R['islanders'] if int(p.get('joinedDay', 0)) == DAY and p['id'] not in in_pair]
n_arrive = sum(1 for p in R['islanders'] if int(p.get('joinedDay', 0)) == DAY)
special = {YURA, TSUKI, DAN, NAKA, IBU, RINO, AYANE} | in_pair
older = [p for p in R['islanders'] if int(p.get('joinedDay', 0)) < DAY and p['id'] not in special]
by_job = lambda j, n: [p['id'] for p in older if p.get('job') == j][:n]
carp, fishers, farmers = by_job('大工', 5), by_job('漁師', 3), by_job('農家', 4)
used = set(carp) | set(fishers) | set(farmers)
crowd = [p['id'] for p in older if p['id'] not in used][:20]

# ---- 場所（ワールド座標） ----
PLAZA = [0, 15]
YURA_AT = [-8.4, 13.2]       # 広場の輪の手前（カメラ側）
WS = [-121.0, -27.0]          # 石の作業場（昔の住人の跡の手前）
TREE = [-71.0, -29.0]         # 石斧で切る木
COVE = [-8.5, 188.7]          # 入り江（漁）
FARM = [-7.0, 99.0]           # 畑
EDGE = [-78.0, -24.0]         # 森の入口
LAND, SEA = [238.0, 147.0], [276.0, 180.0]   # 木箱が着く浜・流れてくる海

groups = [
    {'name': 'beach', 'type': 'ring', 'spot': [236, 124], 'radius': 3.2, 'gap': 2.6, 'members': arrivals[:22]},
    {'name': 'plaza', 'type': 'ring', 'spot': PLAZA, 'radius': 7, 'gap': 2.8, 'members': crowd},
    {'name': 'ws', 'type': 'line', 'spot': [WS[0] + 1.0, WS[1] + 6.5], 'face': [0.3, -0.95], 'gap': 2.4, 'members': [x for x in [AYANE] if inr(x)] + carp[:3] + crowd[:3]},
    {'name': 'cove', 'type': 'shore', 'spot': COVE, 'gap': 2.6, 'members': [x for x in [IBU, RINO] if inr(x)] + fishers[:2]},
    {'name': 'farm', 'type': 'line', 'spot': FARM, 'face': [0.6, 0.8], 'gap': 2.8, 'members': farmers},
    {'name': 'edge', 'type': 'line', 'spot': EDGE, 'face': [0.98, 0.2], 'gap': 2.6, 'members': [x for x in [TSUKI, DAN, NAKA] if inr(x)]},
    {'name': 'pairs', 'type': 'line', 'spot': [15, 36], 'face': [0, 1], 'members': []},  # カメラの向きの基準
    *[{'name': f'pair{k}', 'type': 'line', 'spot': [12.0 + k * 5.5, 36], 'face': [0, 1], 'gap': 1.8, 'members': list(pr)} for k, pr in enumerate(pairs)],
    {'name': 'yura', 'type': 'line', 'spot': YURA_AT, 'face': [0, 1], 'members': [x for x in [YURA] if inr(x)]},
    {'name': 'shore', 'type': 'line', 'spot': [LAND[0] - 9, LAND[1] - 7], 'face': [0.75, 0.66], 'gap': 2.4, 'members': crowd[:12]},
]
G = {g['name']: g for g in groups}
acts = [{'who': '*', 't': 0, 'anim': 'idle', 'face': 'front'}]
A = acts.append
# S0 漂着（0〜3.5）
A({'who': G['beach']['members'], 't': 0, 'at': {'slot': 'beach'}, 'anim': 'sleep'})
A({'who': G['beach']['members'], 't': 1.4, 'anim': 'sit', 'pick': 0.35, 'seed': 5})
A({'who': G['beach']['members'], 't': 2.3, 'anim': 'cheer', 'pick': 0.2, 'seed': 9})
# S2 ゆらさん（6.5〜10.5）：広場のまん中で、みんなに囲まれる
A({'who': crowd, 't': 6.5, 'at': {'slot': 'plaza'}, 'anim': 'idle', 'face': {'at': YURA_AT}})
A({'who': crowd, 't': 8.4, 'anim': 'cheer', 'pick': 0.6, 'seed': 3})
if inr(YURA):
    A({'who': YURA, 't': 6.5, 'at': YURA_AT, 'anim': 'cheer', 'face': 'front'})
    A({'who': YURA, 't': 7.6, 'anim': 'talk'})
# S3 仲良し（10.5〜13.5）：ふたりずつ並んで歩く
for k, pr in enumerate(pairs): A({'who': list(pr), 't': 10.5, 'at': {'slot': f'pair{k}'}, 'anim': 'idle', 'face': 'front'})
A({'who': [x for pr in pairs for x in pr], 't': 12.2, 'anim': 'cheer', 'face': 'front'})
# S5 石の作業場（17.5〜24）
A({'who': G['ws']['members'], 't': 17.5, 'at': {'slot': 'ws'}, 'anim': 'work', 'face': {'at': WS}})
A({'who': G['ws']['members'], 't': 22.4, 'anim': 'cheer', 'face': 'front'})
# S6 道具の効果（24〜34）
A({'who': carp, 't': 24.0, 'at': [[TREE[0] + 2.3, TREE[1] + 0.8], [TREE[0] - 2.0, TREE[1] + 1.6], [TREE[0] + 4.5, TREE[1] + 3.0], [TREE[0] - 4.0, TREE[1] + 3.4], [TREE[0] + 0.4, TREE[1] + 4.6]], 'anim': 'work', 'face': {'at': TREE}})
A({'who': carp, 't': 25.6, 'anim': 'cheer', 'face': 'front'})
A({'who': G['cove']['members'], 't': 27.5, 'at': {'slot': 'cove'}, 'anim': 'work'})
A({'who': G['cove']['members'], 't': 29.4, 'anim': 'cheer', 'face': 'front'})
A({'who': farmers, 't': 31.0, 'at': {'slot': 'farm'}, 'anim': 'work'})
A({'who': farmers, 't': 33.0, 'anim': 'cheer', 'pick': 0.5, 'seed': 2})
# S7 A派・C派（34〜38）
A({'who': G['edge']['members'], 't': 34.0, 'at': {'slot': 'edge'}, 'anim': 'idle', 'face': 'back'})
if inr(TSUKI): A({'who': TSUKI, 't': 34.0, 'anim': 'work', 'face': 'front'})
# S8 夕方、木箱（38〜）
A({'who': G['shore']['members'], 't': 38.0, 'at': {'slot': 'shore'}, 'anim': 'idle', 'face': {'at': SEA}})
A({'who': G['shore']['members'], 't': 41.2, 'anim': 'shock'})
for k, i in enumerate(G['shore']['members']):
    a = 0.4 + k * 0.48
    A({'who': i, 't': 42.6 + (k % 4) * 0.12, 'to': [LAND[0] - 5.5 + 7 * __import__('math').cos(a) * 0.9, LAND[1] - 5.5 + 7 * __import__('math').sin(a) * 0.4], 'dur': 1.4, 'run': True})
    A({'who': i, 't': 44.4, 'anim': 'cheer' if k % 3 == 0 else 'idle', 'face': {'at': LAND}})

camera = [
    {'from': 0, 'to': 3.5, 'hour': 7.5, 'keys': [{'t': 0, 'look': {'rel': 'g:beach'}, 'dist': 24, 'az': 1.1, 'pol': 1.22, 'up': 1.5, 'frame': 'beach'}, {'t': 3.5, 'look': {'rel': 'g:beach'}, 'dist': 20, 'az': 1.2, 'pol': 1.24, 'up': 1.5, 'frame': 'beach'}]},
    {'from': 3.5, 'to': 6.5, 'hour': 11, 'keys': [{'t': 3.5, 'look': [15, 40], 'dist': 760, 'az': 0.5, 'pol': 0.78, 'up': 0, 'frame': 'edge'}, {'t': 6.5, 'look': [15, 40], 'dist': 700, 'az': 0.62, 'pol': 0.8, 'up': 0, 'frame': 'edge'}]},
    {'from': 6.5, 'to': 10.5, 'hour': 12, 'keys': [{'t': 6.5, 'look': YURA_AT, 'dist': 22, 'az': 0.2, 'pol': 1.18, 'up': 2.2, 'frame': 'edge'}, {'t': 10.5, 'look': YURA_AT, 'dist': 12, 'az': 0.28, 'pol': 1.28, 'up': 2.4, 'frame': 'edge'}]},
    {'from': 10.5, 'to': 13.5, 'hour': 13, 'keys': [{'t': 10.5, 'look': [14.0, 36], 'dist': 26, 'az': 0.0, 'pol': 1.25, 'up': 2.0, 'frame': 'pairs'}, {'t': 13.5, 'look': [14.0, 36], 'dist': 24, 'az': 0.03, 'pol': 1.26, 'up': 2.0, 'frame': 'pairs'}]},
    {'from': 13.5, 'to': 17.5, 'hour': 14, 'keys': [{'t': 13.5, 'look': PLAZA, 'dist': 80, 'az': 0.5, 'pol': 0.95, 'up': 0, 'frame': 'edge'}, {'t': 17.5, 'look': PLAZA, 'dist': 70, 'az': 0.6, 'pol': 0.95, 'up': 0, 'frame': 'edge'}]},
    {'from': 17.5, 'to': 24.0, 'hour': 9.0, 'keys': [{'t': 17.5, 'look': WS, 'dist': 26, 'az': 0.1, 'pol': 1.1, 'up': 2.0, 'frame': 'ws'}, {'t': 24.0, 'look': WS, 'dist': 20, 'az': 0.45, 'pol': 1.12, 'up': 2.4, 'frame': 'ws'}]},
    {'from': 24.0, 'to': 27.5, 'hour': 10.0, 'keys': [{'t': 24.0, 'look': [TREE[0], TREE[1] + 2], 'dist': 20, 'az': 3.4, 'pol': 1.2, 'up': 2.5, 'frame': 'edge'}, {'t': 27.5, 'look': [TREE[0], TREE[1] + 2], 'dist': 17, 'az': 3.25, 'pol': 1.18, 'up': 2.5, 'frame': 'edge'}]},
    {'from': 27.5, 'to': 31.0, 'hour': 11.0, 'keys': [{'t': 27.5, 'look': {'rel': 'g:cove'}, 'dist': 16, 'az': 2.6, 'pol': 1.25, 'up': 2.0, 'frame': 'cove'}, {'t': 31.0, 'look': {'rel': 'g:cove'}, 'dist': 14, 'az': 2.7, 'pol': 1.25, 'up': 2.0, 'frame': 'cove'}]},
    {'from': 31.0, 'to': 34.0, 'hour': 12.0, 'keys': [{'t': 31.0, 'look': {'rel': 'g:farm'}, 'dist': 20, 'az': 0.3, 'pol': 1.18, 'up': 2.0, 'frame': 'farm'}, {'t': 34.0, 'look': {'rel': 'g:farm'}, 'dist': 18, 'az': 0.4, 'pol': 1.18, 'up': 2.0, 'frame': 'farm'}]},
    {'from': 34.0, 'to': 38.0, 'hour': 15.5, 'keys': [{'t': 34.0, 'look': {'rel': 'g:edge'}, 'dist': 16, 'az': -0.3, 'pol': 1.25, 'up': 2.2, 'frame': 'edge'}, {'t': 38.0, 'look': {'rel': 'g:edge'}, 'dist': 14, 'az': -0.2, 'pol': 1.25, 'up': 2.2, 'frame': 'edge'}]},
    # 夕方：浜から海を見る → 木箱が寄ってくる → みんな駆け寄る
    {'from': 38.0, 'to': 44.5, 'hour': 17.3, 'keys': [{'t': 38.0, 'look': [LAND[0] + 12, LAND[1] + 10], 'dist': 46, 'az': 3.3, 'pol': 1.12, 'up': 2.0, 'frame': 'shore'}, {'t': 44.5, 'look': LAND, 'dist': 34, 'az': 3.45, 'pol': 1.1, 'up': 3.0, 'frame': 'shore'}]},
    {'from': 44.5, 'to': 54.0, 'hour': 17.6, 'keys': [{'t': 44.5, 'look': LAND, 'dist': 30, 'az': 3.6, 'pol': 1.12, 'up': 3.0, 'frame': 'shore'}, {'t': 54.0, 'look': LAND, 'dist': 36, 'az': 4.0, 'pol': 1.05, 'up': 3.5, 'frame': 'shore'}]},
]
DUR = 57.0
camera.append({'from': 54.0, 'to': DUR, 'hour': 17.8, 'keys': [{'t': 54.0, 'look': [15, 40], 'dist': 700, 'az': 0.8, 'pol': 0.85, 'up': 0, 'frame': 'edge'}, {'t': DUR, 'look': [15, 40], 'dist': 760, 'az': 0.9, 'pol': 0.85, 'up': 0, 'frame': 'edge'}]})

props = [{'type': 'zzz', 'from': {'rel': i, 'up': 1.6, 't': 0.6}, 't0': 0, 't1': 0.01, 't2': 2.4, 'size': 0.9, 'phase': k * 0.3} for k, i in enumerate(G['beach']['members'][:6])]
for k, (a, b) in enumerate(pairs):
    props.append({'type': 'heart', 'from': {'rel': a, 'up': 3.4, 't': 0.85}, 'to': {'rel': a, 'up': 3.4, 't': 0.85}, 't0': 10.6, 't1': 13.0, 't2': 13.4, 'size': 1.4, 'phase': k})
fs = G['cove']['members'][:2]
for k, i in enumerate(fs):
    props.append({'type': 'fish', 'from': {'rel': i, 't': 28.6, 'n': -3.2, 'up': -0.4}, 'to': {'rel': i, 't': 28.6, 'up': 3.2}, 't0': 28.6 + k * 0.3, 't1': 29.2 + k * 0.3, 't2': 31.0, 'arc': 3.0, 'size': 0.9})
    props.append({'type': 'splash', 'from': {'rel': i, 't': 28.6, 'n': -3.2, 'up': -0.2}, 't0': 28.5 + k * 0.3, 't1': 28.51 + k * 0.3, 't2': 29.0 + k * 0.3, 'size': 1.2})
props.append({'type': 'question', 'from': [LAND[0], LAND[1]], 't0': 44.4, 't1': 44.41, 't2': 54.0, 'size': 4})

props3d = [
    {'type': 'build', 'kind': 'workshop', 'at': WS, 'rot': 10, 't0': 18.2, 't1': 22.2, 'show': 17.5, 'hide': 24.0},
    {'type': 'tree', 'at': TREE, 'rot': 200, 'chop': 24.0, 't0': 24.7, 't1': 25.4, 't2': 27.5, 'hide': 27.5, 'size': 1.25},
    {'type': 'float', 'kind': 'bigcrate', 'from': SEA, 'at': LAND, 'rot': 35, 't0': 38.0, 't1': 44.0, 'show': 38.0, 'sink': 2.4},
]

def star(i, a, b, bubble=True):
    if not inr(i): return None
    return {'who': i, 'from': a, 'to': b, **({'bubble': said[i]} if bubble and said.get(i) else {})}
stars = [x for x in [star(YURA, 6.8, 10.4), star(AYANE, 17.6, 21.6), star(TSUKI, 34.1, 36.0), star(DAN, 36.0, 38.0)] if x]
ROWS = [{'key': k, 'label': OPTS[k], 'count': tally[k]} for k in OPTS]
overlay = {
    'banner': 'コメントで動く無人島　5日目',
    'bannerOff': [[0, 6.5], [44.5, DUR]],
    'commenters': commenters,
    'names': {**{i: name_of(i) for i in people}, **{x: name_of(x) for pr in pairs for x in pr}},
    'titles': [{'text': '5日目', 'from': 0.1, 'to': 3.5}],
    'tagAll': [[0.3, 3.5, 0.06]],
    'stars': stars,
    'tagOnly': [{'from': 10.6, 'to': 13.4, 'who': list(pr), 'join': True, 'size': 38} for pr in pairs],
    'tally': {'from': 13.5, 'to': 17.5, 'title': '昨日の質問　昔の住人の跡、どうする？', 'grow': [13.9, 15.4], 'winner': winner, 'winnerAt': 15.8, 'rows': ROWS},
    'images': [
        {'file': 'profile.png', 'from': 3.5, 'to': 5.0, 'w': 900, 'y': 600, 'tap': [0.24, 0.905], 'tapLabel': 'フォローすると…'},
        {'file': 'profile.png', 'from': 5.0, 'to': 6.5, 'w': 900, 'y': 600, 'tap': [0.37, 0.78], 'tapLabel': '島のいまは、ここ'},
        {'file': 'profile.png', 'from': 54.1, 'to': DUR, 'w': 900, 'y': 520, 'tap': [0.37, 0.78], 'tapLabel': 'ここから'},
    ],
    'captions': [
        {'text': f'フォローした{n_arrive}人が、流れ着いた', 'from': 0.4, 'to': 3.5, 'y': 1290, 'size': 66},
        {'text': 'あなたも、次の動画で流れ着きます', 'from': 3.6, 'to': 5.0, 'y': 1400, 'size': 50, 'color': [255, 214, 74]},
        {'text': 'ゆらさん本人から、コメントが！', 'from': 6.6, 'to': 10.4, 'y': 330, 'size': 56, 'color': [255, 214, 74]},
        {'text': 'コメントで友達を@タグ付けすると', 'from': 10.6, 'to': 13.4, 'y': 330, 'size': 52},
        {'text': '島で「仲良し」に', 'from': 10.6, 'to': 13.4, 'y': 420, 'size': 64, 'color': [255, 214, 74]},
        {'text': '漁労長 ibu13さん', 'from': 27.6, 'to': 31.0, 'y': 330, 'size': 52, 'color': [255, 214, 74]},
        {'text': 'その夕方', 'from': 38.0, 'to': 39.6, 'y': 420, 'size': 64, 'color': [255, 214, 74]},
        {'text': '次の質問', 'from': 46.0, 'to': 54.0, 'y': 330, 'size': 64, 'color': [255, 214, 74]},
        {'text': '流れ着いた大きな木箱。', 'from': 46.1, 'to': 54.0, 'y': 450, 'size': 60},
        {'text': '中身はなんだろう？', 'from': 46.1, 'to': 54.0, 'y': 545, 'size': 60},
        {'text': 'A 種と苗', 'from': 47.0, 'to': 54.0, 'y': 760, 'size': 56},
        {'text': 'B 灯台', 'from': 47.6, 'to': 54.0, 'y': 860, 'size': 56},
        {'text': 'C もこもこのひつじ', 'from': 48.2, 'to': 54.0, 'y': 960, 'size': 56},
        {'text': 'D 自由に予想', 'from': 48.8, 'to': 54.0, 'y': 1060, 'size': 56},
        {'text': '一番多い予想が、中身になります', 'from': 49.6, 'to': 54.0, 'y': 1300, 'size': 50, 'color': [255, 214, 74]},
        {'text': 'あなたの島民のいまは、', 'from': 54.2, 'to': DUR, 'y': 1300, 'size': 54},
        {'text': 'プロフィールのリンクから', 'from': 54.2, 'to': DUR, 'y': 1390, 'size': 54},
    ],
    'action': [{'text': '昔の住人の石器をまねて、石を割る', 'from': 17.6, 'to': 22.3}, {'text': '大工：石斧', 'from': 24.1, 'to': 27.5},
               {'text': '漁師：石の銛', 'from': 27.6, 'to': 31.0}, {'text': '農家：石のくわ', 'from': 31.1, 'to': 34.0}],
    'result': [{'text': '石の作業場が、できた！', 'from': 22.4, 'to': 24.0}, {'text': '木が、あっという間に！', 'from': 25.5, 'to': 27.5},
               {'text': '魚が、2匹！', 'from': 29.3, 'to': 31.0}, {'text': '畑も、はかどる', 'from': 32.6, 'to': 34.0},
               {'text': '迷子が出ないように、名簿づくり', 'from': 34.2, 'to': 36.0}, {'text': '森の奥が、気になる…', 'from': 36.1, 'to': 38.0},
               {'text': '海から、大きな木箱！', 'from': 41.4, 'to': 44.4}],
    'smallTagsMax': 5,
}
narr = [
    {'at': 0.3, 'until': 3.5, 'text': f'{n_arrive}人が、流れ着いた！'},
    {'at': 3.6, 'until': 5.0, 'text': 'フォローすると、あなたも。'},
    {'at': 5.1, 'until': 6.5, 'text': '島は、リンクから。'},
    {'at': 6.7, 'until': 10.4, 'text': 'なんと、ゆらさん本人から、コメントが！'},
    {'at': 10.6, 'until': 13.4, 'text': 'タグ付けした二人は、島で仲良しに。'},
    {'at': 13.6, 'until': 17.4, 'text': '昨日の質問。一番多かったのは、石の道具！'},
    {'at': 17.7, 'until': 22.3, 'text': '昔の住人の石器をまねて、石を割る。'},
    {'at': 22.4, 'until': 24.0, 'text': '作業場が、できた！'},
    {'at': 24.1, 'until': 25.5, 'text': '石斧で、木を切る。'},
    {'at': 25.6, 'until': 27.5, 'text': 'あっという間！'},
    {'at': 27.6, 'until': 31.0, 'text': '石の銛で、魚が二匹！'},
    {'at': 31.1, 'until': 34.0, 'text': '石のくわで、畑もはかどる。'},
    {'at': 34.1, 'until': 38.0, 'text': '迷子が出ないように、名簿づくり。森の奥も、気になる。'},
    {'at': 38.1, 'until': 41.3, 'text': 'その夕方。'},
    {'at': 41.4, 'until': 45.8, 'text': '海から、大きな木箱が流れ着いた！'},
    {'at': 46.1, 'until': 54.0, 'text': '中身はなんだろう？エー、種と苗。ビー、灯台。シー、もこもこのひつじ。ディー、自由に予想。'},
    {'at': 54.2, 'until': DUR, 'text': 'あなたの島民のいまは、プロフィールのリンクから。'},
]
EXIST = [
    {'id': 'ruins-1', 'type': 'ruins', 'name': '昔の住人の跡', 'x': -44.7, 'z': -12.7, 'rot': 0, 'builtDay': 1},
    {'id': 'hut-1', 'type': 'hut', 'name': 'はじまりの小屋', 'x': -20, 'z': -5, 'rot': 20, 'builtDay': 4},
]
story = {
    'title': '5日目', 'roster': ROSTER_REL, 'day': DAY, 'fps': 24, 'duration': DUR, 'hour': 10,
    'baseTime': '2026-11-21T09:00:00+09:00', 'base': {'name': '中央の広場', 'x': 0, 'z': 5, 'decidedDay': 2},
    'forestRoad': {'points': [[-74, -22], [-128, -34]], 'need': 300, 'startDay': 4, 'label': '光の場所', 'open': True},
    'toolAge': 'stone',
    'buildings': EXIST,
    'cast': list(dict.fromkeys([x for x in commenters] + [x for pr in pairs for x in pr] + crowd + carp + fishers + farmers + arrivals[:22])),
    'groups': groups, 'acts': acts, 'props': props, 'props3d': props3d, 'camera': camera,
    'overlay': overlay, 'override': {},
    'audio': {'narration': narr, 'bgm': {'volume': 0.18}, 'speed': 1.15},
    'cover': {'at': 45.0, 'day': f'{DAY}日目', 'lines': ['石の道具ができた', '海から、大きな木箱が…']},
}
json.dump(story, open(os.path.join(HERE, 'story', 'ep5.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

# ---- PWA の続き（きょうの行動）と、Firebase の state に入れる差分 ----
# 座標：buildings の x・z は旧単位（ワールド ÷ 3）。today の spot は pwa_patch.py の SPOTS
CRATE_OLD = [round(LAND[0] / 3, 1), round(LAND[1] / 3, 1)]
WS_OLD = [round(WS[0] / 3, 1), round(WS[1] / 3, 1)]
today = []
def td(i, spot, anim, text, tool=None):
    if inr(i): today.append({'id': i, 'spot': spot, 'anim': anim, 'text': text, **({'tool': tool} if tool else {})})
td(YURA, 'plaza', 'talk', '「行方がわからなかったゆらさんです！」と、みんなにあいさつしている')
td(IBU, 'cove', 'work', '漁労長として、石の銛で漁をしている', 'rod')
td(RINO, 'cove', 'work', '石の銛で漁をしながら、武器にできないか考えている', 'rod')
td(AYANE, 'forestEdge', 'work', '石の作業場で、チームごとの道具を作っている', 'hammer')
td(TSUKI, 'plaza', 'work', '迷子が出ないように、島民の名簿を作っている')
td(DAN, 'forestEdge', 'idle', '森の奥の、昔の住人の行方が気になっている', 'scope')
td(NAKA, 'forestEdge', 'idle', '斥候として、森の奥をのぞいている', 'scope')
pwa = {'day': DAY, 'roster': ROSTER_REL, 'today': today, 'missing': {}}
json.dump(pwa, open(os.path.join(HERE, 'story', 'ep5_pwa.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
state = {
    'day': DAY,
    'toolAge': 'stone',
    'buildings_add': [
        {'id': 'workshop-1', 'type': 'workshop', 'name': '石の作業場', 'x': WS_OLD[0], 'z': WS_OLD[1], 'rot': 10, 'builtDay': DAY, 'note': '昔の住人の跡にあった石器をまねて、石を割って道具を作る場所。'},
        {'id': 'crate-1', 'type': 'bigcrate', 'name': '大きな木箱', 'x': CRATE_OLD[0], 'z': CRATE_OLD[1], 'rot': 35, 'builtDay': DAY,
         'note': '海から流れ着いた、大きな木箱。中身はなんだろう？ 予想はInstagramのコメントで（A 種と苗／B 灯台／C もこもこのひつじ／D 自由に予想）。一番多い予想が中身になります。'},
    ],
    'chronicle_add': {'day': DAY, 'title': '石の道具ができた。海から大きな木箱', 'text': '昔の住人の跡にあった石器をまねて、石の作業場で道具を作った。石斧・石の銛・石のくわで、仕事がはかどる。夕方、海から大きな木箱が流れ着いた。',
                      'vote': {'question': '森の奥の、昔の住人の跡。どうする？', 'adopted': OPTS[winner], 'note': '　'.join(f'{k} {tally[k]}件' for k in OPTS)}},
    'currentVote': {'id': 'vote-005-crate', 'status': 'open', 'question': '流れ着いた大きな木箱。中身はなんだろう？',
                    'description': 'A・B・C・D でコメントしてね。一番多い予想が中身になります（Dが一番多いときは、Dの中でいいねが一番多い予想）',
                    'options': [{'key': 'A', 'label': '種と苗'}, {'key': 'B', 'label': '灯台'}, {'key': 'C', 'label': 'もこもこのひつじ'}, {'key': 'D', 'label': '自由に予想'}]},
}
json.dump(state, open(os.path.join(HERE, 'story', 'ep5_state.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
rec = {'fetchedAt': C.get('fetchedAt'), 'tally': tally, 'winner': winner, 'votes': {name_of(i): p['vote'] for i, p in people.items()}}
json.dump(rec, open(os.path.join(HERE, 'story', 'ep5_tally.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(json.dumps({'arrivals': n_arrive, 'tally': tally, 'winner': winner, 'pairs': [(name_of(a), name_of(b)) for a, b in pairs], 'cast': len(story['cast']), 'today': len(today)}, ensure_ascii=False))
