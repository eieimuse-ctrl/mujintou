#!/usr/bin/env python3
"""4日目の台本を組み立てる（約48秒）。
  python3 video-tools/ep4/build_story.py
入力：ep4/input/comments.json（3日目の投稿のコメント）・ep3/input/islanders.json（名簿。4日目に漂着した人は joinedDay=4）
出力：ep4/story/ep4.json（台本）・ep4/story/ep4_pwa.json（PWA の続き）・ep4/story/ep4_state.json（Firebase の state に入れる差分）

方針（2026-11-20 本人と確定）
- 冒頭2秒で漂着（フォローした人が流れ着いて名前が出る）。最初の8秒以内に「フォローすると流れ着く」「島はリンクから」
- 本筋は1本：火を焚く → 松明で森へ → 奥の光はゆらさんの焚き火 → 昔の住人の跡。寄り道は ao.さんの戦闘係だけ
- 300人の制限はやめた（森の道は開通）。ゆらさんは今日見つかる
- 質問は3択＋自由（件数で採用。D が最多ならその中のいいね最多）
"""
import json, os

HERE = os.path.dirname(os.path.abspath(__file__))
C = json.load(open(os.path.join(HERE, 'input', 'comments.json'), encoding='utf-8'))
# 名簿：既定は ep3/input/islanders.json（Muse が4日目の漂着を反映した版を置く）。試しには ROSTER=ファイル で差し替え
ROSTER_PATH = os.path.abspath(os.environ.get('ROSTER') or os.path.join(HERE, '..', 'ep3', 'input', 'islanders.json'))
ROSTER_REL = os.path.relpath(ROSTER_PATH, os.path.join(HERE, 'story'))
R = json.load(open(ROSTER_PATH, encoding='utf-8'))
ROSTER = {p['id']: p for p in R['islanders']}
DAY = 4
inr = lambda i: bool(i) and i in ROSTER

# ---- コメント（いいね順、同数は早い順） ----
cm = [c for c in C['comments'] if not c.get('own')]
cm.sort(key=lambda c: (-int(c.get('likes') or 0), c.get('at') or ''))
top = cm[:3]
name_of = lambda c: (c.get('name') or '').strip() or ROSTER.get(c.get('userId') or '', {}).get('name') or '名無し'
commenters = {c['userId']: '-' for c in cm if inr(c.get('userId'))}
said = {c['userId']: c['text'] for c in cm if c.get('userId')}

SAORI, TOMO, TSUKI, NAKA, RYUJI, WAN, AO, YURA = 'saori.siegert', 'nabemegane', 'tsuki5747', 'atsukidesu', 'ryuji_111', '1kichi_chan', 'ao.030499', 'yuradayo0330'
searchers = [x for x in [TSUKI, NAKA, RYUJI, WAN] if inr(x)]
arrivals = [p['id'] for p in R['islanders'] if int(p.get('joinedDay', 0)) == DAY]
n_arrive = len(arrivals)
crowd = [p['id'] for p in R['islanders'] if p['id'] not in commenters and int(p.get('joinedDay', 0)) < DAY][:24]

# 森の道（ワールド座標）。P(s) は入口(0)→光の場所(1)
def P(s): return [round(-74 - 54 * s, 2), round(-22 - 12 * s, 2)]
YURA_AT = [-121.0, -31.0]
FIRE_AT = [-119.6, -30.2]

groups = [
    {'name': 'beach', 'type': 'ring', 'spot': [238, 125], 'radius': 3.2, 'gap': 2.6, 'members': arrivals[:22]},
    {'name': 'edge', 'type': 'line', 'spot': [-76, -23], 'face': [0.98, 0.2], 'gap': 2.6, 'members': [x for x in [SAORI, TOMO, AO] if inr(x)] + crowd[:12]},
    {'name': 'road', 'type': 'line', 'spot': P(0.15), 'face': [0.22, -0.97], 'gap': 2.2, 'members': searchers + crowd[12:18]},
    {'name': 'ruins', 'type': 'line', 'spot': [-129, -25], 'face': [0.55, 0.83], 'gap': 2.6, 'members': [x for x in [YURA] + searchers[:3] if inr(x)]},
    {'name': 'plaza', 'type': 'ring', 'spot': [0, 15], 'radius': 7, 'gap': 2.8, 'members': crowd},
]
acts = [{'who': '*', 't': 0, 'anim': 'idle', 'face': 'front'}]
A = acts.append
G = {g['name']: g for g in groups}
# S0 漂着：寝ている → 何人か起きる
A({'who': G['beach']['members'], 't': 0, 'at': {'slot': 'beach'}, 'anim': 'sleep'})
A({'who': G['beach']['members'], 't': 1.2, 'anim': 'sit', 'pick': 0.35, 'seed': 4})
A({'who': G['beach']['members'], 't': 2.0, 'anim': 'cheer', 'pick': 0.2, 'seed': 8})
# S3 森の入口：火を焚く → 松明を持つ
A({'who': G['edge']['members'], 't': 9.6, 'at': {'slot': 'edge'}, 'anim': 'idle'})
if inr(SAORI): A({'who': SAORI, 't': 10.6, 'anim': 'work'})
if inr(TOMO): A({'who': TOMO, 't': 10.6, 'anim': 'work'})
A({'who': G['edge']['members'], 't': 12.6, 'torch': True, 'anim': 'cheer'})
A({'who': G['edge']['members'], 't': 13.4, 'anim': 'idle'})
# S4 夜の森へ：捜索組が松明を持って道を奥へ
road = G['road']['members']
for k, i in enumerate(road):
    side = 1.2 if k % 2 else -1.2
    a0, a1 = P(0.10 + 0.03 * k), P(0.62 + 0.025 * k)
    A({'who': i, 't': 14.6, 'at': [a0[0] + side * 0.2, a0[1] + side], 'torch': True, 'anim': 'idle', 'hide': False})
    A({'who': i, 't': 15.0, 'to': [a1[0] + side * 0.2, a1[1] + side], 'dur': 5.4})
# S5 光の正体：ゆらさんの焚き火
if inr(YURA):
    A({'who': YURA, 't': 0, 'hide': True})
    A({'who': YURA, 't': 20.6, 'hide': False, 'at': YURA_AT, 'anim': 'sit', 'face': {'at': FIRE_AT}})
    A({'who': YURA, 't': 22.4, 'anim': 'cheer'})
for k, i in enumerate(searchers):
    A({'who': i, 't': 20.6, 'at': [YURA_AT[0] + 9 + k * 1.6, YURA_AT[1] + 2.5 - k * 0.8], 'to': [YURA_AT[0] + 3 + k * 1.4, YURA_AT[1] + 1.2 - k * 0.9], 'dur': 1.6, 'run': True, 'torch': True})
    A({'who': i, 't': 22.4, 'anim': 'cheer', 'face': {'to': YURA}})
# S6 次の朝：昔の住人の跡
A({'who': G['ruins']['members'], 't': 26.0, 'at': {'slot': 'ruins'}, 'anim': 'idle', 'torch': False, 'hide': False, 'face': 'back'})
A({'who': G['ruins']['members'], 't': 27.4, 'anim': 'work', 'face': 'back'})
if inr(YURA): A({'who': YURA, 't': 28.0, 'anim': 'cheer', 'face': 'front'})
# S7 ao.さん：戦闘係
if inr(AO):
    A({'who': AO, 't': 31.5, 'at': [-70, -21], 'torch': True, 'anim': 'cheer', 'face': 'front'})
    A({'who': [x for x in G['edge']['members'] if x != AO], 't': 31.5, 'at': {'slot': 'edge'}, 'torch': False, 'anim': 'idle'})
# S8 以降：広場に集まる
A({'who': crowd, 't': 34.3, 'at': {'slot': 'plaza'}, 'torch': False, 'anim': 'idle', 'face': {'at': [0, 15]}})

camera = [
    {'from': 0, 'to': 3.0, 'hour': 7.5, 'keys': [{'t': 0, 'look': {'rel': 'g:beach'}, 'dist': 24, 'az': 1.1, 'pol': 1.22, 'up': 1.5, 'frame': 'edge'}, {'t': 3.0, 'look': {'rel': 'g:beach'}, 'dist': 20, 'az': 1.2, 'pol': 1.24, 'up': 1.5, 'frame': 'edge'}]},
    {'from': 3.0, 'to': 6.0, 'hour': 11, 'keys': [{'t': 3.0, 'look': [15, 40], 'dist': 760, 'az': 0.5, 'pol': 0.78, 'up': 0, 'frame': 'edge'}, {'t': 6.0, 'look': [15, 40], 'dist': 700, 'az': 0.62, 'pol': 0.8, 'up': 0, 'frame': 'edge'}]},
    {'from': 6.0, 'to': 9.6, 'hour': 16.5, 'keys': [{'t': 6.0, 'look': {'rel': 'g:edge'}, 'dist': 90, 'az': 0.3, 'pol': 1.0, 'up': 0}, {'t': 9.6, 'look': {'rel': 'g:edge'}, 'dist': 80, 'az': 0.35, 'pol': 1.0, 'up': 0}]},
    {'from': 9.6, 'to': 14.6, 'hour': 18.2, 'keys': [{'t': 9.6, 'look': {'rel': SAORI if inr(SAORI) else 'g:edge'}, 'dist': 15, 'az': 0.3, 'pol': 1.3, 'up': 2.2}, {'t': 12.4, 'look': {'rel': SAORI if inr(SAORI) else 'g:edge'}, 'dist': 16, 'az': 0.3, 'pol': 1.3, 'up': 2.2}, {'t': 14.6, 'look': {'rel': 'g:edge'}, 'dist': 26, 'az': 0.25, 'pol': 1.28, 'up': 2}]},
    {'from': 14.6, 'to': 20.6, 'hour': 20.5, 'keys': [{'t': 14.6, 'look': P(0.2) , 'dist': 18, 'az': -0.5, 'pol': 1.25, 'up': 2.4, 'frame': 'road'}, {'t': 20.6, 'look': P(0.62), 'dist': 18, 'az': -0.45, 'pol': 1.25, 'up': 2.4, 'frame': 'road'}]},
    {'from': 20.6, 'to': 26.0, 'hour': 20.8, 'keys': [{'t': 20.6, 'look': YURA_AT, 'dist': 16, 'az': -0.2, 'pol': 1.28, 'up': 2.2, 'frame': 'road'}, {'t': 26.0, 'look': [YURA_AT[0] + 2, YURA_AT[1]], 'dist': 14, 'az': -0.15, 'pol': 1.28, 'up': 2.2, 'frame': 'road'}]},
    {'from': 26.0, 'to': 31.5, 'hour': 8.0, 'keys': [{'t': 26.0, 'look': [-134, -37], 'dist': 34, 'az': 0, 'pol': 0.85, 'up': 1.0, 'frame': 'ruins'}, {'t': 31.5, 'look': [-134, -37], 'dist': 28, 'az': 0.2, 'pol': 0.9, 'up': 1.0, 'frame': 'ruins'}]},
    {'from': 31.5, 'to': 34.3, 'hour': 20.5, 'keys': [{'t': 31.5, 'look': [-70, -21], 'dist': 11, 'az': 0.3, 'pol': 1.3, 'up': 2.2, 'frame': 'edge'}, {'t': 34.3, 'look': [-70, -21], 'dist': 10, 'az': 0.3, 'pol': 1.3, 'up': 2.2, 'frame': 'edge'}]},
    {'from': 34.3, 'to': 44.5, 'hour': 9.5, 'keys': [{'t': 34.3, 'look': {'rel': 'g:plaza'}, 'dist': 90, 'az': 0.5, 'pol': 0.9, 'up': 0}, {'t': 44.5, 'look': {'rel': 'g:plaza'}, 'dist': 70, 'az': 0.7, 'pol': 0.92, 'up': 0}]},
]
DUR = 48.5
camera.append({'from': 44.5, 'to': DUR, 'hour': 17.5, 'keys': [{'t': 44.5, 'look': [15, 40], 'dist': 700, 'az': 0.8, 'pol': 0.85, 'up': 0, 'frame': 'edge'}, {'t': DUR, 'look': [15, 40], 'dist': 760, 'az': 0.9, 'pol': 0.85, 'up': 0, 'frame': 'edge'}]})

props = [{'type': 'zzz', 'from': {'rel': i, 'up': 1.6, 't': 0.6}, 't0': 0, 't1': 0.01, 't2': 2.2, 'size': 0.9, 'phase': k * 0.3} for k, i in enumerate(G['beach']['members'][:6])]
props += [
    {'type': 'flame', 'from': [-73.5, -19.5], 't0': 10.8, 't1': 10.81, 't2': 14.6, 'size': 1.6},
    {'type': 'flame', 'from': FIRE_AT, 't0': 14.6, 't1': 14.61, 't2': 26.0, 'size': 1.6},
]

def star(i, a, b, bubble=True):
    if not inr(i): return None
    return {'who': i, 'from': a, 'to': b, **({'bubble': said[i]} if bubble and said.get(i) else {})}
stars = [x for x in [star(SAORI, 9.8, 12.6), star(TOMO, 12.7, 14.5), star(TSUKI, 14.8, 18.2), star(YURA, 22.2, 26.0, False), star(AO, 31.6, 34.3)] if x]
overlay = {
    'banner': 'コメントで動く無人島　4日目',
    'bannerOff': [[0, 6.0], [44.5, DUR]],
    'commenters': commenters,
    'names': {c['userId']: name_of(c) for c in cm if c.get('userId')},
    'titles': [{'text': '4日目', 'from': 0.1, 'to': 3.0}],
    'tagAll': [[0.3, 3.0, 0.08]],
    'stars': stars,
    'ranking': {'from': 6.0, 'to': 9.6, 'title': '昨日の質問　いいねが多かった案', 'winnerAt': 8.0,
                'rows': [{'name': name_of(c), 'text': c['text'], 'likes': c.get('likes', 0)} for c in top]},
    'images': [
        {'file': 'profile.png', 'from': 3.0, 'to': 4.6, 'w': 900, 'y': 600, 'tap': [0.24, 0.905], 'tapLabel': 'フォローすると…'},
        {'file': 'profile.png', 'from': 4.6, 'to': 6.0, 'w': 900, 'y': 600, 'tap': [0.37, 0.78], 'tapLabel': '島のいまは、ここ'},
        {'file': 'profile.png', 'from': 44.6, 'to': DUR, 'w': 900, 'y': 520, 'tap': [0.37, 0.78], 'tapLabel': 'ここから'},
    ],
    'captions': [
        {'text': f'フォローした{n_arrive}人が、流れ着いた' if n_arrive else '新しい仲間が、流れ着いた', 'from': 0.4, 'to': 3.0, 'y': 1290, 'size': 66},
        {'text': 'あなたも、次の動画で流れ着きます', 'from': 3.1, 'to': 4.6, 'y': 1400, 'size': 50, 'color': [255, 214, 74]},
        {'text': 'ゆらさん、発見', 'from': 24.6, 'to': 26.0, 'y': 1290, 'size': 84},
        {'text': 'この島には、前にも誰かいた…？', 'from': 29.6, 'to': 31.5, 'y': 360, 'size': 52, 'color': [255, 214, 74]},
        {'text': 'みんなの声', 'from': 34.3, 'to': 37.5, 'y': 220, 'size': 1},
        {'text': '次の質問', 'from': 37.6, 'to': 44.5, 'y': 330, 'size': 64, 'color': [255, 214, 74]},
        {'text': '森の奥の、昔の住人の跡。', 'from': 37.7, 'to': 44.5, 'y': 450, 'size': 60},
        {'text': 'どうする？', 'from': 37.7, 'to': 44.5, 'y': 545, 'size': 60},
        {'text': 'A 跡を直して、森の拠点に', 'from': 38.6, 'to': 44.5, 'y': 760, 'size': 52},
        {'text': 'B 石の道具をまねて作る', 'from': 39.2, 'to': 44.5, 'y': 860, 'size': 52},
        {'text': 'C 昔の住人の行方を探す', 'from': 39.8, 'to': 44.5, 'y': 960, 'size': 52},
        {'text': 'D 自由に提案', 'from': 40.4, 'to': 44.5, 'y': 1060, 'size': 52},
        {'text': 'A・B・C・Dでコメントしてね', 'from': 41.0, 'to': 44.5, 'y': 1300, 'size': 50, 'color': [255, 214, 74]},
        {'text': 'あなたの島民のいまは、', 'from': 44.7, 'to': DUR, 'y': 1300, 'size': 54},
        {'text': 'プロフィールのリンクから', 'from': 44.7, 'to': DUR, 'y': 1390, 'size': 54},
    ],
    'action': [{'text': '火を焚く', 'from': 9.8, 'to': 14.6}, {'text': '松明を持って、森の奥へ', 'from': 14.8, 'to': 20.6},
               {'text': '奥の光へ', 'from': 20.7, 'to': 22.2}, {'text': '戦闘係', 'from': 31.6, 'to': 34.3}],
    'result': [{'text': '獣は、火をこわがる', 'from': 12.8, 'to': 14.6}, {'text': 'ゆらさんの、焚き火だった！', 'from': 22.3, 'to': 24.5},
               {'text': '昔だれかが暮らしていた跡', 'from': 28.0, 'to': 31.5}, {'text': '…ひとりだけ、気合十分。', 'from': 33.0, 'to': 34.3}],
    'wall': {'from': 34.3, 'to': 37.5, 'title': 'みんなの声', 'step': 0.08, 'items': [{'name': name_of(c), 'text': c['text'], 'vote': None} for c in cm]},
    'smallTagsMax': 5,
}
overlay['captions'] = [c for c in overlay['captions'] if c['size'] > 1]
narr = [
    {'at': 0.3, 'until': 3.0, 'text': f'{n_arrive}人が、流れ着いた！' if n_arrive else '4日目。'},
    {'at': 3.1, 'until': 4.6, 'text': 'フォローすると、あなたも。'},
    {'at': 4.7, 'until': 6.0, 'text': '島は、リンクから。'},
    {'at': 6.1, 'until': 8.0, 'text': '昨日の一番人気は…'},
    {'at': 8.1, 'until': 9.6, 'text': '夜になる前に、火を焚く！'},
    {'at': 12.8, 'until': 14.6, 'text': '獣は、火をこわがる。'},
    {'at': 15.0, 'until': 18.0, 'text': '松明を持って、森の奥へ。'},
    {'at': 18.3, 'until': 20.6, 'text': '奥に見えた光は…'},
    {'at': 22.3, 'until': 24.8, 'text': 'ゆらさんの焚き火だった！'},
    {'at': 26.2, 'until': 29.5, 'text': 'ゆらさんが見つけたのは、昔だれかが暮らした跡。'},
    {'at': 29.7, 'until': 31.5, 'text': '前にも、誰かいた…？'},
    {'at': 37.7, 'until': 44.4, 'text': '次の質問。昔の住人の跡、どうする？エー、ビー、シー、ディーでコメントしてね。'},
    {'at': 44.7, 'until': DUR, 'text': 'あなたの島民のいまは、プロフィールのリンクから。'},
]
story = {
    'title': '4日目', 'roster': ROSTER_REL, 'day': DAY, 'fps': 24, 'duration': DUR, 'hour': 10,
    'baseTime': '2026-11-20T09:00:00+09:00', 'base': {'name': '中央の広場', 'x': 0, 'z': 5, 'decidedDay': 2},
    'forestRoad': {'points': [[-74, -22], [-128, -34]], 'need': 300, 'startDay': 4, 'label': '光の場所', 'open': True},
    'buildings': [{'id': 'ruins-1', 'type': 'ruins', 'name': '昔の住人の跡', 'x': -44.7, 'z': -12.7, 'rot': 0, 'builtDay': 1}],
    'cast': list(dict.fromkeys(list(commenters) + crowd + arrivals[:22])), 'groups': groups, 'acts': acts, 'props': props, 'camera': camera,
    'overlay': overlay, 'override': {**{i: {'job': '探検家'} for i in searchers}},
    'audio': {'narration': narr, 'bgm': {'volume': 0.18}, 'speed': 1.15},
    'cover': {'at': 23.0, 'day': f'{DAY}日目', 'lines': ['火を持って、森の奥へ', 'そこにいたのは…']},
}
json.dump(story, open(os.path.join(HERE, 'story', 'ep4.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

# ---- PWA の続き（きょうの行動）と、Firebase の state に入れる差分 ----
today = []
def td(i, spot, anim, text, tool=None):
    if inr(i): today.append({'id': i, 'spot': spot, 'anim': anim, 'text': text, **({'tool': tool} if tool else {})})
td(YURA, 'plaza', 'talk', '森の奥で見つけた「昔の住人の跡」のことを、みんなに話している')
td(SAORI, 'forestEdge', 'work', '森の入口で、焚き火の番をしている')
td(TSUKI, 'forestEdge', 'idle', 'ゆらさん奪還作戦、成功。森の奥を見張っている', 'scope')
td(AO, 'forestEdge', 'cheer', '戦闘係として、森の入口で気合十分に見張っている')
for i in [NAKA, RYUJI, WAN]: td(i, 'forestEdge', 'idle', '森の奥の跡を、もう一度見に行く準備をしている', 'scope')
pwa = {'day': DAY, 'roster': ROSTER_REL, 'today': today, 'missing': {}}
json.dump(pwa, open(os.path.join(HERE, 'story', 'ep4_pwa.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
state = {
    'day': DAY,
    'forestRoad': story['forestRoad'],
    'districts_forest': {'id': 'forest', 'inRange': True, 'expandedDay': DAY, 'reason': '松明を持って、みんなで森へ入った（獣は火をこわがる）'},
    'buildings_add': story['buildings'],
    'chronicle_add': {'day': DAY, 'title': '火を持って森の奥へ。ゆらさん発見', 'text': '夜になる前に火を焚き、松明を持って森へ。奥の光はゆらさんの焚き火だった。そばには、昔だれかが暮らしていた跡が。',
                      'vote': {'question': '行方不明者がいる島で、みんなは何をする？', 'adopted': top[0]['text'] if top else '', 'note': 'いいね最多のコメントを採用'}},
    'currentVote': {'id': 'vote-004-ruins', 'status': 'open', 'question': '森の奥の、昔の住人の跡。どうする？',
                    'description': 'A・B・C・D でコメントしてね。コメントが一番多い案を採用します（Dが一番多いときは、Dの中でいいねが一番多い案）',
                    'options': [{'key': 'A', 'label': '跡を直して、森の拠点に'}, {'key': 'B', 'label': '石の道具をまねて作る'}, {'key': 'C', 'label': '昔の住人の行方を探す'}, {'key': 'D', 'label': '自由に提案'}]},
}
json.dump(state, open(os.path.join(HERE, 'story', 'ep4_state.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(json.dumps({'arrivals': n_arrive, 'top': [(name_of(c), c.get('likes')) for c in top], 'cast': len(story['cast']), 'today': len(today)}, ensure_ascii=False))
