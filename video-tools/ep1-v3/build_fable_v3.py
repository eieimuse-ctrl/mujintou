#!/usr/bin/env python3
"""ep1 v3 — one-shot build of out/ep1_fable_v3.mp4 (1080x1920, H.264/AAC, 57.0 s, faststart)
and the light copy out/ep1_fable_v3_preview.mp4 (780x1688 shown as 9:16 like the v1 preview, CRF 24, veryfast).

  python3 tools/build_fable_v3.py            check takes -> tracks -> compose (resumable) -> MKV -> MP4 -> verify -> preview
  python3 tools/build_fable_v3.py --force    re-compose every frame first

Needs: build/rec3/{a,b2,c,d} + build/rec3h/p (tools/fable_rec_v3.mjs, resumable) and the UI layers
build/ui3/hd/h*.png (tools/v3_ui_hd.mjs). The encode goes to Matroska first and is remuxed to MP4 under
a temp name: an MKV cut off by a VM restart is still readable, a half-written MP4 (no moov) is not.
Narration audio/n1..n8.wav and assets/bgm.mp3 are used as they are; mix = the v1 mix.
The earlier films (out/ep1_fable*.mp4) are not touched.
"""
import os, subprocess, sys, json
from concurrent.futures import ProcessPoolExecutor

V = os.path.expanduser('~/workspace/mujintou/video')
T = f'{V}/tools'
COMP, OUT = f'{V}/build/comp3', f'{V}/out'
FPS, N, DUR = 24, 1368, 57.0
TAKES = {'rec3/a': 306, 'rec3/b2': 173, 'rec3/c': 548, 'rec3/d': 132, 'rec3h/p': 233}
UI = ['h0_home', 'h1_list', 'h2_type1', 'h2_type2', 'h2_type3', 'h3_detail']
NARR = [('n1', 1.30), ('n2', 5.00), ('n3', 13.00), ('n4', 19.70), ('n5', 27.50), ('n7', 42.55), ('n8', 46.75), ('n6', 52.00)]
WORKERS = 3
NAME = 'ep1_fable_v3'


def run(cmd, **kw):
    print('+', ' '.join(str(c) for c in cmd)[:300], flush=True)
    return subprocess.run(cmd, check=True, **kw)


def jpeg_ok(path):
    if not os.path.exists(path) or os.path.getsize(path) < 1000: return False
    with open(path, 'rb') as fh:
        fh.seek(-2, 2)
        return fh.read() == b'\xff\xd9'


def compose_range(rng):
    sys.path.insert(0, T)
    import compose_fable_v3 as C
    lo, hi, force = rng
    done = 0
    for f in range(lo, hi):
        out = f'{COMP}/f{f:05d}.jpg'
        if not force and jpeg_ok(out): continue
        C.compose(f).save(out + f'.tmp{os.getpid()}', 'JPEG', quality=95, subsampling=0)
        os.replace(out + f'.tmp{os.getpid()}', out)
        done += 1
    return done


def probe(path):
    info = json.loads(subprocess.run(['ffprobe', '-v', 'error', '-show_streams', '-show_format', '-of', 'json', path], capture_output=True, text=True, check=True).stdout)
    v = next(s for s in info['streams'] if s['codec_type'] == 'video'); a = next(s for s in info['streams'] if s['codec_type'] == 'audio')
    with open(path, 'rb') as fh: blob = fh.read()
    return v, a, float(info['format']['duration']), len(blob), blob.find(b'moov') < blob.find(b'mdat')


def main():
    force = '--force' in sys.argv
    # 1. inputs complete?
    for take, n in TAKES.items():
        have = sum(1 for i in range(n) if jpeg_ok(f'{V}/build/{take}/f{i:05d}.jpg'))
        print(f'take {take}: {have}/{n}', flush=True)
        if have != n: sys.exit(f'take {take} incomplete -> cd tools && node fable_rec_v3.mjs {"--half " if "rec3h" in take else ""}{take.split("/")[1]}')
    for u in UI:
        if not os.path.exists(f'{V}/build/ui3/hd/{u}.png'): sys.exit(f'UI layer {u} missing -> cd tools && node v3_ui_hd.mjs')
    for n, _ in NARR:
        if not os.path.exists(f'{V}/audio/{n}.wav'): sys.exit(f'audio/{n}.wav missing')
    # 2. tracks + cameras (pure maths, checked against the recorder's own measurements)
    run(['node', f'{T}/fable_tracks_v3.mjs'])
    # 3. composite every film frame (skips frames already on disk)
    os.makedirs(COMP, exist_ok=True)
    step = 48
    with ProcessPoolExecutor(WORKERS) as ex:
        done = sum(ex.map(compose_range, [(lo, min(N, lo + step), force) for lo in range(0, N, step)]))
    have = sum(1 for f in range(N) if jpeg_ok(f'{COMP}/f{f:05d}.jpg'))
    print(f'composed {done} new frames, {have}/{N} on disk', flush=True)
    assert have == N
    # 4. encode -> MKV
    os.makedirs(OUT, exist_ok=True)
    mkv, mp4 = f'{OUT}/{NAME}.mkv', f'{OUT}/{NAME}.mp4'
    cmd = ['ffmpeg', '-hide_banner', '-loglevel', 'warning', '-stats', '-y', '-framerate', str(FPS), '-i', f'{COMP}/f%05d.jpg']
    for n, _ in NARR: cmd += ['-i', f'{V}/audio/{n}.wav']
    cmd += ['-i', f'{V}/assets/bgm.mp3']
    # JPEG (BT.601 full range) -> BT.709 limited; accurate_rnd keeps the round trip within 1-2 levels
    fc = ['[0:v]scale=in_color_matrix=bt601:in_range=pc:out_color_matrix=bt709:out_range=tv:flags=accurate_rnd+full_chroma_int,format=yuv420p,setsar=1[vout]']
    for k, (n, st) in enumerate(NARR, 1):
        fc.append(f'[{k}:a]aresample=48000,adelay={round(st * 1000)}:all=1,apad,atrim=end={DUR}[n{k}]')
    fc.append(''.join(f'[n{k}]' for k in range(1, len(NARR) + 1)) + f'amix=inputs={len(NARR)}:normalize=0,pan=stereo|c0=c0|c1=c0[voice]')
    fc.append(f'[{len(NARR) + 1}:a]aresample=48000,atrim=end={DUR},volume=0.15,afade=t=in:st=0:d=1,afade=t=out:st={DUR - 2}:d=2[bgm]')
    fc.append('[voice][bgm]amix=inputs=2:normalize=0,alimiter=limit=0.95,aformat=sample_rates=48000:channel_layouts=stereo[aout]')
    cmd += ['-filter_complex', ';'.join(fc), '-map', '[vout]', '-map', '[aout]',
            '-c:v', 'libx264', '-profile:v', 'high', '-preset', 'medium', '-crf', '20', '-g', '48', '-r', str(FPS),
            '-colorspace', 'bt709', '-color_primaries', 'bt709', '-color_trc', 'bt709', '-color_range', 'tv',
            '-c:a', 'aac', '-b:a', '192k', '-ar', '48000', '-t', str(DUR), mkv]
    run(cmd)
    # 5. remux -> MP4 (faststart), via a temp name so a cut-off remux never looks finished
    tmp = f'{OUT}/{NAME}.part.mp4'
    run(['ffmpeg', '-hide_banner', '-loglevel', 'warning', '-y', '-i', mkv, '-c', 'copy', '-movflags', '+faststart', tmp])
    os.replace(tmp, mp4)
    # 6. verify
    v, a, dur, size, fast = probe(mp4)
    print(f"VERIFY {v['codec_name']} {v['profile']} {v['width']}x{v['height']} {v['pix_fmt']} {v['r_frame_rate']} frames={v.get('nb_frames')} | "
          f"{a['codec_name']} {a['sample_rate']}Hz ch={a['channels']} | duration={dur:.3f}s size={size / 1e6:.1f}MB faststart={fast}", flush=True)
    ok = v['codec_name'] == 'h264' and (v['width'], v['height']) == (1080, 1920) and a['codec_name'] == 'aac' and abs(dur - DUR) < 0.05 and fast
    if not ok:
        print('BUILD FAILED CHECKS'); sys.exit(1)
    # 7. light preview (same look as out/ep1_fable_preview.mp4: 780x1688 stored, 9:16 displayed)
    prev, ptmp = f'{OUT}/{NAME}_preview.mp4', f'{OUT}/{NAME}_preview.part.mp4'
    run(['ffmpeg', '-hide_banner', '-loglevel', 'warning', '-stats', '-y', '-i', mp4, '-vf', 'scale=780:1688:flags=lanczos',
         '-c:v', 'libx264', '-profile:v', 'high', '-preset', 'veryfast', '-crf', '24', '-g', '48', '-pix_fmt', 'yuv420p',
         '-colorspace', 'bt709', '-color_primaries', 'bt709', '-color_trc', 'bt709', '-color_range', 'tv',
         '-c:a', 'aac', '-b:a', '160k', '-movflags', '+faststart', ptmp])
    os.replace(ptmp, prev)
    v, a, dur, size, fast = probe(prev)
    print(f"PREVIEW {v['codec_name']} {v['width']}x{v['height']} sar={v.get('sample_aspect_ratio')} dar={v.get('display_aspect_ratio')} | "
          f"{a['codec_name']} {a['sample_rate']}Hz | duration={dur:.3f}s size={size / 1e6:.1f}MB faststart={fast}", flush=True)
    print('BUILD OK')


if __name__ == '__main__':
    main()
