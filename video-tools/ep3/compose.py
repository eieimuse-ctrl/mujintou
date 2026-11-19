#!/usr/bin/env python3
"""ep3 合成：python3 ep3/compose.py <story.json>
録画コマ（build/ep3/<名>/frames）に、看板・名札・吹き出し・アクション名・結果文を1コマずつ描き、
ナレーション（VOICEVOX）と BGM を混ぜて mp4 にする。再実行すると、できている合成コマは飛ばす。

画面のルール（docs/EP3-PLAN.md「画面のルール」）
- 主役：大きな名札（投票チップ＋名前＋@ID）＋本人のコメントをそのまま吹き出しに
- 今回コメントした人：小さな名札（色の点＋名前）。画面に smallTagsMax 人より多くいるときは出さない
- 下：アクション名（白・大）→ 結果（黄）。結果は台本の時刻＝結果が画面で分かったコマから
- 文字は Reels の安全域の内側（下から約20%・右端150px には置かない）

環境変数：FONT（本文）、FONT_BLACK（太字）、EMOJI_FONT、BGM（mp3）、VOICEVOX（既定 http://127.0.0.1:50021）
"""
import json, os, sys, hashlib, subprocess, urllib.request, urllib.parse, wave, unicodedata
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
story_path = os.path.abspath(sys.argv[1])
S = json.load(open(story_path, encoding='utf-8'))
NAME = os.path.splitext(os.path.basename(story_path))[0]
BUILD = os.path.join(HERE, '..', 'build', 'ep3', NAME)
OUTDIR = os.path.join(HERE, '..', 'out')
FR, COMP = os.path.join(BUILD, 'frames'), os.path.join(BUILD, 'comp')
os.makedirs(COMP, exist_ok=True); os.makedirs(OUTDIR, exist_ok=True)
FPS = S.get('fps', 24)
N = round(S['duration'] * FPS)

FONT = os.environ.get('FONT', '/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc')
FONT_BLACK = os.environ.get('FONT_BLACK', '/usr/share/fonts/opentype/noto/NotoSansCJK-Black.ttc')
EMOJI = os.environ.get('EMOJI_FONT', '/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf')
if not os.path.exists(FONT_BLACK):
    print(f'!! 太字フォントが無い（{FONT_BLACK}）。Bold で代用するので見た目が少し変わる：sudo apt install fonts-noto-cjk-extra')
    FONT_BLACK = FONT
if not os.path.exists(EMOJI):
    print(f'!! 絵文字フォントが無い（{EMOJI}）。絵文字が出ない：sudo apt install fonts-noto-color-emoji')
_fc = {}
def font(size, black=False):
    k = (size, black)
    if k not in _fc: _fc[k] = ImageFont.truetype(FONT_BLACK if black else FONT, size)
    return _fc[k]
_emo = None
def emoji_font():
    global _emo
    if _emo is None: _emo = ImageFont.truetype(EMOJI, 109) if os.path.exists(EMOJI) else False
    return _emo

INK = (35, 29, 54); CREAM = (255, 248, 230); YELLOW = (255, 214, 74)
VOTE = {'A': (63, 143, 214), 'B': (176, 120, 60), 'C': (70, 160, 80)}
W, H = 1080, 1920
SAFE_BOTTOM, SAFE_RIGHT = 1520, 150

# ---- 絵文字まじりの文字（絵文字はカラー絵文字フォントで描いて縮める） ----
def is_emoji(ch):
    o = ord(ch)
    return o >= 0x1F000 or 0x2600 <= o <= 0x27BF or o in (0x2B50, 0x2B55, 0x3030, 0x303D) or 0xFE00 <= o <= 0xFE0F or o == 0x200D
def displayable(text):
    """装飾文字（𝓗𝓲𝓻𝓸 など数学用の英字・丸文字）は、ふつうの文字にして描く（フォントに無く□になるため）"""
    out = []
    for ch in str(text):
        o = ord(ch)
        if 0x1D400 <= o <= 0x1D7FF or 0x2100 <= o <= 0x214F or 0x24B6 <= o <= 0x24E9 or 0xFF01 <= o <= 0xFF5E and False:
            out.append(unicodedata.normalize('NFKC', ch))
        else:
            out.append(ch)
    return ''.join(out)

def runs(text):
    text = displayable(text)
    out, cur, emo = [], '', None
    for ch in text:
        e = is_emoji(ch)
        if emo is None or e == emo: cur += ch
        else: out.append((cur, emo)); cur = ch
        emo = e
    if cur: out.append((cur, emo))
    return out
def text_w(d, text, size, black=False):
    w = 0
    for r, e in runs(text):
        if e and emoji_font():
            w += size * sum(1 for c in r if not (0xFE00 <= ord(c) <= 0xFE0F or ord(c) == 0x200D))
        else:
            w += d.textlength(r, font=font(size, black))
    return w
def draw_text(img, d, x, y, text, size, fill, black=False, stroke=0, stroke_fill=INK):
    """左上 (x, y) から描く（y は文字の上端の目安）。"""
    for r, e in runs(text):
        if e and emoji_font():
            for ch in r:
                if 0xFE00 <= ord(ch) <= 0xFE0F or ord(ch) == 0x200D: continue
                g = Image.new('RGBA', (136, 128), (0, 0, 0, 0))
                ImageDraw.Draw(g).text((0, 0), ch, font=emoji_font(), embedded_color=True)
                bb = g.getbbox()
                if bb: g = g.crop(bb)
                g = g.resize((size, max(1, int(size * g.height / max(1, g.width)))), Image.LANCZOS)
                img.alpha_composite(g, (int(x), int(y + size * 0.12)))
                x += size
        else:
            d.text((x, y), r, font=font(size, black), fill=fill, stroke_width=stroke, stroke_fill=stroke_fill)
            x += d.textlength(r, font=font(size, black))
def wrap(d, text, size, maxw):
    """コメントの改行は残し、そのうえで長い行は句読点のあとを優先して折り返す。"""
    out = []
    for para in str(text).replace('\r', '').split('\n'):
        para = para.strip()
        if para: out += wrap_line(d, para, size, maxw)
    return out or ['']

def wrap_line(d, text, size, maxw):
    lines, cur = [], ''
    for ch in text:
        if text_w(d, cur + ch, size) > maxw and cur:
            # 直前の句読点で切れるなら、そこで切る
            cut = max(cur.rfind('、'), cur.rfind('。'), cur.rfind('！'), cur.rfind('？'))
            if cut >= len(cur) * 0.5: lines.append(cur[:cut + 1]); cur = cur[cut + 1:] + ch
            else: lines.append(cur); cur = ch
        else:
            cur += ch
    if cur: lines.append(cur)
    return lines

# ---- 部品 ----
def banner(img, d, text):
    w = text_w(d, text, 38) + 70
    d.rounded_rectangle([W / 2 - w / 2, 96, W / 2 + w / 2, 176], 40, fill=(35, 29, 54, 215))
    draw_text(img, d, W / 2 - (w - 70) / 2, 110, text, 38, (255, 255, 255))

def big_tag(img, d, X, Y, name, uid, vote):
    """主役の名札。(X, Y)＝頭の上。戻り値：名札の上端 y"""
    wn = text_w(d, name, 38); wi = d.textlength('@' + uid, font=font(24))
    w = int(max(wn, wi)) + 40 + (64 if vote else 0); h = 96
    x0 = max(30, min(W - SAFE_RIGHT - w, X - w // 2)); y0 = Y - 14 - h
    d.rounded_rectangle([x0, y0, x0 + w, y0 + h], 16, fill=CREAM, outline=INK, width=5)
    tx = x0 + 18
    if vote:
        d.rounded_rectangle([x0 + 12, y0 + 18, x0 + 64, y0 + 78], 12, fill=VOTE[vote])
        d.text((x0 + 38, y0 + 48), vote, font=font(40, True), fill='white', anchor='mm')
        tx = x0 + 78
    draw_text(img, d, tx, y0 + 6, name, 38, INK)
    d.text((tx + 2, y0 + 56), '@' + uid, font=font(24), fill=(110, 100, 130))
    return y0

def bubble(img, d, X, y_tag, text):
    """本人のコメント（そのまま）。しっぽは名札（＝本人）へ"""
    size = 44
    lines = wrap(d, text, size, 620)
    lw = max(text_w(d, l, size) for l in lines)
    bw = int(lw) + 56; bh = len(lines) * 60 + 40
    bx0 = max(36, min(W - SAFE_RIGHT - bw, X - bw // 2 + 40)); by1 = y_tag - 34; by0 = by1 - bh
    if by0 < 200:  # 看板にかぶるときは下げる
        by0 = 200; by1 = by0 + bh
    d.rounded_rectangle([bx0, by0, bx0 + bw, by1], 28, fill='white', outline=INK, width=5)
    tx = max(bx0 + 30, min(bx0 + bw - 30, X))
    d.polygon([(tx - 16, by1 - 3), (tx + 16, by1 - 3), (tx - 2, y_tag - 4)], fill='white')
    d.line([(tx - 16, by1 + 1), (tx - 2, y_tag - 4), (tx + 16, by1 + 1)], fill=INK, width=5)
    for i, l in enumerate(lines): draw_text(img, d, bx0 + 28, by0 + 16 + i * 60, l, size, INK)

def small_tag(img, d, X, Y, name, vote):
    tw = int(text_w(d, name, 26)) + 52
    x0 = max(10, min(W - SAFE_RIGHT - tw, X - tw // 2))
    d.rounded_rectangle([x0, Y - 56, x0 + tw, Y - 10], 12, fill=(255, 248, 230, 215))
    d.ellipse([x0 + 12, Y - 42, x0 + 30, Y - 24], fill=VOTE.get(vote, (150, 150, 150)))
    draw_text(img, d, x0 + 38, Y - 52, name, 26, INK)

def stroke_center(img, d, text, y, size, fill):
    w = text_w(d, text, size, True)
    draw_text(img, d, W / 2 - w / 2, y - size * 0.7, text, size, fill, black=True, stroke=9)

def caption(img, d, text, y, size, fill, alpha=1.0):
    """中央の縁取り文字（つかみ・…1人足りない・あと◯人 など）"""
    stroke_center(img, d, text, y, size, fill)

def title_badge(img, d, text, t, a, b):
    """大きな「◯日目」バッジ（つかみ）。入りで少し弾む"""
    u = min(1, (t - a) / 0.25)
    sc = 0.7 + 0.3 * (1 - (1 - u) ** 3) + (0.06 * (1 - u) if u < 1 else 0)
    fs = int(120 * sc); w = int(text_w(d, text, fs, True)) + 110; h = int(fs * 1.5)
    x0, y0 = W // 2 - w // 2, 430 - h // 2
    d.rounded_rectangle([x0, y0, x0 + w, y0 + h], 40, fill=(244, 196, 64), outline=INK, width=8)
    draw_text(img, d, W / 2 - (w - 110) / 2, y0 + h / 2 - fs * 0.72, text, fs, INK, black=True)

def tally(img, d, T, t):
    """集計バー：件数が伸びて、最多に「採用」"""
    rows = T['rows']; mx = max(r['count'] for r in rows) or 1
    g0, g1 = T.get('grow', [T['from'] + 0.3, T['from'] + 1.8])
    u = max(0, min(1, (t - g0) / max(0.01, g1 - g0))); u = 1 - (1 - u) ** 3
    x0, y0, bw = 90, 560, W - 90 - 90 - SAFE_RIGHT + 60
    d.rounded_rectangle([60, y0 - 110, W - 60, y0 + len(rows) * 150 + 20], 30, fill=(255, 248, 230, 240), outline=INK, width=6)
    draw_text(img, d, 100, y0 - 92, T.get('title', 'コメントの数'), 40, INK)
    for i, r in enumerate(rows):
        y = y0 + i * 150
        d.rounded_rectangle([x0, y + 10, x0 + 70, y + 80], 14, fill=VOTE.get(r['key'], (150, 150, 150)))
        d.text((x0 + 35, y + 45), r['key'], font=font(46, True), fill='white', anchor='mm')
        draw_text(img, d, x0 + 90, y + 2, r['label'], 34, INK)
        full = W - 180 - (x0 + 90) - 40
        L = int(full * r['count'] / mx * u)
        d.rounded_rectangle([x0 + 90, y + 56, x0 + 90 + max(10, L), y + 96], 10, fill=VOTE.get(r['key'], (150, 150, 150)))
        n = round(r['count'] * u)
        d.text((x0 + 90 + max(10, L) + 16, y + 76), f'{n}件', font=font(40, True), fill=INK, anchor='lm')
        if T.get('winner') == r['key'] and t >= T.get('winnerAt', g1 + 0.3):
            k = min(1, (t - T['winnerAt']) / 0.2)
            sz = int(60 * (1.6 - 0.6 * k))
            cx, cy = W - 170, y + 50
            d.rounded_rectangle([cx - sz * 1.3, cy - sz * 0.7, cx + sz * 1.3, cy + sz * 0.7], 16, outline=(214, 60, 50), width=8, fill=(255, 255, 255, 230))
            d.text((cx, cy), '採用', font=font(sz, True), fill=(214, 60, 50), anchor='mm')

def wall(img, d, Wl, t):
    """みんなの声：名前と一言のカードを順に出す（2列）"""
    d.rounded_rectangle([40, 220, W - 40, 1500], 30, fill=(35, 29, 54, 200))
    draw_text(img, d, 80, 236, Wl.get('title', 'みんなの声'), 48, (255, 214, 74), black=True)
    items = Wl['items']; dt = Wl.get('step', 0.12)
    colw = (W - 40 * 2 - 40 * 3) // 2
    y = [330, 330]
    for i, it in enumerate(items):
        if t < Wl['from'] + 0.2 + i * dt: break
        c = 0 if y[0] <= y[1] else 1
        x = 80 + c * (colw + 40)
        lines = wrap(d, it['text'], 30, colw - 40)[:3]
        h = 62 + len(lines) * 40
        if y[c] + h > 1480: continue
        d.rounded_rectangle([x, y[c], x + colw, y[c] + h], 16, fill=CREAM)
        d.ellipse([x + 16, y[c] + 18, x + 36, y[c] + 38], fill=VOTE.get(it.get('vote'), (150, 150, 150)))
        draw_text(img, d, x + 46, y[c] + 8, it['name'], 28, INK)
        for j, l in enumerate(lines): draw_text(img, d, x + 20, y[c] + 52 + j * 40, l, 30, (60, 54, 80))
        y[c] += h + 16

def chip(img, d, text, t, a, b):
    """画面の隅の小さなチップ（URL の案内など）。動画は止めない"""
    w = text_w(d, text, 30) + 90
    x0, y0 = 40, 200
    d.rounded_rectangle([x0, y0, x0 + w, y0 + 62], 31, fill=(255, 248, 230, 235), outline=INK, width=4)
    d.ellipse([x0 + 18, y0 + 18, x0 + 44, y0 + 44], fill=(70, 160, 80))
    draw_text(img, d, x0 + 58, y0 + 8, text, 30, INK)

_imgs = {}
def picture(img, P, t):
    """画像（スマホ画面など）を下から差し込む"""
    if P['file'] not in _imgs:
        _imgs[P['file']] = Image.open(os.path.join(os.path.dirname(story_path), P['file'])).convert('RGBA')
    im = _imgs[P['file']]
    w = P.get('w', 600); h = int(im.height * w / im.width)
    u = min(1, (t - P['from']) / 0.3); u = 1 - (1 - u) ** 3
    x = P.get('x', (W - w) // 2); y = int(P.get('y', 260) + (1 - u) * 400)
    frame = Image.new('RGBA', (w + 36, h + 36), (0, 0, 0, 0))
    ImageDraw.Draw(frame).rounded_rectangle([0, 0, w + 35, h + 35], 44, fill=(35, 29, 54, 255))
    frame.alpha_composite(im.resize((w, h), Image.LANCZOS), (18, 18))
    img.alpha_composite(frame, (x - 18, y - 18))

def fade(t, a, b, k=0.12):
    """a〜b の間だけ 1（入りと終わりを k 秒でふわっと）"""
    if t < a or t > b: return 0
    return min(1, (t - a) / k, (b - t) / k)

# ---- 名簿（表示名） ----
roster = json.load(open(os.path.join(os.path.dirname(story_path), S['roster']), encoding='utf-8'))
NAMES = {p['id']: p.get('name') or p['id'] for p in roster['islanders']}
NAMES.update(S.get('overlay', {}).get('names', {}))
O = S['overlay']
track = {}
for line in open(os.path.join(BUILD, 'track.jsonl'), encoding='utf-8'):
    r = json.loads(line); track[r['i']] = r['people']

def head_y(p):
    return (p['hy'] + (p['fy'] - p['hy']) * 0.13) * H

def compose_frame(i):
    out = os.path.join(COMP, f'f{i:05d}.jpg')
    if os.path.exists(out): return
    t = i / FPS
    base = Image.open(os.path.join(FR, f'f{i:05d}.jpg')).convert('RGBA')
    if base.size != (W, H): base = base.resize((W, H), Image.LANCZOS)
    layer = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(layer)
    ppl = track.get(i, {})
    if not any(a <= t <= b for a, b in O.get('bannerOff', [])): banner(layer, d, O['banner'])
    for c in O.get('chips', []):
        if c['from'] <= t <= c['to']: chip(layer, d, c['text'], t, c['from'], c['to'])
    stars = [s for s in O.get('stars', []) if s['from'] <= t <= s['to']]
    star_ids = {s['who'] for s in stars}
    # 小さな名札（今回コメントした人、主役以外）。人が多い引きの画では出さない
    if len(ppl) <= O.get('smallTagsMax', 4):
        for uid, p in ppl.items():
            if uid in O.get('commenters', {}) and uid not in star_ids:
                small_tag(layer, d, p['hx'] * W, head_y(p), NAMES.get(uid, uid), O['commenters'][uid])
    # 全員に小さな名札を出す区間（動画に出ていない島民たちのカット）
    if any(a <= t <= b for a, b in O.get('tagAll', [])) and len(ppl) <= 14:
        for uid, p in ppl.items():
            if uid not in star_ids: small_tag(layer, d, p['hx'] * W, head_y(p), NAMES.get(uid, uid), O.get('commenters', {}).get(uid, '-'))
    for s in stars:
        if s.get('xy'):  # 姿のない人の名札（…1人足りない）
            X, Y = s['xy'][0] * W, s['xy'][1] * H
            y0 = big_tag(layer, d, X, Y, NAMES.get(s['who'], s['who']), s['who'], O.get('commenters', {}).get(s['who']))
            continue
        p = ppl.get(s['who'])
        if not p: continue
        X, Y = p['hx'] * W, head_y(p)
        y0 = big_tag(layer, d, X, Y, NAMES.get(s['who'], s['who']), s['who'], O.get('commenters', {}).get(s['who']))
        if s.get('bubble'): bubble(layer, d, X, y0, s['bubble'])
    for c in O.get('titles', []):
        if c['from'] <= t <= c['to']: title_badge(layer, d, c['text'], t, c['from'], c['to'])
    if O.get('tally') and O['tally']['from'] <= t <= O['tally']['to']: tally(layer, d, O['tally'], t)
    if O.get('wall') and O['wall']['from'] <= t <= O['wall']['to']: wall(layer, d, O['wall'], t)
    for P in O.get('images', []):
        if P['from'] <= t <= P['to']: picture(layer, P, t)
    for c in O.get('captions', []):
        if c['from'] <= t <= c['to']: caption(layer, d, c['text'], c.get('y', 1290), c.get('size', 80), tuple(c.get('color', (255, 255, 255))))
    for a in O.get('action', []):
        if a['from'] <= t <= a['to']: stroke_center(layer, d, a['text'], 1290, 92, (255, 255, 255))
    for r in O.get('result', []):
        if r['from'] <= t <= r['to']: stroke_center(layer, d, r['text'], 1415, 54, YELLOW)
    Image.alpha_composite(base, layer).convert('RGB').save(out, quality=92)

# ---- 音：ナレーション（VOICEVOX 春日部つむぎ＝speaker 8）と BGM ----
VV = os.environ.get('VOICEVOX', 'http://127.0.0.1:50021')
def voice(text, speaker=8):
    os.makedirs(os.path.join(BUILD, 'voice'), exist_ok=True)
    f = os.path.join(BUILD, 'voice', hashlib.md5(f'{speaker}:{text}'.encode()).hexdigest()[:12] + '.wav')
    if os.path.exists(f): return f
    try:
        q = urllib.request.urlopen(urllib.request.Request(f'{VV}/audio_query?speaker={speaker}&text={urllib.parse.quote(text)}', method='POST'), timeout=20).read()
        wav = urllib.request.urlopen(urllib.request.Request(f'{VV}/synthesis?speaker={speaker}', data=q, headers={'content-type': 'application/json'}, method='POST'), timeout=60).read()
        open(f, 'wb').write(wav); return f
    except Exception as e:
        print(f'!! VOICEVOX に届かないので、ナレーション「{text}」は無音（{e.__class__.__name__}）')
        return None

def build_audio():
    # ffmpeg の入力0はコマ画像（音声なし）なので、音声の入力番号は 1 から数える（src）。k は混ぜる本数
    inputs, filters, k = [], [], 0
    src = lambda: k + 1
    for n in S.get('audio', {}).get('narration', []):
        f = voice(n['text'])
        if not f: continue
        inputs += ['-i', f]; ms = int(n['at'] * 1000)
        filters.append(f'[{src()}:a]adelay={ms}|{ms},volume=1.0[n{k}]'); k += 1
    bgm = os.environ.get('BGM', os.path.expanduser('~/workspace/mujintou/video/assets/bgm.mp3'))
    bg = S.get('audio', {}).get('bgm')
    if bg and os.path.exists(bgm):
        inputs += ['-i', bgm]; dur = S['duration']
        filters.append(f'[{src()}:a]atrim=0:{dur},asetpts=PTS-STARTPTS,volume={bg.get("volume", 0.18)},afade=t=in:d=0.5,afade=t=out:st={max(0, dur - 2)}:d=2[n{k}]'); k += 1
    elif bg:
        print(f'!! BGM が無い（{bgm}）。BGM なしで出す')
    if not k: return None, []
    mix = ''.join(f'[n{j}]' for j in range(k)) + f'amix=inputs={k}:normalize=0:duration=longest,apad,atrim=0:{S["duration"]}[aout]'
    return ';'.join(filters + [mix]), inputs

if __name__ == '__main__':
    missing = [i for i in range(N) if not os.path.exists(os.path.join(FR, f'f{i:05d}.jpg'))]
    if missing:
        sys.exit(f'録画コマが {len(missing)} 枚足りない（最初は f{missing[0]:05d}）。rec.mjs を再実行してください')
    for i in range(N): compose_frame(i)
    fc, ain = build_audio()
    master = os.path.join(OUTDIR, f'{NAME}.mp4')
    vf = 'scale=in_range=full:in_color_matrix=bt601:out_range=tv:out_color_matrix=bt709,format=yuv420p'
    cmd = ['ffmpeg', '-y', '-v', 'error', '-framerate', str(FPS), '-i', os.path.join(COMP, 'f%05d.jpg')] + ain
    if fc: cmd += ['-filter_complex', fc, '-map', '0:v', '-map', '[aout]', '-c:a', 'aac', '-b:a', '192k']
    cmd += ['-vf', vf, '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '20', '-color_primaries', 'bt709', '-color_trc', 'bt709', '-colorspace', 'bt709', '-movflags', '+faststart', '-t', str(S['duration']), master]
    subprocess.run(cmd, check=True)
    # Instagram に上げられる大きさ（100MB 未満）に収める：超えたら CRF を上げて作り直す
    crf = 20
    while os.path.getsize(master) > 95 * 1024 * 1024 and crf < 32:
        crf += 3
        print(f'!! {os.path.getsize(master) / 1e6:.0f}MB あるので CRF {crf} で作り直す')
        cmd[cmd.index('-crf') + 1] = str(crf)
        subprocess.run(cmd, check=True)
    print(f'投稿用 {os.path.getsize(master) / 1e6:.1f}MB（CRF {crf}）')
    prev = os.path.join(OUTDIR, f'{NAME}_preview.mp4')
    subprocess.run(['ffmpeg', '-y', '-v', 'error', '-i', master, '-vf', 'scale=780:1688', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '26', '-c:a', 'copy', '-movflags', '+faststart', prev], check=True)
    # 確認用のコマ一覧（1秒ごと）
    sheet = os.path.join(OUTDIR, f'{NAME}_sheet.jpg')
    subprocess.run(['ffmpeg', '-y', '-v', 'error', '-i', master, '-vf', 'fps=1,scale=216:384,tile=7x2', '-frames:v', '1', sheet], check=True)
    # 表紙（ギャラリー用）：録画コマ1枚＋中央に黄色の「◯日目」＋看板＋一言の結果。3:4 の切り抜き（y 240〜1680）に収める
    cv = S.get('cover')
    if cv:
        i = min(N - 1, round(cv['at'] * FPS))
        im = Image.open(os.path.join(FR, f'f{i:05d}.jpg')).convert('RGBA').resize((W, H), Image.LANCZOS)
        L = Image.new('RGBA', (W, H), (20, 30, 60, 70)); dd = ImageDraw.Draw(L)
        fs = 150; tw = text_w(dd, cv['day'], fs, True)
        dd.rounded_rectangle([W / 2 - tw / 2 - 60, 500, W / 2 + tw / 2 + 60, 720], 44, fill=(244, 196, 64), outline=INK, width=9)
        draw_text(L, dd, W / 2 - tw / 2, 518, cv['day'], fs, INK, black=True)
        stroke_center(L, dd, O['banner'].split('　')[0], 830, 66, (255, 255, 255))
        for k, line in enumerate(cv['lines']):
            stroke_center(L, dd, line, 1230 + k * 120, 84, YELLOW if k == 0 else (255, 255, 255))
        Image.alpha_composite(im, L).convert('RGB').save(os.path.join(OUTDIR, f'{NAME}_cover.jpg'), quality=92)
    # 何から作ったかの記録（Claude と Muse で同じ入力かを照合する）
    def sha(path):
        try: return hashlib.sha256(open(path, 'rb').read()).hexdigest()[:16]
        except Exception: return None
    def run(c):
        try: return subprocess.run(c, capture_output=True, text=True, cwd=HERE).stdout.strip()
        except Exception: return None
    env = json.load(open(os.path.join(BUILD, 'env.json'))) if os.path.exists(os.path.join(BUILD, 'env.json')) else {}
    try: vv = urllib.request.urlopen(f'{VV}/version', timeout=3).read().decode().strip('"')
    except Exception: vv = None
    bgm_path = os.environ.get('BGM', os.path.expanduser('~/workspace/mujintou/video/assets/bgm.mp3'))
    man = {
        'story': os.path.relpath(story_path, os.path.join(HERE, '..', '..')), 'story_sha': sha(story_path),
        'roster_sha': sha(os.path.join(os.path.dirname(story_path), S['roster'])),
        'git_commit': run(['git', 'rev-parse', '--short', 'HEAD']), 'git_dirty': bool(run(['git', 'status', '--porcelain', '--', '.', '../../js'])),
        'code_sha': {f: sha(os.path.join(HERE, f)) for f in ['rec.mjs', 'lib/stage.js', 'compose.py']},
        'chrome': env.get('chrome'), 'voicevox': vv, 'bgm_sha': sha(bgm_path),
        'fonts': {'bold': os.path.exists(FONT), 'black': FONT_BLACK != FONT, 'emoji': bool(emoji_font())},
        'frames': N, 'size_mb': round(os.path.getsize(master) / 1e6, 1), 'crf': crf,
    }
    json.dump(man, open(os.path.join(OUTDIR, f'{NAME}_manifest.json'), 'w'), ensure_ascii=False, indent=1)
    print('記録:', json.dumps(man, ensure_ascii=False))
    print('出力:', master, prev, sheet)
