# 4日目（ep4）

台本は `ep4/build_story.py` が作る（録画・合成は ep3 のツールをそのまま使う）。

## Muse の手順
1. main を pull
2. 名簿を更新：Firebase の islanders（**4日目に漂着させた人は joinedDay=4**。漂流中53人を昇格させた後）を job・color 付きで `video-tools/ep3/input/islanders.json` に書き出す
3. 台本を作る：`python3 video-tools/ep4/build_story.py`（出力の arrivals が漂着人数）
4. 動画：`BGM=~/workspace/mujintou/video/assets/bgm.mp3 bash video-tools/ep3/run.sh video-tools/ep4/story/ep4.json`
   → `video-tools/out/ep4.mp4`・`ep4_preview.mp4`・`ep4_cover.jpg`・`ep4_manifest.json`
5. 投稿時（Firebase）
   - 名簿：`python3 video-tools/ep3/pwa_patch.py video-tools/ep4/story/ep4_pwa.json` の出力 `video-tools/out/islanders_day4.json` を islanders に同期（ゆらさんの missing はこれで外れる）
   - state：`video-tools/ep4/story/ep4_state.json` のとおり
     - `day`=4、`forestRoad`（open: true）を入れる
     - `districts` の森を `districts_forest` の内容に差し替える
     - `buildings` に `buildings_add`（昔の住人の跡）を足す
     - `chronicle` に `chronicle_add` を足す
     - `currentVote` を差し替える（3択＋D）
