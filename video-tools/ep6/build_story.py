#!/usr/bin/env python3
"""6日目の台本を組み立てる（約61秒）。カメラは大げさに（本人の指示：フォロワーの反応を見たい）。
  python3 video-tools/ep6/build_story.py
入力：ep6/input/comments.json（5日目の投稿のコメント。スクショ補完分もそのまま採用）・ep6/input/islanders.json（名簿。6日目の漂着は joinedDay=6、仲良しは relationships）
      試すときは COMMENTS=… ROSTER=… で差し替え
出力：ep6/story/ep6.json（台本）・ep6_pwa.json（PWA の続き）・ep6_state.json（Firebase の state 差分）・ep6_tally.json

流れ（2026-11-22 本人と確定）
  漂着 → リンク → 仲良し（ざーふさんの輪＋ペア）→ 集計（A 種と苗）→ 木箱が開いて種と苗 → 森を1/3切りひらく
  → くわ・釣り竿・のこぎり → 巨大な畑に植える（PWA で2日かけて育つ）→ 夕方のたき火
  → 森からクマ！島民を追いかけまわす → 次の問い「クマが現れた！どうする？」
"""
import json, os, re, math

HERE = os.path.dirname(os.path.abspath(__file__))
os.makedirs(os.path.join(HERE, 'story'), exist_ok=True)
C = json.load(open(os.environ.get('COMMENTS') or os.path.join(HERE, 'input', 'comments.json'), encoding='utf-8'))
ROSTER_PATH = os.path.abspath(os.environ.get('ROSTER') or os.path.join(HERE, 'input', 'islanders.json'))
ROSTER_REL = os.path.relpath(ROSTER_PATH, os.path.join(HERE, 'story'))
R = json.load(open(ROSTER_PATH, encoding='utf-8'))
ROSTER = {p['id']: p for p in R['islanders']}
PREV = {p['id']: p for p in json.load(open(os.path.join(HERE, '..', 'ep5', 'input', 'islanders.json'), encoding='utf-8'))['islanders']}
DAY = 6
inr = lambda i: bool(i) and i in ROSTER

# ---- 集計（1人1票・最後の投票コメント。@タグの文字は数えない） ----
OPTS = {'A': '種と苗', 'B': '灯台', 'C': 'もこもこのひつじ', 'D': '自由に予想'}
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
said = {}
for c in sorted(cm, key=lambda c: c.get('at') or ''):
    if vote_of(c.get('text')) or c['userId'] not in said: said[c['userId']] = (c.get('text') or '').strip()
def name_of(i):
    n = (people.get(i, {}).get('name') or '').strip() or ROSTER.get(i, {}).get('name') or i
    ok = sum(1 for ch in n if ch.isascii() and ch.isalnum() or '぀' <= ch <= 'ヿ' or '一' <= ch <= '鿿')
    return n if ok >= max(1, len(n) // 2) else i
commenters = {i: (p['vote'] or '-') for i, p in people.items() if inr(i)}
def bit(i, n=24):  # コメントの一部（吹き出し用）
    t = said.get(i, '').split('\n')[0].strip()
    return t if len(t) <= n else t[:n - 1] + '…'

# ---- 仲良し：今回あたらしく増えた関係（5日目の名簿に無いもの） ----
edges = set()
for p in R['islanders']:
    for r in p.get('relationships') or []:
        if r.get('type') != 'friend' or not inr(r.get('id')): continue
        a, b = sorted([p['id'], r['id']])
        old = {x.get('id') for x in (PREV.get(a, {}).get('relationships') or [])}
        if b not in old: edges.add((a, b))
deg = {}
for a, b in edges: deg[a] = deg.get(a, 0) + 1; deg[b] = deg.get(b, 0) + 1
hub = max(deg, key=lambda k: (deg[k], k)) if deg and max(deg.values()) >= 2 else None
hub_friends = sorted([b if a == hub else a for a, b in edges if hub in (a, b)])[:4] if hub else []
pairs = [e for e in sorted(edges) if hub not in e][:2]

arrivals = [p['id'] for p in R['islanders'] if int(p.get('joinedDay', 0)) == DAY]
n_arrive = len(arrivals)
TSUKI, YURI, RINO, HERO, MA, DAICHI, AYANE, DENZI, YURA = 'tsuki5747', 'yuridazo68', 'rino._.15', 'heroruto7', 'marumegane4', 'fuse.daichi', 'analogayane', 'denzirouu', 'yuradayo0330'
special = set(hub_friends) | {hub} | {x for e in pairs for x in e} | {TSUKI, YURI, RINO}
older = [p for p in R['islanders'] if int(p.get('joinedDay', 0)) < DAY and p['id'] not in special]
by_job = lambda j, n, skip=(): [p['id'] for p in older if p.get('job') == j and p['id'] not in skip][:n]
carp = by_job('大工', 6)
farmers = by_job('農家', 6)
crowd = [p['id'] for p in older if p['id'] not in set(carp) | set(farmers)][:18]
campers = [x for x in [TSUKI, YURI] if inr(x)] + crowd[:6]

# ---- 場所（ワールド座標） ----
LAND = [238.0, 147.0]                 # 木箱のある浜
PLAZA = [15.0, 36.0]                  # 仲良しの場面
FIELD = [-104.0, -2.0]                # 巨大な畑（26×18）
CLEAR = {'x0': -132, 'x1': -86, 'z0': -62, 'z1': 22}   # 森を切りひらく範囲（森の東の1/3）
FIRE = [-104.0, 18.0]                 # 夕方のたき火（畑の南）
DEN = [-140.0, 15.0]                  # クマが出てくる森の暗がり
RC, RR = FIRE, 8.0                    # 追いかけっこの輪

groups = [
    {'name': 'beach', 'type': 'ring', 'spot': [236, 124], 'radius': 3.2, 'gap': 2.6, 'members': arrivals[:22]},
    {'name': 'star', 'type': 'line', 'spot': PLAZA, 'face': [0, 1], 'gap': 2.0, 'members': ([hub] if hub else []) + hub_friends},
    *[{'name': f'pair{k}', 'type': 'line', 'spot': [PLAZA[0] - 14 + k * 5.5, PLAZA[1] + 10], 'face': [0, 1], 'gap': 1.8, 'members': list(e)} for k, e in enumerate(pairs)],
    {'name': 'pairs', 'type': 'line', 'spot': [PLAZA[0] - 11, PLAZA[1] + 10], 'face': [0, 1], 'members': []},
    {'name': 'plaza', 'type': 'ring', 'spot': [0, 15], 'radius': 7, 'gap': 2.8, 'members': crowd},
    {'name': 'crate', 'type': 'ring', 'spot': LAND, 'radius': 7.5, 'gap': 2.4, 'members': crowd[:12] + [x for x in [MA, DAICHI, AYANE, HERO] if inr(x)]},
    {'name': 'carp', 'type': 'line', 'spot': [-112, 12], 'face': [0, -1], 'gap': 3.0, 'members': carp},
    {'name': 'farm', 'type': 'line', 'spot': [FIELD[0], FIELD[1] + 11.5], 'face': [0, -1], 'gap': 3.2, 'members': farmers + [x for x in [RINO] if inr(x)]},
    {'name': 'fire', 'type': 'ring', 'spot': FIRE, 'radius': 3.4, 'gap': 2.2, 'members': campers},
    {'name': 'south', 'type': 'line', 'spot': FIRE, 'face': [0, 1], 'members': []},
]
G = {g['name']: g for g in groups}
acts = [{'who': '*', 't': 0, 'anim': 'idle', 'face': 'front'}]
A = acts.append
# S0 漂着
if arrivals:
    A({'who': G['beach']['members'], 't': 0, 'at': {'slot': 'beach'}, 'anim': 'sleep'})
    A({'who': G['beach']['members'], 't': 1.3, 'anim': 'sit', 'pick': 0.35, 'seed': 6})
    A({'who': G['beach']['members'], 't': 2.2, 'anim': 'cheer', 'pick': 0.25, 'seed': 2})
# S2 仲良し（6〜11.5）：輪の真ん中にハブの人
if hub:
    A({'who': hub, 't': 6.0, 'at': PLAZA, 'anim': 'cheer', 'face': 'front'})
    for k, f in enumerate(hub_friends):
        a = math.pi * (0.15 + 0.7 * k / max(1, len(hub_friends) - 1))
        A({'who': f, 't': 6.0, 'at': [PLAZA[0] + 3.2 * math.cos(a), PLAZA[1] - 3.2 * math.sin(a) + 0.6], 'to': [PLAZA[0] + 2.2 * math.cos(a), PLAZA[1] - 2.2 * math.sin(a) + 0.6], 'dur': 0.8, 'run': True})
        A({'who': f, 't': 7.0 + k * 0.15, 'anim': 'cheer', 'face': 'front'})
for k, e in enumerate(pairs):
    A({'who': list(e), 't': 9.4, 'at': {'slot': f'pair{k}'}, 'anim': 'cheer', 'face': 'front'})
# S3 集計（11.5〜14.5）：広場
A({'who': crowd, 't': 11.5, 'at': {'slot': 'plaza'}, 'anim': 'idle', 'face': {'at': [0, 15]}})
# S4 木箱（14.5〜20）
A({'who': G['crate']['members'], 't': 14.5, 'at': {'slot': 'crate'}, 'anim': 'idle', 'face': {'at': LAND}})
A({'who': G['crate']['members'], 't': 15.7, 'anim': 'shock'})
A({'who': G['crate']['members'], 't': 16.4, 'anim': 'cheer', 'pick': 0.7, 'seed': 5})
# S5 森を切る（20〜27）
TREES = []
for j in range(5):
    for i in range(7):
        x = CLEAR['x0'] + 4 + i * 6.6 + (j % 2) * 2.4
        z = CLEAR['z0'] + 6 + j * 15.5
        if FIELD[0] - 15 < x < FIELD[0] + 15 and FIELD[1] - 11 < z < FIELD[1] + 11: continue
        TREES.append([round(x, 1), round(z, 1)])
A({'who': carp, 't': 20.0, 'at': {'slot': 'carp'}, 'anim': 'work', 'face': 'back'})
A({'who': carp, 't': 25.8, 'anim': 'cheer', 'face': 'front'})
# S6 道具（27〜31）
A({'who': carp, 't': 27.0, 'anim': 'cheer', 'face': 'front'})
# S7 畑（31〜37）
A({'who': G['farm']['members'], 't': 31.0, 'at': {'slot': 'farm'}, 'anim': 'work', 'face': 'back'})
A({'who': G['farm']['members'], 't': 35.6, 'anim': 'cheer', 'face': 'front'})
# S8 たき火（37〜40.5）
A({'who': campers, 't': 37.0, 'at': {'slot': 'fire'}, 'anim': 'sit', 'face': {'at': FIRE}})
for x in [TSUKI, YURI]:
    if inr(x): A({'who': x, 't': 37.2, 'anim': 'talk'})
# S9 クマ（40.5〜52）
A({'who': campers, 't': 41.0, 'anim': 'idle', 'face': {'at': DEN}})
A({'who': campers, 't': 42.6, 'anim': 'shock', 'face': {'at': DEN}})
W = 1.15  # 追いかけっこの角速度
def ring(th, r): return [round(RC[0] + math.cos(th) * r, 2), round(RC[1] + math.sin(th) * r * 0.8, 2)]
TH0 = math.pi  # クマは西（森）側から
for k, i in enumerate(campers):
    off = 0.8 + k * 0.5; rr = RR + ((k % 3) - 1) * 1.5
    A({'who': i, 't': 43.2 + k * 0.05, 'to': ring(TH0 - off, rr), 'dur': 0.5, 'run': True})
    t = 43.7
    while t < 52.0:
        if 47.0 <= t < 48.4:  # クマが立ち上がる間は、少し離れて振り返る
            A({'who': i, 't': round(t, 2), 'anim': 'shock', 'face': {'at': ring(TH0 - W * (47.0 - 43.4), RR)}}); t = 48.4; continue
        th = TH0 - off - W * (t - 43.7)
        A({'who': i, 't': round(t, 2), 'to': ring(th - W * 0.3, rr), 'dur': 0.3, 'run': True})
        t += 0.3

# クマの道すじ
def bear_at(t):
    if t < 42.4: return DEN
    if t < 43.4:
        u = (t - 42.4) / 1.0
        e = ring(TH0, RR)
        return [DEN[0] + (e[0] - DEN[0]) * u, DEN[1] + (e[1] - DEN[1]) * u]
    tt = min(t, 47.0) - 43.4 + max(0, t - 48.3)  # 47.0〜48.3 は立ち止まる
    return ring(TH0 - W * tt, RR)
BPATH = []
t = 40.0
while t <= 52.0001:
    p = bear_at(t); BPATH.append([round(t, 2), round(p[0], 2), round(p[1], 2)]); t += 0.1

# ---- カメラ（大げさに）：寄る・引く・回る・振り向く、を短く切りかえる ----
def bear_heading(t):
    a, b = bear_at(t), bear_at(t + 0.15)
    return math.atan2(b[0] - a[0], b[1] - a[1])  # 進む向き（az の向きで）
def chase_key(t, dist=22, pol=1.0, ahead=7.0, fov=46):
    p = bear_at(t); h = bear_heading(t)
    look = [p[0] + math.sin(h) * ahead, p[1] + math.cos(h) * ahead]
    return {'t': t, 'look': [round(look[0], 2), round(look[1], 2)], 'dist': dist, 'az': round(h + math.pi, 3), 'pol': pol, 'up': 2.0, 'fov': fov, 'frame': 'south'}
def unwrap(keys):  # az が ±π をまたいでも、カメラがぐるっと回らないように
    for a, b in zip(keys, keys[1:]):
        while b['az'] - a['az'] > math.pi: b['az'] -= 2 * math.pi
        while b['az'] - a['az'] < -math.pi: b['az'] += 2 * math.pi
    return keys
camera = [
    # 漂着：真上から一気に降りてくる
    {'from': 0, 'to': 3.0, 'hour': 7.5, 'keys': [{'t': 0, 'look': {'rel': 'g:beach'}, 'dist': 70, 'az': 0.4, 'pol': 0.35, 'up': 1.5, 'frame': 'beach'}, {'t': 1.4, 'look': {'rel': 'g:beach'}, 'dist': 26, 'az': 1.0, 'pol': 1.0, 'up': 1.5, 'frame': 'beach'}, {'t': 3.0, 'look': {'rel': 'g:beach'}, 'dist': 17, 'az': 1.35, 'pol': 1.25, 'up': 1.5, 'frame': 'beach'}]},
    {'from': 3.0, 'to': 6.0, 'hour': 11, 'keys': [{'t': 3.0, 'look': [15, 40], 'dist': 900, 'az': 0.2, 'pol': 0.7, 'up': 0, 'frame': 'beach'}, {'t': 6.0, 'look': [15, 40], 'dist': 620, 'az': 0.9, 'pol': 0.85, 'up': 0, 'frame': 'beach'}]},
    # 仲良し：輪の真上から → ぐるっと回りこんで正面へ → ペアへ振る
    {'from': 6.0, 'to': 9.4, 'hour': 12, 'keys': [{'t': 6.0, 'look': PLAZA, 'dist': 22, 'az': -1.2, 'pol': 0.3, 'up': 1.5, 'frame': 'star', 'fov': 50}, {'t': 7.6, 'look': PLAZA, 'dist': 14, 'az': -0.4, 'pol': 1.0, 'up': 2.0, 'frame': 'star', 'fov': 42}, {'t': 9.4, 'look': PLAZA, 'dist': 11, 'az': 0.15, 'pol': 1.3, 'up': 2.2, 'frame': 'star', 'fov': 38}]},
    {'from': 9.4, 'to': 11.5, 'hour': 12.5, 'keys': [{'t': 9.4, 'look': {'rel': 'g:pairs'}, 'dist': 28, 'az': 0.9, 'pol': 1.15, 'up': 2.0, 'frame': 'pairs'}, {'t': 11.5, 'look': {'rel': 'g:pairs'}, 'dist': 21, 'az': 0.0, 'pol': 1.25, 'up': 2.0, 'frame': 'pairs'}]},
    {'from': 11.5, 'to': 14.5, 'hour': 13, 'keys': [{'t': 11.5, 'look': [0, 15], 'dist': 60, 'az': 0.0, 'pol': 0.8, 'up': 0, 'frame': 'star'}, {'t': 14.5, 'look': [0, 15], 'dist': 80, 'az': 1.0, 'pol': 0.95, 'up': 0, 'frame': 'star'}]},
    # 木箱：遠くから一気に寄って、ふたが飛ぶ瞬間にぐっとズーム
    {'from': 14.5, 'to': 20.0, 'hour': 9, 'shake': [[15.6, 16.3, 0.8]], 'keys': [{'t': 14.5, 'look': LAND, 'dist': 60, 'az': 3.2, 'pol': 0.85, 'up': 2.0, 'frame': 'south', 'fov': 46}, {'t': 15.5, 'look': LAND, 'dist': 22, 'az': 3.5, 'pol': 1.12, 'up': 3.0, 'frame': 'south', 'fov': 40}, {'t': 16.1, 'look': LAND, 'dist': 21, 'az': 3.55, 'pol': 1.05, 'up': 4.0, 'frame': 'south', 'fov': 34}, {'t': 20.0, 'look': LAND, 'dist': 30, 'az': 4.3, 'pol': 1.0, 'up': 3.0, 'frame': 'south', 'fov': 40}]},
    # 森を切る：森の上をすべるように飛び、ぐるっと回って全体を見せる
    {'from': 20.0, 'to': 27.0, 'hour': 10, 'shake': [[21.0, 21.6, 0.5], [23.0, 23.6, 0.5], [24.8, 25.4, 0.6]], 'keys': [{'t': 20.0, 'look': [-112, 10], 'dist': 14, 'az': 0.3, 'pol': 1.3, 'up': 3, 'frame': 'south', 'fov': 44}, {'t': 22.0, 'look': [-112, -10], 'dist': 45, 'az': 0.0, 'pol': 0.95, 'up': 2, 'frame': 'south'}, {'t': 24.5, 'look': [-109, -20], 'dist': 95, 'az': -0.9, 'pol': 0.7, 'up': 0, 'frame': 'south'}, {'t': 27.0, 'look': [-109, -20], 'dist': 120, 'az': -1.6, 'pol': 0.55, 'up': 0, 'frame': 'south'}]},
    # 道具：真下から見上げる
    {'from': 27.0, 'to': 31.0, 'hour': 11, 'shake': [[27.4, 27.8, 0.4], [27.9, 28.3, 0.4], [28.4, 28.8, 0.4]], 'keys': [{'t': 27.0, 'look': [-112, 12], 'dist': 26, 'az': 0.9, 'pol': 1.15, 'up': 4.0, 'frame': 'south', 'fov': 50}, {'t': 28.0, 'look': [-112, 12], 'dist': 18, 'az': 0.1, 'pol': 1.25, 'up': 5.0, 'frame': 'south', 'fov': 40}, {'t': 31.0, 'look': [-112, 12], 'dist': 16, 'az': -0.3, 'pol': 1.25, 'up': 5.0, 'frame': 'south', 'fov': 36}]},
    # 畑：畑のまわりを大きく一周しながら上がっていく
    {'from': 31.0, 'to': 37.0, 'hour': 13, 'keys': [{'t': 31.0, 'look': FIELD, 'dist': 26, 'az': -0.8, 'pol': 1.2, 'up': 1, 'frame': 'south'}, {'t': 34.0, 'look': FIELD, 'dist': 40, 'az': 0.8, 'pol': 0.95, 'up': 1, 'frame': 'south'}, {'t': 37.0, 'look': FIELD, 'dist': 58, 'az': 2.2, 'pol': 0.75, 'up': 0, 'frame': 'south'}]},
    {'from': 37.0, 'to': 40.5, 'hour': 18.2, 'keys': [{'t': 37.0, 'look': FIRE, 'dist': 13, 'az': 0.3, 'pol': 1.22, 'up': 2, 'frame': 'south'}, {'t': 40.5, 'look': FIRE, 'dist': 10, 'az': 0.0, 'pol': 1.25, 'up': 2, 'frame': 'south'}]},
    # クマ：暗がりへじわじわ寄る → 飛び出す（大ゆれ）
    {'from': 40.5, 'to': 42.4, 'hour': 19.3, 'keys': [{'t': 40.5, 'look': [DEN[0] + 6, DEN[1]], 'dist': 26, 'az': 1.45, 'pol': 1.3, 'up': 2.5, 'frame': 'south', 'fov': 40}, {'t': 42.4, 'look': [DEN[0] + 2, DEN[1]], 'dist': 12, 'az': 1.5, 'pol': 1.32, 'up': 2.5, 'frame': 'south', 'fov': 30}]},
    {'from': 42.4, 'to': 43.6, 'hour': 19.3, 'shake': [[42.4, 43.6, 1.6]], 'keys': [{'t': 42.4, 'look': [DEN[0] + 4, DEN[1]], 'dist': 16, 'az': 1.6, 'pol': 1.3, 'up': 2.5, 'frame': 'south', 'fov': 50}, {'t': 43.6, 'look': ring(TH0, RR), 'dist': 20, 'az': 1.1, 'pol': 1.2, 'up': 2, 'frame': 'south', 'fov': 50}]},
    # 後ろから低く追いかける
    {'from': 43.6, 'to': 47.0, 'hour': 19.3, 'keys': unwrap([chase_key(43.6 + k * 0.4) for k in range(9)] + [chase_key(47.0)])},
    # 立ち上がって吠える：顔にぐっと寄る
    {'from': 47.0, 'to': 48.4, 'hour': 19.3, 'shake': [[47.4, 48.4, 1.2]], 'keys': [{'t': 47.0, 'look': bear_at(47.0), 'dist': 26, 'az': bear_heading(46.9) + 2.2, 'pol': 1.2, 'up': 3.0, 'frame': 'south', 'fov': 44}, {'t': 47.6, 'look': bear_at(47.0), 'dist': 18, 'az': bear_heading(46.9) + 1.65, 'pol': 1.28, 'up': 4.0, 'frame': 'south', 'fov': 36}, {'t': 48.4, 'look': bear_at(47.0), 'dist': 16, 'az': bear_heading(46.9) + 1.55, 'pol': 1.3, 'up': 4.2, 'frame': 'south', 'fov': 32}]},
    # 一気に上空へ：畑のまわりをぐるぐる追いかけまわしている
    {'from': 48.4, 'to': 52.0, 'hour': 19.0, 'keys': [{'t': 48.4, 'look': RC, 'dist': 18, 'az': 0.4, 'pol': 1.2, 'up': 2, 'frame': 'south', 'fov': 44}, {'t': 49.6, 'look': RC, 'dist': 42, 'az': 1.4, 'pol': 0.75, 'up': 0, 'frame': 'south', 'fov': 40}, {'t': 52.0, 'look': RC, 'dist': 52, 'az': 2.6, 'pol': 0.6, 'up': 0, 'frame': 'south', 'fov': 40}]},
    {'from': 52.0, 'to': 58.0, 'hour': 19.0, 'keys': [{'t': 52.0, 'look': RC, 'dist': 30, 'az': 2.8, 'pol': 0.95, 'up': 1, 'frame': 'south'}, {'t': 58.0, 'look': RC, 'dist': 40, 'az': 3.6, 'pol': 0.9, 'up': 1, 'frame': 'south'}]},
]
DUR = 61.0
camera.append({'from': 58.0, 'to': DUR, 'hour': 18.5, 'keys': [{'t': 58.0, 'look': [15, 40], 'dist': 700, 'az': 0.8, 'pol': 0.85, 'up': 0, 'frame': 'beach'}, {'t': DUR, 'look': [15, 40], 'dist': 780, 'az': 1.0, 'pol': 0.85, 'up': 0, 'frame': 'beach'}]})

props = [{'type': 'zzz', 'from': {'rel': i, 'up': 1.6}, 't0': 0, 't1': 0.01, 't2': 2.2, 'size': 0.9, 'phase': k * 0.3} for k, i in enumerate(G['beach']['members'][:6])]
for k, f in enumerate(hub_friends):
    props.append({'type': 'heart', 'from': {'rel': f, 'up': 3.4}, 'to': {'rel': f, 'up': 3.4}, 't0': 7.2 + k * 0.2, 't1': 9.3, 't2': 9.3, 'size': 1.4, 'phase': k})
for k, e in enumerate(pairs):
    props.append({'type': 'heart', 'from': {'rel': e[0], 'up': 3.4, 't': 0.9}, 'to': {'rel': e[0], 'up': 3.4, 't': 0.9}, 't0': 9.6, 't1': 11.4, 't2': 11.4, 'size': 1.4, 'phase': k})
# 木箱の手前の板がパタリと倒れて、種と苗がドバーっと流れ出す（カメラ側へ扇形に）
CROT = 20  # 木箱の向き（手前の板がカメラを向く）
fdx, fdz = -math.sin(math.radians(CROT)), -math.cos(math.radians(CROT))
pdx, pdz = -fdz, fdx
for k in range(24):
    r = 3.5 + ((k * 7) % 11) * 0.55
    side = (((k * 5) % 9) - 4) * 0.9
    props.append({'type': 'sack' if k % 4 == 0 else 'sprout', 'from': {'xz': [LAND[0] + fdx * 2.4, LAND[1] + fdz * 2.4], 'up': 1.2 + (k % 3) * 0.8},
                  'to': [round(LAND[0] + fdx * r + pdx * side, 2), round(LAND[1] + fdz * r + pdz * side, 2)],
                  't0': 15.75 + k * 0.045, 't1': 16.35 + k * 0.045, 't2': 20.0, 'arc': 1.2 + (k % 4) * 0.5, 'size': 1.1 if k % 4 else 1.0})
# 道具：真ん中に浮かぶ
for k, (tp, dx, sz) in enumerate([('hoe', -4.2, 3.0), ('rod', 0, 2.8), ('saw', 4.2, 1.4)]):
    props.append({'type': tp, 'from': {'xz': [-112 + dx, 12], 'up': 3}, 'to': {'xz': [-112 + dx, 12], 'up': 5.2}, 'arc': 2, 't0': 27.4 + k * 0.5, 't1': 28.2 + k * 0.5, 't2': 31.0, 'size': sz})
props += [
    {'type': 'flame', 'from': FIRE, 't0': 37.0, 't1': 37.01, 't2': 52.0, 'size': 1.8},
    {'type': 'eyes', 'from': {'xz': DEN, 'up': 2.8}, 'to': {'xz': DEN, 'up': 2.8}, 't0': 40.6, 't1': 42.4, 't2': 42.4, 'size': 0.5},
]
props3d = [
    {'type': 'crateopen', 'at': LAND, 'rot': CROT, 't0': 15.6, 'show': 14.5, 'hide': 20.0},
    *[{'type': 'tree', 'at': p, 'rot': 150 + (k * 37) % 80, 'chop': 20.0 + (k % 7) * 0.7, 't0': 20.6 + (k % 7) * 0.75, 't1': 21.3 + (k % 7) * 0.75, 't2': 27.0, 'hide': 27.0, 'size': 1.25} for k, p in enumerate(TREES)],
    {'type': 'logs', 'at': [-116, 16], 'rot': 20, 'count': 5, 't0': 24.5, 't1': 26.5, 'show': 20.0, 'hide': 31.0},
    {'type': 'build', 'kind': 'bigfield0', 'at': FIELD, 'rot': 0, 't0': 31.4, 't1': 35.4, 'show': 31.0},
    {'type': 'tree', 'at': [DEN[0] + 3, DEN[1] - 2.5], 'rot': 270, 'chop': 41.8, 't0': 42.4, 't1': 42.9, 'size': 1.3},
    {'type': 'beast', 'at': DEN, 'path': BPATH, 'show': 42.3, 't0': 40.0, 't1': 52.0, 'rear': [[47.1, 48.3]]},
]

def star(i, a, b, text=None):
    if not inr(i): return None
    t = text if text is not None else bit(i)
    return {'who': i, 'from': a, 'to': b, **({'bubble': t} if t else {})}
stars = [x for x in [star(hub, 6.2, 9.3, bit(hub)) if hub else None, star(TSUKI, 37.2, 38.9, 'みんなでキャンプファイヤーしながらご飯！'), star(YURI, 38.9, 40.5, '料理人だから、ご飯作りたーい！')] if x]
wish = [(HERO, '小麦'), (MA, '大豆とさつまいも'), (DAICHI, '服の材料になる種'), (AYANE, '果物の苗')]
wish = [(i, w) for i, w in wish if inr(i)]
ROWS = [{'key': k, 'label': OPTS[k], 'count': tally[k]} for k in OPTS]
overlay = {
    'banner': 'コメントで動く無人島　6日目',
    'bannerOff': [[0, 6.0], [52.0, DUR]],
    'commenters': commenters,
    'names': {**{i: name_of(i) for i in people}, **{x: name_of(x) for e in edges for x in e}},
    'titles': [{'text': '6日目', 'from': 0.1, 'to': 3.0}],
    'tagAll': [[0.3, 3.0, 0.08]] if arrivals else [],
    'tagOnly': [{'from': 7.0, 'to': 9.3, 'who': hub_friends, 'below': True, 'size': 34}] + [{'from': 9.6, 'to': 11.4, 'who': list(e), 'join': True, 'size': 36} for e in pairs],
    'stars': stars,
    'tally': {'from': 11.5, 'to': 14.5, 'title': '昨日の質問　木箱の中身は？', 'grow': [11.8, 13.0], 'winner': winner, 'winnerAt': 13.3, 'rows': ROWS},
    'images': [
        {'file': 'profile.png', 'from': 3.0, 'to': 4.5, 'w': 900, 'y': 600, 'tap': [0.24, 0.905], 'tapLabel': 'フォローすると…'},
        {'file': 'profile.png', 'from': 4.5, 'to': 6.0, 'w': 900, 'y': 600, 'tap': [0.37, 0.78], 'tapLabel': '島のいまは、ここ'},
        {'file': 'profile.png', 'from': 58.1, 'to': DUR, 'w': 900, 'y': 520, 'tap': [0.37, 0.78], 'tapLabel': 'ここから'},
    ],
    'captions': [
        {'text': f'フォローした{n_arrive}人が、流れ着いた' if n_arrive else '6日目の朝', 'from': 0.4, 'to': 3.0, 'y': 1290, 'size': 66},
        {'text': 'あなたも、次の動画で流れ着きます', 'from': 3.1, 'to': 4.5, 'y': 1400, 'size': 50, 'color': [255, 214, 74]},
        *([{'text': f'「誰か仲良くなろう」♥{people.get(hub, {}).get("likes", 0)}', 'from': 6.2, 'to': 9.3, 'y': 330, 'size': 50, 'color': [255, 214, 74]},
           {'text': f'{name_of(hub)}さん、{len(hub_friends)}人と仲良しに！', 'from': 7.3, 'to': 9.3, 'y': 420, 'size': 56}] if hub else []),
        {'text': '仲良し同士は、島でいつも一緒に過ごすよ', 'from': 9.5, 'to': 11.4, 'y': 330, 'size': 46},
        {'text': '中身は…', 'from': 14.6, 'to': 15.6, 'y': 360, 'size': 70, 'color': [255, 214, 74]},
        {'text': '種と苗だった！', 'from': 15.7, 'to': 17.2, 'y': 360, 'size': 76, 'color': [255, 214, 74]},
        *[{'text': f'{name_of(i)}さん：{w}', 'from': 17.2 + k * 0.7, 'to': 20.0, 'y': 1180 + k * 80, 'size': 44} for k, (i, w) in enumerate(wish)],
        {'text': '畑を作るために…', 'from': 20.1, 'to': 22.0, 'y': 360, 'size': 60},
        {'text': '森を、1/3切りひらく！', 'from': 22.0, 'to': 27.0, 'y': 360, 'size': 64, 'color': [255, 214, 74]},
        {'text': '切った木で、道具ができた！', 'from': 27.1, 'to': 31.0, 'y': 360, 'size': 58},
        {'text': 'くわ　釣り竿　のこぎり', 'from': 27.8, 'to': 31.0, 'y': 1290, 'size': 54, 'color': [255, 214, 74]},
        *([{'text': 'Rinoさん「東京ドームくらいの巨大な畑を！」', 'from': 31.1, 'to': 35.4, 'y': 330, 'size': 40}] if inr(RINO) else []),
        {'text': '巨大な畑に、種と苗を植えた！', 'from': 35.5, 'to': 37.0, 'y': 360, 'size': 54, 'color': [255, 214, 74]},
        {'text': 'PWAで、2日かけて育ちます', 'from': 35.5, 'to': 37.0, 'y': 1290, 'size': 46},
        {'text': 'その夜', 'from': 37.0, 'to': 38.4, 'y': 420, 'size': 64, 'color': [255, 214, 74]},
        {'text': '…森の奥で、何かが光った', 'from': 40.6, 'to': 42.4, 'y': 360, 'size': 54},
        {'text': 'クマだーーー！', 'from': 42.5, 'to': 44.6, 'y': 360, 'size': 84, 'color': [255, 120, 90]},
        {'text': '森を切ったから、住処を追われた…！', 'from': 48.5, 'to': 52.0, 'y': 330, 'size': 48},
        {'text': '次の質問', 'from': 52.1, 'to': 58.0, 'y': 330, 'size': 64, 'color': [255, 214, 74]},
        {'text': 'クマが現れた！どうする？', 'from': 52.2, 'to': 58.0, 'y': 450, 'size': 62},
        {'text': 'A 松明の火で追い払う', 'from': 52.9, 'to': 58.0, 'y': 700, 'size': 52},
        {'text': 'B 柵と落とし穴で畑を守る', 'from': 53.4, 'to': 58.0, 'y': 800, 'size': 52},
        {'text': 'C 食べ物を分けて、仲良くなる', 'from': 53.9, 'to': 58.0, 'y': 900, 'size': 52},
        {'text': 'D 自由に提案', 'from': 54.4, 'to': 58.0, 'y': 1000, 'size': 52},
        {'text': 'A・B・C・Dでコメントしてね', 'from': 55.0, 'to': 58.0, 'y': 1300, 'size': 50, 'color': [255, 214, 74]},
        {'text': 'クマはいまも、島を歩いています', 'from': 58.2, 'to': DUR, 'y': 1300, 'size': 54},
        {'text': 'プロフィールのリンクから', 'from': 58.2, 'to': DUR, 'y': 1390, 'size': 54},
    ],
    'action': [{'text': '大工：木を切りひらく', 'from': 20.2, 'to': 26.8}, {'text': '農家：くわで耕して植える', 'from': 31.2, 'to': 35.4}],
    'result': [{'text': '倒れたー！', 'from': 21.4, 'to': 22.0}],
    'smallTagsMax': 5,
}
narr = [
    {'at': 0.3, 'until': 3.0, 'text': f'{n_arrive}人が、流れ着いた！' if n_arrive else '6日目。'},
    {'at': 3.1, 'until': 4.5, 'text': 'フォローすると、あなたも。'},
    {'at': 4.6, 'until': 6.0, 'text': '島は、リンクから。'},
    *([{'at': 6.2, 'until': 9.3, 'text': f'{name_of(hub)}さん、{len(hub_friends)}人と仲良しに！'}] if hub else []),
    {'at': 9.5, 'until': 11.4, 'text': '仲良し同士は、いつも一緒。'},
    {'at': 11.6, 'until': 14.4, 'text': '木箱の中身、一番多い予想は…'},
    {'at': 14.6, 'until': 15.6, 'text': '開けてみると…'},
    {'at': 15.7, 'until': 17.2, 'text': '種と苗！'},
    {'at': 20.1, 'until': 22.0, 'text': '畑を作るために。'},
    {'at': 22.1, 'until': 27.0, 'text': '森を、三分の一切りひらく！'},
    {'at': 27.1, 'until': 31.0, 'text': '切った木で、くわと釣り竿と、のこぎり！'},
    {'at': 31.1, 'until': 35.4, 'text': '東京ドームくらいの、巨大な畑！'},
    {'at': 35.5, 'until': 37.0, 'text': '種と苗を、植えた！'},
    {'at': 37.1, 'until': 40.5, 'text': 'その夜。みんなで、たき火を囲む。'},
    {'at': 40.6, 'until': 42.4, 'text': '…森の奥で、何かが光った。'},
    {'at': 42.5, 'until': 44.6, 'text': 'クマだー！'},
    {'at': 44.7, 'until': 48.4, 'text': 'みんな、逃げてー！'},
    {'at': 48.5, 'until': 52.0, 'text': '森を切ったから、住処を追われたんだ。'},
    {'at': 52.2, 'until': 58.0, 'text': 'クマが現れた！どうする？エー、ビー、シー、ディーでコメントしてね。'},
    {'at': 58.2, 'until': DUR, 'text': 'クマはいまも、島を歩いています。'},
]
EXIST = [
    {'id': 'ruins-1', 'type': 'ruins', 'name': '昔の住人の跡', 'x': -44.7, 'z': -12.7, 'rot': 0, 'builtDay': 1},
    {'id': 'hut-1', 'type': 'hut', 'name': 'はじまりの小屋', 'x': -20, 'z': -5, 'rot': 20, 'builtDay': 4},
    {'id': 'workshop-1', 'type': 'workshop', 'name': '石の作業場', 'x': -40.3, 'z': -9.0, 'rot': 10, 'builtDay': 5},
]
story = {
    'title': '6日目', 'roster': ROSTER_REL, 'day': DAY, 'fps': 24, 'duration': DUR, 'hour': 10,
    'baseTime': '2026-11-22T09:00:00+09:00', 'base': {'name': '中央の広場', 'x': 0, 'z': 5, 'decidedDay': 2},
    'forestRoad': {'points': [[-74, -22], [-128, -34]], 'need': 300, 'startDay': 4, 'label': '光の場所', 'open': True},
    'toolAge': 'stone', 'clearings': [{**CLEAR, 'day': DAY}], 'buildings': EXIST,
    'cast': list(dict.fromkeys(list(commenters) + [x for e in edges for x in e] + crowd + carp + farmers + campers + arrivals[:22])),
    'groups': groups, 'acts': acts, 'props': props, 'props3d': props3d, 'camera': camera,
    'overlay': overlay, 'override': {},
    'cutaway': {'radius': 1.6},
    'audio': {'narration': narr, 'bgm': {'volume': 0.18}, 'speed': 1.15},
    'cover': {'at': 44.0, 'day': f'{DAY}日目', 'lines': ['畑を作ったら…', 'クマが出た！']},
}
json.dump(story, open(os.path.join(HERE, 'story', 'ep6.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

# ---- PWA の続きと state ----
today = []
def td(i, spot, anim, text, tool=None):
    if inr(i): today.append({'id': i, 'spot': spot, 'anim': anim, 'text': text, **({'tool': tool} if tool else {})})
td(RINO, 'farm', 'work', '東京ドームくらいの巨大な畑で、苗の世話をしている', 'hoe')
td(HERO, 'farm', 'work', '巨大な畑に、小麦をまいている', 'hoe')
td(MA, 'farm', 'work', '大豆とさつまいもの苗を植えている', 'hoe')
td(TSUKI, 'plaza', 'talk', 'クマから逃げて、みんなで夜のたき火を囲む相談をしている')
td(YURI, 'plaza', 'work', '料理人として、みんなのご飯を作っている', 'ladle')
pwa = {'day': DAY, 'roster': ROSTER_REL, 'today': today, 'missing': {}}
json.dump(pwa, open(os.path.join(HERE, 'story', 'ep6_pwa.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
state = {
    'day': DAY,
    'clearings_add': [{**CLEAR, 'day': DAY}],
    'beast': {'day': DAY, 'x': FIELD[0], 'z': FIELD[1], 'r': 20, 'text': '森を切りひらいて住処を追われたクマが、島を歩きまわっている。近づかれた島民は逃げていく…'},
    'buildings_remove': ['crate-1'],
    'buildings_add': [{'id': 'bigfield-1', 'type': 'bigfield', 'name': '巨大な畑', 'x': round(FIELD[0] / 3, 2), 'z': round(FIELD[1] / 3, 2), 'rot': 0, 'builtDay': DAY,
                       'note': '木箱の種と苗を植えた、みんなの巨大な畑。植えた日→次の日に芽が伸びて→2日後に実る（小麦・大豆・さつまいも・綿・果物）。'}],
    'chronicle_add': {'day': DAY, 'title': '巨大な畑。そしてクマ', 'text': '木箱の中身は種と苗。森を1/3切りひらいて、くわ・釣り竿・のこぎりを作り、巨大な畑に植えた。その夜、住処を追われたクマが森から現れた。',
                      'vote': {'question': '流れ着いた大きな木箱。中身はなんだろう？', 'adopted': OPTS[winner], 'note': '　'.join(f'{k} {tally[k]}件' for k in OPTS)}},
    'currentVote': {'id': 'vote-006-bear', 'status': 'open', 'question': 'クマが現れた！どうする？',
                    'description': 'A・B・C・D でコメントしてね。コメントが一番多い案を採用します（Dが一番多いときは、Dの中でいいねが一番多い案）',
                    'options': [{'key': 'A', 'label': '松明の火で追い払う'}, {'key': 'B', 'label': '柵と落とし穴で畑を守る'}, {'key': 'C', 'label': '食べ物を分けて、仲良くなる'}, {'key': 'D', 'label': '自由に提案'}]},
}
json.dump(state, open(os.path.join(HERE, 'story', 'ep6_state.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
json.dump({'fetchedAt': C.get('fetchedAt'), 'tally': tally, 'winner': winner, 'votes': {name_of(i): p['vote'] for i, p in people.items()}},
          open(os.path.join(HERE, 'story', 'ep6_tally.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(json.dumps({'arrivals': n_arrive, 'tally': tally, 'winner': winner, 'hub': hub and name_of(hub), 'hub_friends': [name_of(x) for x in hub_friends],
                  'pairs': [(name_of(a), name_of(b)) for a, b in pairs], 'trees': len(TREES), 'cast': len(story['cast'])}, ensure_ascii=False))
