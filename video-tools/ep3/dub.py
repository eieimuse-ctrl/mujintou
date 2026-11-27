#!/usr/bin/env python3
"""できあがった映像（声なし）に、声と BGM だけを入れる。映像は作り直さない（画質そのまま：-c:v copy）。
  python3 video-tools/ep3/voices.py video-tools/ep11/story/ep11.json    （声：video-tools/voices/ep11/*.wav）
  python3 video-tools/ep3/dub.py video-tools/ep11/story/ep11.json        （→ video-tools/out/ep11.mp4）
映像：video-tools/finished/<名前>_silent.mp4（Claude が録画・合成して入れたもの）。VIDEO=… で別の映像も使える
"""
import json, os, sys, hashlib, subprocess, wave
HERE = os.path.dirname(os.path.abspath(__file__))
story_path = os.path.abspath(sys.argv[1])
S = json.load(open(story_path, encoding='utf-8'))
NAME = os.path.splitext(os.path.basename(story_path))[0]
SPEED = float(S.get('audio', {}).get('speed', 1.0))
VIDEO = os.environ.get('VIDEO') or os.path.join(HERE, '..', 'finished', f'{NAME}_silent.mp4')
OUT = os.path.join(HERE, '..', 'out', f'{NAME}.mp4')
os.makedirs(os.path.dirname(OUT), exist_ok=True)
if not os.path.exists(VIDEO): sys.exit(f'映像が無い：{VIDEO}')

def voice(text, speaker=8):
    tag = f'{speaker}:{text}' if SPEED == 1.0 else f'{speaker}:{SPEED}:{text}'
    f = os.path.join(HERE, '..', 'voices', NAME, hashlib.md5(tag.encode()).hexdigest()[:12] + '.wav')
    if os.path.exists(f): return f
    print(f'!! 声が無い（先に voices.py を実行）：「{text}」')
    return None

inputs, filters, k = [], [], 0
narr = sorted(S.get('audio', {}).get('narration', []), key=lambda n: n['at'])
for j, n in enumerate(narr):
    f = voice(n['text'])
    if not f: continue
    nxt = narr[j + 1]['at'] if j + 1 < len(narr) else S['duration'] - 0.2
    room = min(n.get('until', nxt), nxt) - n['at'] - 0.12
    with wave.open(f) as w: dur = w.getnframes() / w.getframerate()
    tempo = min(1.3, dur / room) if dur > room else 1.0
    print(f'  {n["at"]:6.2f}s  {room:5.2f}s  {dur:5.2f}s  x{tempo:.2f}  {n["text"]}')
    inputs += ['-i', f]; ms = int(n['at'] * 1000)
    speed = f'atempo={tempo:.3f},' if tempo > 1.0 else ''  # atempo → adelay の順（逆にしない）
    filters.append(f'[{k + 1}:a]{speed}adelay={ms}|{ms},volume=1.0[n{k}]'); k += 1
bgm = os.environ.get('BGM') or os.path.join(HERE, '..', 'assets', 'bgm.mp3')
bg = S.get('audio', {}).get('bgm')
if bg and os.path.exists(bgm):
    inputs += ['-i', bgm]; dur = S['duration']
    filters.append(f'[{k + 1}:a]atrim=0:{dur},asetpts=PTS-STARTPTS,volume={bg.get("volume", 0.18)},afade=t=in:d=0.5,afade=t=out:st={max(0, dur - 2)}:d=2[n{k}]'); k += 1
if not k: sys.exit('入れる音が無い')
mix = ''.join(f'[n{j}]' for j in range(k)) + f'amix=inputs={k}:normalize=0:duration=longest,apad,atrim=0:{S["duration"]}[aout]'
cmd = ['ffmpeg', '-y', '-v', 'error', '-i', VIDEO] + inputs + ['-filter_complex', ';'.join(filters + [mix]), '-map', '0:v', '-map', '[aout]', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart', '-t', str(S['duration']), OUT]
subprocess.run(cmd, check=True)
print(f'出力：{OUT}（{os.path.getsize(OUT) / 1e6:.1f}MB、映像はそのまま）')
