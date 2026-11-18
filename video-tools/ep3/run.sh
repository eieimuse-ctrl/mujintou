#!/usr/bin/env bash
# 3日目の1シーンを、録画→合成まで通しで作る。
#   bash video-tools/ep3/run.sh video-tools/ep3/story/<名前>.json
# 出力：video-tools/out/<名前>.mp4（1080×1920）・<名前>_preview.mp4（780×1688）・<名前>_sheet.jpg（1秒ごとのコマ一覧）
# 途中で止まっても、もう一度同じコマンドで続きから（できたコマは飛ばす）。
# 台本を直したら、そのシーンの build/ep3/<名前>/ を消してから実行する。
set -euo pipefail
# 台本のパスは、cd する前に（呼び出した場所から見た）絶対パスにしておく
STORY="$(cd "$(dirname "$1")" && pwd)/$(basename "$1")"
cd "$(dirname "$0")/.."
[ -d node_modules/puppeteer-core ] || npm ci
node ep3/rec.mjs "$STORY"
python3 ep3/compose.py "$STORY"
