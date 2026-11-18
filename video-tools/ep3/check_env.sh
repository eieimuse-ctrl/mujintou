#!/usr/bin/env bash
# 3日目の制作環境チェック。Muse のマシンで実行し、出力をそのまま Claude に渡す。
# 使い方: bash video-tools/ep3/check_env.sh > video-tools/ep3/input/env.txt
set -u
echo "date: $(date -Iseconds)"
echo "node: $(node --version 2>&1)"
echo "python: $(python3 --version 2>&1)"
python3 -c "import PIL; print('PIL:', PIL.__version__)" 2>&1
echo "ffmpeg: $(ffmpeg -version 2>&1 | head -1)"
CH=$(ls -d "$HOME"/.cache/puppeteer/chrome-headless-shell/*/chrome-headless-shell-linux64/chrome-headless-shell 2>/dev/null | tail -1)
echo "chrome-headless-shell: ${CH:-なし} $( [ -n "${CH:-}" ] && "$CH" --version 2>&1 )"
echo "puppeteer-core: $(node -e "console.log(require('puppeteer-core/package.json').version)" 2>/dev/null || echo 'video-tools で npm ci が必要')"
for f in /usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc /usr/share/fonts/opentype/noto/NotoSansCJK-Black.ttc /usr/share/fonts/truetype/noto/NotoColorEmoji.ttf; do
  [ -f "$f" ] && echo "font: $f" || echo "font なし: $f"
done
echo "voicevox: $(curl -s -m 3 localhost:50021/version 2>&1 || echo '起動していない')"
echo "speaker8(春日部つむぎ): $(curl -s -m 3 localhost:50021/speakers 2>/dev/null | python3 -c 'import sys,json; d=json.load(sys.stdin); print([s["name"] for s in d for st in s["styles"] if st["id"]==8])' 2>/dev/null)"
B="$HOME/workspace/mujintou/video/assets/bgm.mp3"
[ -f "$B" ] && echo "bgm: $B ($(ffprobe -v error -show_entries format=duration -of csv=p=0 "$B")s)" || echo "bgm なし: $B"
echo "nproc: $(nproc)  mem: $(free -g 2>/dev/null | awk '/Mem/{print $2"G"}')"
