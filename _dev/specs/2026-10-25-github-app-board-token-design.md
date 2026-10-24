# Design: ボード更新のトークンを GitHub App にする

Date: 2026-10-25
Issue: #78（Tier 2）。#75（PAT のスコープの記載不足と、gh の失敗理由が分からない件）を含む
関連: #73（状態管理を GitHub Projects に移した）、#76（Organization solvelio への移動）

この文書の「（設計者判断）」は、人と合意したことではなく、設計者が決めたこと。

## 1. なぜやるか

- 今の `sdd-board.yml` は classic PAT（secret `SDD_PROJECT_TOKEN`）でボードを更新している。
  - PAT には期限があり、切れると警告だけ出てボードが黙って止まる。
  - 必要なスコープ（`repo`・`project`・`read:org`）が広く、全リポジトリのコードを書き換えられる。
  - 個人アカウントに紐づく。
- 人の望み: **リポジトリを足すときに、秘密の値を手で扱わなくてよいこと**。ブラウザでの作業も手作業もない形がよい。
- ボードを Organization `solvelio`（Free プラン）に移したので、GitHub App が使えるようになった（App は個人アカウントの Projects を操作できない）。

## 2. ゴール・非ゴール・アンチゴール

### ゴール

- `sdd-board.yml` が GitHub App `solvelio-sdd-board` のインストールトークンでボードを更新する。
- リポジトリを足す作業が、コマンドだけで終わる（ブラウザ不要）: App の対象への追加、鍵の secret の登録、`.sdd/board.json` の用意。
- 鍵は 1Password にだけ保管し、画面・ログ・ディスクに出さない。
- #75 を直す: PAT の必要スコープの記載と、スコープ不足の見分け。

### 非ゴール

- ボード更新の担い手を変えること。`sdd-board.yml` の 6 つの役割（ラベル付け、Issue 作成で backlog、Issue 終了で done / アーカイブ、PR の作成・更新でフェーズの割り出し直し、マージで done）は今のまま残す（人の判断）。エージェントの `sdd-board.sh sync` も今のまま。
- 1 か所からの定期的な見回り、Cloudflare Worker での受信（人が却下: 状態は作業しているエージェントが変えるべき）。
- リポジトリごとに鍵を作って使い捨てる方式（鍵の作成に API がなく、ブラウザ作業が要るため不採用）。
- Team プランへの変更。
- 手元の `sdd-board.sh sync` の認証方法の変更（今までどおり手元の `gh` のログイン）。

### アンチゴール

- 鍵が標準出力・ログ・Actions のログ・一時ファイルに出る。
- 鍵がないときに CI が失敗する（今までどおり警告して成功）。
- `run:` に `${{ }}` を埋め込む（既存の方針）。
- App の権限を必要以上に広げる。

## 3. 決まったこと（人と合意済み）

- トークンは GitHub App。App `solvelio-sdd-board` は作成・インストール済み。
  - 権限: リポジトリの Issues・Pull requests・Metadata は読み取り、Organization の Projects は読み書き。
  - インストール先: `solvelio` の選んだリポジトリだけ（今は ai-sdd-guide と soro-quest）。
- 鍵は 1 つだけ作り、1Password に保管する。リポジトリごとに鍵は作らない。
- 鍵を配るスクリプトは、人の Mac（1Password アプリと連携した `op`、`gh`）で実行する前提。
- PAT（`SDD_PROJECT_TOKEN`）は、App の鍵がないリポジトリのための予備として当面残す（設計者判断。移行が終わったら別 Issue で消す）。
- **鍵はあるのに App のトークンを作れない（鍵が無効・取り違え・App 未インストールなど）ときは、ボードのジョブを失敗させる**（PR に ✗ が付く）。鍵がまったくないときは、今までどおり警告して成功（人の判断）。

## 4. 仕組み

### 4.1 ワークフロー（`integration/ci/sdd-board.yml`）

トークンの選び方（上から順に、最初に使えるもの）:

1. App: `.sdd/board.json` に `app_id` があり、secret `SDD_APP_PRIVATE_KEY` がある → `actions/create-github-app-token` でインストールトークンを作る。`owner` は `board.json` の `owner`、`repositories` はそのリポジトリだけに絞る（設計者判断。最小権限）。**作れなかったらジョブを失敗させる**（PAT には落ちない。人の判断）。
2. PAT: App の設定（`app_id` か鍵）がなく、secret `SDD_PROJECT_TOKEN` がある → 今までどおり。
3. どちらもない → 警告して、ボードの手順を飛ばす（成功で終わる）。

- App を使えるのは、ボードの持ち主（`board.json` の `owner`）が App を入れた Organization のときだけ。個人アカウントのボードや、App の入っていない Organization のボードでは、`app_id` を書かず PAT を使う（設計者判断）。
- 今の App の権限（Issues・Pull requests・Metadata 読み取り、Organization の Projects 読み書き）で、`sdd_board.py` が使うすべての `gh` 呼び出し（`project view`・`field-list`・`item-list`・`item-add`・`item-edit`・`item-archive`、`issue view`、`repo view`）が通ることを、本物の App で確かめるタスクを入れる。足りなければ、権限を足す前に人に確認する（設計者判断）。

- `app_id` は秘密ではないので `.sdd/board.json` に整数で書く（設計者判断。各リポジトリの secret を 1 つで済ませるため）。ワークフローは checkout 後に `python3` で読む。`sdd_board.py` の `board.json` の読み込みは `app_id`（任意、整数）を受け付けて型を確かめ、`init` は既存の `app_id` などのキーを消さない。
- secret 名は `SDD_APP_PRIVATE_KEY`（設計者判断）。
- ラベル付けは今までどおり標準の `GITHUB_TOKEN`。
- `actions/create-github-app-token` は版を固定する（設計者判断。メジャー版のタグか commit SHA。どちらにするかは plan で決める）。

### 4.2 鍵を配るスクリプト（新規）

`orchestration/tools/sdd-app-secret.sh`（名前は設計者判断）。

- 入力: 1Password の参照（例 `op://<保管庫>/<項目>/<欄>`、引数）、対象リポジトリ（`owner/name` を並べる。または `--all --org <org>`）、App ID（引数。なければ対象リポジトリの `board.json` の `app_id`）。
- App のインストール先は、人の `gh` で `GET /user/installations` から App ID に一致するものを探す（設計者判断）。見つからなければ止まる。
- `--all` の対象: Organization のリポジトリのうち `.sdd/board.json` を持つもの（API で確かめる）。
- リポジトリごとにすること:
  1. App のインストール先に入っていなければ追加する（`gh api` で。ブラウザ不要）。
  2. リポジトリの secret `SDD_APP_PRIVATE_KEY` に鍵を入れる。public・private を問わずリポジトリの secret にする（設計者判断。Organization の secret の対象一覧を変えるには人の `gh` に `admin:org` が要るため。全リポジトリを同じ扱いにできる）。
  3. `.sdd/board.json` に `app_id` がなければ、その旨を表示する（ファイルは書き換えない。変更は PR で行うため）。
- 鍵は `op read` の出力を `gh secret set` の標準入力へ直接渡す。変数・ファイルに置かない。
- 何度実行しても結果が同じ（冪等）。
- 実行前に、何をするかの一覧を表示する（`--dry-run` でそこで止まる）。

### 4.3 #75 の修正

- PAT の必要スコープの記載を「classic、`repo`（private リポジトリの場合）・`project`・`read:org`」にする（`docs/migration.md`、README / docs、`sdd-board.yml` の先頭コメント、`sdd_board.py` の init 失敗時のヒント）。
- `gh` の失敗時、stderr のうちスコープ不足を示す定型文だけを判定し、「トークンの権限が足りない可能性があります」と警告に出す。stderr そのものは出さない。

### 4.4 文書

- App の作り方（権限、Webhook なし、インストール先の選び方）、鍵の作成と 1Password への保管、スクリプトの使い方、リポジトリを足す手順を docs に書く。
- `docs/migration.md` に v3.1（PAT から App へ）の手順を足す。

## 5. このリポジトリと soro-quest への適用

- ai-sdd-guide（public）と soro-quest（private）の `.sdd/board.json` に `app_id` を足す（PR）。
- 人が App の鍵を作って 1Password に保管し、Mac でスクリプトを実行する。
- 動作を確かめたら、`SDD_PROJECT_TOKEN`（リポジトリの secret と Organization の secret）を消し、PAT を無効にする（別 Issue でもよい）。

## 6. 制約

- Free プラン: private リポジトリは Organization の secret を読めない。public リポジトリは読める。
- App の秘密鍵を新しく作る API はない（App の設定画面でだけ作れる）。
- フォークからの PR には secret が渡らない（`pull_request` トリガー）。ボードは飛ばされる。
- 同じリポジトリのブランチからの PR では、PR 側のスクリプトがトークンを持って動く（今までどおり。App のトークンは 1 時間で切れ、権限も狭い）。
- consumer は submodule の `vendor/ai-sdd-guide` から配布物を受け取る。

## 7. 実装する人に任せること

- スクリプトの内部（bash、`gh api` の呼び方、インストール先の追加の API）。
- テストの方法（偽の `gh` と偽の `op` を使う。既存の `tests/fake_gh.py` を流用してよい）。
- ワークフローの手順の分け方。
