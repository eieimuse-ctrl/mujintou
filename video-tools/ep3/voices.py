#!/usr/bin/env python3
"""ナレーションの声だけを作る（VOICEVOX がある所＝Muse で実行）。映像の録画・合成は別の所（Claude）でできる。
  python3 video-tools/ep3/voices.py video-tools/ep7/story/ep7.json
→ video-tools/voices/<名前>/*.wav（compose.py と同じファイル名）。これを push すると、compose.py が声に使う。
"""
import os, sys, json, hashlib, urllib.request, urllib.parse
story_path = os.path.abspath(sys.argv[1]); NAME = os.path.splitext(os.path.basename(story_path))[0]
S = json.load(open(story_path, encoding='utf-8'))
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, '..', 'voices', NAME); os.makedirs(OUT, exist_ok=True)
VV = os.environ.get('VOICEVOX', 'http://127.0.0.1:50021')
SPEED = float(S.get('audio', {}).get('speed', 1.0))
n = 0
for line in S.get('audio', {}).get('narration', []):
    text, speaker = line['text'], 8
    tag = f'{speaker}:{text}' if SPEED == 1.0 else f'{speaker}:{SPEED}:{text}'
    f = os.path.join(OUT, hashlib.md5(tag.encode()).hexdigest()[:12] + '.wav')
    if os.path.exists(f): continue
    q = urllib.request.urlopen(urllib.request.Request(f'{VV}/audio_query?speaker={speaker}&text={urllib.parse.quote(text)}', method='POST'), timeout=20).read()
    if SPEED != 1.0:
        qj = json.loads(q); qj['speedScale'] = SPEED; q = json.dumps(qj).encode()
    wav = urllib.request.urlopen(urllib.request.Request(f'{VV}/synthesis?speaker={speaker}', data=q, headers={'content-type': 'application/json'}, method='POST'), timeout=60).read()
    open(f, 'wb').write(wav); n += 1
print(f'{NAME}: 声 {n} 本を作った → {OUT}')
