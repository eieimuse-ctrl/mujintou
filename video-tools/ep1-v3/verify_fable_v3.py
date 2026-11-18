#!/usr/bin/env python3
"""Checks on the finished out/ep1_fable_v3.mp4 (run after build_fable_v3.py).

  python3 tools/verify_fable_v3.py   -> decode errors, narration positions, one contact sheet check/v3/sheet.jpg
"""
import os, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont

V = os.path.expanduser('~/workspace/mujintou/video')
MP4 = f'{V}/out/ep1_fable_v3.mp4'
CHK = f'{V}/check/v3'
NARR = [('n1', 1.30), ('n2', 5.00), ('n3', 13.00), ('n4', 19.70), ('n5', 27.50), ('n7', 42.55), ('n8', 46.75), ('n6', 52.00)]
SR = 8000  # plenty for locating speech
SHEET_T = [2.5, 11.5, 18.6, 25.9, 44.6, 47.8, 50.6, 55.9]


def pcm(path):
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', path, '-ac', '1', '-ar', str(SR), '-f', 's16le', '-'], capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.int16).astype(np.float32) / 32768


def main():
    os.makedirs(CHK, exist_ok=True)
    err = subprocess.run(['ffmpeg', '-v', 'error', '-i', MP4, '-f', 'null', '-'], capture_output=True, text=True).stderr.strip()
    print('full decode:', 'no errors' if not err else f'{len(err.splitlines())} error lines\n' + err[:500])
    mix = pcm(MP4)
    print(f'audio {len(mix) / SR:.3f}s  peak {20 * np.log10(np.abs(mix).max() + 1e-9):.1f} dBFS')
    worst = 0
    for n, st in NARR:
        x = pcm(f'{V}/audio/{n}.wav')
        lo = int((st - 0.5) * SR); seg = mix[lo:lo + len(x) + SR]
        c = np.correlate(seg, x, 'valid')
        off = (lo + int(np.argmax(c))) / SR
        worst = max(worst, abs(off - st))
        print(f'  {n}: planned {st:6.2f}s  found {off:7.3f}s  (diff {1000 * (off - st):+.0f} ms)')
    print('narration positions', 'OK' if worst < 1 / 24 else 'OFF', f'(worst {1000 * worst:.0f} ms)')
    F = ImageFont.truetype('/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc', 26)
    S = Image.new('RGB', (len(SHEET_T) * 304, 540), (255, 0, 255))
    for k, t in enumerate(SHEET_T):
        out = f'{CHK}/t{t:05.2f}.jpg'
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', f'{t}', '-i', MP4, '-frames:v', '1', '-q:v', '2', out], check=True)
        im = Image.open(out).convert('RGB').resize((300, 533), Image.LANCZOS)
        ImageDraw.Draw(im).text((6, 500), f'{t:.1f}s', font=F, fill=(255, 255, 0), stroke_width=3, stroke_fill=(0, 0, 0))
        S.paste(im, (k * 304, 0))
    S.save(f'{CHK}/sheet.jpg', quality=86)
    print('sheet', f'{CHK}/sheet.jpg')


if __name__ == '__main__':
    main()
