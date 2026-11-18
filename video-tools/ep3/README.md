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
