#!/usr/bin/env python3
"""ep1 revision — one-shot build of video/out/ep1_fable.mp4 (1080x1920, H.264/AAC, 48.0 s, faststart).

  python3 tools/build_fable.py            compose (resumable) -> encode MKV -> remux MP4 -> verify
  python3 tools/build_fable.py --force    re-compose every frame first

Needs the three recorded takes in build/rec/{a,b,c} (tools/fable_rec.mjs, resumable).
The encode goes to Matroska first and is remuxed to MP4 afterwards: an MKV that is cut off
by a VM restart is still readable, a half-written MP4 (no moov) is not.
Narration (audio/n1..n6.wav) and BGM (assets/bgm.mp3) are used as they are; mix = draft mix.
"""
import os, subprocess, sys, json
from concurrent.futures import ProcessPoolExecutor

V = os.path.expanduser('~/workspace/mujintou/video')
T = f'{V}/tools'
REC, COMP, OUT = f'{V}/build/rec', f'{V}/build/comp', f'{V}/out'
FPS, N, DUR = 24, 1152, 48.0
TAKES = {'a': 306, 'b': 173, 'c': 685}
NARR = [('n1', 1.30), ('n2', 5.00), ('n3', 13.00), ('n4', 19.70), ('n5', 27.50), ('n6', 42.60)]
WORKERS = 3


def run(cmd, **kw):
    print('+', ' '.join(str(c) for c in cmd)[:300], flush=True)
    return subprocess.run(cmd, check=True, **kw)


def compose_range(rng):
    sys.path.insert(0, T)
    import compose_fable as C
    lo, hi, force = rng
    done = 0
    for f in range(lo, hi):
        out = f'{COMP}/f{f:05d}.jpg'
        if not force and os.path.exists(out) and os.path.getsize(out) > 1000: continue
        C.compose(f).save(out + f'.tmp{os.getpid()}', 'JPEG', quality=95, subsampling=0)
        os.replace(out + f'.tmp{os.getpid()}', out)
        done += 1
    return done


def main():
    force = '--force' in sys.argv
    # 1. takes complete?
    for take, n in TAKES.items():
        have = sum(1 for i in range(n) if os.path.exists(f'{REC}/{take}/f{i:05d}.jpg') and os.path.getsize(f'{REC}/{take}/f{i:05d}.jpg') > 1000)
        print(f'take {take}: {have}/{n}')
        if have != n: sys.exit(f'take {take} incomplete -> cd tools && node fable_rec.mjs {take}')
    # 2. overlay tracks (pure maths, checked against the recorder's own measurements)
    run(['node', f'{T}/fable_tracks_math.mjs'])
    # 3. composite every film frame (skips frames already on disk)
    os.makedirs(COMP, exist_ok=True)
    step = 48
    with ProcessPoolExecutor(WORKERS) as ex:
        done = sum(ex.map(compose_range, [(lo, min(N, lo + step), force) for lo in range(0, N, step)]))
    have = sum(1 for f in range(N) if os.path.exists(f'{COMP}/f{f:05d}.jpg'))
    print(f'composed {done} new frames, {have}/{N} on disk', flush=True)
    assert have == N
    # 4. encode -> MKV
    os.makedirs(OUT, exist_ok=True)
    mkv, mp4 = f'{OUT}/ep1_fable.mkv', f'{OUT}/ep1_fable.mp4'
    cmd = ['ffmpeg', '-hide_banner', '-loglevel', 'warning', '-stats', '-y', '-framerate', str(FPS), '-i', f'{COMP}/f%05d.jpg']
    for n, _ in NARR: cmd += ['-i', f'{V}/audio/{n}.wav']
    cmd += ['-i', f'{V}/assets/bgm.mp3']
    # JPEG (BT.601 full range) -> BT.709 limited; accurate_rnd keeps the round trip within 1-2 levels
    # (the plain scale call darkened the picture by ~3 levels — measured on frame 90)
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
    tmp = f'{OUT}/ep1_fable.part.mp4'
    run(['ffmpeg', '-hide_banner', '-loglevel', 'warning', '-y', '-i', mkv, '-c', 'copy', '-movflags', '+faststart', tmp])
    os.replace(tmp, mp4)
    # 6. verify
    info = json.loads(subprocess.run(['ffprobe', '-v', 'error', '-show_streams', '-show_format', '-of', 'json', mp4], capture_output=True, text=True, check=True).stdout)
    v = next(s for s in info['streams'] if s['codec_type'] == 'video'); a = next(s for s in info['streams'] if s['codec_type'] == 'audio')
    dur = float(info['format']['duration'])
    head = open(mp4, 'rb').read(4096)
    blob = open(mp4, 'rb').read()
    fast = blob.find(b'moov') < blob.find(b'mdat')
    print(f"VERIFY {v['codec_name']} {v['profile']} {v['width']}x{v['height']} {v['pix_fmt']} {v['r_frame_rate']} frames={v.get('nb_frames')} | "
          f"{a['codec_name']} {a['sample_rate']}Hz ch={a['channels']} | duration={dur:.3f}s size={len(blob) / 1e6:.1f}MB faststart={fast}")
    ok = v['codec_name'] == 'h264' and (v['width'], v['height']) == (1080, 1920) and a['codec_name'] == 'aac' and 45 <= dur <= 55 and fast
    print('BUILD OK' if ok else 'BUILD FAILED CHECKS')
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
