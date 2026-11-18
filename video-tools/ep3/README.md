# 3日目（ep3）制作ツール

担当：Claude（台本・コード）／Muse（実行・データ・投稿）。投稿 18:30。

## 方針（2026-11-18 本人決定）
- 採用は **コメント件数が最多の案**（いいね数は使わない）。動画では「A ◯件・B ◯件・C ◯件 → 採用」をバーで見せて納得させる
- **コメントした人は、それぞれの場所へ行って、それぞれの案を実行してみる**（名札つき。失敗も見せる）
- 漂流中のままの人は、**海に浮かんだままコメントしている**（シュールに）
- フォロワー **300人** で森の奥が解放（獣の正体）。毎回「あと◯人」と「？？？」で引く
- 島民はドット絵のまま。見た目のバリエーションは `js/pixelart.js`（髪型10種・メガネ・ひげ・柄・帽子・背丈。IDから決定的）
- 締切は公開しない。集計は制作時（14:00）

## Muse に置いてほしいもの：`input/comments.json`（14:00）
形は `input/comments.sample.json` と同じ。

| 項目 | 内容 |
|---|---|
| `post.id` / `post.day` / `post.question` / `post.options` | 集計した投稿と、その投票の選択肢 |
| `fetchedAt` | 取得した時刻（JST つき ISO） |
| `totalComments` / `fetchedComments` | アプリで見える総数と、読めた件数 |
| `followers` | 取得時点のフォロワー数（「300人まであと◯人」） |
| `comments[].userId` / `name` | Instagram ID と表示名 |
| `comments[].text` | 本文（**そのまま**。絵文字も） |
| `comments[].likes` / `at` / `replyTo` | いいね数・投稿時刻・返信なら親コメントの ID |
| `comments[].source` | `api` か `screenshot`（スクショで補った分） |
| `comments[].status` | 取得時点の立場：`islander`（島民）／`drifter`（漂流者）／`none`（未フォロー） |

読めなかった分はスクショを `input/screens/` に置けば、Claude が文字を起こして足します。

## 実行環境のチェック
```sh
bash video-tools/ep3/check_env.sh > video-tools/ep3/input/env.txt
```
結果をコミットしてください（Chrome・フォント・VOICEVOX・BGM の版をそろえるため）。

## 録画のしかた（2日目からの変更点）
- `js/actors.js` に録画用フックを入れた：`globalThis.__stagePose(i, tMs)` が値を返すと、その島民は台本どおりに動く（`null` ならふだんの暮らし）。漂流者は `globalThis.__stageDrift(j, tMs, drift)`（`hide: true` で非表示）
- 演技のコマ：`anim` に `idle / walk / run / work / cheer / talk / sit / shock / eat`。`frame` で直接コマ指定も可
- これで **stage2 のコピーに手を入れなくても**本番サイトのコードのまま録画できる（データだけ差し替え）

## 制作パイプライン（2026-11-18 23:50 追加）
```sh
bash video-tools/ep3/run.sh video-tools/ep3/story/fish_test.json
```
- `story/*.json`＝シーンの台本（だれが・どこで・いつ何をするか、カメラ、名札と文字の出る時刻、ナレーション）
- `rec.mjs`：このリポジトリのサイトをそのまま配信して録画（外への通信は止める＝Firebase を読まず、台本の名簿だけで撮る）
- `lib/stage.js`：ページの中で台本を解釈（`actors.js` の `__stagePose` フックを使う。サイトのコードは変えない）
- `compose.py`：名札・吹き出し・アクション名・結果文を描き、VOICEVOX のナレーションと BGM を混ぜて mp4 に
- 同じ台本・同じ名簿なら、どのマシンでも同じ動画になる（描画は1コマずつ時刻から決まる）。違いが出るのは Chrome の版の細部だけ
- 環境変数：`CHROME`（既定は chrome-headless-shell → google-chrome）、`BGM`（既定 `~/workspace/mujintou/video/assets/bgm.mp3`）、`VOICEVOX`（既定 `http://127.0.0.1:50021`）、`FONT`・`FONT_BLACK`・`EMOJI_FONT`
- VOICEVOX や BGM が無いときは、無音で出して「!!」で知らせる（止まらない）
- 速さの目安：14秒（336コマ）の録画が約1分、合成が約30秒（2コア・GPUなし）

### 台本の書き方（story JSON）
| 項目 | 内容 |
|---|---|
| `roster` | 名簿（`input/islanders.json`。job・color 付き） |
| `cast` | 出る人の ID。先頭が真ん中、あとは左右交互に岸へ並ぶ |
| `place` | `shore`（岸に並ぶ）：`spot` 座標・`gap` 間隔・`back` 岸からの距離 |
| `acts` | `{who, t, anim, frame, face, at, to, dur, hide, pick, except}`。`who` は ID・ID の配列・`"*"`。位置は `{rel: ID, t: 岸沿い, n: 陸の奥(+)/海(-), up}` |
| `props` | 小道具（`fish`・`splash`）：`from`→`to` を `t0`〜`t1` で弧（`arc`）を描いて動き、`t2` まで残る |
| `camera` | ショットごとのキー。`look` は相対位置、`az` は「海側から見る」を0にした角度、`dist`・`pol`・`up`・`fov` |
| `overlay.stars` | 主役の名札と吹き出し（本人のコメントをそのまま）の出る時刻 |
| `overlay.action` / `result` | 下の白文字（何をしたか）と黄文字（どうなったか）。**黄は結果が画面で分かった時刻から** |
| `overlay.commenters` | 今回コメントした人と投票（小さな名札の色） |
| `audio.narration` | `{at, text}`。春日部つむぎ（speaker 8） |
