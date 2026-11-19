#!/usr/bin/env python3
"""3日目の台本を、コメントと名簿から組み立てる。
  python3 video-tools/ep3/build_story.py
入力：ep3/input/comments.json・ep3/input/islanders.json
出力：ep3/story/ep3.json（動画の台本）・ep3/story/ep3_pwa.json（PWA の続き）・ep3/story/ep3_tally.json（集計の記録）

役（だれがどの場面の主役か）と、長いコメントの抜き出しは下の ROLES / EXCERPT で決める（Claude が書く）。
それ以外（集計・みんなの声・名札の色・名前）はデータから自動で決まる。
"""
import json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
INP = os.path.join(HERE, 'input')
C = json.load(open(os.path.join(INP, 'comments.json'), encoding='utf-8'))
R = json.load(open(os.path.join(INP, 'islanders.json'), encoding='utf-8'))
ROSTER = {p['id']: p for p in R['islanders']}
DAY = 3
OPTS = C['post']['options']

# ---- 役（データを見て Claude が決める。名簿に無い ID は自動で外す） ----
ROLES = {
    'forest': ['rino._.15', 'hyuga_0619', 'atsukidesu', '_3yu.96_', 'momosann.0420.sabu', 'yuradayo0330', 'tsuki5747', 'bear.44190633', 'dosukoi.5845', 'nanasi774_ou', 'kubotto0505'],
    'forestStar': 'rino._.15',       # 「みんなで協力して探そう！」
    'watcher': 'tsuki5747',          # 見張り → 物音で真っ先に逃げる（本人了解）
    'missing': 'yuradayo0330',       # 森の奥へ行ったまま（本人了解）
    'fishStar': 'ibu131313',         # 全員でやれば釣れる → 1匹だけ
    'fishAnswer': 'kubotto0505',     # 全員分は難しそう（答え合わせ）
    'fishers': ['ibu131313', 'kazuzu4771', 'nabemegane', 'taishi.uramoto23', 'yukikun4126', 'savans880', 'saori.siegert', 'ichi.09', 'marumegane4'],
    'netStar': 'kazuzu4771',         # 全員で地引き網 → 網がない
    'crateStar': 'analogayane',      # 資材が流れてきてそう → 木箱
    'farmers': ['masatk_no_m', 'takada_1gram', 'yamato_family327'],
    'farmStar': 'masatk_no_m',
    'farmAnswer': 'nanasi774_ou',    # 水と種がなきゃ作れない（答え合わせ）
    'waterStar': 'bear.44190633',    # まず飲み水
    'waterDrinker': 'dosukoi.5845',  # 海水を飲む
}
# 40字を超えるコメントは、本人の言葉のまま要点を抜き出す（言葉は足さない）
EXCERPT = {
    'rino._.15': 'みんなで協力して探そう！😆',
    'tsuki5747': '危険な動物がいないかも確認します　もし出たら最前線で戦います',
    'analogayane': '浜に資材とかも流れてきてそう…',
    'kubotto0505': '…釣りも全員分獲るのは難しいそう😓',
    'bear.44190633': '飲み水確保してから海で魚を取って畑を作ろう！',
    'ibu131313': '魚は栄養素高いし、全員でやれば釣る確率も上がる',
    'nanasi774_ou': '畑は水と種がなきゃ作れないから',
    'dosukoi.5845': 'まずは飲み水を確保するべきだと思う。',
}

# ---- 集計：1人1票（最後のコメント）。本文が寄せている案で数える ----
VOTE_RE = re.compile(r'(?<![A-Za-zＡ-Ｚａ-ｚ])([ABCabcＡＢＣａｂｃ])(?![A-Za-zＡ-Ｚａ-ｚ])')
def vote_of(text):
    m = VOTE_RE.search(text or '')
    if not m: return None
    return {'Ａ': 'A', 'Ｂ': 'B', 'Ｃ': 'C', 'ａ': 'A', 'ｂ': 'B', 'ｃ': 'C'}.get(m.group(1), m.group(1).upper())
people = {}  # key → {id, name, text, vote, at, status}
for c in sorted(C['comments'], key=lambda c: c.get('at') or ''):
    key = c.get('userId') or ('name:' + (c.get('name') or ''))
    v = vote_of(c.get('text'))
    prev = people.get(key)
    name = (c.get('name') or '').strip() or (ROSTER.get(c.get('userId') or '', {}).get('name')) or c.get('userId') or '名無し'
    people[key] = {'id': c.get('userId'), 'name': name, 'text': (c.get('text') or '').strip(),
                   'vote': v or (prev or {}).get('vote'), 'at': c.get('at'), 'status': c.get('status'), 'likes': c.get('likes', 0)}
tally = {k: 0 for k in OPTS}
for p in people.values():
    if p['vote'] in tally: tally[p['vote']] += 1
# 同数のときの決め方（本人の判断）：12時の集計で A 12・C 12 → C を 13 にする（2026-11-19 12:10 本人の指示）
TIE_ADD = {'C': 1}
_o = sorted(tally, key=lambda k: -tally[k])
if tally[_o[0]] == tally[_o[1]]:
    for k, n in TIE_ADD.items(): tally[k] += n
order = sorted(tally, key=lambda k: -tally[k])
winner = order[0]
if tally[order[0]] == tally[order[1]]:
    sys.exit(f'同数で決まらない：{tally}（決め方を本人に確認）')
margin = tally[order[0]] - tally[order[1]]
followers = int(C.get('followers') or 0)
left = max(0, 300 - followers)
joined3 = sum(1 for p in R['islanders'] if int(p.get('joinedDay', 0)) == DAY)

in_roster = lambda i: bool(i) and i in ROSTER
byid = {p['id']: p for p in people.values() if p['id']}
def says(i):
    """吹き出しの文：抜き出し（あれば）か、本人のコメントそのまま"""
    return EXCERPT.get(i) or byid.get(i, {}).get('text', '')
def keep(ids): return [i for i in ids if in_roster(i)]
for k in list(ROLES):
    if isinstance(ROLES[k], list): ROLES[k] = keep(ROLES[k])
    elif not in_roster(ROLES[k]): print(f'!! 役 {k} の {ROLES[k]} が名簿に無いので外す'); ROLES[k] = None

# ---- 出演者：コメントした島民＋背景の島民（2日目に漂着した人から） ----
commenters = {p['id']: p['vote'] or '-' for p in people.values() if in_roster(p['id'])}
crowd = [p['id'] for p in R['islanders'] if p['id'] not in commenters][:34]
beach_new = [i for i in commenters if int(ROSTER[i].get('joinedDay', 0)) == DAY][:10] + \
            [p['id'] for p in R['islanders'] if int(p.get('joinedDay', 0)) == DAY and p['id'] not in commenters][:14]
everyone = list(dict.fromkeys(list(commenters) + crowd))
plaza_ring = [i for i in everyone if i != ROLES['missing']]

F = ROLES
fs, fa, ns, cs = F['fishStar'], F['fishAnswer'], F['netStar'], F['crateStar']
groups = [
    {'name': 'forest', 'type': 'line', 'spot': [-76, -23], 'face': [0.98, 0.2], 'gap': 2.6, 'members': F['forest'] + crowd[:10]},
    {'name': 'beach', 'type': 'ring', 'spot': [238, 125], 'radius': 3.2, 'gap': 2.6, 'members': beach_new},
    {'name': 'net', 'type': 'shore', 'spot': [236, 150], 'gap': 2.6, 'back': 1.6, 'members': [x for x in [ns, cs] if x] + crowd[10:14]},
    {'name': 'cove', 'type': 'shore', 'spot': [-9, 189], 'gap': 2.4, 'back': 1.4, 'members': [fs] + [x for x in F['fishers'] if x not in (fs, ns)] + crowd[14:30]},
    {'name': 'farm', 'type': 'line', 'spot': [-7, 99], 'face': [0.6, 0.8], 'gap': 3.0, 'members': F['farmers']},
    {'name': 'water', 'type': 'shore', 'spot': [244, 110], 'gap': 2.6, 'back': 1.4, 'members': [x for x in [F['waterStar'], F['waterDrinker']] if x]},
    {'name': 'plaza', 'type': 'ring', 'spot': [0, 5], 'radius': 7, 'gap': 2.8, 'members': plaza_ring},
]
# 森・浜・入り江・畑・水の人は、自分の場面より前はそれぞれの持ち場に、終盤は広場に集まる
acts = [{'who': '*', 't': 0, 'anim': 'idle', 'face': 'front'}]
A = acts.append
# 場面のはじめに、その場面の人をその群の持ち場へ（家は漂着した浜などになっているため）
for g, t0 in [('forest', 0), ('beach', 2.4), ('cove', 19.2), ('net', 28.0), ('farm', 34.4), ('water', 39.6)]:
    mem = next(x for x in groups if x['name'] == g)['members']
    A({'who': mem, 't': t0, 'at': {'slot': g}, 'anim': 'sleep' if g == 'beach' else 'idle', 'face': 'front'})
A({'who': next(x for x in groups if x['name'] == 'beach')['members'], 't': 5.0, 'anim': 'sit', 'pick': 0.3, 'seed': 11})
# S0 つかみ（森の入口で実を見つけて喜ぶ）
A({'who': F['forest'], 't': 0, 'anim': 'cheer'})
# S3 森：探す → 見つける
A({'who': F['forest'], 't': 10.4, 'anim': 'idle', 'face': 'back'})
A({'who': F['forest'], 't': 11.4, 'anim': 'work', 'face': 'back'})
A({'who': F['forest'], 't': 12.8, 'anim': 'eat', 'face': 'front'})
if F['forestStar']: A({'who': F['forestStar'], 't': 12.8, 'anim': 'cheer'})
if F['watcher']: A({'who': F['watcher'], 't': 15.0, 'anim': 'idle', 'face': 'back', 'at': {'rel': 'g:forest', 't': -7, 'n': -1.5}})
if F['missing']:  # ゆらさん：ひとりで森の奥へ歩いていく（伏線）→ 姿を消す
    A({'who': F['missing'], 't': 16.4, 'to': {'rel': 'g:forest', 't': -3, 'n': 16}, 'dur': 2.6})
    A({'who': F['missing'], 't': 19.0, 'hide': True})
# S4 入り江：一斉に竿 → 待つ → 1匹 → kubotto が来る
cove_people = [x for x in groups[3]['members'] if x != fa]
A({'who': cove_people, 't': 19.6, 'anim': 'work'})
A({'who': cove_people, 't': 20.4, 'frame': 'workB'})
A({'who': cove_people, 't': 21.6, 'anim': 'sit', 'pick': 0.35, 'seed': 3, 'except': [fs]})
A({'who': fs, 't': 23.4, 'frame': 'workA'})
A({'who': fs, 't': 24.0, 'anim': 'cheer'})
if fa:
    A({'who': fa, 't': 0, 'hide': True})
    A({'who': fa, 't': 24.6, 'hide': False, 'at': {'rel': fs, 't': -10, 'n': -0.3}, 'to': {'rel': fs, 't': -1.3, 'n': -0.5}, 'dur': 1.0})
    A({'who': fa, 't': 25.7, 'anim': 'idle', 'face': {'to': fs}})
# S5 浜：網がない → 木箱
if ns:
    A({'who': ns, 't': 28.2, 'anim': 'work'})
    A({'who': [x for x in groups[2]['members']], 't': 29.2, 'anim': 'shock'})
    A({'who': [x for x in groups[2]['members']], 't': 29.9, 'anim': 'idle'})
if cs: A({'who': cs, 't': 31.4, 'anim': 'cheer'})
# S6 畑：耕す → 種がない
A({'who': F['farmers'], 't': 34.6, 'anim': 'work'})
A({'who': F['farmers'], 't': 35.8, 'anim': 'shock'})
A({'who': F['farmers'], 't': 36.4, 'anim': 'idle'})
if F['farmAnswer'] and F['farmStar']:
    A({'who': F['farmAnswer'], 't': 36.0, 'at': {'rel': F['farmStar'], 't': -9, 'n': -0.5}, 'to': {'rel': F['farmStar'], 't': -3.2, 'n': -0.6}, 'dur': 0.6})
    A({'who': F['farmAnswer'], 't': 36.7, 'anim': 'idle', 'face': {'to': F['farmStar']}})
# S7 飲み水：海水を飲む → しょっぱい
if F['waterDrinker']:
    A({'who': F['waterDrinker'], 't': 41.0, 'anim': 'eat', 'face': 'front'})
    A({'who': F['waterDrinker'], 't': 41.9, 'anim': 'shock'})
# S8 森で物音 → つきさんが真っ先に逃げる → 全員逃げる → 広場で数える
forest_now = [x for x in groups[0]['members'] if x != F['missing']]
A({'who': forest_now, 't': 44.0, 'at': {'slot': 'forest'}, 'anim': 'eat', 'hide': False})
if F['watcher']: A({'who': F['watcher'], 't': 44.0, 'at': {'rel': 'g:forest', 't': -2, 'n': -1.2}})
A({'who': forest_now, 't': 45.0, 'anim': 'shock', 'face': 'back'})
if F['watcher']: A({'who': F['watcher'], 't': 45.25, 'to': {'rel': 'g:forest', 't': 3, 'n': -30}, 'dur': 1.3, 'run': True, 'face': 'front'})
A({'who': forest_now, 't': 45.9, 'to': {'rel': 'g:forest', 't': 0, 'n': -30}, 'dur': 1.5, 'run': True, 'except': [F['watcher']]})
A({'who': plaza_ring, 't': 47.4, 'at': {'slot': 'plaza'}, 'anim': 'idle', 'hide': False, 'face': {'at': [0, 5]}})
A({'who': plaza_ring, 't': 48.6, 'anim': 'shock', 'pick': 0.4, 'seed': 9})
A({'who': plaza_ring, 't': 49.2, 'anim': 'idle'})

# コメントしていない人だけ（ゆらさんも出さない）。コメントした人は広場に残す
bm = [i for i in next(x for x in groups if x['name'] == 'beach')['members'] if i not in commenters]
A({'who': bm, 't': 58.4, 'at': {'slot': 'beach'}, 'anim': 'idle', 'hide': False})
A({'who': bm, 't': 58.4, 'anim': 'work', 'pick': 0.4, 'seed': 5})
A({'who': bm, 't': 58.4, 'anim': 'sit', 'pick': 0.25, 'seed': 6})
ALL = everyone
camera = [
    {'from': 0, 'to': 2.4, 'hour': 9.5, 'keys': [{'t': 0, 'look': {'rel': 'g:forest', 't': 0}, 'dist': 21, 'az': 0.25, 'pol': 1.3, 'up': 2}, {'t': 2.4, 'look': {'rel': 'g:forest'}, 'dist': 18, 'az': 0.3, 'pol': 1.3, 'up': 2}]},
    {'from': 2.4, 'to': 6.2, 'hour': 7.5, 'keys': [{'t': 2.4, 'look': {'rel': 'g:beach'}, 'dist': 34, 'az': 1.1, 'pol': 1.2, 'up': 1.5, 'frame': 'cove'}, {'t': 6.2, 'look': {'rel': 'g:beach'}, 'dist': 27, 'az': 1.2, 'pol': 1.22, 'up': 1.5, 'frame': 'cove'}]},
    {'from': 6.2, 'to': 10.4, 'hour': 9.0, 'keys': [{'t': 6.2, 'look': {'rel': 'g:plaza'}, 'dist': 120, 'az': 0.3, 'pol': 0.95, 'up': 0}, {'t': 10.4, 'look': {'rel': 'g:plaza'}, 'dist': 105, 'az': 0.4, 'pol': 0.95, 'up': 0}]},
    {'from': 10.4, 'to': 15.0, 'hour': 10.0, 'keys': [{'t': 10.4, 'look': {'rel': F['forestStar'] or 'g:forest'}, 'dist': 15, 'az': 0.3, 'pol': 1.3, 'up': 2.2}, {'t': 15.0, 'look': {'rel': F['forestStar'] or 'g:forest', 't': -2}, 'dist': 19, 'az': 0.25, 'pol': 1.3, 'up': 2.2}]},
    {'from': 15.0, 'to': 19.2, 'hour': 10.3, 'keys': [{'t': 15.0, 'look': {'rel': 'g:forest', 't': -7, 'n': -1.5}, 'dist': 13, 'az': 0.35, 'pol': 1.3, 'up': 2.2}, {'t': 19.2, 'look': {'rel': 'g:forest', 't': -5, 'n': -6}, 'dist': 17, 'az': 0.2, 'pol': 1.28, 'up': 2.2}]},
    {'from': 19.2, 'to': 21.4, 'hour': 11, 'keys': [{'t': 19.2, 'look': {'rel': fs}, 'dist': 13, 'az': 0.35, 'pol': 1.32, 'up': 2.2}, {'t': 20.0, 'look': {'rel': fs}, 'dist': 14, 'az': 0.33, 'pol': 1.31, 'up': 2.2}, {'t': 21.4, 'look': {'rel': fs, 't': -2}, 'dist': 60, 'az': 0.22, 'pol': 1.12, 'up': 1}]},
    {'from': 21.4, 'to': 23.2, 'hour': 11, 'keys': [{'t': 21.4, 'look': {'rel': fs, 't': -7}, 'dist': 24, 'az': 0.7, 'pol': 1.3, 'up': 1.6}, {'t': 23.2, 'look': {'rel': fs, 't': -5}, 'dist': 21, 'az': 0.65, 'pol': 1.3, 'up': 1.6}]},
    {'from': 23.2, 'to': 24.6, 'hour': 11, 'keys': [{'t': 23.2, 'look': {'rel': fs, 'n': -1}, 'dist': 14, 'az': 0.3, 'pol': 1.3, 'up': 2.6}, {'t': 24.6, 'look': {'rel': fs, 'n': -1}, 'dist': 12.5, 'az': 0.32, 'pol': 1.3, 'up': 2.6}]},
    {'from': 24.6, 'to': 28.0, 'hour': 11, 'keys': [{'t': 24.6, 'look': {'rel': fs, 't': -0.8}, 'dist': 14.5, 'az': 0.3, 'pol': 1.3, 'up': 2.2}, {'t': 28.0, 'look': {'rel': fs, 't': -0.8}, 'dist': 15.5, 'az': 0.28, 'pol': 1.3, 'up': 2.2}]},
    {'from': 28.0, 'to': 34.4, 'hour': 13, 'keys': [{'t': 28.0, 'look': {'rel': ns or 'g:net'}, 'dist': 13, 'az': 0.3, 'pol': 1.3, 'up': 2.2}, {'t': 30.8, 'look': {'rel': ns or 'g:net'}, 'dist': 15, 'az': 0.3, 'pol': 1.3, 'up': 2.2}, {'t': 31.2, 'look': {'rel': cs or 'g:net'}, 'dist': 13, 'az': 0.3, 'pol': 1.3, 'up': 2.2}, {'t': 34.4, 'look': {'rel': cs or 'g:net'}, 'dist': 14, 'az': 0.3, 'pol': 1.3, 'up': 2.2}]},
    {'from': 34.4, 'to': 39.6, 'hour': 14, 'keys': [{'t': 34.4, 'look': {'rel': F['farmStar'] or 'g:farm'}, 'dist': 16, 'az': 0.25, 'pol': 1.3, 'up': 2.2}, {'t': 39.6, 'look': {'rel': F['farmStar'] or 'g:farm'}, 'dist': 18, 'az': 0.3, 'pol': 1.3, 'up': 2.2}]},
    {'from': 39.6, 'to': 43.8, 'hour': 15.5, 'keys': [{'t': 39.6, 'look': {'rel': 'g:water'}, 'dist': 14, 'az': 0.3, 'pol': 1.3, 'up': 2.2}, {'t': 43.8, 'look': {'rel': 'g:water'}, 'dist': 13, 'az': 0.3, 'pol': 1.3, 'up': 2.2}]},
    {'from': 43.8, 'to': 47.4, 'hour': 16.5, 'keys': [{'t': 43.8, 'look': {'rel': 'g:forest'}, 'dist': 22, 'az': 0.2, 'pol': 1.3, 'up': 2}, {'t': 45.2, 'look': {'rel': 'g:forest'}, 'dist': 20, 'az': 0.22, 'pol': 1.3, 'up': 2}, {'t': 47.4, 'look': {'rel': 'g:forest', 'n': -14}, 'dist': 30, 'az': 0.2, 'pol': 1.25, 'up': 2}]},
    {'from': 47.4, 'to': 51.0, 'hour': 17.0, 'keys': [{'t': 47.4, 'look': {'rel': 'g:plaza'}, 'dist': 34, 'az': 0.3, 'pol': 1.05, 'up': 1}, {'t': 51.0, 'look': {'rel': 'g:plaza'}, 'dist': 30, 'az': 0.35, 'pol': 1.08, 'up': 1}]},
    {'from': 51.0, 'to': 54.0, 'hour': 17.2, 'keys': [{'t': 51.0, 'look': [-128, -34], 'dist': 120, 'az': 2.6, 'pol': 0.8, 'up': 6, 'frame': 'forest'}, {'t': 54.0, 'look': [-128, -34], 'dist': 100, 'az': 2.7, 'pol': 0.82, 'up': 6, 'frame': 'forest'}]},
    {'from': 54.0, 'to': 58.4, 'hour': 17.4, 'keys': [{'t': 54.0, 'look': {'rel': 'g:plaza'}, 'dist': 90, 'az': 0.5, 'pol': 0.9, 'up': 0}, {'t': 58.4, 'look': {'rel': 'g:plaza'}, 'dist': 80, 'az': 0.6, 'pol': 0.9, 'up': 0}]},
    {'from': 58.4, 'to': 62.2, 'hour': 12, 'keys': [{'t': 58.4, 'look': {'rel': 'g:beach'}, 'dist': 20, 'az': 1.0, 'pol': 1.25, 'up': 2, 'frame': 'cove'}, {'t': 62.2, 'look': {'rel': 'g:beach'}, 'dist': 22, 'az': 1.3, 'pol': 1.25, 'up': 2, 'frame': 'cove'}]},
    {'from': 62.2, 'to': 68.5, 'hour': 17.8, 'keys': [{'t': 62.2, 'look': {'rel': 'g:plaza'}, 'dist': 60, 'az': 0.7, 'pol': 1.1, 'up': 1}, {'t': 68.5, 'look': {'rel': 'g:plaza'}, 'dist': 75, 'az': 0.8, 'pol': 1.05, 'up': 1}]},
]
DUR = 72.0
camera.append({'from': 68.5, 'to': DUR, 'hour': 18.3, 'keys': [{'t': 68.5, 'look': {'rel': 'g:plaza'}, 'dist': 260, 'az': 0.8, 'pol': 0.9, 'up': 0}, {'t': DUR, 'look': {'rel': 'g:plaza'}, 'dist': 300, 'az': 0.85, 'pol': 0.88, 'up': 0}]})

bmem = next(x for x in groups if x['name'] == 'beach')['members']
props = [{'type': 'zzz', 'from': {'rel': i, 'up': 1.6, 't': 0.6}, 't0': 2.4, 't1': 2.41, 't2': 6.2, 'size': 0.9, 'phase': k * 0.3} for k, i in enumerate(bmem[:6])] + [
    {'type': 'fruit', 'from': {'rel': 'g:forest', 't': -1.2, 'up': 0.2}, 't0': 0, 't1': 0.01, 't2': 2.4, 'size': 0.9},
    {'type': 'fruit', 'from': {'rel': 'g:forest', 't': 1.5, 'up': 0.2}, 't0': 0, 't1': 0.01, 't2': 2.4, 'size': 0.9},
    {'type': 'fruit', 'from': {'rel': F['forestStar'] or 'g:forest', 't': 0.9, 'n': -1, 'up': 2.6}, 't0': 12.8, 't1': 12.81, 't2': 15.0, 'size': 0.8},
    {'type': 'splash', 'from': {'rel': fs, 't': 1.2, 'n': -3.2, 'up': -0.2}, 't0': 23.4, 't1': 23.75, 'size': 1.2},
    {'type': 'fish', 'from': {'rel': fs, 't': 1.2, 'n': -3.2, 'up': -0.4}, 'to': {'rel': fs, 't': 0.9, 'up': 3.2}, 't0': 23.45, 't1': 24.0, 't2': 28.0, 'arc': 3.0, 'size': 0.9},
]
if cs: props.append({'type': 'crate', 'from': {'rel': cs, 't': 1.4, 'n': -1.2, 'up': 0}, 't0': 31.2, 't1': 31.21, 't2': 34.4, 'size': 1.2})
props.append({'type': 'question', 'from': [-128, -34], 't0': 51.0, 't1': 51.01, 't2': 54.0, 'size': 9})

def star(i, a, b, bubble=True):
    return {'who': i, 'from': a, 'to': b, **({'bubble': says(i)} if bubble and says(i) else {})} if i else None
stars = [x for x in [
    star(F['forestStar'], 10.6, 14.4), star(F['watcher'], 15.2, 19.0),
    star(fs, 19.3, 22.6), star(fs, 23.2, 24.6, False), star(fa, 25.7, 28.0),
    star(ns, 28.1, 30.8), star(cs, 31.2, 34.4),
    star(F['farmStar'], 34.5, 36.2), star(F['farmAnswer'], 36.7, 39.6),
    star(F['waterStar'], 39.7, 42.4),
    {'who': F['missing'], 'from': 49.0, 'to': 51.0, 'xy': [0.5, 0.36], 'label': '？？？', 'handle': '？？？'} if F['missing'] else None,
] if x]
VN = {'A': 'エー', 'B': 'ビー', 'C': 'シー'}
overlay = {
    'banner': 'コメントで動く無人島　3日目',
    'bannerOff': [[0, 2.4], [62.2, DUR]],
    'commenters': commenters,
    'names': {i: p['name'] for i, p in byid.items()},
    'titles': [{'text': '3日目', 'from': 0.1, 'to': 2.4}],
    'stars': stars,
    'tally': {'from': 6.2, 'to': 10.4, 'title': '昨日の質問　食料をどうする？', 'grow': [6.8, 8.4], 'winner': winner, 'winnerAt': 8.8,
              'rows': [{'key': k, 'label': OPTS[k], 'count': tally[k]} for k in ['A', 'B', 'C']]},
    'chips': [{'text': 'この人のいまは、プロフィールのリンクから', 'from': 19.6, 'to': 22.6}],
    'captions': [
        {'text': '食料、どうなった？', 'from': 0.5, 'to': 2.4, 'y': 1290, 'size': 84},
        {'text': f'新しく{joined3}人が漂着', 'from': 2.8, 'to': 6.2, 'y': 1290, 'size': 76},
        {'text': 'みんな、ぐっすり', 'from': 4.0, 'to': 6.2, 'y': 1400, 'size': 52, 'color': [255, 214, 74]},
        {'text': 'ガサッ', 'from': 44.9, 'to': 45.9, 'y': 700, 'size': 130},
        {'text': '…1人、足りない。', 'from': 48.6, 'to': 51.0, 'y': 1290, 'size': 84},
        {'text': '森の奥へ行けるのは、', 'from': 51.2, 'to': 54.0, 'y': 1230, 'size': 64},
        {'text': 'フォロワー300人から', 'from': 51.2, 'to': 54.0, 'y': 1320, 'size': 64},
        {'text': '動画に出ていない人も、', 'from': 58.6, 'to': 62.2, 'y': 1230, 'size': 60},
        {'text': '島で暮らしています', 'from': 58.6, 'to': 62.2, 'y': 1320, 'size': 60},
        {'text': '次の質問', 'from': 62.4, 'to': 68.5, 'y': 420, 'size': 70, 'color': [255, 214, 74]},
        {'text': '行方不明者がいる島で、', 'from': 62.6, 'to': 68.5, 'y': 560, 'size': 72},
        {'text': 'みんなは何をする？', 'from': 62.6, 'to': 68.5, 'y': 670, 'size': 72},
        {'text': '自由にコメントしてね', 'from': 64.0, 'to': 68.5, 'y': 1230, 'size': 52},
        {'text': 'いいなと思うコメントに、いいねを', 'from': 64.0, 'to': 68.5, 'y': 1310, 'size': 44},
    ],
    'action': [
        {'text': '森の実りを探す', 'from': 10.6, 'to': 15.0}, {'text': '見張り', 'from': 15.2, 'to': 19.0},
        {'text': '全員で釣る', 'from': 19.4, 'to': 24.6}, {'text': '地引き網をする', 'from': 28.2, 'to': 31.0},
        {'text': '浜を調べる', 'from': 31.2, 'to': 34.4}, {'text': '畑を作る', 'from': 34.6, 'to': 39.6},
        {'text': 'まずは飲み水', 'from': 39.8, 'to': 43.8},
    ],
    'result': [
        {'text': '木の実が、見つかった！', 'from': 12.9, 'to': 13.9},
        {'text': '…でも、全員分には足りない。', 'from': 13.9, 'to': 15.0},
        {'text': '…釣れたのは、1匹だけ。', 'from': 24.0, 'to': 25.0},
        {'text': 'でも、島で初めての魚！', 'from': 25.0, 'to': 26.2},
        {'text': '…網が、ない。', 'from': 29.3, 'to': 31.0},
        {'text': '木箱の中に、ロープが入っていた', 'from': 31.4, 'to': 34.4},
        {'text': '…種が、ない。', 'from': 35.9, 'to': 37.8},
        {'text': '木の実の種を、まいてみることに', 'from': 37.8, 'to': 39.6},
        {'text': '海の水は、飲めない。', 'from': 42.0, 'to': 43.8},
        {'text': f'あと{left}人', 'from': 52.0, 'to': 54.0},
    ],
    'wall': {'from': 54.0, 'to': 58.4, 'title': 'みんなの声', 'step': 0.1,
             'items': [{'name': p['name'], 'text': EXCERPT.get(p['id']) or p['text'], 'vote': p['vote']} for p in people.values() if p['id'] != F['missing']]},
    'noTag': [F['missing']] if F['missing'] else [],
    'images': [{'file': 'ep3_phone.png', 'from': 68.6, 'to': DUR, 'w': 430, 'y': 230, 'note': '森の「？」をタップすると…'}],
    'tagAll': [[58.4, 62.2, 0.15], [2.6, 6.2, 0.2]],
    'smallTagsMax': 5,
}
overlay['captions'] += [
    {'text': 'いなくなったのは、だれ？', 'from': 68.8, 'to': DUR, 'y': 1340, 'size': 62, 'color': [255, 214, 74]},
    {'text': 'プロフィールのリンクから', 'from': 68.8, 'to': DUR, 'y': 1440, 'size': 52},
]
narr = [
    {'at': 0.2, 'text': '3日目。食料は、どうなった？'},
    {'at': 2.8, 'text': f'今日、新しく{joined3}人が流れ着きました。みんな、ぐっすり。'},
    {'at': 6.4, 'text': '昨日の質問、食料をどうする。'},
    {'at': 8.8, 'text': f'結果は、{VN[winner]}。{margin}件差でした。' if margin <= 3 else f'結果は、{VN[winner]}。'},
    {'at': 23.4, 'text': '釣れたのは…'},
    {'at': 24.05, 'text': '1匹だけ。'},
    {'at': 44.6, 'text': '森で物音がして、みんなで逃げ帰ると…'},
    {'at': 48.6, 'text': '1人、足りない。'},
    {'at': 51.2, 'text': f'森の奥へ行けるのは、フォロワー300人から。あと{left}人。'},
    {'at': 58.6, 'text': '動画に出ていない人も、島で暮らしています。'},
    {'at': 62.6, 'text': '次の質問です。行方不明者がいる島で、みんなは何をする？自由にコメントしてね。'},
    {'at': 68.8, 'text': 'いなくなったのは、だれ？プロフィールのリンクから。では、また明日、4日目。'},
]
story = {
    'title': '3日目（本番）', 'roster': '../input/islanders.json', 'day': DAY, 'fps': 24, 'duration': DUR, 'hour': 10,
    'baseTime': '2026-11-19T09:00:00+09:00',
    'cast': ALL, 'groups': groups, 'acts': acts, 'props': props, 'camera': camera, 'overlay': overlay,
    'override': {**({F['watcher']: {'job': '探検家'}} if F['watcher'] else {}), **{i: {'job': '漁師'} for i in groups[3]['members']},
                 **{i: {'job': '農家'} for i in F['farmers']}},
    'audio': {'narration': narr, 'bgm': {'volume': 0.18}},
    'cover': {'at': 12.9, 'day': f'{DAY}日目', 'lines': [f'食料は、{OPTS[winner]}' if winner != 'C' else '食料は、森の実りに', 'そして、1人いなくなった']},
}
TIME_KEYS = {'t', 'from', 'to', 'at', 't0', 't1', 't2', 'winnerAt'}
def shift(o, at, by):
    """at 以降の時刻を by 秒うしろへ。時刻の項目（TIME_KEYS）と、区間の並び（tagAll・bannerOff・grow）だけを動かす"""
    def mv(v, end=False):
        return round(v + by, 3) if (v > at + 1e-6 if end else v >= at - 1e-6) else v
    if isinstance(o, dict):
        for k, v in o.items():
            if k in TIME_KEYS and isinstance(v, (int, float)): o[k] = mv(v, end=k in ('to', 't2'))
            elif k in ('tagAll', 'bannerOff') and isinstance(v, list):
                o[k] = [[mv(iv[0]), mv(iv[1], True), *iv[2:]] for iv in v]
            elif k == 'grow' and isinstance(v, list): o[k] = [mv(x) for x in v]
            elif isinstance(v, (dict, list)): shift(v, at, by)
    elif isinstance(o, list):
        for x in o:
            if isinstance(x, (dict, list)): shift(x, at, by)
INS, LEN = 2.4, 1.5
for part in ('acts', 'props', 'camera', 'overlay', 'audio'): shift(story[part], INS, LEN)
story['duration'] = DUR + LEN
story['cover']['at'] += LEN
story['camera'].insert(1, {'from': INS, 'to': INS + LEN, 'hour': 9.0, 'keys': [
    {'t': INS, 'look': [15, 40], 'dist': 760, 'az': 0.5, 'pol': 0.78, 'up': 0, 'frame': 'cove'},
    {'t': INS + LEN, 'look': [15, 40], 'dist': 700, 'az': 0.62, 'pol': 0.8, 'up': 0, 'frame': 'cove'}]})
story['overlay']['captions'] += [{'text': '島のいまは、', 'from': INS + 0.1, 'to': INS + LEN, 'y': 1230, 'size': 62},
                                  {'text': 'プロフィールのリンクから', 'from': INS + 0.1, 'to': INS + LEN, 'y': 1320, 'size': 62}]
story['overlay']['bannerOff'][0] = [0, INS + LEN]
story['audio']['narration'].append({'at': INS + 0.05, 'text': '島は、リンクから見られます。'})
# 漂着の場面の名札は、起きている人も寝ている人も左から順に
json.dump(story, open(os.path.join(HERE, 'story', 'ep3.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

# ---- PWA の続き：きょうの行動・行方不明 ----
today = []
def td(i, spot, anim, text, tool=None):
    if i and in_roster(i): today.append({'id': i, 'spot': spot, 'anim': anim, 'text': text, **({'tool': tool} if tool else {})})
for i in F['forest']:
    if i not in (F['missing'], F['watcher']): td(i, 'forestEdge', 'work', '森の入口で、木の実を集めている')
td(F['watcher'], 'forestEdge', 'idle', '森の入口で見張りをしている（物音には真っ先に逃げた）', 'scope')
td(fs, 'cove', 'work', '入り江で釣りをしている（昨日は1匹だけ釣れた）', 'rod')
for i in F['fishers']:
    if i not in (fs, ns): td(i, 'cove', 'work', '入り江で釣りをしている', 'rod')
td(ns, 'beach', 'work', '浜で、網の代わりになるものを探している')
td(cs, 'beach', 'idle', '浜で見つけた木箱のロープを調べている')
for i in F['farmers']: td(i, 'farm', 'work', '木の実の種をまいてみた畑を、耕している', 'hoe')
td(F['waterStar'], 'beach', 'idle', '飲める水を探している')
td(F['waterDrinker'], 'beach', 'idle', '海の水を飲んで、しょっぱい思いをした')
pwa = {'day': DAY, 'roster': '../input/islanders.json', 'today': today,
       'missing': {F['missing']: {'text': '森の奥へ探検に行ったまま、戻ってこない…'}} if F['missing'] else {}}
json.dump(pwa, open(os.path.join(HERE, 'story', 'ep3_pwa.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
rec = {'fetchedAt': C.get('fetchedAt'), 'comments': len(C['comments']), 'voters': len(people), 'tally': tally, 'winner': winner,
       'margin': margin, 'followers': followers, 'left': left, 'joined_day3': joined3,
       'votes': {p['name']: p['vote'] for p in people.values()}}
json.dump(rec, open(os.path.join(HERE, 'story', 'ep3_tally.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(json.dumps({k: rec[k] for k in ['tally', 'winner', 'margin', 'followers', 'left', 'joined_day3', 'voters']}, ensure_ascii=False))
print('出演', len(ALL), '人／きょうの行動', len(today), '人')
