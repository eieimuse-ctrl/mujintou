# 7日目（ep7）

## Muse の手順
1. main を pull
2. `python3 video-tools/ep7/build_story.py`（arrivals 274 / likes 445 / winner C を確認）
3. `rm -rf video-tools/build/ep3/ep7` → `BGM=~/workspace/mujintou/video/assets/bgm.mp3 bash video-tools/ep3/run.sh video-tools/ep7/story/ep7.json`
4. 投稿時（Firebase）
   - 名簿：`python3 video-tools/ep3/pwa_patch.py video-tools/ep7/story/ep7_pwa.json` → `video-tools/out/islanders_day7.json` を islanders に同期
   - state：`video-tools/ep7/story/ep7_state.json` のとおり
     - `day`=7、`likes`（いいね合計。投稿時点の最新の合計に更新してよい）
     - `beast` を差し替える（friendly: true。クマの家のまわりでのんびり、追いかけない）
     - `buildings` に `buildings_add`（クマの家）を足す
     - `chronicle` に `chronicle_add`、`currentVote` を差し替え
