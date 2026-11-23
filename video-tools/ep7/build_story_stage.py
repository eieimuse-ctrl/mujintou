#!/usr/bin/env python3
"""ステージの場所アンケート用ストーリー（約10秒）：拠点でさかさんが「娯楽が欲しい…」→ 4か所に建った様子を順に見せる。
  python3 video-tools/ep7/build_story_stage.py   （先に build_story.py を実行しておく）
出力：ep7/story/stage_s.json → ep3/run.sh で video-tools/out/stage_s.mp4（声なし・BGMのみ）
"""
import json, os
HERE = os.path.dirname(os.path.abspath(__file__))
E = json.load(open(os.path.join(HERE, 'story', 'ep7.json'), encoding='utf-8'))
SAKA = 'sakasaka_1482'
POOL = [c for c in E['cast'] if c != SAKA]
HUT = [-60.0, -15.0]
SITES = [('A', '砂浜', [215.0, 105.0]), ('B', '中央の広場のそば', [22.0, 34.0]), ('C', '入り江', [20.0, 165.0]), ('D', '切りひらいた森', [-100.0, 0.0])]
T0, OV, CUT = 2.4, 2.2, 1.5
T1 = T0 + OV
DUR = T1 + CUT * 4
blds = list(E['buildings']) + [{'id': 'bearhouse-1', 'type': 'bearhouse', 'name': 'クマの家', 'x': -88 / 3, 'z': -36 / 3, 'rot': 0, 'builtDay': 7}]
groups = [{'name': 'base', 'type': 'ring', 'spot': [HUT[0] - 5, HUT[1] + 4], 'radius': 3.0, 'gap': 2.6, 'members': POOL[:5]}]
acts = [{'who': '*', 't': 0, 'anim': 'idle', 'face': 'front'},
        {'who': SAKA, 't': 0, 'at': [HUT[0] + 2, HUT[1] + 8], 'anim': 'idle', 'face': 'front', 'hide': False},
        {'who': POOL[:5], 't': 0, 'at': {'slot': 'base'}, 'anim': 'idle'},
        {'who': SAKA, 't': 1.2, 'anim': 'talk'}]
cams = [{'from': 0, 'to': T0, 'hour': 17.6, 'keys': [{'t': 0, 'look': [HUT[0] + 2, HUT[1] + 8], 'dist': 30, 'az': -0.5, 'pol': 1.15, 'up': 1.8, 'frame': 'base'},
                                                    {'t': T0, 'look': [HUT[0] + 2, HUT[1] + 8], 'dist': 16, 'az': -0.2, 'pol': 1.28, 'up': 1.6, 'frame': 'base'}]}]
caps = [{'text': '拠点で、さかさんが…', 'from': 0.2, 'to': T0, 'y': 330, 'size': 60, 'color': [255, 214, 74]}]
k = 5
for n, (L, name, (x, z)) in enumerate(SITES):
    blds.append({'id': f'stage-{L}', 'type': 'stage', 'name': 'ステージ', 'x': round(x / 3, 2), 'z': round(z / 3, 2), 'rot': 0, 'builtDay': 7})
    aud, perf = POOL[k:k + 9], POOL[k + 9:k + 12]; k += 12
    groups.append({'name': f'aud{L}', 'type': 'line', 'spot': [x, z + 9.5], 'face': [0, -1], 'gap': 1.9, 'rows': 2, 'members': aud})
    acts.append({'who': aud, 't': 0, 'at': {'slot': f'aud{L}'}, 'anim': 'cheer', 'face': {'at': [x, z]}})
    for j, (dx, dz) in enumerate([(0, 0.4), (-2.2, 0.0), (2.2, 0.0)]):
        acts.append({'who': perf[j], 't': 0, 'at': {'xz': [x + dx, z + dz], 'up': 1.1}, 'anim': 'cheer' if j else 'talk', 'face': 'front', 'hide': False})
    a, b = T1 + n * CUT, T1 + (n + 1) * CUT
    cams.append({'from': a, 'to': b, 'hour': 18.7, 'keys': [{'t': a, 'look': [x, z + 1], 'dist': 34, 'az': 3.14 - 0.45, 'pol': 1.1, 'up': 2.5, 'frame': f'aud{L}'},
                                                            {'t': b, 'look': [x, z + 1], 'dist': 26, 'az': 3.14 + 0.35, 'pol': 1.18, 'up': 2.5, 'frame': f'aud{L}'}]})
    caps.append({'text': f'{L}　{name}', 'from': a + 0.05, 'to': b, 'y': 1360, 'size': 84, 'color': [255, 255, 255]})
# 全体像：島を引きで見て、A〜D の位置に札
cams.insert(1, {'from': T0, 'to': T1, 'hour': 18.2, 'keys': [{'t': T0, 'look': [52, 78], 'dist': 800, 'az': 3.14 - 1.3, 'pol': 0.72, 'up': 0, 'frame': 'audA'},
                                                       {'t': T1, 'look': [48, 76], 'dist': 720, 'az': 3.14 - 1.22, 'pol': 0.7, 'up': 0, 'frame': 'audA'}]})
props = [{'type': 'sack', 'from': [x, z], 't0': T0, 't1': T0 + 0.01, 't2': T1, 'size': 0.01, 'label': L} for L, _, (x, z) in SITES]
ptags = [{'label': L, 'text': f'{L}　{nm}', 'from': T0 + 0.2 + i * 0.25, 'to': T1, 'size': 60} for i, (L, nm, _) in enumerate(SITES)]
caps.append({'text': 'ステージ、どこに建てる？', 'from': T0, 'to': DUR, 'y': 300, 'size': 70, 'color': [255, 214, 74]})
story = {
    'title': 'ステージの場所ストーリー', 'roster': E['roster'], 'day': 7, 'fps': 24, 'duration': DUR, 'hour': 18,
    'baseTime': E['baseTime'], 'base': E['base'], 'forestRoad': E['forestRoad'], 'toolAge': E['toolAge'], 'clearings': E['clearings'],
    'buildings': blds, 'cast': [SAKA] + POOL[:k], 'groups': groups, 'acts': acts, 'props': props, 'props3d': [], 'camera': cams,
    'overlay': {'banner': '', 'bannerOff': [[0, DUR]], 'commenters': {}, 'names': E['overlay']['names'], 'smallTagsMax': 0, 'tagCycle': [], 'propTags': ptags,
                'stars': [{'who': SAKA, 'from': 0.6, 'to': T0, 'bubble': '娯楽が欲しい…'}], 'captions': caps},
    'audio': {'narration': [
        {'at': 0.5, 'until': T0, 'text': '娯楽が、欲しい…'},
        {'at': T0 + 0.1, 'until': T1, 'text': 'ステージ、どこに建てる？'},
    ] + [{'at': T1 + n * CUT + 0.1, 'until': T1 + (n + 1) * CUT, 'text': t} for n, t in enumerate(['エー、砂浜。', 'ビー、広場のそば。', 'シー、入り江。', 'ディー、切りひらいた森。'])], 'bgm': {'volume': 0.22}, 'speed': 1.15},
}
json.dump(story, open(os.path.join(HERE, 'story', 'stage_s.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(json.dumps({'cast': len(story['cast']), 'duration': DUR}))
