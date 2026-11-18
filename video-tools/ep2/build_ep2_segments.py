# ep2 segment builder (Muse direct, checkpointed): builds seg_hook/seg_recap/seg_main MKVs.
# Each segment is skipped if already built, so re-running resumes where it stopped.
import os, subprocess, sys, time

V = os.path.expanduser('~/workspace/mujintou/video')
REC = f'{V}/build/ep2/rec'
REC3 = f'{V}/build/rec3'
COMP = f'{V}/build/ep2/comp'
PROG = f'{V}/ep2_build_progress.md'
os.makedirs(COMP, exist_ok=True)

COLOR = 'scale=in_color_matrix=bt601:in_range=pc:out_color_matrix=bt709:out_range=tv:flags=accurate_rnd+full_chroma_int,format=yuv420p'
TAGS = ['-color_primaries', 'bt709', '-color_trc', 'bt709', '-colorspace', 'bt709']

def log(msg):
    ts = time.strftime('%Y-%m-%d %H:%M')
    line = f'- {ts} ▶ [segments] {msg}'
    print(line, flush=True)
    with open(PROG, 'a') as f:
        f.write(line + '\n')

def frames(d):
    return sorted(f for f in os.listdir(d) if f.startswith('f') and f.endswith('.jpg'))

def seq_dir(name, paths):
    d = f'{COMP}/{name}'
    os.makedirs(d, exist_ok=True)
    for i, p in enumerate(paths):
        link = f'{d}/f{i:05d}.jpg'
        if not os.path.exists(link):
            os.symlink(p, link)
    return d

def encode(seq, out, extra_vf=None, fps=24):
    if os.path.exists(out) and os.path.getsize(out) > 100000:
        log(f'skip {os.path.basename(out)} (already built)')
        return
    vf = (extra_vf + ',' if extra_vf else '') + COLOR
    cmd = ['ffmpeg', '-y', '-framerate', str(fps), '-i', f'{seq}/f%05d.jpg',
           '-vf', vf, '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '15',
           *TAGS, out + '.tmp.mkv']
    log(f'encode start {os.path.basename(out)}')
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stderr[-2000:], flush=True)
        sys.exit(f'ffmpeg failed for {out}')
    os.rename(out + '.tmp.mkv', out)
    log(f'encode done {os.path.basename(out)} ({os.path.getsize(out)//1024} KB)')

# --- main: L B P H QB QC QD QE E in film order ---
main_paths = []
for shot in ['L', 'B', 'P', 'H', 'QB', 'QC', 'QD', 'QE', 'E']:
    fs = frames(f'{REC}/{shot}')
    main_paths += [f'{REC}/{shot}/{f}' for f in fs]
    log(f'{shot}: {len(fs)} frames')
log(f'main total {len(main_paths)} frames (expect 846)')
encode(seq_dir('main_frames', main_paths), f'{COMP}/seg_main.mkv')

# --- recap: 55 frames sampled across ep1 takes a/b2/c ---
def sample(d, n):
    fs = frames(d)
    if n >= len(fs):
        return [f'{d}/{f}' for f in fs]
    idx = [round(i * (len(fs) - 1) / (n - 1)) for i in range(n)]
    return [f'{d}/{fs[i]}' for i in idx]

recap_paths = sample(f'{REC3}/a', 18) + sample(f'{REC3}/b2', 12) + sample(f'{REC3}/c', 25)
log(f'recap total {len(recap_paths)} frames (expect 55)')
encode(seq_dir('recap_frames', recap_paths), f'{COMP}/seg_recap.mkv')

# --- hook: p2 (540x960) inside a phone frame over its own blurred frame ---
p2 = [f'{REC}/p2/{f}' for f in frames(f'{REC}/p2')]
log(f'p2 total {len(p2)} frames (expect 192)')
hook_vf = ('split=2[base][fg];[base]scale=1080:1920,boxblur=25:2[bg];'
           '[fg]scale=864:1536[ph];[bg][ph]overlay=(W-w)/2:(H-h)/2,'
           'drawbox=x=102:y=186:w=876:h=1548:color=white@0.9:t=6')
# hook uses a filtergraph, not -vf chain: handle separately
out = f'{COMP}/seg_hook.mkv'
if os.path.exists(out) and os.path.getsize(out) > 100000:
    log('skip seg_hook.mkv (already built)')
else:
    seq = seq_dir('p2_frames', p2)
    cmd = ['ffmpeg', '-y', '-framerate', '24', '-i', f'{seq}/f%05d.jpg',
           '-filter_complex', hook_vf + '[v]', '-map', '[v]',
           '-vf', COLOR, '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '15',
           *TAGS, out + '.tmp.mkv']
    # NOTE: -vf after -filter_complex is invalid; rebuild cmd properly below if this fails
    log('encode start seg_hook.mkv')
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        cmd = ['ffmpeg', '-y', '-framerate', '24', '-i', f'{seq}/f%05d.jpg',
               '-filter_complex', hook_vf + ',' + COLOR + '[v]', '-map', '[v]',
               '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '15',
               *TAGS, out + '.tmp.mkv']
        r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stderr[-2000:], flush=True)
        sys.exit('ffmpeg failed for seg_hook')
    os.rename(out + '.tmp.mkv', out)
    log(f'encode done seg_hook.mkv ({os.path.getsize(out)//1024} KB)')

log('ALL SEGMENTS DONE')
