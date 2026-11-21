# 5日目（ep5）

台本は `ep5/build_story.py` が作る（録画・合成は ep3 のツールをそのまま使う）。

## Muse の手順
1. main を pull（**必ず最新に**。manifest の code_sha で確かめる）
2. 台本を作る：`python3 video-tools/ep5/build_story.py`（名簿は `ep5/input/islanders.json`）
   → 出力が `arrivals 65 / tally A6 B12 C3 D1 / winner B` になるか確認
3. 動画：`rm -rf video-tools/build/ep3/ep5` のあと `BGM=~/workspace/mujintou/video/assets/bgm.mp3 bash video-tools/ep3/run.sh video-tools/ep5/story/ep5.json`
   → `video-tools/out/ep5.mp4`・`ep5_preview.mp4`・`ep5_cover.jpg`・`ep5_manifest.json`
4. 投稿時（Firebase）
   - 名簿：`python3 video-tools/ep3/pwa_patch.py video-tools/ep5/story/ep5_pwa.json` の出力 `video-tools/out/islanders_day5.json` を islanders に同期（仲良しの relationships も入っている）
   - state：`video-tools/ep5/story/ep5_state.json` のとおり
     - `day`=5、`toolAge`="stone" を入れる（島民の道具が石になる）
     - `buildings` に `buildings_add`（石の作業場・大きな木箱）を足す
     - `chronicle` に `chronicle_add` を足す
     - `currentVote` を差し替える（木箱の中身の予想）
