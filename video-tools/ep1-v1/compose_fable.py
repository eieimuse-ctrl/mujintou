#!/usr/bin/env python3
"""ep1 revision — composite recorded takes (build/rec/{a,b,c}) + overlays into build/comp/f%05d.jpg.

  python3 compose_fable.py                 all 1152 frames (existing files are skipped -> resumable)
  python3 compose_fable.py --force         re-render everything
  python3 compose_fable.py --test 30 96 …  only these film frames, written to build/test/

Every overlay is a pure function of film time t (= frame / 24); tracked elements read
build/tracks.json (screen positions of world points, exported by fable_tracks.mjs).
"""
import json, math, os, random, sys
from functools import lru_cache
from PIL import Image, ImageDraw, ImageFont, ImageFilter

V = os.path.expanduser('~/workspace/mujintou/video')
REC, COMP, TEST = f'{V}/build/rec', f'{V}/build/comp', f'{V}/build/test'
FONT = '/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc'
W, H, FPS, N = 1080, 1920, 24, 1152
F_B0, F_BX, F_C0 = 294, 306, 467  # b starts (dissolve begins) / dissolve ends / hard cut to c

INK, INK2 = (35, 29, 54), (58, 51, 82)
CREAM, WHITE = (251, 242, 216), (255, 255, 255)
YELLOW, ACC = (242, 194, 48), (255, 216, 74)
ORANGE, REDBROWN, PINK = (232, 100, 60), (184, 67, 31), (226, 96, 126)
GREEN, BLUE, ICE, GREY = (63, 154, 69), (47, 127, 208), (170, 225, 255), (93, 86, 116)

TR = json.load(open(f'{V}/build/tracks.json'))
PT = {n: i for i, n in enumerate(TR['names'])}


def shot_of(f):
    if f < F_B0 + 6: return 'a', f
    if f < F_C0: return 'b', f - F_B0
    return 'c', f - F_C0


def track(name, f, shot=None):
    """-> (x px, y px, distance) of a world point; distance < 0 when behind the camera"""
    s, i = shot_of(f)
    if shot and shot != s:
        s, i = shot, {'a': f, 'b': f - F_B0, 'c': f - F_C0}[shot]
    fr = TR['shots'][s]['frames']
    p = fr[max(0, min(len(fr) - 1, i))]['pts'][PT[name]]
    return p[0] * W, p[1] * H, p[2]


def hour_at(f):
    s, i = shot_of(f)
    fr = TR['shots'][s]['frames']
    return fr[max(0, min(len(fr) - 1, i))]['hour'] % 24


# ---------------------------------------------------------------- helpers
clamp = lambda x, a=0.0, b=1.0: max(a, min(b, x))
smooth = lambda x: (lambda u: u * u * (3 - 2 * u))(clamp(x))


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
    return Image.open(f'{REC}/{shot}/f{i:05d}.jpg').convert('RGB')


def base(f):
    if f < F_B0: return load('a', f)
    if f < F_BX: return Image.blend(load('a', f), load('b', f - F_B0), smooth((f - F_B0 + 0.5) / (F_BX - F_B0)))
    if f < F_C0: return load('b', f - F_B0)
    return load('c', f - F_C0)


# ---------------------------------------------------------------- subtitles (phrase-synced to the narration)
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
    (42.3, [[(39.38, (('コメント', ACC), ('で、', Wt))), (40.51, (('教えてください。', Wt),))]]),
]
SUB_SIZE, SUB_PITCH = 58, 90


def subtitles(cv, t):
    for n, (end, lines) in enumerate(SUBS):
        start = lines[0][0][0]
        if not (start - 0.02 <= t <= end): continue
        out = clamp((end - t) / 0.14)
        f = font(SUB_SIZE)
        cy0 = (1448 if n == len(SUBS) - 1 else 1388) - (len(lines) - 1) * SUB_PITCH / 2
        for li, line in enumerate(lines):
            widths = [sum(f.getlength(s) for s, _ in segs) for _, segs in line]
            x = 540 - sum(widths) / 2
            for (t0, segs), w in zip(line, widths):
                s, a = pop(t, t0, 0.2)
                blit(cv, rich(segs, SUB_SIZE), x + w / 2, cy0 + li * SUB_PITCH, 0.82 + 0.18 * (s - 0.6) / 0.4 if s else 0, a * out)
                x += w


# ---------------------------------------------------------------- scene overlays
def clock_chip(cv, f, t):
    a = fade(t, 0.7, 14.3, 0.3, 0.4)
    if a <= 0: return
    h = hour_at(f); day = 6 <= h < 18
    m = int(h * 6) % 6 * 10
    bg, fg = (CREAM, INK) if day else (INK2, CREAM)
    im = Image.new('RGBA', (232, 84), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle((7, 7, 230, 82), 16, fill=INK + (255,))
    d.rounded_rectangle((0, 0, 223, 75), 16, fill=bg + (255,), outline=INK + (255,), width=5)
    if day:
        d.ellipse((22, 20, 58, 56), fill=YELLOW + (255,), outline=INK + (255,), width=4)
    else:
        d.ellipse((22, 20, 58, 56), fill=(214, 222, 255, 255))
        d.ellipse((34, 14, 66, 46), fill=bg + (255,))
    txt = f'{int(h):d}:{m:02d}'
    fo = font(44); d.text((216 - 14 - fo.getlength('00:00') + (fo.getlength('00:00') - fo.getlength(txt)), 5), txt, font=fo, fill=fg)
    blit(cv, im, 60 + 116, 262 + 42, 1, a)


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
        x = clamp(x, 200, 880); y = clamp(y, 380, 1120)
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


SIL = Image.open(f'{V}/assets/silhouette_you.png').convert('RGBA')
SIL_BODY = SIL.crop((36, 70, 256, 464))   # 394 px tall figure
SIL_TAG = SIL.crop((66, 0, 226, 66))      # the asset's own 「あなた」 name tag
T_LAND, T_HEAD, T_TAG = 14.85, 16.56, 17.96


def silhouette(cv, f, t):
    if t < T_LAND or f >= F_C0: return
    fx, fy, d = track('silFeet', f, 'b'); hx, hy, _ = track('silHead', f, 'b')
    hgt = fy - hy
    if d <= 0 or hgt < 20: return
    x = (t - T_LAND)
    a = clamp(x / 0.35)
    # arrival rings on the sand
    for k in range(2):
        r = (x - 0.12 * k) / 0.7
        if 0 < r < 1:
            rw, rh = hgt * (0.25 + 0.75 * r), hgt * (0.07 + 0.2 * r)
            ov = Image.new('RGBA', (int(rw * 2 + 20), int(rh * 2 + 20)), (0, 0, 0, 0))
            ImageDraw.Draw(ov).ellipse((6, 6, ov.width - 6, ov.height - 6), outline=(255, 255, 255, int(230 * (1 - r))), width=max(3, int(hgt * 0.02)))
            blit(cv, ov, fx, fy)
    # ground shadow
    sw, sh = hgt * 0.62, hgt * 0.11
    ov = Image.new('RGBA', (int(sw), int(sh)), (0, 0, 0, 0))
    ImageDraw.Draw(ov).ellipse((0, 0, ov.width - 1, ov.height - 1), fill=INK + (int(80 * a),))
    blit(cv, ov, fx, fy)
    bob = math.sin((t - T_LAND) * 2 * math.pi * 0.8) * hgt * 0.006
    rise = (1 - back(x / 0.4)) * hgt * 0.18
    k = hgt / SIL_BODY.height
    blit(cv, SIL_BODY, fx, fy + bob + rise, k, a, anchor='b')
    top = fy + bob - hgt
    # 島民 +1
    p = (t - (T_LAND + 0.25)) / 1.3
    if 0 < p < 1:
        s, a1 = pop(t, T_LAND + 0.25)
        blit(cv, plate((('島民 ', INK), ('+1', ORANGE)), 50, bg=YELLOW, padx=24, pady=6, shadow=6), fx + hgt * 0.75, top + hgt * 0.25 - p * 110, s, a1 * clamp((1 - p) / 0.25))
    # 「頭の上には」 -> bouncing marker, then the name tag
    if T_HEAD <= t < T_TAG:
        s, a2 = pop(t, T_HEAD)
        by = top - hgt * 0.10 - abs(math.sin((t - T_HEAD) * 2 * math.pi * 1.6)) * hgt * 0.06
        sz = hgt * 0.13
        ov = Image.new('RGBA', (int(sz * 2 + 16), int(sz * 1.5 + 16)), (0, 0, 0, 0)); dr = ImageDraw.Draw(ov)
        dr.polygon([(4, 4), (ov.width - 4, 4), (ov.width / 2, ov.height - 4)], fill=YELLOW + (255,), outline=INK + (255,), width=6)
        blit(cv, ov, fx, by, s, a2, anchor='b')
    if t >= T_TAG:
        s, a3 = pop(t, T_TAG, 0.3)
        kt = k * 1.7
        tw, th = SIL_TAG.width * kt + 44, SIL_TAG.height * kt + 20
        pl = Image.new('RGBA', (int(tw + 10), int(th + 10)), (0, 0, 0, 0)); dr = ImageDraw.Draw(pl)
        dr.rounded_rectangle((8, 8, tw + 8, th + 8), 16, fill=INK + (255,))
        dr.rounded_rectangle((0, 0, tw, th), 16, fill=CREAM + (255,), outline=INK + (255,), width=5)
        tg = SIL_TAG.resize((round(SIL_TAG.width * kt), round(SIL_TAG.height * kt)), Image.BICUBIC)
        pl.paste(tg, (22, 10), tg)
        ty = top - hgt * 0.06
        blit(cv, pl, fx, ty, s, a3, anchor='b')
        b = (t - T_TAG) / 0.45  # sparkle burst
        if 0 < b < 1:
            ov = Image.new('RGBA', (int(tw * 2.2), int(tw * 1.6)), (0, 0, 0, 0)); dr = ImageDraw.Draw(ov)
            cx, cy = ov.width / 2, ov.height / 2
            for i in range(10):
                ang = i * math.pi / 5 + 0.3
                r0, r1 = tw * (0.5 + 0.35 * b), tw * (0.62 + 0.42 * b)
                dr.line((cx + math.cos(ang) * r0, cy + math.sin(ang) * r0 * 0.62, cx + math.cos(ang) * r1, cy + math.sin(ang) * r1 * 0.62), fill=ACC + (int(255 * (1 - b)),), width=9)
            blit(cv, ov, fx, ty - th / 2)


COMMENTS = [  # track, text, likes, pop time, bubble offset, winner
    ('cForest', '森を探検しよう', 37, 20.0, (-10, -200), False),
    ('cCove', '魚を釣りたい', 64, 20.5, (-90, 170), False),
    ('cBeach', 'いかだを作ろう', 21, 21.0, (-70, 165), False),
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
        # tail from the place on the island to the bubble
        ov = Image.new('RGBA', (W, H), (0, 0, 0, 0)); dr = ImageDraw.Draw(ov)
        al = int(255 * a)
        dr.line((x, y, bx, by), fill=INK + (al,), width=7)
        dr.ellipse((x - 13, y - 13, x + 13, y + 13), fill=(YELLOW if win else CREAM) + (al,), outline=INK + (al,), width=5)
        cv.paste(ov, (0, 0), ov)
        # hearts pulse while 「いいねが一番多い案が」 is spoken
        if 23.65 <= t < T_ADOPT: s *= 1 + 0.035 * math.sin((t - 23.65) * 2 * math.pi * 2.2)
        blit(cv, bubble(text, n, adopted), bx, by, s, a)
        if adopted:
            z = clamp((t - T_ADOPT - 0.08) / 0.18)
            if z > 0:
                st = plate((('採用！', WHITE),), 64, bg=REDBROWN, padx=26, pady=6, shadow=7)
                blit(cv, st, min(bx + 140, 925), by - 150, 2.2 - 1.2 * z ** 0.5, a * clamp(z * 3), rot=-9)  # sits on the bubble's top edge, clear of its text


PINS = [('pinA', 'A', ORANGE, 31.68), ('pinB', 'B', BLUE, 34.57), ('pinC', 'C', GREEN, 36.83)]
OPTIONS = [  # letter, colour, card in, label in, card out, label, note
    ('A', ORANGE, 31.68, 32.62, 34.45, '島の真ん中の平原', '平らで広い。森にも高原にも近い'),
    ('B', BLUE, 34.57, 35.40, 36.75, '入り江のほとり', '波がおだやか。釣りや舟出に向いている'),
    ('C', GREEN, 36.83, 37.72, 39.25, '漂着した砂浜', '見晴らしがよく、漂流者をすぐ迎えられる'),
]
T_Q_OUT = 42.35


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
    if t < 27.5 or t > T_Q_OUT + 0.2: return
    gout = clamp((T_Q_OUT + 0.15 - t) / 0.2)
    # pins on the island — drawn first so that the header plates and cards always sit on top of them
    for name, letter, col, t0 in PINS:
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
        if 30.24 <= t < 30.5:  # second phrase lands with a small kick
            pass
    # option cards, one at a time while each is read out
    for letter, col, t0, t1, t2, label, note in OPTIONS:
        if t0 <= t <= t2:
            s, a = pop(t, t0)
            blit(cv, option_card(letter, col, label, note, t >= t1), 540, 1345, s, a * clamp((t2 - t) / 0.15))
            if t1 <= t < t1 + 0.2:
                pass
    # all three together for the call to action
    if t >= 39.38:
        for k, (letter, col, *_r, label, note) in enumerate(OPTIONS):
            s, a = pop(t, 39.45 + 0.14 * k)
            blit(cv, option_row(letter, col, label), 540, 1130 + k * 96, s, a * gout)


def titles(cv, f, t):
    # opening
    a = fade(t, 0.6, 4.45, 0.4, 0.2)
    if a > 0:
        up = (1 - smooth((t - 0.6) / 0.45)) * 40
        blit(cv, plate((('第1話', INK),), 42, bg=YELLOW, padx=26, pady=6, shadow=6), 540, 322 + up, 1, a)
        blit(cv, rich((('無人島プロジェクト', WHITE),), 94, stroke=9, shadow=7), 540, 440 + up, 1, a)
    if 3.35 <= t <= 4.5:
        s, a = pop(t, 3.35, 0.3)
        blit(cv, plate((('島民 ', INK), ('0', ORANGE), ('人', INK)), 88, padx=44, pady=12, shadow=10), 540, 640, s, a * clamp((4.5 - t) / 0.15))
    # ending
    if t >= 42.71:
        s, a = pop(t, 42.71, 0.3)
        blit(cv, rich((('無人島プロジェクト', WHITE),), 98, stroke=9, shadow=7), 540, 520, s, a)
    if t >= 44.38:
        s, a = pop(t, 44.38, 0.3)
        blit(cv, rich((('まもなく始まります', ACC),), 66, stroke=8, shadow=6), 540, 660, s, a)
    if t >= 45.7:
        s, a = pop(t, 45.7, 0.3)
        s *= 1 + 0.025 * math.sin((t - 45.7) * 2 * math.pi * 1.1)
        blit(cv, plate((('フォローして、最初の漂着者になろう', INK),), 46, bg=YELLOW, padx=34, pady=14, shadow=9), 540, 830, s, a)


def compose(f):
    t = f / FPS
    cv = base(f)
    # looks
    vignette(cv, fade(t, 8.8, 10.6, 0.5, 0.4) * 0.5)
    k = fade(t, 10.55, 12.75, 0.4, 0.5)
    if k > 0: cv = snow(cv, t, k)
    if t < 0.6: cv = Image.blend(Image.new('RGB', (W, H), (10, 8, 20)), cv, smooth(t / 0.6))
    # world-anchored things first, then cards and text
    eyes(cv, f, t)
    districts(cv, f, t)
    silhouette(cv, f, t)
    comments(cv, f, t)
    question(cv, f, t)
    clock_chip(cv, f, t)
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
