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
VOTE = {'A': (63, 143, 214), 'B': (176, 120, 60), 'C': (70, 160, 80), 'D': (150, 100, 180)}
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
    vote = vote if vote in VOTE else None  # 自由コメントの回は投票チップなし
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

def small_tag(img, d, X, Y, name, vote, fs=26):
    k = fs / 26
    tw = int(text_w(d, name, fs) + 52 * k)
    x0 = max(10, min(W - SAFE_RIGHT - tw, X - tw // 2))
    d.rounded_rectangle([x0, Y - 56 * k, x0 + tw, Y - 10 * k], 12 * k, fill=(255, 248, 230, 215))
    d.ellipse([x0 + 12 * k, Y - 42 * k, x0 + 30 * k, Y - 24 * k], fill=VOTE.get(vote, (150, 150, 150)))
    draw_text(img, d, x0 + 38 * k, Y - 52 * k, name, fs, INK)

def faint_tag(img, X, Y, name, fs=24, alpha=0.62):
    """控えめな名札（半透明）。人の多い場面で、だれがいるか分かる程度に"""
    L = Image.new('RGBA', img.size, (0, 0, 0, 0)); dl = ImageDraw.Draw(L)
    name = re.split(r'[｜|/／]', name)[0].strip() or name  # 「名前｜肩書き」は名前だけ
    if len(name) > 10: name = name[:9] + '…'
    tw = int(text_w(dl, name, fs)) + 20
    x0 = max(10, min(W - SAFE_RIGHT - tw, X - tw // 2))
    dl.rounded_rectangle([x0, Y, x0 + tw, Y + fs + 12], 10, fill=(255, 248, 230, 200))
    draw_text(L, dl, x0 + 10, Y + 1, name, fs, INK)
    a = L.split()[3].point(lambda v: int(v * alpha)); L.putalpha(a)
    img.alpha_composite(L)

def stroke_center(img, d, text, y, size, fill):
    w = text_w(d, text, size, True)
    draw_text(img, d, W / 2 - w / 2, y - size * 0.7, text, size, fill, black=True, stroke=9)

SIL = ['.....xxxxx......', '....xxxxxxx.....', '...xxxxxxxxx....', '...xxxxxxxxx....', '...xxxxxxxxx....', '....xxxxxxx.....',
       '.....xxxxx......', '...xxxxxxxxx....', '..xxxxxxxxxxx...', '..xxxxxxxxxxx...', '..xxxxxxxxxxx...', '..xxxxxxxxxxx...',
       '..xx.xxxxx.xx...', '....xxxxxxx.....', '....xxx.xxx.....', '....xxx.xxx.....', '....xxx.xxx.....', '...xxxx.xxxx....']
def silhouette(img, X, Yfeet, px):
    """ドット絵の人影（色はつけない）"""
    d = ImageDraw.Draw(img)
    h = len(SIL) * px; x0 = X - 8 * px; y0 = Yfeet - h
    for j, row in enumerate(SIL):
        for i, ch in enumerate(row):
            if ch == 'x': d.rectangle([x0 + i * px, y0 + j * px, x0 + (i + 1) * px - 1, y0 + (j + 1) * px - 1], fill=(28, 24, 44, 235))

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

def likebar(img, d, L, t):
    """島のいいね合計のバー（PWA と同じ）。{"from","to","total","max","goals":[{"at","label"}],"y","from0"}。数字は from0 から伸びる"""
    a = L['from']; u = min(1, max(0, (t - a - 0.2) / 1.0)); u = 1 - (1 - u) ** 3
    total = round(L.get('from0', 0) + (L['total'] - L.get('from0', 0)) * u); mx = L.get('max', 1000)
    y0 = L.get('y', 560); x0, x1 = 90, W - 90
    pop = min(1, (t - a) / 0.25); sc = 0.85 + 0.15 * (1 - (1 - pop) ** 3)
    d.rounded_rectangle([60, y0 - 120, W - 60, y0 + 215], 30, fill=(255, 248, 230, 240), outline=INK, width=6)
    draw_text(img, d, 100, y0 - 100, '島のいいね合計（全投稿）', 38, INK)
    d.text((W - 100, y0 - 78), f'{total} / {mx}', font=font(int(48 * sc), True), fill=(214, 60, 90), anchor='rm')
    d.rectangle([x0, y0, x1, y0 + 56], fill=(234, 223, 200), outline=INK, width=6)
    fw = int((x1 - x0 - 12) * min(1, total / mx))
    if fw > 0: d.rectangle([x0 + 6, y0 + 6, x0 + 6 + fw, y0 + 50], fill=(226, 69, 106))
    for g in L.get('goals', []):
        gx = x0 + (x1 - x0) * g['at'] / mx
        done = total >= g['at']
        if g['at'] < mx: d.rectangle([gx - 3, y0 - 8, gx + 3, y0 + 64], fill=(47, 143, 74) if done else INK)
    for k, g in enumerate(L.get('goals', [])):
        done = total >= g['at']
        draw_text(img, d, 110, y0 + 74 + k * 38, ('✓ ' if done else '・') + f"{g['at']}：{g['label']}", 30, (47, 143, 74) if done else (70, 60, 90))

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

def ranking(img, d, Rk, t):
    """いいね順位（自由コメントの採用）：上位を1行ずつ出して、1位に「採用」"""
    rows = Rk['rows']; y0 = 520
    d.rounded_rectangle([60, y0 - 110, W - 60, y0 + len(rows) * 170], 30, fill=(255, 248, 230, 240), outline=INK, width=6)
    draw_text(img, d, 100, y0 - 92, Rk.get('title', 'いいねの多かったコメント'), 40, INK)
    for i, r in enumerate(rows):
        if t < Rk['from'] + 0.3 + (len(rows) - 1 - i) * 0.45: continue  # 下の順位から出す
        y = y0 + i * 170
        d.rounded_rectangle([90, y, 160, y + 70], 14, fill=(214, 60, 50) if i == 0 else (120, 110, 140))
        d.text((125, y + 35), f'{i + 1}', font=font(44, True), fill='white', anchor='mm')
        draw_text(img, d, 180, y - 4, r['name'], 32, INK)
        lines = wrap(d, r['text'], 34, W - 180 - 200)[:2]
        for j, l in enumerate(lines): draw_text(img, d, 180, y + 40 + j * 44, l, 34, (60, 54, 80))
        d.text((W - 110, y + 35), f"♥{r['likes']}", font=font(42, True), fill=(214, 60, 50), anchor='rm')
        if i == 0 and t >= Rk.get('winnerAt', 99):
            k = min(1, (t - Rk['winnerAt']) / 0.2); sz = int(54 * (1.6 - 0.6 * k))
            cx, cy = W - 200, y - 40
            d.rounded_rectangle([cx - sz * 1.3, cy - sz * 0.7, cx + sz * 1.3, cy + sz * 0.7], 16, outline=(214, 60, 50), width=8, fill=(255, 255, 255, 235))
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
    if P.get('tap'):  # ここを押す、の輪（脈打つ）
        tx, ty = x + P['tap'][0] * w, y + P['tap'][1] * h
        ph = ((t - P['from']) * 1.6) % 1
        dd = ImageDraw.Draw(img)
        for rr, a in [(46 + ph * 40, int(255 * (1 - ph))), (40, 255)]:
            dd.ellipse([tx - rr, ty - rr * 0.55, tx + rr, ty + rr * 0.55], outline=(255, 214, 74, a), width=8)
        if P.get('tapLabel'):
            tw = text_w(dd, P['tapLabel'], 40) + 50
            dd.rounded_rectangle([tx - tw / 2, ty + 70, tx + tw / 2, ty + 140], 34, fill=(255, 214, 74), outline=INK, width=5)
            draw_text(img, dd, tx - (tw - 50) / 2, ty + 82, P['tapLabel'], 40, INK)
    if P.get('note'):
        dd = ImageDraw.Draw(img)
        nw = text_w(dd, P['note'], 40) + 60
        dd.rounded_rectangle([W / 2 - nw / 2, y + h + 30, W / 2 + nw / 2, y + h + 110], 40, fill=(255, 214, 74), outline=INK, width=5)
        draw_text(img, dd, W / 2 - (nw - 60) / 2, y + h + 46, P['note'], 40, INK)

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
    ppos = {k[5:]: v for k, v in ppl.items() if k.startswith('prop:')}  # 名前を付けた小道具の位置
    ppl = {k: v for k, v in ppl.items() if not k.startswith('prop:')}
    if not any(a <= t <= b for a, b in O.get('bannerOff', [])): banner(layer, d, O['banner'])
    for c in O.get('chips', []):
        if c['from'] <= t <= c['to']: chip(layer, d, c['text'], t, c['from'], c['to'])
    hidden = set(O.get('noTag', []))
    stars = [s for s in O.get('stars', []) if s['from'] <= t <= s['to']]
    star_ids = {s['who'] for s in stars}
    # 小さな名札（今回コメントした人、主役以外）。人が多い引きの画では出さない
    if len(ppl) <= O.get('smallTagsMax', 4):
        for uid, p in ppl.items():
            if uid in O.get('commenters', {}) and uid not in star_ids and uid not in hidden:
                small_tag(layer, d, p['hx'] * W, head_y(p), NAMES.get(uid, uid), O['commenters'][uid])
    # 全員に小さな名札を出す区間（動画に出ていない島民たちのカット）
    hidden = set(O.get('noTag', []))
    for ta in O.get('tagAll', []):
        a, b = ta[0], ta[1]; step = ta[2] if len(ta) > 2 else 0
        if not (a <= t <= b): continue
        cand = sorted([(p['d'], uid) for uid, p in ppl.items() if uid not in star_ids and uid not in hidden])[:14]
        cand = sorted(cand, key=lambda c: ppl[c[1]]['hx'])  # 左から順に
        for k, (_, uid) in enumerate(cand):
            if step and t < a + k * step: continue
            p = ppl[uid]
            small_tag(layer, d, p['hx'] * W, head_y(p), NAMES.get(uid, uid), O.get('commenters', {}).get(uid, '-'))
    # 決めた人だけに名札（足もと。頭の上にハートなどがある場面用）：{"from","to","who":[id…],"below":true}
    for ta in O.get('tagOnly', []):
        if not (ta['from'] <= t <= ta['to']): continue
        fs = ta.get('size', 26)
        if ta.get('join'):  # ふたり組など：まとめて1枚（左から「A × B」）
            ps = sorted([(ppl[u]['hx'], u) for u in ta['who'] if u in ppl])
            if not ps: continue
            Y = max(ppl[u]['fy'] for _, u in ps) * H + 66 * fs / 26
            small_tag(layer, d, sum(x for x, _ in ps) / len(ps) * W, Y, ' × '.join(NAMES.get(u, u) for _, u in ps), ta.get('vote', '-'), fs)
            continue
        for uid in ta['who']:
            p = ppl.get(uid)
            if not p: continue
            Y = p['fy'] * H + 66 * fs / 26 if ta.get('below') else head_y(p)
            small_tag(layer, d, p['hx'] * W, Y, NAMES.get(uid, uid), O.get('commenters', {}).get(uid, '-'), fs)
    # 小道具の注釈（種の袋に「小麦　ヘロルトさん」など）：{"label","text","from","to","size"}
    for pt in O.get('propTags', []):
        p = ppos.get(pt['label'])
        if p and pt['from'] <= t <= pt['to']:
            small_tag(layer, d, p['hx'] * W, p['hy'] * H - 6, pt['text'], pt.get('vote', '-'), pt.get('size', 34))
    for s in stars:
        if s.get('xy'):  # いなくなった人：黒いシルエットと「？？？」（名前は動画では明かさない）
            X, Y = s['xy'][0] * W, s['xy'][1] * H
            silhouette(layer, X, Y + 300, 14)
            big_tag(layer, d, X, Y, s.get('label', '？？？'), s.get('handle', '？？？'), None)
            continue
        p = ppl.get(s['who'])
        if not p: continue
        X, Y = p['hx'] * W, head_y(p)
        y0 = big_tag(layer, d, X, Y, NAMES.get(s['who'], s['who']), s['who'], O.get('commenters', {}).get(s['who']))
        if s.get('bubble'): bubble(layer, d, X, y0, s['bubble'])
    for c in O.get('titles', []):
        if c['from'] <= t <= c['to']: title_badge(layer, d, c['text'], t, c['from'], c['to'])
    if O.get('tally') and O['tally']['from'] <= t <= O['tally']['to']: tally(layer, d, O['tally'], t)
    for L in O.get('likebars', []):
        if L['from'] <= t <= L['to']: likebar(layer, d, L, t)
    if O.get('wall') and O['wall']['from'] <= t <= O['wall']['to']: wall(layer, d, O['wall'], t)
    if O.get('ranking') and O['ranking']['from'] <= t <= O['ranking']['to']: ranking(layer, d, O['ranking'], t)
    for P in O.get('images', []):
        if P['from'] <= t <= P['to']: picture(layer, P, t)
    # 入れ替わる控えめな名札：{"from","to","n":4,"step":2.0,"size":24,"alpha":0.62}
    #   画面に映る人のうち、手前から順に n 人ずつ、step 秒ごとに入れ替え。字幕の帯（いま出ている captions）とは重ねない
    for tc in O.get('tagCycle', []):
        if not (tc['from'] <= t <= tc['to']): continue
        bands = [(c.get('y', 1290) - c.get('size', 80) * 0.9, c.get('y', 1290) + c.get('size', 80) * 0.9) for c in O.get('captions', []) if c['from'] <= t <= c['to']]
        fs = tc.get('size', 24)
        cand = []
        for uid, p in sorted(ppl.items(), key=lambda kv: kv[1]['d']):
            if uid in star_ids: continue
            Y = p['fy'] * H + 8
            if Y > SAFE_BOTTOM or Y < 180 or any(a - 10 < Y < b + 10 or a - 10 < Y + fs + 12 < b + 10 for a, b in bands): continue
            cand.append((uid, p, Y))
        if not cand: continue
        n = tc.get('n', 4); slot = int((t - tc['from']) / tc.get('step', 2.0))
        pick = [cand[(slot * n + j) % len(cand)] for j in range(min(n, len(cand)))]
        used = []
        for uid, p, Y in pick:
            X = p['fx'] * W
            if any(abs(X - ux) < 150 and abs(Y - uy) < fs + 14 for ux, uy in used): continue
            used.append((X, Y)); faint_tag(layer, X, Y, NAMES.get(uid, uid), fs, tc.get('alpha', 0.62))
    for c in O.get('captions', []):
        if c['from'] <= t <= c['to']: caption(layer, d, c['text'], c.get('y', 1290), c.get('size', 80), tuple(c.get('color', (255, 255, 255))))
    for a in O.get('action', []):
        if a['from'] <= t <= a['to']: stroke_center(layer, d, a['text'], 1290, 92, (255, 255, 255))
    for r in O.get('result', []):
        if r['from'] <= t <= r['to']: stroke_center(layer, d, r['text'], 1415, 54, YELLOW)
    Image.alpha_composite(base, layer).convert('RGB').save(out, quality=92)

# ---- 音：ナレーション（VOICEVOX 春日部つむぎ＝speaker 8）と BGM ----
VV = os.environ.get('VOICEVOX', 'http://127.0.0.1:50021')
SPEED = float(S.get('audio', {}).get('speed', 1.0))  # VOICEVOX の話す速さ（speedScale）
def voice(text, speaker=8):
    os.makedirs(os.path.join(BUILD, 'voice'), exist_ok=True)
    tag = f'{speaker}:{text}' if SPEED == 1.0 else f'{speaker}:{SPEED}:{text}'
    f = os.path.join(BUILD, 'voice', hashlib.md5(tag.encode()).hexdigest()[:12] + '.wav')
    if os.path.exists(f): return f
    # 声だけ別の所（Muse）で作ってリポジトリに置いたもの：video-tools/voices/<名前>/<同じファイル名>
    shared = os.path.join(HERE, '..', 'voices', NAME, os.path.basename(f))
    if os.path.exists(shared):
        import shutil; shutil.copy(shared, f); return f
    try:
        q = urllib.request.urlopen(urllib.request.Request(f'{VV}/audio_query?speaker={speaker}&text={urllib.parse.quote(text)}', method='POST'), timeout=20).read()
        if SPEED != 1.0:
            qj = json.loads(q); qj['speedScale'] = SPEED; q = json.dumps(qj).encode()
        wav = urllib.request.urlopen(urllib.request.Request(f'{VV}/synthesis?speaker={speaker}', data=q, headers={'content-type': 'application/json'}, method='POST'), timeout=60).read()
        open(f, 'wb').write(wav); return f
    except Exception as e:
        print(f'!! VOICEVOX に届かないので、ナレーション「{text}」は無音（{e.__class__.__name__}）')
        return None

def build_audio():
    # ffmpeg の入力0はコマ画像（音声なし）なので、音声の入力番号は 1 から数える（src）。k は混ぜる本数
    inputs, filters, k = [], [], 0
    src = lambda: k + 1
    narr = sorted(S.get('audio', {}).get('narration', []), key=lambda n: n['at'])
    print('ナレーション（開始・使える長さ・声の長さ・速さ）')
    for j, n in enumerate(narr):
        f = voice(n['text'])
        if not f: continue
        # 使える長さ：次の文の開始（または台本の until、動画の終わり）まで
        nxt = narr[j + 1]['at'] if j + 1 < len(narr) else S['duration'] - 0.2
        room = min(n.get('until', nxt), nxt) - n['at'] - 0.12
        with wave.open(f) as w: dur = w.getnframes() / w.getframerate()
        tempo = 1.0
        if dur > room:
            tempo = min(1.3, dur / room)
            if dur / tempo > room + 0.05:
                print(f'!! 収まらない：{n["at"]:.2f}s「{n["text"]}」声 {dur:.2f}s／使える {room:.2f}s（1.3倍速でも {dur / 1.3:.2f}s）')
        print(f'  {n["at"]:6.2f}s  {room:5.2f}s  {dur:5.2f}s  x{tempo:.2f}  {n["text"]}')
        inputs += ['-i', f]; ms = int(n['at'] * 1000)
        speed = f'atempo={tempo:.3f},' if tempo > 1.0 else ''
        filters.append(f'[{src()}:a]{speed}adelay={ms}|{ms},volume=1.0[n{k}]'); k += 1
    bgm = os.environ.get('BGM') or next((p for p in [os.path.join(HERE, '..', 'assets', 'bgm.mp3'), os.path.expanduser('~/workspace/mujintou/video/assets/bgm.mp3')] if os.path.exists(p)), os.path.expanduser('~/workspace/mujintou/video/assets/bgm.mp3'))
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
    bgm_path = os.environ.get('BGM') or next((p for p in [os.path.join(HERE, '..', 'assets', 'bgm.mp3'), os.path.expanduser('~/workspace/mujintou/video/assets/bgm.mp3')] if os.path.exists(p)), os.path.expanduser('~/workspace/mujintou/video/assets/bgm.mp3'))
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
