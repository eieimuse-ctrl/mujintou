#!/usr/bin/env python3
"""2日目（EP2）合成スクリプト — video/EP2-COMPOSE-SPEC.md の仕様どおりに組む。

手順
  1. video/build/ep2/comp/plates/ に 1080x1920 透明 PNG のプレートを生成
     （ファイル名に内容ハッシュを含める → 既存なら作り直さない／仕様が変われば別名で作り直す）
  2. ffmpeg で 3 セグメントを concat → プレートを overlay 連鎖 →
     adelay で配置した m1〜m7 と BGM を amix → video/out/ep2_master.mkv（CRF 16）
  3. master から ep2_post.mp4（CRF 22・AAC 192k・faststart・100MB 以下）と
     ep2_preview.mp4（780x1688・CRF 26）を作る
  4. ffprobe で尺・解像度・音声の有無を検証して標準出力へ

冪等：各工程はコマンドのハッシュを video/build/ep2/comp/state/ に記録し、
出力が存在してハッシュが一致すれば飛ばす。エンコードは comp/ 下の一時ファイルに書いてから
rename するので、途中で止まっても壊れた成果物は残らない。

使い方:
  python3 video/tools/compose_ep2.py            # 全工程
  python3 video/tools/compose_ep2.py --plates-only
  python3 video/tools/compose_ep2.py --dry-run  # プレート生成＋ffmpeg コマンド表示のみ
  python3 video/tools/compose_ep2.py --force    # 状態を無視して全部作り直す

終了時に "BUILD OK" または "BUILD FAILED" を出力する。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

# ───────────────────────── パス ─────────────────────────
ROOT = Path(__file__).resolve().parents[2]          # …/mujintou
VIDEO = ROOT / "video"
COMP = VIDEO / "build" / "ep2" / "comp"
PLATES = COMP / "plates"
STATE = COMP / "state"
LOGS = COMP / "logs"
OUT = VIDEO / "out"

SEGMENTS = [COMP / "seg_hook.mkv", COMP / "seg_recap.mkv", COMP / "seg_main.mkv"]
SEG_FRAMES = [192, 55, 846]
VOICES = [VIDEO / "audio" / f"m{i}.wav" for i in range(1, 8)]
BGM = VIDEO / "assets" / "bgm.mp3"
FONT_PATH = "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"
FONT_INDEX = 0
EMOJI_FONT_PATHS = [
    "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf",
    "/usr/share/fonts/noto/NotoColorEmoji.ttf",
    "/usr/share/fonts/truetype/noto-color-emoji/NotoColorEmoji.ttf",
]

MASTER = OUT / "ep2_master.mkv"
POST = OUT / "ep2_post.mp4"
PREVIEW = OUT / "ep2_preview.mp4"

# ───────────────────────── 定数 ─────────────────────────
W, H = 1080, 1920
FPS = 24
TARGET = 45.6
N_FRAMES = round(TARGET * FPS)        # 1094 コマ
DUR = N_FRAMES / FPS                  # 45.583… 秒（映像はコマ単位なのでこれを全体尺にする）
PREVIEW_W, PREVIEW_H = 780, 1688
POST_MAX_BYTES = 100 * 1000 * 1000
BGM_VOLUME = 0.18
BGM_FADE_IN = 0.5
BGM_FADE_OUT = 3.0
SUB_TAIL = 0.3                        # 字幕は声の終了＋0.3 秒まで
SUB_MAX_CHARS = 18
SUB_MAX_LINES = 2

RENDER_VERSION = "ep2-plates-v1"      # 描画ロジックを変えたら上げる → 全プレート再生成

BG_DARK = (0, 0, 0, 140)
FG_WHITE = (255, 255, 255, 255)
BG_BUBBLE = (255, 255, 255, 240)
FG_BLACK = (0, 0, 0, 255)

COLOR_ARGS = ["-colorspace", "bt709", "-color_primaries", "bt709",
              "-color_trc", "bt709", "-color_range", "tv"]

# ───────────────────────── 台本（仕様の表そのまま） ─────────────────────────
NARRATION = [
    # (声, 開始, 尺, 字幕)
    ("m1", 0.20, 7.62, "島のいまは、プロフィールのリンクから見られます。あなたが今なにをしているかも、名前で検索すれば分かります。"),
    ("m2", 8.20, 4.77, "1日目。52人がフォローして、海を漂っていました。"),
    ("m3", 13.20, 4.25, "2日目。漂流者たちが、ついに島へ流れ着きました。"),
    ("m4", 18.00, 4.79, "拠点は、投票の結果、島の真ん中の平原に決まりました。"),
    ("m5", 23.20, 3.73, "島民たちは拠点へ集まって、暮らしが始まります。"),
    ("m6", 28.30, 13.77, "次の質問です。食料は、どうしますか。エー、海で魚を捕る。ビー、畑を作る。シー、森の実りを探す。コメントで、教えてください。"),
    ("m7", 42.60, 2.59, "では、また明日、3日目。"),
]


# ═════════════════════════ 文字描画 ═════════════════════════
_font_cache: dict[int, ImageFont.FreeTypeFont] = {}
_emoji_cache: dict[tuple[str, int], Image.Image | None] = {}
_emoji_font: ImageFont.FreeTypeFont | None | bool = False   # False = 未探索


def font(size: int) -> ImageFont.FreeTypeFont:
    if size not in _font_cache:
        _font_cache[size] = ImageFont.truetype(FONT_PATH, size, index=FONT_INDEX)
    return _font_cache[size]


def is_emoji(ch: str) -> bool:
    cp = ord(ch)
    return 0x1F000 <= cp <= 0x1FAFF or 0x2600 <= cp <= 0x27BF


def is_invisible(ch: str) -> bool:
    return ord(ch) in (0xFE0F, 0xFE0E, 0x200D)


def emoji_image(ch: str, size: int) -> Image.Image | None:
    """Noto Sans CJK に絵文字（🐸 など）は無いので、カラー絵文字フォントで描いて縮小する。"""
    global _emoji_font
    key = (ch, size)
    if key in _emoji_cache:
        return _emoji_cache[key]
    if _emoji_font is False:
        _emoji_font = None
        for p in EMOJI_FONT_PATHS:
            if os.path.exists(p):
                try:
                    _emoji_font = ImageFont.truetype(p, 109)   # CBDT は 109px 固定
                    break
                except OSError:
                    continue
        if _emoji_font is None:
            print("  [warn] カラー絵文字フォントが見つからない → 絵文字は本文フォントで描く（豆腐の可能性）")
    img = None
    if _emoji_font:
        try:
            canvas = Image.new("RGBA", (180, 160), (0, 0, 0, 0))
            ImageDraw.Draw(canvas).text((10, 10), ch, font=_emoji_font, embedded_color=True)
            bb = canvas.getbbox()
            if bb:
                g = canvas.crop(bb)
                scale = size / max(g.width, g.height)
                img = g.resize((max(1, round(g.width * scale)), max(1, round(g.height * scale))),
                               Image.LANCZOS)
        except Exception as e:  # noqa: BLE001
            print(f"  [warn] 絵文字 {ch!r} の描画に失敗: {e}")
            img = None
    _emoji_cache[key] = img
    return img


def runs(text: str) -> list[tuple[str, str]]:
    """文字列を (kind, s) の並びに分ける。kind は 'text' / 'emoji'。"""
    out: list[tuple[str, str]] = []
    buf = ""
    for ch in text:
        if is_invisible(ch):
            continue
        if is_emoji(ch):
            if buf:
                out.append(("text", buf))
                buf = ""
            out.append(("emoji", ch))
        else:
            buf += ch
    if buf:
        out.append(("text", buf))
    return out


def emoji_advance(size: int) -> float:
    return size * 1.08


def measure(text: str, size: int) -> float:
    w = 0.0
    for kind, s in runs(text):
        w += emoji_advance(size) if kind == "emoji" else font(size).getlength(s)
    return w


BREAK_AFTER = set("、。，．！？!?）」』】・…　 ")
NO_LINE_START = set("、。，．！？!?）」』】ー〜…ぁぃぅぇぉっゃゅょァィゥェォッャュョ")


def wrap(text: str, size: int, max_w: float, max_chars: int | None = None) -> list[str]:
    """日本語の折り返し。幅（と任意の文字数上限）に収まる最長を取り、
    後半に句読点があればその直後で折る。行頭禁則も守る。"""
    lines: list[str] = []
    for para in text.split("\n"):
        rest = para
        while rest:
            n = 0
            while (n < len(rest)
                   and (max_chars is None or n < max_chars)
                   and measure(rest[:n + 1], size) <= max_w):
                n += 1
            n = max(n, 1)
            if n < len(rest):
                for i in range(n, max(n // 2, 1) - 1, -1):
                    if rest[i - 1] in BREAK_AFTER:
                        n = i
                        break
                while n < len(rest) and rest[n] in NO_LINE_START:
                    n += 1
            lines.append(rest[:n].rstrip("　 ") or rest[:n])
            rest = rest[n:].lstrip("　 ")
    return lines


def draw_box(rows: list[dict], *, cx: float = W / 2, x: float | None = None,
             cy: float | None = None, top: float | None = None, bottom: float | None = None,
             min_top: float = 0, pad_x: int = 32, pad_y: int = 18, radius: int | None = 24,
             bg=BG_DARK, align: str = "center", tail: bool = False) -> Image.Image:
    """角丸の箱＋文字を 1080x1920 透明キャンバスに描く。
    rows: [{"text", "size", "color", "lh"(行高倍率), "align"(任意)}]"""
    widths = [measure(r["text"], r["size"]) for r in rows]
    heights = [round(r["size"] * r.get("lh", 1.45)) for r in rows]
    bw = math.ceil(max(widths)) + 2 * pad_x
    bh = sum(heights) + 2 * pad_y
    x0 = x if x is not None else cx - bw / 2
    x0 = round(min(max(x0, 0), W - bw))
    if top is not None:
        y0 = top
    elif bottom is not None:
        y0 = bottom - bh
    else:
        y0 = (cy if cy is not None else H / 2) - bh / 2
    y0 = round(min(max(y0, min_top), H - bh))
    r = bh // 2 if radius is None else radius            # None = ピル型

    canvas = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    bgl = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(bgl)
    d.rounded_rectangle([x0, y0, x0 + bw - 1, y0 + bh - 1], radius=r, fill=bg)
    if tail:
        tx = x0 + bw / 2
        d.polygon([(tx - 28, y0 + bh - 2), (tx + 28, y0 + bh - 2), (tx, y0 + bh + 36)], fill=bg)
    canvas.alpha_composite(bgl)

    # 文字は色ごとに L マスクへ描いてから色を流し込む（straight alpha を正しく保つ）
    masks: dict[tuple, Image.Image] = {}
    emoji_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    y = y0 + pad_y
    for row, w, h in zip(rows, widths, heights):
        a = row.get("align", align)
        lx = x0 + pad_x if a == "left" else x0 + (bw - w) / 2
        yc = y + h / 2
        size = row["size"]
        color = tuple(row["color"])
        m = masks.setdefault(color, Image.new("L", (W, H), 0))
        md = ImageDraw.Draw(m)
        px = lx
        for kind, s in runs(row["text"]):
            if kind == "emoji":
                em = emoji_image(s, size)
                if em is not None:
                    emoji_layer.alpha_composite(
                        em, (round(px + (emoji_advance(size) - em.width) / 2), round(yc - em.height / 2)))
                    px += emoji_advance(size)
                    continue
                md.text((px, yc), s, font=font(size), fill=255, anchor="lm")
                px += font(size).getlength(s)
            else:
                md.text((px, yc), s, font=font(size), fill=255, anchor="lm")
                px += font(size).getlength(s)
        y += h
    for color, m in masks.items():
        if len(color) == 4 and color[3] < 255:
            m = m.point(lambda v, k=color[3]: v * k // 255)
        layer = Image.new("RGBA", (W, H), color[:3] + (0,))
        layer.putalpha(m)
        canvas.alpha_composite(layer)
    canvas.alpha_composite(emoji_layer)
    return canvas


# ═════════════════════════ プレート定義 ═════════════════════════
BADGE_BOTTOM_GUARD = 60 + 40 * 1.45 + 2 * 14 + 16   # バッジ下端＋余白（フック板をこれより下に置く）


def subtitle_pages(text: str) -> list[list[str]]:
    """文単位でまとめ、1ページ最大2行（1行18字目安）に分ける。文面は一字も変えない。"""
    size = 44
    max_w = W - 2 * 60 - 2 * 32
    sentences = [s for s in re.findall(r"[^。！？]*[。！？]?", text) if s]
    pages: list[list[str]] = []
    cur = ""
    for s in sentences:
        cand = cur + s
        if len(wrap(cand, size, max_w, SUB_MAX_CHARS)) <= SUB_MAX_LINES:
            cur = cand
            continue
        if cur:
            pages.append(wrap(cur, size, max_w, SUB_MAX_CHARS))
            cur = ""
        lines = wrap(s, size, max_w, SUB_MAX_CHARS)
        while len(lines) > SUB_MAX_LINES:
            pages.append(lines[:SUB_MAX_LINES])
            lines = lines[SUB_MAX_LINES:]
        cur = "".join(lines)
    if cur:
        pages.append(wrap(cur, size, max_w, SUB_MAX_CHARS))
    return pages


def plate_specs() -> list[dict]:
    """各プレート: key, render(描画パラメータ), windows[(開始, 終了)]。"""
    specs: list[dict] = []

    def add(key, render, windows):
        specs.append({"key": key, "render": render, "windows": windows})

    # 1. バッジ「2日目」左上ピル型
    add("badge", {"rows": [{"text": "2日目", "size": 40, "color": FG_WHITE}],
                  "x": 40, "top": 60, "pad_x": 28, "pad_y": 14, "radius": None},
        [(0.0, 6.0), (42.1, DUR)])

    # 2. フック板（上部中央 y≈180。バッジと同時表示なのでバッジの下に逃がす）
    hook_lines = wrap("プロフィールのリンクから、島の今が見られます", 46, W - 2 * 40 - 2 * 40)
    add("hook", {"rows": [{"text": t, "size": 46, "color": FG_WHITE} for t in hook_lines],
                 "cy": 180, "min_top": BADGE_BOTTOM_GUARD, "pad_x": 40, "pad_y": 20, "radius": 28},
        [(0.3, 7.8)])

    # 3. みんなの声カード（下部。字幕 y≈1620 の上に収める）
    voices = [
        (19.5, 23.0, "さか：A！他の土地にアクセスしやすそうだから（採用）"),
        (23.0, 26.5, "🐸ま🐸：B！！序盤は食料大事だから浅瀬でみんなで掴み取る(*^^*)"),
    ]
    for i, (a, b, text) in enumerate(voices, 1):
        body = wrap(text, 40, W - 2 * 50 - 2 * 40)
        rows = [{"text": "みんなの声", "size": 32, "color": FG_WHITE, "lh": 1.6, "align": "left"}]
        rows += [{"text": t, "size": 40, "color": FG_WHITE, "align": "left"} for t in body]
        add(f"voice{i}", {"rows": rows, "bottom": 1500, "pad_x": 40, "pad_y": 24, "radius": 28,
                          "align": "left"}, [(a, b)])

    # 4. 空腹の吹き出し（白い角丸＋黒文字、y≈700）
    add("hungry", {"rows": [{"text": "お腹すいた…", "size": 48, "color": FG_BLACK}],
                   "cy": 700, "pad_x": 40, "pad_y": 20, "radius": 36, "bg": BG_BUBBLE, "tail": True},
        [(27.3, 30.0)])

    # 5. 質問タイトル
    add("question", {"rows": [{"text": "次の質問　食料をどうする？", "size": 54, "color": FG_WHITE}],
                     "cy": 180, "min_top": 60, "pad_x": 44, "pad_y": 22, "radius": 30},
        [(28.3, 32.0)])

    # 6. 選択肢板
    for key, a, b, text in [("optA", 32.0, 34.7, "A　海で魚を捕る"),
                            ("optB", 34.7, 36.95, "B　畑を作る"),
                            ("optC", 36.95, 39.55, "C　森の実りを探す")]:
        add(key, {"rows": [{"text": text, "size": 48, "color": FG_WHITE}],
                  "cy": 180, "min_top": 60, "pad_x": 44, "pad_y": 22, "radius": 30}, [(a, b)])
    rows = [{"text": t, "size": 48, "color": FG_WHITE, "align": "left"}
            for t in ("A 海で魚を捕る", "B 畑を作る", "C 森の実りを探す")]
    rows.append({"text": "コメントで教えてね", "size": 32, "color": FG_WHITE, "lh": 1.8, "align": "center"})
    add("optAll", {"rows": rows, "cy": 180, "min_top": 60, "pad_x": 48, "pad_y": 24, "radius": 30,
                   "align": "left"}, [(39.55, 42.1)])

    # 7. 終了板（中央）
    add("end", {"rows": [{"text": "無人島プロジェクト　2日目", "size": 64, "color": FG_WHITE}],
                "cy": H / 2, "pad_x": 48, "pad_y": 28, "radius": 32},
        [(42.1, DUR)])

    # 字幕（下部中央 y≈1620、44px）— 窓は 開始〜終了+0.3、次の声の開始で打ち切る
    for idx, (vid, start, dur, text) in enumerate(NARRATION):
        end = start + dur + SUB_TAIL
        if idx + 1 < len(NARRATION):
            end = min(end, NARRATION[idx + 1][1])
        end = min(end, DUR)
        pages = subtitle_pages(text)
        total = sum(len("".join(p)) for p in pages)
        t = start
        for pi, lines in enumerate(pages):
            share = len("".join(lines)) / total
            t1 = end if pi == len(pages) - 1 else round(t + (end - start) * share, 3)
            add(f"sub_{vid}_{pi + 1}",
                {"rows": [{"text": ln, "size": 44, "color": FG_WHITE} for ln in lines],
                 "cy": 1620, "pad_x": 32, "pad_y": 16, "radius": 24},
                [(round(t, 3), round(t1, 3))])
            t = t1
    return specs


def spec_hash(render: dict) -> str:
    blob = json.dumps({"v": RENDER_VERSION, "font": FONT_PATH, "r": render},
                      ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha1(blob.encode()).hexdigest()[:10]


def build_plates(specs: list[dict], force: bool) -> list[dict]:
    PLATES.mkdir(parents=True, exist_ok=True)
    made = skipped = 0
    for s in specs:
        path = PLATES / f"{s['key']}_{spec_hash(s['render'])}.png"
        s["path"] = path
        if path.exists() and not force:
            skipped += 1
            continue
        img = draw_box(**s["render"])
        tmp = path.with_suffix(".tmp.png")
        img.save(tmp, "PNG")
        os.replace(tmp, path)
        made += 1
    manifest = [{"key": s["key"], "file": s["path"].name, "windows": s["windows"]} for s in specs]
    (PLATES / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1))
    print(f"[plates] {len(specs)} 枚（新規 {made} / 既存 {skipped}） → {PLATES}")
    return specs


# ═════════════════════════ ffmpeg ═════════════════════════
def enable_expr(windows) -> str:
    # 半開区間 [a, b) にして、切り替わりのコマで2枚が重ならないようにする
    return "+".join(f"gte(t,{a:.3f})*lt(t,{b:.3f})" for a, b in windows)


def master_cmd(specs: list[dict], tmp_out: Path) -> list[str]:
    cmd = ["ffmpeg", "-hide_banner", "-y", "-nostdin"]
    for seg in SEGMENTS:
        cmd += ["-i", str(seg)]
    for v in VOICES:
        cmd += ["-i", str(v)]
    cmd += ["-i", str(BGM)]
    first_plate = len(SEGMENTS) + len(VOICES) + 1
    for s in specs:
        cmd += ["-i", str(s["path"])]          # 1枚画像。overlay の eof_action=repeat で保持される

    f: list[str] = []
    # 映像：連結 → 目標コマ数まで最終コマを複製して揃える
    for i in range(len(SEGMENTS)):
        f.append(f"[{i}:v]setpts=PTS-STARTPTS,setsar=1,format=yuv420p[s{i}]")
    f.append("".join(f"[s{i}]" for i in range(len(SEGMENTS)))
             + f"concat=n={len(SEGMENTS)}:v=1:a=0,"
               f"tpad=stop_mode=clone:stop_duration=2,trim=end_frame={N_FRAMES},"
               f"setpts=PTS-STARTPTS[v0]")
    # プレート：RGBA → bt709/TV レンジの yuva420p（既定の bt601 変換で色がずれないように）
    for k, s in enumerate(specs):
        f.append(f"[{first_plate + k}:v]format=rgba,"
                 f"scale=out_color_matrix=bt709:out_range=tv,format=yuva420p[p{k}]")
    cur = "v0"
    for k, s in enumerate(specs):
        nxt = f"v{k + 1}"
        f.append(f"[{cur}][p{k}]overlay=0:0:format=yuv420:enable='{enable_expr(s['windows'])}'[{nxt}]")
        cur = nxt
    f.append(f"[{cur}]format=yuv420p[vout]")

    # 音声：ナレーション（音量1.0）を adelay で配置、BGM は 0.18・FI 0.5s・最後3s FO
    afmt = "aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo"
    labels = []
    for i, (vid, start, _dur, _txt) in enumerate(NARRATION):
        ms = round(start * 1000)
        f.append(f"[{len(SEGMENTS) + i}:a]{afmt},adelay=delays={ms}:all=1[n{i}]")
        labels.append(f"[n{i}]")
    bgm_idx = len(SEGMENTS) + len(VOICES)
    f.append(f"[{bgm_idx}:a]{afmt},atrim=0:{DUR:.4f},asetpts=PTS-STARTPTS,"
             f"volume={BGM_VOLUME},afade=t=in:st=0:d={BGM_FADE_IN},"
             f"afade=t=out:st={DUR - BGM_FADE_OUT:.4f}:d={BGM_FADE_OUT}[bgm]")
    labels.append("[bgm]")
    f.append("".join(labels) + f"amix=inputs={len(labels)}:duration=longest:"
             f"dropout_transition=0:normalize=0,apad,atrim=0:{DUR:.4f},asetpts=PTS-STARTPTS[aout]")

    cmd += ["-filter_complex", ";".join(f),
            "-map", "[vout]", "-map", "[aout]",
            "-r", str(FPS),
            "-c:v", "libx264", "-preset", "slow", "-crf", "16", "-pix_fmt", "yuv420p",
            *COLOR_ARGS,
            "-c:a", "flac", "-ar", "48000",
            "-t", f"{DUR:.4f}",
            str(tmp_out)]
    return cmd


def post_encode_cmd(crf: int, tmp_mkv: Path) -> list[str]:
    return ["ffmpeg", "-hide_banner", "-y", "-nostdin", "-i", str(MASTER),
            "-map", "0:v:0", "-map", "0:a:0",
            "-c:v", "libx264", "-preset", "slow", "-crf", str(crf), "-pix_fmt", "yuv420p",
            "-profile:v", "high", *COLOR_ARGS,
            "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
            str(tmp_mkv)]


def preview_encode_cmd(tmp_mkv: Path) -> list[str]:
    # 1080x1920（9:16）→ 780x1688 は縦横比が違うので、歪ませず幅に合わせて縮小し上下を黒で埋める
    vf = (f"scale={PREVIEW_W}:-2:flags=lanczos,"
          f"pad={PREVIEW_W}:{PREVIEW_H}:0:(oh-ih)/2:black,setsar=1,format=yuv420p")
    return ["ffmpeg", "-hide_banner", "-y", "-nostdin", "-i", str(MASTER),
            "-map", "0:v:0", "-map", "0:a:0", "-vf", vf,
            "-c:v", "libx264", "-preset", "medium", "-crf", "26", "-pix_fmt", "yuv420p",
            *COLOR_ARGS,
            "-c:a", "aac", "-b:a", "128k", "-ar", "48000",
            str(tmp_mkv)]


def remux_faststart_cmd(src: Path, dst_tmp: Path) -> list[str]:
    return ["ffmpeg", "-hide_banner", "-y", "-nostdin", "-i", str(src),
            "-map", "0", "-c", "copy", "-movflags", "+faststart", "-f", "mp4", str(dst_tmp)]


def run(cmd: list[str], log_name: str) -> None:
    LOGS.mkdir(parents=True, exist_ok=True)
    log = LOGS / f"{log_name}.log"
    print(f"  $ {' '.join(cmd[:6])} … → {cmd[-1]}  (log: {log})")
    with open(log, "w") as lf:
        lf.write(" ".join(repr(c) if (" " in c or ";" in c) else c for c in cmd) + "\n\n")
        lf.flush()
        p = subprocess.run(cmd, stdout=lf, stderr=subprocess.STDOUT)
    if p.returncode != 0:
        tail = log.read_text(errors="replace").splitlines()[-25:]
        print("\n".join("    | " + t for t in tail))
        raise RuntimeError(f"ffmpeg 失敗（{log_name}, rc={p.returncode}）")


def cmd_key(*parts) -> str:
    return hashlib.sha1(json.dumps(parts, ensure_ascii=False, default=str).encode()).hexdigest()


def stamp_ok(name: str, key: str, out: Path) -> bool:
    st = STATE / f"{name}.json"
    if not out.exists() or not st.exists():
        return False
    try:
        return json.loads(st.read_text()).get("key") == key
    except (OSError, json.JSONDecodeError):
        return False


def write_stamp(name: str, key: str, out: Path, extra: dict | None = None) -> None:
    STATE.mkdir(parents=True, exist_ok=True)
    data = {"key": key, "out": str(out), "size": out.stat().st_size, **(extra or {})}
    (STATE / f"{name}.json").write_text(json.dumps(data, ensure_ascii=False, indent=1))


def read_stamp(name: str) -> dict:
    try:
        return json.loads((STATE / f"{name}.json").read_text())
    except (OSError, json.JSONDecodeError):
        return {}


# ═════════════════════════ ffprobe ═════════════════════════
def probe(path: Path) -> dict:
    p = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                        "format=duration,size:stream=codec_type,codec_name,width,height,duration",
                        "-of", "json", str(path)], capture_output=True, text=True)
    if p.returncode != 0:
        return {}
    return json.loads(p.stdout or "{}")


def check_inputs() -> list[str]:
    errs = []
    for tool in ("ffmpeg", "ffprobe"):
        if not shutil.which(tool):
            errs.append(f"{tool} が見つからない")
    for p in [*SEGMENTS, *VOICES, BGM, Path(FONT_PATH)]:
        if not p.exists():
            errs.append(f"素材が無い: {p}")
    if errs:
        return errs
    # 参考チェック（警告のみ）：セグメント解像度、声の尺
    for seg, frames in zip(SEGMENTS, SEG_FRAMES):
        info = probe(seg)
        v = [s for s in info.get("streams", []) if s.get("codec_type") == "video"]
        if v and (v[0].get("width"), v[0].get("height")) != (W, H):
            errs.append(f"{seg.name} の解像度が {v[0].get('width')}x{v[0].get('height')}（期待 {W}x{H}）")
        dur = float(info.get("format", {}).get("duration", 0) or 0)
        if dur and abs(dur - frames / FPS) > 0.1:
            print(f"  [warn] {seg.name} の尺 {dur:.3f}s（仕様 {frames / FPS:.3f}s）")
    for (vid, _s, d, _t), wav in zip(NARRATION, VOICES):
        dur = float(probe(wav).get("format", {}).get("duration", 0) or 0)
        if dur and abs(dur - d) > 0.1:
            print(f"  [warn] {wav.name} の尺 {dur:.3f}s（仕様 {d:.2f}s）")
    return errs


def verify(path: Path, w: int, h: int, max_bytes: int | None = None) -> tuple[bool, str]:
    if not path.exists():
        return False, f"{path.name}: ファイルが無い"
    info = probe(path)
    streams = info.get("streams", [])
    v = [s for s in streams if s.get("codec_type") == "video"]
    a = [s for s in streams if s.get("codec_type") == "audio"]
    dur = float(info.get("format", {}).get("duration", 0) or 0)
    size = int(info.get("format", {}).get("size", 0) or path.stat().st_size)
    problems = []
    if not v:
        problems.append("映像なし")
    elif (v[0].get("width"), v[0].get("height")) != (w, h):
        problems.append(f"解像度 {v[0].get('width')}x{v[0].get('height')}≠{w}x{h}")
    if not a:
        problems.append("音声なし")
    if abs(dur - TARGET) > 0.15:
        problems.append(f"尺 {dur:.3f}s が目標 {TARGET}s から外れる")
    if max_bytes is not None and size > max_bytes:
        problems.append(f"サイズ {size / 1e6:.1f}MB > {max_bytes / 1e6:.0f}MB")
    desc = (f"{path.name}: {dur:.3f}s  "
            f"{(str(v[0].get('width')) + 'x' + str(v[0].get('height'))) if v else '-'}  "
            f"video={v[0].get('codec_name') if v else '-'}  audio={a[0].get('codec_name') if a else 'なし'}  "
            f"{size / 1e6:.1f}MB")
    return (not problems), desc + ("" if not problems else "  ← NG: " + "; ".join(problems))


# ═════════════════════════ 工程 ═════════════════════════
def step_master(specs: list[dict], force: bool, dry: bool) -> None:
    tmp = COMP / "ep2_master.tmp.mkv"
    cmd = master_cmd(specs, tmp)
    inputs_sig = [(str(p), p.stat().st_size, int(p.stat().st_mtime)) for p in [*SEGMENTS, *VOICES, BGM]]
    key = cmd_key(cmd, inputs_sig)
    if dry:
        print("[master] ffmpeg コマンド:")
        print("  " + " ".join(c if " " not in c and ";" not in c else repr(c) for c in cmd))
        return
    if not force and stamp_ok("master", key, MASTER):
        print(f"[master] 既存（変更なし）→ skip: {MASTER}")
        return
    print("[master] 連結＋プレート＋音声ミックス（CRF 16）")
    OUT.mkdir(parents=True, exist_ok=True)
    run(cmd, "master")
    os.replace(tmp, MASTER)
    write_stamp("master", key, MASTER)


def step_post(force: bool) -> None:
    master_key = read_stamp("master").get("key", "")
    tmp_mkv = COMP / "ep2_post.tmp.mkv"
    tmp_mp4 = COMP / "ep2_post.tmp.mp4"
    key = cmd_key("post", master_key, post_encode_cmd(22, tmp_mkv), POST_MAX_BYTES)
    if not force and stamp_ok("post", key, POST):
        print(f"[post] 既存（変更なし）→ skip: {POST}")
        return
    for crf in (22, 24, 26, 28):
        print(f"[post] CRF {crf} / AAC 192k / faststart")
        run(post_encode_cmd(crf, tmp_mkv), f"post_crf{crf}")
        run(remux_faststart_cmd(tmp_mkv, tmp_mp4), "post_remux")
        size = tmp_mp4.stat().st_size
        if size <= POST_MAX_BYTES:
            break
        print(f"  {size / 1e6:.1f}MB > 100MB → CRF を上げて再エンコード")
    else:
        raise RuntimeError("CRF 28 でも 100MB を超えた")
    os.replace(tmp_mp4, POST)
    tmp_mkv.unlink(missing_ok=True)
    write_stamp("post", key, POST, {"crf": crf})


def step_preview(force: bool) -> None:
    master_key = read_stamp("master").get("key", "")
    tmp_mkv = COMP / "ep2_preview.tmp.mkv"
    tmp_mp4 = COMP / "ep2_preview.tmp.mp4"
    key = cmd_key("preview", master_key, preview_encode_cmd(tmp_mkv))
    if not force and stamp_ok("preview", key, PREVIEW):
        print(f"[preview] 既存（変更なし）→ skip: {PREVIEW}")
        return
    print(f"[preview] {PREVIEW_W}x{PREVIEW_H} / CRF 26")
    run(preview_encode_cmd(tmp_mkv), "preview")
    run(remux_faststart_cmd(tmp_mkv, tmp_mp4), "preview_remux")
    os.replace(tmp_mp4, PREVIEW)
    tmp_mkv.unlink(missing_ok=True)
    write_stamp("preview", key, PREVIEW)


def main() -> int:
    ap = argparse.ArgumentParser(description="EP2 合成")
    ap.add_argument("--plates-only", action="store_true", help="プレート生成だけ")
    ap.add_argument("--dry-run", action="store_true", help="プレート生成＋ffmpeg コマンド表示のみ")
    ap.add_argument("--force", action="store_true", help="冪等スキップを無視して作り直す")
    args = ap.parse_args()

    COMP.mkdir(parents=True, exist_ok=True)
    try:
        errs = check_inputs()
        if errs:
            for e in errs:
                print(f"  [error] {e}")
            raise RuntimeError("入力チェック失敗")

        specs = build_plates(plate_specs(), args.force)
        if args.plates_only:
            print("BUILD OK (plates only)")
            return 0
        step_master(specs, args.force, args.dry_run)
        if args.dry_run:
            print("BUILD OK (dry run)")
            return 0
        step_post(args.force)
        step_preview(args.force)

        print("\n[verify] ffprobe")
        results = [verify(MASTER, W, H),
                   verify(POST, W, H, POST_MAX_BYTES),
                   verify(PREVIEW, PREVIEW_W, PREVIEW_H)]
        for ok, desc in results:
            print(f"  {'OK' if ok else 'NG'}  {desc}")
        if not all(ok for ok, _ in results):
            raise RuntimeError("検証で NG")
    except Exception as e:  # noqa: BLE001
        print(f"\nBUILD FAILED: {e}")
        return 1
    print("\nBUILD OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
