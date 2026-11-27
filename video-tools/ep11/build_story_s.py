#!/usr/bin/env python3
"""11日目のストーリー（約10秒）：晴れた島が、突然厚い雲に囲まれる → 雷・大雨 → 洞窟の奥の光る目。
  python3 video-tools/ep11/build_story_s.py   （先に build_story.py を実行しておく）
出力：ep11/story/ep11s.json → ep3/run.sh で video-tools/out/ep11s.mp4
"""
import json, os
HERE = os.path.dirname(os.path.abspath(__file__))
E = json.load(open(os.path.join(HERE, 'story', 'ep11.json'), encoding='utf-8'))
CAVE = [92.0, -156.0]
DUR = 10.0
W = lambda look, dist, az, pol, up, t, fov=42: {'t': t, 'look': look, 'dist': dist, 'az': az, 'pol': pol, 'up': up, 'frame': 'south', 'fov': fov}
FL = [2.3, 3.6, 4.5, 6.15, 7.0]
camera = [
    # 晴れた島（真上の引き）→ 一気に降りる
    {'from': 0, 'to': 1.6, 'hour': 12, 'keys': [W([0, 0], 1700, 0.0, 0.45, 0, 0, 40), W([0, 0], 1300, 0.5, 0.55, 0, 1.6, 40)]},
    # 嵐：低く島の上を飛ぶ（稲光で揺れる）
    {'from': 1.6, 'to': 5.2, 'hour': 20.6, 'shake': [[f, f + 0.6, 2.2] for f in FL[:3]], 'keys': [W([0, 0], 700, 1.2, 0.7, 0, 1.6, 46), W([40, -60], 260, 2.2, 0.95, 0, 3.4, 48), W([CAVE[0], CAVE[1] + 30], 90, 2.9, 1.05, 4, 5.2, 46)]},
    # 洞窟へ突っこむ → 稲光で目が浮かぶ
    {'from': 5.2, 'to': DUR, 'hour': 21.5, 'shake': [[FL[3], FL[3] + 0.7, 1.6], [FL[4], FL[4] + 0.5, 1.0]], 'keys': [W([CAVE[0], CAVE[1] + 4], 40, 0.4, 1.1, 3, 5.2, 46), W([CAVE[0], CAVE[1] + 3], 20, 0.05, 1.18, 2.4, 6.6, 38), W([CAVE[0], CAVE[1] + 3], 15, 0.0, 1.22, 2.2, DUR, 34)]},
]
props = [{'type': 'eyes', 'from': {'xz': [CAVE[0], CAVE[1] + 2.4], 'up': 1.8}, 't0': FL[3] + 0.05, 't1': FL[3] + 0.06, 't2': DUR, 'size': 0.6}]
story = {
    'title': '11日目ストーリー', 'roster': E['roster'], 'day': E['day'], 'fps': 24, 'duration': DUR, 'hour': 12,
    'baseTime': E['baseTime'], 'base': E['base'], 'forestRoad': E['forestRoad'], 'toolAge': E['toolAge'], 'clearings': E['clearings'],
    'buildings': E['buildings'], 'cast': E['cast'][:1], 'groups': [{'name': 'south', 'type': 'line', 'spot': [0, 0], 'face': [0, 1], 'members': []}],
    'acts': [{'who': '*', 't': 0, 'anim': 'idle', 'hide': True}], 'props': props, 'props3d': [], 'camera': camera,
    'overlay': {
        'banner': '', 'bannerOff': [[0, DUR]], 'commenters': {}, 'names': {}, 'smallTagsMax': 0, 'tagCycle': [],
        'storm': [{'from': 0.5, 'to': 5.2, 'ramp': 1.3, 'dark': 0.35, 'clouds': 1.0, 'rain': 1.0, 'flashes': FL[:3]}, {'from': 5.2001, 'to': DUR, 'ramp': 0.01, 'dark': 0.2, 'clouds': 0.3, 'rain': 0.8, 'flashes': FL[3:]}],
        'captions': [
            {'text': '突然、島が', 'from': 0.2, 'to': 1.5, 'y': 330, 'size': 66},
            {'text': '厚い雲に、囲まれた', 'from': 1.0, 'to': 2.3, 'y': 430, 'size': 70, 'color': [220, 230, 255]},
            {'text': '雷', 'from': 2.3, 'to': 3.5, 'y': 520, 'size': 150, 'color': [255, 240, 120]},
            {'text': '大雨', 'from': 3.6, 'to': 5.1, 'y': 520, 'size': 150, 'color': [200, 220, 255]},
            {'text': 'そして、洞窟の奥で…', 'from': 5.2, 'to': 6.1, 'y': 330, 'size': 58},
            {'text': '目が、光った', 'from': 6.2, 'to': DUR, 'y': 330, 'size': 84, 'color': [255, 225, 74]},
            {'text': '今夜18:30、島の投稿で', 'from': 7.6, 'to': DUR, 'y': 1500, 'size': 56, 'color': [255, 255, 255]},
        ],
    },
    'audio': {'narration': [
        {'at': 0.2, 'until': 2.2, 'text': '突然、島が、厚い雲に囲まれた。'},
        {'at': 2.3, 'until': 3.5, 'text': '雷！'},
        {'at': 3.6, 'until': 5.1, 'text': '大雨！'},
        {'at': 5.2, 'until': 7.4, 'text': 'そして、洞窟の奥で、目が光った。'},
        {'at': 7.6, 'until': DUR, 'text': '今夜、六時半。'},
    ], 'bgm': {'volume': 0.22}, 'speed': 1.15},
}
json.dump(story, open(os.path.join(HERE, 'story', 'ep11s.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(json.dumps({'duration': DUR}))
