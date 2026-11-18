# 動画制作ツール（video-tools）

無人島プロジェクトの動画（1日目・2日目）を作ったツール一式です。
PWA本体とは独立した制作側の道具で、サイトの動作には影響しません。

## 構成

- `ep2/` … 2日目で使った現行パイプライン
  - `ep2_rec.mjs`：手動ステップ録画レコーダー（再開可能・既存フレームはスキップ）
  - `ep2_rig.mjs`：録画用のカメラ／シーン rig
  - `ep2_timeline.mjs`：ショット構成とフィルム時間の定義
  - `build_ep2_segments.py`：録画フレームからセグメント（メイン／回想／フック）を組み立てる
  - `compose_ep2.py`：字幕・プレート・みんなの声カード・BGM／ナレーションを合成して完成動画を出す
- `ep1-v3/` … 1日目の投稿版（v3）のパイプライン
  - `fable_rec_v3.mjs`、`fable_timeline_v3.mjs`、`fable_tracks_v3.mjs`
  - `compose_fable_v3.py`、`build_fable_v3.py`、`verify_fable_v3.py`
  - `v3_ui_hd.mjs`：実PWAのUIを透過レイヤーとしてHD撮影する（動画内のスマホ画面用）
- `ep1-v1/` … 1日目・初版のパイプライン（手動ステップ録画の原型）
  - `fable_rec.mjs`、`fable_rig.mjs`、`fable_timeline.mjs`、`fable_tracks.mjs`、`fable_tracks_math.mjs`
  - `compose_fable.py`、`build_fable.py`、`build_video.py`
- `docs/` … 制作の仕様と記録
  - `FABLE_BUILD.md`：1日目（v1／v3）の制作記録
  - `EP2-SCRIPT.md`：2日目の確定台本
  - `EP2-BRIEF.md`：2日目の制作ブリーフ（アニメーション方針・みんなの声・空腹の演出）
  - `EP2-COMPOSE-SPEC.md`：2日目の合成仕様（プレート文言・配置・タイミング）
- `package.json` / `package-lock.json` … Node依存（puppeteer-core）

## 制作方式の要点

- **手動ステップ録画**：PWAの `requestAnimationFrame` を止め、1フレームずつ
  `world.update / setTimeOfDay / render` を手で進めてキャンバスをJPEG化する。
  各フレームはポーズの純粋関数なので、途中で止まっても既存フレームを飛ばして再開できる。
- 2日目は **stage2**（サイトのコピー＋演出用に組んだデータ）に対して録画し、本番データには触らない。
  フック部分だけ実PWAの画面を使う。
- 合成は ffmpeg ＋ PIL（字幕・プレート描画）。
  色変換は `bt601 full → bt709 tv` の指定が必須（素朴に変換すると暗くなる）。
- ナレーションは **VOICEVOX（春日部つむぎ／speaker 8）**、エンジンは `localhost:50021` で別途起動する。
- 出力は 1080×1920、完成マスター（MKV）→ 投稿用MP4（100MB以下）→ プレビュー（780×1688）の3段。

## 含まれていないもの

- VOICEVOXエンジン本体（別途入手してください）
- BGM音源：「Beachfront Celebration」by Kevin MacLeod（CC BY 4.0、クレジット表記が必要）
- ナレーションのwav、録画フレーム、完成動画

## 環境メモ

- スクリプト内のパスは制作マシン（`~/workspace/mujintou/…`）前提です。流用時は要調整。
- ヘッドレスChromeは chrome-headless-shell ＋ SwiftShader フラグ
  （`--use-gl=angle --use-angle=swiftshader --enable-unsafe-swiftshader`）でWebGLを描画。
- サイト配信は `python3 -m http.server`（本番コピーが 8773、stage2 が 8774）。
- PWAは `?freeze&t=<epoch-ms>` で時刻固定、`?debug` で `window.__island` を公開する。
