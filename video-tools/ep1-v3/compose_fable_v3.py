#!/usr/bin/env python3
"""ep1 v3 (ep1_fable_v3.mp4, 57.0 s) — composite the v3 takes + overlays into build/comp3/f%05d.jpg.

  python3 compose_fable_v3.py                 all 1368 frames (existing files are skipped -> resumable)
  python3 compose_fable_v3.py --force         re-render everything
  python3 compose_fable_v3.py --test 30 96 …  only these film frames, written to build/test3/

Takes (tools/fable_timeline_v3.mjs, recorded by fable_rec_v3.mjs):
  a  build/rec3/a   film    0–305  dawn at sea -> whole island -> five districts, day 1 (5:09 -> 23:48)
  b2 build/rec3/b2  film  294–466  next morning, landing beach; the castaway lies at LIE (drawn here)
  c  build/rec3/c   film  467–1014 comments -> map -> A/B/C -> map
  p  build/rec3h/p  film 1015–1247 the empty island inside the phone (540x960) — "see it in the app" part
  d  build/rec3/d   film 1236–1367 sunset pull-back, end titles
Every overlay is a pure function of film time t (= frame / 24); world-anchored ones use
build/tracks_v3.json (screen positions + camera of every frame, tools/fable_tracks_v3.mjs).
The PWA screens are the real UI (build/ui3/hd, tools/v3_ui_hd.mjs) over take p: no islander is ever
drawn in a 3-D island picture — the only person is the lying silhouette.
"""
import json, math, os, random, sys
from functools import lru_cache
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageChops

V = os.path.expanduser('~/workspace/mujintou/video')
REC, RECH, UI = f'{V}/build/rec3', f'{V}/build/rec3h', f'{V}/build/ui3/hd'
COMP, TEST = f'{V}/build/comp3', f'{V}/build/test3'
FONT = '/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc'
W, H, FPS, N = 1080, 1920, 24, 1368
F_B0, F_BX, F_C0, F_P0, F_D0, F_DX = 294, 306, 467, 1015, 1236, 1248  # dissolves 294–305 (a->b2), 1236–1247 (phone->d)

INK, INK2 = (35, 29, 54), (58, 51, 82)
CREAM, WHITE = (251, 242, 216), (255, 255, 255)
YELLOW, ACC = (242, 194, 48), (255, 216, 74)
ORANGE, REDBROWN, PINK = (232, 100, 60), (184, 67, 31), (226, 96, 126)
GREEN, BLUE, ICE, GREY = (63, 154, 69), (47, 127, 208), (170, 225, 255), (93, 86, 116)
RED = (214, 48, 49)

TR = json.load(open(f'{V}/build/tracks_v3.json'))
PT = {n: i for i, n in enumerate(TR['names'])}
ASPECT = TR['aspect']
TAKE0 = {'a': 0, 'b2': F_B0, 'c': F_C0, 'p': F_P0, 'd': F_D0}


def shot_of(f):
    if f < F_B0 + 6: return 'a', f
    if f < F_C0: return 'b2', f - F_B0
    if f < F_P0: return 'c', f - F_C0
    if f < F_D0 + 6: return 'p', f - F_P0
    return 'd', f - F_D0


def frame_of(f, shot=None):
    s = shot or shot_of(f)[0]
    fr = TR['shots'][s]['frames']
    return fr[max(0, min(len(fr) - 1, f - TAKE0[s]))]


def track(name, f, shot=None):
    """-> (x px, y px, distance) of a world point; distance < 0 when behind the camera"""
    p = frame_of(f, shot)['pts'][PT[name]]
    return p[0] * W, p[1] * H, p[2]


def project(cam, w):
    """world point -> (x px, y px, depth) with the frame's camera (C, forward, right, up, tan(fov/2))"""
    d0, d1, d2 = w[0] - cam[0], w[1] - cam[1], w[2] - cam[2]
    z = d0 * cam[3] + d1 * cam[4] + d2 * cam[5]
    if z <= 0.1: return None
    x = (d0 * cam[6] + d1 * cam[7] + d2 * cam[8]) / (z * cam[12] * ASPECT) * 0.5 + 0.5
    y = -(d0 * cam[9] + d1 * cam[10] + d2 * cam[11]) / (z * cam[12]) * 0.5 + 0.5
    return x * W, y * H, z


# ---------------------------------------------------------------- helpers
clamp = lambda x, a=0.0, b=1.0: max(a, min(b, x))
smooth = lambda x: (lambda u: u * u * (3 - 2 * u))(clamp(x))
lerp = lambda a, b, u: a + (b - a) * u


def back(x):
    x = clamp(x); c1 = 1.70158; c3 = c1 + 1
    return 1 + c3 * (x - 1) ** 3 + c1 * (x - 1) ** 2


def pop(t, t0, d=0.26):
    """(scale, alpha) for a bouncy pop-in starting at t0"""
    if t < t0: return 0.0, 0.0
    x = (t - t0) / d
    return 0.6 + 0.4 * back(x), clamp(x * 3)


def fade(t, t0, t1, din=0.18, dout=0.18):
    if t < t0 or t > t1: return 0.0
    return min(clamp((t - t0) / din), clamp((t1 - t) / dout))


@lru_cache(maxsize=None)
def font(size):
    return ImageFont.truetype(FONT, size, index=0)


@lru_cache(maxsize=None)
def rich(segs, size, stroke=7, shadow=5):
    """outlined text, segs = ((text, colour), ...) on one line"""
    f = font(size); asc, desc = f.getmetrics()
    ws = [f.getlength(s) for s, _ in segs]
    pad = stroke + shadow + 6
    im = Image.new('RGBA', (int(sum(ws)) + 2 * pad, asc + desc + 2 * pad), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    for dy in ([shadow] if shadow else []) + [0]:
        x = pad
        for (s, _), w in zip(segs, ws):
            d.text((x, pad + dy), s, font=f, fill=INK, stroke_width=stroke, stroke_fill=INK); x += w
    x = pad
    for (s, c), w in zip(segs, ws):
        d.text((x, pad), s, font=f, fill=c); x += w
    return im


@lru_cache(maxsize=None)
def plate(segs, size, bg=CREAM, padx=34, pady=10, radius=16, border=5, shadow=8, minw=0):
    """PWA-style name plate: flat fill, ink border, hard offset shadow"""
    f = font(size); asc, desc = f.getmetrics()
    ws = [f.getlength(s) for s, _ in segs]
    tw = int(sum(ws)); w = max(minw, tw + 2 * padx); h = asc + desc + 2 * pady
    im = Image.new('RGBA', (w + shadow + 2, h + shadow + 2), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    if shadow: d.rounded_rectangle((shadow, shadow, w + shadow, h + shadow), radius, fill=INK + (255,))
    d.rounded_rectangle((0, 0, w, h), radius, fill=bg + (255,), outline=INK + (255,), width=border)
    x = (w - tw) // 2
    for (s, c), ww in zip(segs, ws):
        d.text((x, pady - size * 0.04), s, font=f, fill=c); x += ww
    return im


def blit(cv, im, cx, cy, scale=1.0, alpha=1.0, anchor='c', rot=0):
    if alpha <= 0.01 or scale <= 0.02: return
    if abs(scale - 1) > 1e-3:
        im = im.resize((max(1, round(im.width * scale)), max(1, round(im.height * scale))), Image.BICUBIC)
    if rot: im = im.rotate(rot, Image.BICUBIC, expand=True)
    if alpha < 0.995:
        im = im.copy(); im.putalpha(im.getchannel('A').point(lambda v: int(v * alpha)))
    x = cx - im.width / 2
    y = {'c': cy - im.height / 2, 'b': cy - im.height, 't': cy}[anchor]
    if x > W or y > H or x + im.width < 0 or y + im.height < 0: return
    cv.paste(im, (round(x), round(y)), im)


@lru_cache(maxsize=None)
def heart(size, col=PINK):
    s = size * 4
    im = Image.new('RGBA', (s, s), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.ellipse((0, s * 0.08, s * 0.54, s * 0.62), fill=col + (255,))
    d.ellipse((s * 0.46, s * 0.08, s, s * 0.62), fill=col + (255,))
    d.polygon([(s * 0.04, s * 0.45), (s * 0.96, s * 0.45), (s * 0.5, s * 0.97)], fill=col + (255,))
    return im.resize((size, size), Image.LANCZOS)


@lru_cache(maxsize=None)
def pin(letter, col):
    S = 2; R = 60 * S
    im = Image.new('RGBA', (R * 2 + 24 * S, R * 2 + 70 * S), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    cx, cy = im.width // 2, R + 6 * S
    for off, c in ((7 * S, INK), (0, None)):
        tip = [(cx - 30 * S + off, cy + R * 0.78 + off), (cx + 30 * S + off, cy + R * 0.78 + off), (cx + off * 0.3, cy + R + 56 * S)]
        d.polygon(tip, fill=(c or INK) + (255,))
        d.ellipse((cx - R + off, cy - R + off, cx + R + off, cy + R + off), fill=(c or INK) + (255,))
    d.ellipse((cx - R + 6 * S, cy - R + 6 * S, cx + R - 6 * S, cy + R - 6 * S), fill=col + (255,))
    f = font(78 * S); w = f.getlength(letter); asc, desc = f.getmetrics()
    d.text((cx - w / 2, cy - (asc + desc) / 2 - 4 * S), letter, font=f, fill=WHITE)
    return im.resize((im.width // S, im.height // S), Image.LANCZOS)


@lru_cache(maxsize=None)
def link_icon(size, col=INK):
    """two chain links (the 'link in profile' glyph)"""
    S = 4; s = size * S
    im = Image.new('RGBA', (s, s), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    w = max(2, int(s * 0.13))
    for k in (0, 1):
        o = k * s * 0.34
        box = (s * 0.06 + o, s * 0.30 + (0.0 if k else 0.0), s * 0.60 + o, s * 0.70)
        d.rounded_rectangle(box, radius=s * 0.2, outline=col + (255,), width=w)
    im = im.rotate(35, Image.BICUBIC)
    return im.resize((size, size), Image.LANCZOS)


VIG = None
def vignette(cv, k):
    global VIG
    if k <= 0.01: return
    if VIG is None:
        m = Image.new('L', (W // 8, H // 8), 0); px = m.load()
        for y in range(m.height):
            for x in range(m.width):
                r = math.hypot((x / m.width - 0.5) * 1.15, (y / m.height - 0.48)) / 0.62
                px[x, y] = int(255 * clamp(r) ** 2.2)
        VIG = m.resize((W, H), Image.BICUBIC)
    cv.paste((8, 6, 28), (0, 0), VIG.point(lambda v: int(v * k)))


_rnd = random.Random(7)
FLAKES = [(_rnd.random() * (W + 80), _rnd.random() * (H + 80), 0.55 + _rnd.random() * 0.9, _rnd.choice([5, 7, 9])) for _ in range(170)]
def snow(cv, t, k):
    """wind-driven voxel snow + cold tint for the highland"""
    if k <= 0.01: return cv
    cv = Image.blend(cv, Image.new('RGB', (W, H), (140, 185, 255)), 0.12 * k)
    ov = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
    for x0, y0, sp, sz in FLAKES:
        x = (x0 - 980 * sp * t) % (W + 80) - 40
        y = (y0 + 440 * sp * t) % (H + 80) - 40
        L = 34 * sp
        d.line((x, y, x + 0.91 * L, y - 0.41 * L), fill=(255, 255, 255, int(110 * k)), width=max(2, sz // 2))
        d.rectangle((x - sz / 2, y - sz / 2, x + sz / 2, y + sz / 2), fill=(255, 255, 255, int(235 * k)))
    cv.paste(ov, (0, 0), ov)
    return cv


# ---------------------------------------------------------------- base picture
def load(shot, i):
    root = RECH if shot == 'p' else REC
    return Image.open(f'{root}/{shot}/f{i:05d}.jpg').convert('RGB')


def base(f):
    """-> (picture, phone_part) ; the phone part composites its own picture (take p inside the phone)"""
    if f < F_B0: return load('a', f)
    if f < F_BX: return Image.blend(load('a', f), load('b2', f - F_B0), smooth((f - F_B0 + 0.5) / (F_BX - F_B0)))
    if f < F_C0: return load('b2', f - F_B0)
    if f < F_P0: return load('c', f - F_C0)
    if f < F_D0: return phone_scene(f)
    if f < F_DX: return Image.blend(phone_scene(f), load('d', f - F_D0), smooth((f - F_D0 + 0.5) / (F_DX - F_D0)))
    return load('d', f - F_D0)


# ---------------------------------------------------------------- subtitles (phrase-synced to the narration)
# narration starts (s): n1 1.30 / n2 5.00 / n3 13.00 / n4 19.70 / n5 27.50 / n7 42.55 / n8 46.75 / n6 52.00
# n1–n5 keep the v1 offsets, so the v1 phrase times are reused; n7/n8 phrase times come from the
# VOICEVOX mora lengths (build/vv3/n7.json, n8.json).
N7, N8, N6 = 42.55, 46.75, 52.00
Wt = WHITE
SUBS = [  # (end, [line, ...]); line = [(time the phrase is spoken, ((text, colour), ...)), ...]
    (4.5, [[(1.42, (('ここは、', Wt),)), (2.26, (('まだ誰も住んでいない', Wt),))], [(3.3, (('無人島。', ACC),))]]),
    (8.0, [[(5.0, (('砂浜、', Wt),)), (6.14, (('入り江、', Wt),)), (7.27, (('平原。', Wt),))]]),
    (9.95, [[(8.13, (('森の奥には', Wt),)), (8.56, (('獣', ORANGE), ('がいて、', Wt)))]]),
    (12.3, [[(10.11, (('高原は', Wt),))], [(10.94, (('寒くて厳しい', ICE), ('場所です。', Wt)))]]),
    (16.4, [[(13.15, (('フォローすると、', Wt),))], [(14.36, (('あなたもこの島に', Wt),)), (15.25, (('漂着', ACC), ('します。', Wt)))]]),
    (19.4, [[(16.56, (('頭の上には、', Wt),))], [(17.96, (('あなたの名前。', ACC),))]]),
    (23.45, [[(19.82, (('島で何が起きるかは、', Wt),))], [(21.65, (('みんなの', Wt), ('コメント', ACC), ('で決まります。', Wt)))]]),
    (27.1, [[(23.65, (('いいね', PINK), ('が一番多い案が、', Wt)))], [(25.63, (('採用', ACC), ('されます。', Wt)))]]),
    (29.05, [[(27.5, (('最初の質問です。', Wt),))]]),
    (42.1, [[(39.38, (('コメント', ACC), ('で、', Wt))), (40.51, (('教えてください。', Wt),))]]),
    (46.5, [[(N7 + 0.10, (('島は、', Wt),)), (N7 + 1.07, (('プロフィールのリンク', ACC), ('から、', Wt)))], [(N7 + 2.75, (('いつでも見られます。', Wt),))]]),
    (48.5, [[(N8 + 0.10, (('名前で', Wt), ('検索', ACC), ('すれば、', Wt)))]]),
    (51.45, [[(N8 + 1.84, (('あなたが今、', Wt),))], [(N8 + 3.03, (('何をしているか', ACC), ('も分かります。', Wt)))]]),
]
SUB_SIZE, SUB_PITCH, SUB_MAXW = 58, 90, 900
SUB_LOW = {9}  # the A/B/C list sits above -> that subtitle goes a little lower


@lru_cache(maxsize=None)
def sub_size(n):
    """58 px unless a line would be wider than SUB_MAXW"""
    lines = SUBS[n][1]
    widest = max(sum(font(SUB_SIZE).getlength(s) for _, segs in line for s, _ in segs) for line in lines)
    return SUB_SIZE if widest <= SUB_MAXW else int(SUB_SIZE * SUB_MAXW / widest)


def subtitles(cv, t):
    for n, (end, lines) in enumerate(SUBS):
        start = lines[0][0][0]
        if not (start - 0.02 <= t <= end): continue
        out = clamp((end - t) / 0.14)
        size = sub_size(n); f = font(size)
        cy0 = (1448 if n in SUB_LOW else 1388) - (len(lines) - 1) * SUB_PITCH / 2
        for li, line in enumerate(lines):
            widths = [sum(f.getlength(s) for s, _ in segs) for _, segs in line]
            x = 540 - sum(widths) / 2
            for (t0, segs), w in zip(line, widths):
                s, a = pop(t, t0, 0.2)
                blit(cv, rich(segs, size), x + w / 2, cy0 + li * SUB_PITCH, 0.82 + 0.18 * (s - 0.6) / 0.4 if s else 0, a * out)
                x += w


# ---------------------------------------------------------------- observation HUD (take a): ● 観察中 | ☀ 1日目 6:00
def hud_chip(cv, f, t):
    a = fade(t, 4.55, 12.25, 0.3, 0.3)
    if a <= 0: return
    h = frame_of(f, 'a')['hour'] % 24; day = 6 <= h < 18
    m = int(h * 6) % 6 * 10
    bg, fg = (CREAM, INK) if day else (INK2, CREAM)
    f30, f36, f44 = font(30), font(36), font(44)
    w = 452; hh = 76
    im = Image.new('RGBA', (w + 10, hh + 10), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle((7, 7, w + 7, hh + 7), 16, fill=INK + (255,))
    d.rounded_rectangle((0, 0, w, hh), 16, fill=bg + (255,), outline=INK + (255,), width=5)
    # REC dot blinks once a second
    on = (t % 1.0) < 0.62
    d.ellipse((20, 26, 44, 50), fill=(RED if on else (RED[0] // 2 + bg[0] // 2, RED[1] // 2 + bg[1] // 2, RED[2] // 2 + bg[2] // 2)) + (255,))
    d.text((54, 15), '観察中', font=f30, fill=fg)
    d.line((156, 14, 156, 62), fill=INK + (255,) if day else CREAM + (140,), width=3)
    if day:
        d.ellipse((172, 21, 206, 55), fill=YELLOW + (255,), outline=INK + (255,), width=4)
    else:
        d.ellipse((172, 21, 206, 55), fill=(214, 222, 255, 255))
        d.ellipse((184, 15, 214, 45), fill=bg + (255,))
    # 「1日目」 in the app's own badge style
    d.rounded_rectangle((220, 15, 314, 61), 9, fill=YELLOW + (255,), outline=INK + (255,), width=3)
    d.text((231, 15), '1日目', font=f30, fill=INK)
    txt = f'{int(h):d}:{m:02d}'
    d.text((w - 18 - f44.getlength(txt), 7), txt, font=f44, fill=fg)
    blit(cv, im, 60 + im.width / 2, 300, 1, a)


DISTRICTS = [  # track, label, in, out, (sub label, bg, time)
    ('beach', '砂浜', 5.0, 6.15, None),
    ('cove', '入り江', 6.14, 7.25, None),
    ('plain', '平原', 7.27, 8.35, None),
    ('forest', '森', 8.45, 10.2, ('獣がいる！', REDBROWN, 8.75)),
    ('highland', '高原', 10.55, 12.4, ('寒くて厳しい', BLUE, 11.0)),
]


def districts(cv, f, t):
    for name, label, t0, t1, sub in DISTRICTS:
        if not (t0 <= t <= t1): continue
        x, y, d = track(name, f, 'a')
        if d < 0: x, y = (W + 400 if x < W / 2 else -400), y
        x = clamp(x, 200, 880); y = clamp(y, 420, 1120)
        s, a = pop(t, t0)
        a *= clamp((t1 - t) / 0.15)
        blit(cv, plate(((label, INK),), 78, padx=40), x, y, s, a)
        if sub:
            s2, a2 = pop(t, sub[2])
            blit(cv, plate(((sub[0], WHITE),), 44, bg=sub[1], padx=26, pady=8, shadow=6), x, y + 112, s2, a2 * clamp((t1 - t) / 0.15))


def eyes(cv, f, t):
    """pairs of eyes glinting in the night forest"""
    for k in range(6):
        t0 = 9.05 + 0.14 * k
        a = fade(t, t0, 10.3, 0.08, 0.12)
        blink = 9.62 + 0.11 * k
        if a <= 0 or blink <= t < blink + 0.09: continue
        x, y, d = track(f'eye{k}', f, 'a')
        if d <= 0 or not (0 < x < W and 250 < y < H) or 1290 < y < 1490: continue  # keep clear of the subtitle band
        u = 2788 / d  # px per world unit at that distance
        e = max(7, 0.42 * u); g = 0.36 * u
        ov = Image.new('RGBA', (int(e * 8), int(e * 5)), (0, 0, 0, 0)); dr = ImageDraw.Draw(ov)
        cx, cy = ov.width / 2, ov.height / 2
        for sx in (-1, 1):
            dr.ellipse((cx + sx * (g + e / 2) - e * 1.3, cy - e * 1.3, cx + sx * (g + e / 2) + e * 1.3, cy + e * 1.3), fill=(255, 220, 90, 70))
        ov = ov.filter(ImageFilter.GaussianBlur(e * 0.45)); dr = ImageDraw.Draw(ov)
        for sx in (-1, 1):
            ex = cx + sx * (g + e / 2)
            dr.rectangle((ex - e / 2, cy - e * 0.36, ex + e / 2, cy + e * 0.36), fill=(255, 232, 120, 255))
            dr.rectangle((ex - e * 0.13, cy - e * 0.36, ex + e * 0.13, cy + e * 0.36), fill=(40, 20, 30, 255))
        blit(cv, ov, x, y, 1, a)


# ---------------------------------------------------------------- the castaway, lying at the water's edge (take b2)
SIL = Image.open(f'{V}/assets/silhouette_you.png').convert('RGBA')
SIL_BODY = SIL.crop((36, 70, 256, 464))   # 220x394 figure, head at the top
SIL_MASK = SIL_BODY.getchannel('A')
SIL_SHADOW = SIL_MASK.filter(ImageFilter.MaxFilter(9))
SIL_TAG = SIL.crop((66, 0, 226, 66))      # the asset's own 「あなた」 name tag
T_LAND, T_HEAD, T_TAG = 14.85, 16.56, 17.96
LIE = TR['world'][PT['lie']]              # (247, ground, 135)
BODY_L = 4.6                              # head-to-toe, world units (v1's standing figure was 5)
BODY_W = BODY_L * SIL_BODY.width / SIL_BODY.height
BODY_T = 0.62                             # thickness of the lying body
AX = (math.cos(0.72), -math.sin(0.72))    # body axis on the ground: along the shoreline, head to the north-east
PX = (-AX[1], AX[0])
SIL_TOP, SIL_SIDE = (44, 50, 80), (14, 20, 38)


def persp_coeffs(dst, src):
    """PIL PERSPECTIVE data mapping output quad dst -> input quad src"""
    A, b = [], []
    for (X, Y), (x, y) in zip(dst, src):
        A.append([X, Y, 1, 0, 0, 0, -X * x, -Y * x]); b.append(x)
        A.append([0, 0, 0, X, Y, 1, -X * y, -Y * y]); b.append(y)
    return np.linalg.solve(np.array(A, float), np.array(b, float)).tolist()


def body_quad(cam, lift):
    """screen corners of the figure lying flat at height `lift` above the sand, sprite order TL TR BR BL"""
    gx, gy, gz = LIE
    hl, hw = BODY_L / 2, BODY_W / 2
    pts = []
    for sa, sp in ((+hl, +hw), (+hl, -hw), (-hl, -hw), (-hl, +hw)):  # head end = sprite top
        pts.append(project(cam, (gx + AX[0] * sa + PX[0] * sp, gy + lift, gz + AX[1] * sa + PX[1] * sp)))
    return pts


def warp_mask(quad, mask=SIL_MASK, pad=4):
    xs = [p[0] for p in quad]; ys = [p[1] for p in quad]
    x0, y0 = math.floor(min(xs)) - pad, math.floor(min(ys)) - pad
    x1, y1 = math.ceil(max(xs)) + pad, math.ceil(max(ys)) + pad
    src = [(0, 0), (mask.width, 0), (mask.width, mask.height), (0, mask.height)]
    co = persp_coeffs([(q[0] - x0, q[1] - y0) for q in quad], src)
    return mask.transform((x1 - x0, y1 - y0), Image.PERSPECTIVE, co, Image.BICUBIC), (x0, y0)


def castaway(cv, f, t):
    if t < T_LAND or not (F_B0 <= f < F_C0): return
    cam = frame_of(f, 'b2')['cam']
    a = clamp((t - T_LAND) / 0.35)
    gx, gy, gz = LIE
    base_q = body_quad(cam, 0.04)
    top_q = body_quad(cam, BODY_T)
    if any(p is None for p in base_q + top_q): return
    length = math.dist(((base_q[0][0] + base_q[1][0]) / 2, (base_q[0][1] + base_q[1][1]) / 2),
                       ((base_q[2][0] + base_q[3][0]) / 2, (base_q[2][1] + base_q[3][1]) / 2))
    # arrival: two rings spreading over the wet sand
    x = t - T_LAND
    for k in range(2):
        r = (x - 0.14 * k) / 0.8
        if 0 < r < 1:
            R = BODY_L * (0.45 + 0.9 * r)
            ring = [project(cam, (gx + R * math.cos(q * math.pi / 24), gy + 0.05, gz + R * math.sin(q * math.pi / 24))) for q in range(49)]
            if all(ring):
                ov = Image.new('RGBA', (W, H), (0, 0, 0, 0))
                ImageDraw.Draw(ov).line([(p[0], p[1]) for p in ring], fill=(255, 255, 255, int(230 * (1 - r))), width=max(3, int(length * 0.016)), joint='curve')
                cv.paste(ov, (0, 0), ov)
    # soft contact shadow
    sm, (sx, sy) = warp_mask(base_q, SIL_SHADOW, pad=24)
    sm = sm.filter(ImageFilter.GaussianBlur(max(2, length * 0.02))).point(lambda v: int(v * 0.42 * a))
    cv.paste(INK, (sx + round(length * 0.012), sy + round(length * 0.02)), sm)
    # the body: base silhouette smeared up to the top face (solid side), then the lit top face
    bm, (bx, by) = warp_mask(base_q)
    tm, (tx, ty) = warp_mask(top_q)
    dx, dy = tx - bx, ty - by
    steps = max(abs(dx), abs(dy))
    bA = np.asarray(bm)
    side = np.zeros((bm.height + abs(dy) + 2, bm.width + abs(dx) + 2), np.uint8)
    ox, oy = max(0, -dx), max(0, -dy)
    for k in range(steps + 1):  # union of the base shape slid up to the top face = the body's solid side
        u = k / steps if steps else 0
        qx, qy = ox + round(dx * u), oy + round(dy * u)
        win = side[qy:qy + bm.height, qx:qx + bm.width]
        np.maximum(win, bA, out=win)
    cv.paste(SIL_SIDE, (bx - ox, by - oy), Image.fromarray(side).point(lambda v: int(v * a)))
    cv.paste(SIL_TOP, (tx, ty), tm.point(lambda v: int(v * a)))
    # head end / centre on screen, for the marks above the figure
    head = project(cam, (gx + AX[0] * BODY_L * 0.40, gy + BODY_T, gz + AX[1] * BODY_L * 0.40))
    head = (head[0], min(top_q[0][1], top_q[1][1]) - 10)  # just above the upper edge of the head end
    mid = project(cam, (gx, gy + BODY_T, gz))
    top_y = min(p[1] for p in top_q)
    k = length / SIL_BODY.height
    # 島民 +1
    p = (t - (T_LAND + 0.25)) / 1.3
    if 0 < p < 1:
        s, a1 = pop(t, T_LAND + 0.25)
        blit(cv, plate((('島民 ', INK), ('+1', ORANGE)), 50, bg=YELLOW, padx=24, pady=6, shadow=6), mid[0] + length * 0.15, top_y - 60 - p * 110, s, a1 * clamp((1 - p) / 0.25))
    # 「頭の上には」 -> bouncing marker over the head, then the name tag
    if T_HEAD <= t < T_TAG:
        s, a2 = pop(t, T_HEAD)
        by_ = head[1] - abs(math.sin((t - T_HEAD) * 2 * math.pi * 1.6)) * length * 0.05
        sz = length * 0.10
        ov = Image.new('RGBA', (int(sz * 2 + 16), int(sz * 1.5 + 16)), (0, 0, 0, 0)); dr = ImageDraw.Draw(ov)
        dr.polygon([(4, 4), (ov.width - 4, 4), (ov.width / 2, ov.height - 4)], fill=YELLOW + (255,), outline=INK + (255,), width=6)
        blit(cv, ov, head[0], by_, s, a2, anchor='b')
    if t >= T_TAG:
        s, a3 = pop(t, T_TAG, 0.3)
        kt = k * 1.55
        tw, th = SIL_TAG.width * kt + 44, SIL_TAG.height * kt + 20
        pl = Image.new('RGBA', (int(tw + 10), int(th + 10)), (0, 0, 0, 0)); dr = ImageDraw.Draw(pl)
        dr.rounded_rectangle((8, 8, tw + 8, th + 8), 16, fill=INK + (255,))
        dr.rounded_rectangle((0, 0, tw, th), 16, fill=CREAM + (255,), outline=INK + (255,), width=5)
        tg = SIL_TAG.resize((round(SIL_TAG.width * kt), round(SIL_TAG.height * kt)), Image.BICUBIC)
        pl.paste(tg, (22, 10), tg)
        ty_ = head[1]
        blit(cv, pl, head[0], ty_, s, a3, anchor='b')
        b = (t - T_TAG) / 0.45  # sparkle burst
        if 0 < b < 1:
            ov = Image.new('RGBA', (int(tw * 2.2), int(tw * 1.6)), (0, 0, 0, 0)); dr = ImageDraw.Draw(ov)
            cx, cy = ov.width / 2, ov.height / 2
            for i in range(10):
                ang = i * math.pi / 5 + 0.3
                r0, r1 = tw * (0.5 + 0.35 * b), tw * (0.62 + 0.42 * b)
                dr.line((cx + math.cos(ang) * r0, cy + math.sin(ang) * r0 * 0.62, cx + math.cos(ang) * r1, cy + math.sin(ang) * r1 * 0.62), fill=ACC + (int(255 * (1 - b)),), width=9)
            blit(cv, ov, head[0], ty_ - th / 2)


# ---------------------------------------------------------------- comments (take c, whole island)
COMMENTS = [  # track, text, likes, pop time, bubble offset, winner
    ('cForest', '森を探検しよう', 37, 20.0, (-20, -200), False),
    ('cCove', '魚を釣りたい', 64, 20.5, (-80, 172), False),
    ('cBeach', 'いかだを作ろう', 21, 21.0, (-20, -205), False),
    ('cPlain', '家を建てよう', 128, 21.5, (190, -265), True),
]
T_ADOPT, T_COUNT_END, T_COMM_OUT = 25.63, 24.9, 27.1


@lru_cache(maxsize=256)
def bubble(text, likes, win):
    f1, f2 = font(46), font(40)
    w = int(max(f1.getlength(text), 150)) + 60; h = 142
    im = Image.new('RGBA', (w + 10, h + 10), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle((8, 8, w + 8, h + 8), 22, fill=INK + (255,))
    d.rounded_rectangle((0, 0, w, h), 22, fill=(YELLOW if win else CREAM) + (255,), outline=INK + (255,), width=5)
    d.text((30, 8), text, font=f1, fill=INK)
    hs = heart(38, REDBROWN if win else PINK); im.paste(hs, (32, 86), hs)
    d.text((80, 72), str(likes), font=f2, fill=REDBROWN if win else PINK)
    return im


def comments(cv, f, t):
    if not (19.9 <= t <= T_COMM_OUT + 0.2): return
    gout = clamp((T_COMM_OUT + 0.15 - t) / 0.2)
    blit(cv, rich((('※コメントはイメージです', WHITE),), 30, stroke=4, shadow=0), 540, 290, 1, fade(t, 20.0, T_COMM_OUT, 0.3, 0.2) * 0.9)
    for name, text, likes, t0, (dx, dy), win in COMMENTS:
        if t < t0: continue
        x, y, d = track(name, f, 'c')
        s, a = pop(t, t0)
        a *= gout
        if not win: a *= 1 - 0.85 * smooth((t - T_ADOPT) / 0.4)
        n = round(likes * smooth((t - t0) / (T_COUNT_END - t0)) ** 0.8)
        adopted = win and t >= T_ADOPT
        if adopted: s *= 1 + 0.22 * back((t - T_ADOPT) / 0.3)
        bx, by = clamp(x + dx, 230, 850), y + dy
        ov = Image.new('RGBA', (W, H), (0, 0, 0, 0)); dr = ImageDraw.Draw(ov)
        al = int(255 * a)
        dr.line((x, y, bx, by), fill=INK + (al,), width=7)
        dr.ellipse((x - 13, y - 13, x + 13, y + 13), fill=(YELLOW if win else CREAM) + (al,), outline=INK + (al,), width=5)
        cv.paste(ov, (0, 0), ov)
        if 23.65 <= t < T_ADOPT: s *= 1 + 0.035 * math.sin((t - 23.65) * 2 * math.pi * 2.2)
        blit(cv, bubble(text, n, adopted), bx, by, s, a)
        if adopted:
            z = clamp((t - T_ADOPT - 0.08) / 0.18)
            if z > 0:
                st = plate((('採用！', WHITE),), 64, bg=REDBROWN, padx=26, pady=6, shadow=7)
                blit(cv, st, min(bx + 140, 925), by - 150, 2.2 - 1.2 * z ** 0.5, a * clamp(z * 3), rot=-9)


# ---------------------------------------------------------------- the first question (take c, map + A/B/C)
PINS = [('pinA', 'A', ORANGE, 31.68), ('pinB', 'B', BLUE, 34.57), ('pinC', 'C', GREEN, 36.83)]
OPTIONS = [  # letter, colour, card in, label in, card out, label, note
    ('A', ORANGE, 31.68, 32.62, 34.45, '島の真ん中の平原', '平らで広い。森にも高原にも近い'),
    ('B', BLUE, 34.57, 35.40, 36.75, '入り江のほとり', '波がおだやか。釣りや舟出に向いている'),
    ('C', GREEN, 36.83, 37.72, 39.25, '漂着した砂浜', '見晴らしがよく、漂流者をすぐ迎えられる'),
]
T_Q_OUT = 42.08  # everything is gone by 42.23, before the cut to the phone part (film 1015 = 42.29 s)


@lru_cache(maxsize=None)
def badge(letter, col, size):
    im = Image.new('RGBA', (size + 8, size + 8), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, size, size), size // 6, fill=col + (255,), outline=INK + (255,), width=5)
    f = font(int(size * 0.66)); asc, desc = f.getmetrics()
    d.text(((size - f.getlength(letter)) / 2, (size - asc - desc) / 2 - size * 0.03), letter, font=f, fill=WHITE)
    return im


@lru_cache(maxsize=None)
def option_card(letter, col, label, note, show_text):
    w, h = 900, 196
    im = Image.new('RGBA', (w + 12, h + 12), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle((10, 10, w + 10, h + 10), 22, fill=INK + (255,))
    d.rounded_rectangle((0, 0, w, h), 22, fill=CREAM + (255,), outline=INK + (255,), width=6)
    b = badge(letter, col, 132); im.paste(b, (30, 32), b)
    if show_text:
        d.text((194, 18), label, font=font(62), fill=INK)
        d.text((196, 118), note, font=font(34), fill=GREY)
    return im


@lru_cache(maxsize=None)
def option_row(letter, col, label):
    w, h = 700, 78
    im = Image.new('RGBA', (w + 10, h + 10), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle((8, 8, w + 8, h + 8), 16, fill=INK + (255,))
    d.rounded_rectangle((0, 0, w, h), 16, fill=CREAM + (255,), outline=INK + (255,), width=5)
    b = badge(letter, col, 58); im.paste(b, (14, 10), b)
    d.text((96, 7), label, font=font(44), fill=INK)
    return im


def question(cv, f, t):
    if t < 27.5 or t > T_Q_OUT + 0.2 or f >= F_P0: return
    gout = clamp((T_Q_OUT + 0.15 - t) / 0.2)
    for name, letter, col, t0 in PINS:  # pins first: the header plates and cards always sit on top of them
        if t < t0: continue
        x, y, d = track(name, f, 'c')
        if d <= 0: continue
        sc = clamp(1.3 - (d - 100) / 500 * 0.5, 0.82, 1.3)
        z = (t - t0) / 0.24
        drop = (1 - clamp(z)) ** 2 * 380
        sq = 1 + 0.16 * math.sin(clamp((z - 1) / 0.9) * math.pi) * (1 if z > 1 else 0)
        if t > 40.5:  # A -> B -> C pulse while 「教えてください」
            ph = (t - 40.6 - 0.28 * 'ABC'.index(letter)) % 1.1
            if 0 < ph < 0.3: sq *= 1 + 0.18 * math.sin(ph / 0.3 * math.pi)
        clear = clamp((y - 600) / 110)  # a pin drifting up into the header plates fades out instead of covering them
        blit(cv, pin(letter, col), x, y - drop, sc * sq, clamp(z * 2.5) * gout * clear, anchor='b')
    s, a = pop(t, 27.5)
    blit(cv, plate((('最初の質問', WHITE),), 44, bg=REDBROWN, padx=28, pady=6, shadow=6), 540, 300, s, a * gout)
    if t >= 29.24:
        s, a = pop(t, 29.24)
        second = INK if t >= 30.24 else CREAM
        blit(cv, plate((('拠点は、', INK), ('どこにしますか？', second)), 62, padx=36, pady=12), 540, 410, s, a * gout)
    for letter, col, t0, t1, t2, label, note in OPTIONS:
        if t0 <= t <= t2:
            s, a = pop(t, t0)
            blit(cv, option_card(letter, col, label, note, t >= t1), 540, 1345, s, a * clamp((t2 - t) / 0.15))
    if t >= 39.38:
        for k, (letter, col, *_r, label, note) in enumerate(OPTIONS):
            s, a = pop(t, 39.45 + 0.14 * k)
            blit(cv, option_row(letter, col, label), 540, 1130 + k * 96, s, a * gout)


# ---------------------------------------------------------------- the app part (film 1015–1247): take p inside the real PWA UI
SW, SH = 390, 844                     # phone screen, CSS px; UI layers are 3x
KP = SH / 960                         # take p (540x960) covers the screen by height
P_OFFX = (540 * KP - SW) / 2
SHEET_SHIFT = -254                    # CSS px: take p slides up with the sheet so the island stays in view
T_UI_IN, T_TAP_TAB, T_SHEET, T_TAP_SEARCH, T_TYPE, T_TAP_ROW, T_DETAIL = 42.36, 46.52, 46.62, 47.0, (47.22, 47.42, 47.62), 48.30, 48.42
T_NOW = N8 + 2.95                     # 「何をしているか」 -> highlight the 「いま」 line
CAMKEYS = [  # t, scale (canvas px per CSS px), CSS focus x, y, canvas x, y
    (42.29, 2.77, 195, 422, 540, 960),
    (42.95, 1.40, 195, 422, 540, 921),   # whole phone: screen y 330–1512 (the n7 subtitles sit over its lower part)
    (46.56, 1.40, 195, 422, 540, 921),
    (47.18, 2.35, 195, 478, 540, 760),   # search box + result row
    (48.36, 2.35, 195, 478, 540, 760),
    (48.98, 2.40, 190, 492, 540, 706),   # detail card; its last line stays above the subtitle band
]
RECT = {  # CSS rects from build/ui3/hd/rects.json
    'tab': (97.5, 789, 97.5, 55), 'search': (14, 415.8, 362, 46), 'row': (14, 496.4, 362, 62),
    'now': (86, 480.8, 214.4, 69.9), 'sheet': (0, 364, 390, 422),
}


@lru_cache(maxsize=3)
def ui_layer(name):
    return Image.open(f'{UI}/{name}.png').convert('RGBA')


def phone_cam(t):
    ks = CAMKEYS
    if t <= ks[0][0]: return ks[0][1:]
    for k0, k1 in zip(ks, ks[1:]):
        if t <= k1[0]:
            u = smooth((t - k0[0]) / (k1[0] - k0[0]))
            # zoom in log space so the push feels even
            s = math.exp(lerp(math.log(k0[1]), math.log(k1[1]), u))
            return (s,) + tuple(lerp(a, b, u) for a, b in zip(k0[2:], k1[2:]))
    return ks[-1][1:]


def place(dst, src, ox, oy, k, clip, alpha=1.0):
    """paste src scaled by k with its top-left at (ox, oy) on dst, only inside clip=(x0,y0,x1,y1)"""
    x0 = max(clip[0], math.floor(ox)); y0 = max(clip[1], math.floor(oy))
    x1 = min(clip[2], math.ceil(ox + src.width * k)); y1 = min(clip[3], math.ceil(oy + src.height * k))
    if x1 - x0 < 1 or y1 - y0 < 1 or alpha <= 0.01: return
    box = (max(0.0, (x0 - ox) / k), max(0.0, (y0 - oy) / k), min(src.width, (x1 - ox) / k), min(src.height, (y1 - oy) / k))
    piece = src.resize((x1 - x0, y1 - y0), Image.BICUBIC, box=box)
    if src.mode == 'RGBA':
        if alpha < 0.995: piece.putalpha(piece.getchannel('A').point(lambda v: int(v * alpha)))
        dst.paste(piece, (x0, y0), piece)
    else:
        dst.paste(piece, (x0, y0))


def ui_state(t):
    """-> [(layer, alpha)], sheet progress 0..1 (slide), layer used for the sheet"""
    if t < T_SHEET: return 'h0_home', 0.0
    e = smooth((t - T_SHEET) / 0.32)
    if t < T_TYPE[0]: return 'h1_list', e
    if t < T_TYPE[1]: return 'h2_type1', 1.0
    if t < T_TYPE[2]: return 'h2_type2', 1.0
    if t < T_DETAIL: return 'h2_type3', 1.0
    return 'h3_detail', 1.0


def tap(scr, X0, Y0, s, cx, cy, t, t0):
    """touch indicator at CSS point (cx, cy) on the screen image"""
    u = (t - t0) / 0.45
    if not (0 <= u < 1): return
    x, y = X0 + cx * s, Y0 + cy * s
    ov = Image.new('RGBA', scr.size, (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
    r0 = 15 * s * (0.85 + 0.15 * smooth(u * 3)); r1 = 15 * s * (1 + 1.6 * u)
    d.ellipse((x - r1, y - r1, x + r1, y + r1), outline=(255, 255, 255, int(220 * (1 - u))), width=max(3, int(2.2 * s)))
    d.ellipse((x - r0, y - r0, x + r0, y + r0), fill=(255, 255, 255, int(150 * clamp((1 - u) * 1.6))))
    scr.alpha_composite(ov)


def phone_scene(f):
    t = f / FPS
    p = load('p', min(232, f - F_P0))
    # backdrop: the same island, blurred and dimmed
    bg = p.resize((270, 480), Image.BILINEAR).filter(ImageFilter.GaussianBlur(7)).resize((W, H), Image.BICUBIC)
    bg = Image.blend(bg, Image.new('RGB', (W, H), INK), 0.42)
    s, ux, uy, cx, cy = phone_cam(t)
    X0, Y0 = cx - ux * s, cy - uy * s
    X1, Y1 = X0 + SW * s, Y0 + SH * s
    # phone body: ink bezel with a hard offset shadow (the PWA's own look)
    bz = 13 * s; rs = 44 * s
    d = ImageDraw.Draw(bg)
    sh = 12 * min(1.0, s)
    d.rounded_rectangle((X0 - bz + sh, Y0 - bz + sh, X1 + bz + sh, Y1 + bz + sh), rs + bz, fill=(14, 11, 26))
    d.rounded_rectangle((X0 - bz, Y0 - bz, X1 + bz, Y1 + bz), rs + bz, fill=INK, outline=(88, 80, 118), width=max(2, round(1.6 * s)))
    # screen, built only where it is visible
    vx0, vy0 = max(0, math.floor(X0)), max(0, math.floor(Y0))
    vx1, vy1 = min(W, math.ceil(X1)), min(H, math.ceil(Y1))
    scr = Image.new('RGBA', (vx1 - vx0, vy1 - vy0), (40, 110, 170, 255))
    name, e = ui_state(t)
    sx, sy = X0 - vx0, Y0 - vy0  # screen origin inside scr
    full = (0, 0, scr.width, scr.height)
    shift = SHEET_SHIFT * e
    place(scr, p, sx - P_OFFX * s, sy + shift * s, KP * s, full)
    ua = smooth((t - T_UI_IN) / 0.34)
    k = s / 3
    if name == 'h1_list' and e < 1:
        # the sheet slides up from the tab bar: home layer above, the list sheet clipped to its rising top
        place(scr, ui_layer('h0_home'), sx, sy, k, (0, 0, scr.width, round(sy + 786 * s)), ua)
        top = 364 + (1 - e) * 422
        L = ui_layer('h1_list')
        place(scr, L, sx, sy + (top - 364) * s, k, (0, max(0, round(sy + top * s)), scr.width, min(scr.height, round(sy + 786 * s))))
        place(scr, L, sx, sy, k, (0, max(0, round(sy + 786 * s)), scr.width, scr.height))  # tab bar with 島民 selected
    elif name == 'h3_detail' and t < T_DETAIL + 0.16:
        place(scr, ui_layer('h2_type3'), sx, sy, k, full, ua)
        place(scr, ui_layer('h3_detail'), sx, sy, k, full, smooth((t - T_DETAIL) / 0.16))
    else:
        place(scr, ui_layer(name), sx, sy, k, full, ua)
    tap(scr, sx, sy, s, RECT['tab'][0] + RECT['tab'][2] / 2, RECT['tab'][1] + 26, t, T_TAP_TAB)
    tap(scr, sx, sy, s, 120, RECT['search'][1] + RECT['search'][3] / 2, t, T_TAP_SEARCH)
    tap(scr, sx, sy, s, 160, RECT['row'][1] + RECT['row'][3] / 2, t, T_TAP_ROW)
    if t >= T_NOW:  # 「いま」 line: pulsing highlight
        x, y, w, h = RECT['now']
        u = (t - T_NOW)
        g = 4 + 2.5 * abs(math.sin(u * math.pi * 1.4))
        ov = Image.new('RGBA', scr.size, (0, 0, 0, 0)); dd = ImageDraw.Draw(ov)
        a = int(255 * clamp(u / 0.2))
        dd.rounded_rectangle((sx + (x - g) * s, sy + (y - g) * s, sx + (x + w + g) * s, sy + (y + h + g) * s), 8 * s, outline=ACC + (a,), width=max(4, round(2.4 * s)))
        scr.alpha_composite(ov)
    # rounded screen corners
    m = Image.new('L', scr.size, 0)
    ImageDraw.Draw(m).rounded_rectangle((sx, sy, sx + SW * s, sy + SH * s), rs, fill=255)
    bg.paste(scr.convert('RGB'), (vx0, vy0), m)
    return bg


def phone_overlays(cv, f, t):
    """stickers around the phone while it is shown whole (n7): profile link -> the island, live"""
    if not (F_P0 <= f < F_D0 + 12): return
    s, ux, uy, cx, cy = phone_cam(t)
    X0, Y0 = cx - ux * s, cy - uy * s
    gone = clamp((46.5 - t) / 0.18)
    # 「プロフィールのリンク」 chip above the phone, with a pointer into it
    t0 = N7 + 1.07
    if t >= t0 and gone > 0:
        sc, a = pop(t, t0, 0.3)
        f46 = font(46)
        txt = 'プロフィールのリンク'
        w = int(f46.getlength(txt)) + 130; h = 84
        im = Image.new('RGBA', (w + 12, h + 40), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
        d.rounded_rectangle((9, 9, w + 9, h + 9), 20, fill=INK + (255,))
        d.rounded_rectangle((0, 0, w, h), 20, fill=CREAM + (255,), outline=INK + (255,), width=5)
        li = link_icon(56); im.paste(li, (26, 14), li)
        d.text((96, 9), txt, font=f46, fill=INK)
        d.polygon([(w / 2 - 22, h - 3), (w / 2 + 22, h - 3), (w / 2, h + 30)], fill=INK + (255,))
        d.polygon([(w / 2 - 14, h - 6), (w / 2 + 14, h - 6), (w / 2, h + 16)], fill=CREAM + (255,))
        blit(cv, im, 540, Y0 - 62, sc, a * gone)  # pointer tip just over the top bezel, the app header stays clear
    # live sticker on the phone's shoulder
    t1 = N7 + 2.75
    if t >= t1 and gone > 0:
        sc, a = pop(t, t1, 0.3)
        on = ((t - t1) % 0.9) < 0.6
        f40 = font(40)
        w, h = 186, 70
        im = Image.new('RGBA', (w + 10, h + 10), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
        d.rounded_rectangle((7, 7, w + 7, h + 7), 16, fill=INK + (255,))
        d.rounded_rectangle((0, 0, w, h), 16, fill=RED + (255,), outline=INK + (255,), width=5)
        d.ellipse((22, 23, 46, 47), fill=(WHITE if on else (240, 160, 160)) + (255,))
        d.text((58, 6), 'LIVE', font=f40, fill=WHITE)
        blit(cv, im, X0 + SW * s + 4, Y0 + 210 * s, sc, a * gone, rot=-8)
        sc2, a2 = pop(t, t1 + 0.22, 0.3)
        blit(cv, plate((('いまも動いている', INK),), 34, bg=YELLOW, padx=18, pady=6, shadow=6), X0 + SW * s - 30, Y0 + 210 * s + 84, sc2, a2 * gone, rot=-8)


# ---------------------------------------------------------------- titles
def titles(cv, f, t):
    # opening: 1日目 badge (not 第1話), title, the experiment line
    a = fade(t, 0.6, 4.45, 0.4, 0.2)
    if a > 0:
        up = (1 - smooth((t - 0.6) / 0.45)) * 40
        blit(cv, plate((('1日目', INK),), 46, bg=YELLOW, padx=28, pady=6, shadow=6), 540, 322 + up, 1, a)
        blit(cv, rich((('無人島プロジェクト', WHITE),), 94, stroke=9, shadow=7), 540, 440 + up, 1, a)
        s2, a2 = pop(t, 1.0, 0.3)
        blit(cv, plate((('フォロワーが島民になる', CREAM), ('観察実験', ACC)), 36, bg=INK, padx=26, pady=6, shadow=0, border=3), 540, 548 + up, s2, a2 * a)
    if 3.35 <= t <= 4.5:
        s, a = pop(t, 3.35, 0.3)
        blit(cv, plate((('島民 ', INK), ('0', ORANGE), ('人', INK)), 88, padx=44, pady=12, shadow=10), 540, 690, s, a * clamp((4.5 - t) / 0.15))
    # ending (take d, n6 at 52.00)
    if t >= N6 + 0.11:
        s, a = pop(t, N6 + 0.11, 0.3)
        blit(cv, plate((('1日目', INK),), 40, bg=YELLOW, padx=24, pady=5, shadow=6), 540, 400, s, a)
        blit(cv, rich((('無人島プロジェクト', WHITE),), 98, stroke=9, shadow=7), 540, 520, s, a)
    if t >= N6 + 1.78:
        s, a = pop(t, N6 + 1.78, 0.3)
        blit(cv, rich((('まもなく始まります', ACC),), 66, stroke=8, shadow=6), 540, 660, s, a)
    if t >= 54.6:
        s, a = pop(t, 54.6, 0.3)
        s *= 1 + 0.025 * math.sin((t - 54.6) * 2 * math.pi * 1.1)
        blit(cv, plate((('フォローして、最初の漂着者になろう', INK),), 46, bg=YELLOW, padx=34, pady=14, shadow=9), 540, 830, s, a)
    if t >= 55.2:
        s, a = pop(t, 55.2, 0.3)
        f40 = font(40); txt = '島はプロフィールのリンクから'
        w = int(f40.getlength(txt)) + 112; h = 72
        im = Image.new('RGBA', (w + 10, h + 10), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
        d.rounded_rectangle((7, 7, w + 7, h + 7), 16, fill=INK + (255,))
        d.rounded_rectangle((0, 0, w, h), 16, fill=CREAM + (255,), outline=INK + (255,), width=5)
        li = link_icon(48); im.paste(li, (24, 12), li)
        d.text((84, 7), txt, font=f40, fill=INK)
        blit(cv, im, 540, 950, s, a)


def compose(f):
    t = f / FPS
    cv = base(f)
    vignette(cv, fade(t, 8.8, 10.6, 0.5, 0.4) * 0.5)
    k = fade(t, 10.55, 12.75, 0.4, 0.5)
    if k > 0: cv = snow(cv, t, k)
    if t < 0.6: cv = Image.blend(Image.new('RGB', (W, H), (10, 8, 20)), cv, smooth(t / 0.6))
    eyes(cv, f, t)
    districts(cv, f, t)
    castaway(cv, f, t)
    comments(cv, f, t)
    question(cv, f, t)
    phone_overlays(cv, f, t)
    hud_chip(cv, f, t)
    titles(cv, f, t)
    subtitles(cv, t)
    return cv


if __name__ == '__main__':
    args = sys.argv[1:]
    if '--test' in args:
        os.makedirs(TEST, exist_ok=True)
        for f in map(int, args[args.index('--test') + 1:]):
            compose(f).save(f'{TEST}/t{f:05d}.jpg', quality=90)
            print('test', f, f'{f / FPS:.2f}s')
        sys.exit(0)
    os.makedirs(COMP, exist_ok=True)
    force = '--force' in args
    done = 0
    for f in range(N):
        out = f'{COMP}/f{f:05d}.jpg'
        if not force and os.path.exists(out) and os.path.getsize(out) > 1000: continue
        compose(f).save(out + '.tmp', 'JPEG', quality=95, subsampling=0)
        os.replace(out + '.tmp', out)
        done += 1
        if done % 100 == 0: print('composed', f, flush=True)
    print('COMPOSE DONE', done, 'new frames')
