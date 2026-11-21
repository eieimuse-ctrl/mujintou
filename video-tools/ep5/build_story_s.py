#!/usr/bin/env python3
"""5日目のストーリー用（約12秒）：夕方の浜に、大きな木箱が流れ着く。
  python3 video-tools/ep5/build_story_s.py   （先に build_story.py を実行しておく）
出力：ep5/story/ep5s.json → run.sh で video-tools/out/ep5s.mp4
ストーリーに載せるときは、リンクスタンプで島（https://eieimuse-ctrl.github.io/mujintou/）を付ける。
"""
import json, os, math

HERE = os.path.dirname(os.path.abspath(__file__))
E = json.load(open(os.path.join(HERE, 'story', 'ep5.json'), encoding='utf-8'))
LAND, SEA = [238.0, 147.0], [276.0, 180.0]
G = {g['name']: g for g in E['groups']}
crowd = G['shore']['members']
DUR = 12.0

acts = [{'who': '*', 't': 0, 'anim': 'idle', 'face': 'front'},
        {'who': crowd, 't': 0, 'at': {'slot': 'shore'}, 'anim': 'idle', 'face': {'at': SEA}},
        {'who': crowd, 't': 3.4, 'anim': 'shock'}]
for k, i in enumerate(crowd):
    a = 0.4 + k * 0.48
    acts.append({'who': i, 't': 4.6 + (k % 4) * 0.12, 'to': [LAND[0] - 5.5 + 6.3 * math.cos(a), LAND[1] - 5.5 + 2.8 * math.sin(a)], 'dur': 1.4, 'run': True})
    acts.append({'who': i, 't': 6.3, 'anim': 'cheer' if k % 3 == 0 else 'idle', 'face': {'at': LAND}})

story = {
    'title': '5日目ストーリー', 'roster': E['roster'], 'day': E['day'], 'fps': 24, 'duration': DUR, 'hour': 17.4,
    'baseTime': E['baseTime'], 'base': E['base'], 'forestRoad': E['forestRoad'], 'toolAge': 'stone', 'buildings': E['buildings'],
    'cast': crowd, 'groups': [G['shore'], {**G['edge'], 'members': []}],
    'acts': acts,
    'props': [{'type': 'question', 'from': LAND, 't0': 6.4, 't1': 6.41, 't2': DUR, 'size': 4}],
    'props3d': [{'type': 'float', 'kind': 'bigcrate', 'from': SEA, 'at': LAND, 'rot': 35, 't0': 0, 't1': 5.0, 'show': 0, 'sink': 2.4}],
    'camera': [
        {'from': 0, 'to': 6.4, 'hour': 17.3, 'keys': [{'t': 0, 'look': [LAND[0] + 14, LAND[1] + 12], 'dist': 44, 'az': 3.3, 'pol': 1.12, 'up': 2.0, 'frame': 'shore'},
                                                      {'t': 6.4, 'look': LAND, 'dist': 32, 'az': 3.45, 'pol': 1.1, 'up': 3.0, 'frame': 'shore'}]},
        {'from': 6.4, 'to': DUR, 'hour': 17.5, 'keys': [{'t': 6.4, 'look': LAND, 'dist': 30, 'az': 3.6, 'pol': 1.12, 'up': 3.0, 'frame': 'shore'},
                                                        {'t': DUR, 'look': LAND, 'dist': 38, 'az': 4.1, 'pol': 1.04, 'up': 3.5, 'frame': 'shore'}]},
    ],
    'overlay': {
        'banner': '無人島プロジェクト　5日目', 'bannerOff': [[0, DUR]], 'commenters': {}, 'names': {}, 'smallTagsMax': 0,
        'captions': [
            {'text': '夕方の浜に…', 'from': 0.3, 'to': 3.3, 'y': 360, 'size': 64, 'color': [255, 214, 74]},
            {'text': '大きな木箱が、流れ着いた！', 'from': 3.4, 'to': 6.3, 'y': 360, 'size': 64},
            {'text': '中身はなんだろう？', 'from': 6.4, 'to': DUR, 'y': 330, 'size': 72, 'color': [255, 214, 74]},
            {'text': '予想は、最新の投稿にコメントで', 'from': 7.4, 'to': DUR, 'y': 1300, 'size': 50},
            {'text': '木箱は、いまも島の浜にあります', 'from': 8.6, 'to': DUR, 'y': 1390, 'size': 50},
        ],
    },
    'audio': {'narration': [
        {'at': 0.3, 'until': 3.3, 'text': '夕方の浜に…'},
        {'at': 3.4, 'until': 6.3, 'text': '大きな木箱が、流れ着いた！'},
        {'at': 6.4, 'until': 9.0, 'text': '中身は、なんだろう？'},
        {'at': 9.1, 'until': DUR, 'text': '予想は、投稿にコメントしてね。'},
    ], 'bgm': {'volume': 0.18}, 'speed': 1.15},
    'cover': {'at': 7.0, 'day': '5日目', 'lines': ['大きな木箱が', '流れ着いた']},
}
json.dump(story, open(os.path.join(HERE, 'story', 'ep5s.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(json.dumps({'cast': len(crowd), 'duration': DUR}))
