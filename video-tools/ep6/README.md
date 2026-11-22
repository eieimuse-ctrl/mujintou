# 6日目（ep6）

台本は `ep6/build_story.py` が作る（録画・合成は ep3 のツール）。カメラは大げさ（本人の指示）。

## Muse の手順
1. 12時の確定データを置いて push
   - `video-tools/ep6/input/comments.json`（5日目の投稿のコメント。スクショで補った分も入れてよい：source "screenshot"）
   - `video-tools/ep6/input/islanders.json`（名簿。6日目の漂着は joinedDay=6。仲良し5組を relationships に type: friend・両方向で）
2. 台本：`python3 video-tools/ep6/build_story.py`（出力の tally・hub・pairs を確認）
3. 動画：`rm -rf video-tools/build/ep3/ep6` → `BGM=~/workspace/mujintou/video/assets/bgm.mp3 bash video-tools/ep3/run.sh video-tools/ep6/story/ep6.json`
4. 投稿時（Firebase）
   - 名簿：`python3 video-tools/ep3/pwa_patch.py video-tools/ep6/story/ep6_pwa.json` → `video-tools/out/islanders_day6.json` を islanders に同期
   - state：`video-tools/ep6/story/ep6_state.json` のとおり
     - `day`=6
     - `clearings` に `clearings_add` を足す（森の東1/3を切りひらいた土地）
     - `beast` をそのまま入れる（クマが島を歩き、近づかれた島民が逃げる）
     - `buildings` から `buildings_remove`（木箱 crate-1）を消し、`buildings_add`（巨大な畑。2日かけて実る）を足す
     - `chronicle` に `chronicle_add` を足す、`currentVote` を差し替える
