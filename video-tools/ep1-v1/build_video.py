#!/usr/bin/env python3
"""Assemble episode-1 draft: canvas frames @12fps + VOICEVOX narration + BGM.
Timeline (47.5s): seg1 overview 5.0 / seg2 districts 10.0 / seg3 beach+silhouette 5.0 /
seg4 demo life 9.0 / seg5 A-B-C b-roll + vote card 14.6 / seg6 closing 3.9"""
import subprocess, os, sys

V = os.path.expanduser('~/workspace/mujintou/video')
SHOTS, AUDIO, ASSETS, OUT = f'{V}/shots', f'{V}/audio', f'{V}/assets', f'{V}/out'
FONT = '/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc'
W, H = 1080, 1920

def seg(path, fps=12, start=0):
    return ['-framerate', str(fps), '-start_number', str(start), '-i', f'{path}/f%05d.jpg']

inputs = []
inputs += seg(f'{SHOTS}/s1_overview')                 # 0  60f 5.0s
for d in ['beach', 'cove', 'plain', 'forest', 'highland']:
    inputs += seg(f'{SHOTS}/s2_{d}')                  # 1-5 24f 2.0s each
inputs += seg(f'{SHOTS}/s3_beach')                    # 6  60f 5.0s
inputs += seg(f'{SHOTS}/s4_demo_wide')                # 7  48f 4.0s
inputs += seg(f'{SHOTS}/s5_demo_follow')              # 8  60f 5.0s
inputs += seg(f'{SHOTS}/s2_plain')                    # 9  A 2.0s
inputs += seg(f'{SHOTS}/s2_cove')                     # 10 B 2.0s
inputs += seg(f'{SHOTS}/s2_beach')                    # 11 C 2.0s
inputs += ['-loop', '1', '-t', '8.6', '-i', f'{SHOTS}/s6_vote/f00001.jpg']  # 12 card 8.6s
inputs += seg(f'{SHOTS}/s7_closing')                  # 13 46f 3.83s
inputs += ['-loop', '1', '-framerate', '24', '-t', '21', '-i', f'{ASSETS}/silhouette_you.png']  # 14
for n in ['n1', 'n2', 'n3', 'n4', 'n5', 'n6']:
    inputs += ['-i', f'{AUDIO}/{n}.wav']              # 15-20
inputs += ['-i', f'{ASSETS}/bgm.mp3']                 # 21

counts = [60, 24, 24, 24, 24, 24, 60, 48, 60, 24, 24, 24]
fc = []
for i, c in enumerate(counts):
    fc.append(f'[{i}:v]scale={W}:-2,crop={W}:{H},setsar=1,trim=end_frame={c},setpts=PTS-STARTPTS[v{i}]')
fc.append(f'[12:v]scale={W}:-2,crop={W}:{H},setsar=1,fps=12,trim=end_frame=103,setpts=PTS-STARTPTS[v12]')
fc.append(f'[13:v]scale={W}:-2,crop={W}:{H},setsar=1,trim=end_frame=46,setpts=PTS-STARTPTS[v13]')
fc.append(''.join(f'[v{i}]' for i in range(14)) + 'concat=n=14:v=1:a=0,fps=24[vc]')
fc.append('[14:v]scale=300:-1,format=rgba,fade=t=in:st=15.8:d=0.6:alpha=1,fade=t=out:st=19.2:d=0.6:alpha=1[sil]')
fc.append('[vc][sil]overlay=x=(W-w)/2:y=H*0.50:enable=\'between(t,15.0,20.0)\'[vo]')

def dt(text, st, en, size, y, x='(w-text_w)/2'):
    return (f"drawtext=fontfile={FONT}:text='{text}':fontsize={size}:fontcolor=white:"
            f"borderw=3:bordercolor=black@0.55:x={x}:y={y}:enable='between(t,{st},{en})'")

texts = [
    dt('無人島プロジェクト', 0.5, 4.8, 76, 250),
    dt('コメントで育つ、架空の島の開拓シミュレーション', 0.5, 4.8, 34, 350),
    dt('砂浜', 5.2, 6.9, 44, 'h-300'),
    dt('入り江', 7.2, 8.9, 44, 'h-300'),
    dt('平原', 9.2, 10.9, 44, 'h-300'),
    dt('森（獣がいて危険）', 11.2, 12.9, 44, 'h-300'),
    dt('高原（寒くて厳しい）', 13.2, 14.9, 44, 'h-300'),
    dt('フォローすると、あなたも島民に', 15.6, 19.6, 40, 'h-260'),
    dt('A 平原', 29.2, 31.0, 54, 200, x='60'),
    dt('B 入り江', 31.2, 33.0, 54, 200, x='60'),
    dt('C 砂浜', 33.2, 35.0, 54, 200, x='60'),
    dt('無人島プロジェクト', 43.8, 47.3, 84, 700),
    dt('まもなく始まります', 43.8, 47.3, 44, 810),
    dt('フォローして、最初の漂着者になろう', 43.8, 47.3, 34, 900),
]
fc.append('[vo]' + ','.join(texts) + '[vout]')

delays = [(15, 400), (16, 5400), (17, 15400), (18, 20600), (19, 29200), (20, 43900)]
for idx, ms in delays:
    fc.append(f'[{idx}:a]adelay={ms}:all=1,apad,atrim=end=47.5[v{idx}]')
fc.append(''.join(f'[v{i}]' for i, _ in delays) + 'amix=inputs=6:normalize=0[voice]')
fc.append('[21:a]atrim=end=47.5,volume=0.15,afade=t=in:st=0:d=1,afade=t=out:st=45.5:d=2[bgm]')
fc.append('[voice][bgm]amix=inputs=2:normalize=0,alimiter=limit=0.95[aout]')

os.makedirs(OUT, exist_ok=True)
cmd = ['ffmpeg', '-y'] + inputs + [
    '-filter_complex', ';'.join(fc),
    '-map', '[vout]', '-map', '[aout]',
    '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-r', '24', '-crf', '21', '-preset', 'veryfast',
    '-c:a', 'aac', '-b:a', '160k', '-t', '47.5',
    f'{OUT}/ep1_draft.mkv',
]
r = subprocess.run(cmd, capture_output=True, text=True)
print(r.stderr[-3000:] if r.returncode else 'OK')
sys.exit(r.returncode)
