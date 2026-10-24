# Spec: 78-github-app-token

- Tier: 2
- Status: frozen
- Feature slug: 78-github-app-token
- Issue: #78（#75 を含む）
- Design: [_dev/specs/2026-10-25-github-app-board-token-design.md](../../_dev/specs/2026-10-25-github-app-board-token-design.md)
- Traceability: [traceability.json](traceability.json)

## 背景 / 意図

`sdd-board.yml` は classic PAT（`SDD_PROJECT_TOKEN`）でボードを更新している。PAT は期限切れで黙って止まり、権限が広く、個人アカウントに紐づく。ボードを Organization に移したので、GitHub App のインストールトークンに切り替える。リポジトリを足す作業は、1Password に保管した App の鍵をスクリプトで配るだけにする（ブラウザ不要）。あわせて #75（PAT の必要スコープの記載不足と、gh の失敗理由が分からない件）を直す。理由と経緯は Design を参照。

## 用語と規則

### トークンの選び方（認証モード）

入力: `.sdd/board.json` の `app_id`（任意、整数）、secret `SDD_APP_PRIVATE_KEY` の有無、secret `SDD_PROJECT_TOKEN` の有無。

| app_id | 鍵 | PAT | モード | 結果 |
|---|---|---|---|---|
| あり | あり | 問わない | `app` | App のトークンを作る。作れなければジョブを失敗させる |
| なし | あり | 問わない | `error` | 設定の誤り（鍵があるのに app_id がない）としてジョブを失敗させる |
| あり | なし | あり | `pat` | PAT で更新する |
| なし | なし | あり | `pat` | PAT で更新する |
| あり／なし | なし | なし | `none` | 警告して、ボードの手順を飛ばす（成功） |

- App のトークンは `actions/create-github-app-token` で作る。`owner` は `board.json` の `owner`、`repositories` はそのリポジトリだけ。
- App のトークンを作れたあとのボード操作の失敗（権限不足など）は、今までどおり警告して成功（`sdd-board.sh` の既存の振る舞い）。

### board.json

- キー: `owner`（文字列）、`project`（整数）、`tier0_branch_prefixes`（任意）、`app_id`（任意、整数。真偽値は不可）。
- `sdd-board.sh init` が `board.json` を書くとき、既存のキー（`app_id` など）を消さない。

### 鍵を配るスクリプト `orchestration/tools/sdd-app-secret.sh`

- 必要なもの: `bash`、`gh`（人のログイン）、`op`（1Password CLI）。リポジトリのファイルを読まない。
- 引数: `--op-ref <op://...>`（必須）、`--app-id <N>`（任意）、対象（`owner/name` を 1 つ以上、または `--all --org <org>`）、`--dry-run`。
- `--all --org <org>` の対象: その Organization のリポジトリのうち `.sdd/board.json` を持つもの。
- App ID: `--app-id`、なければ対象リポジトリの `board.json` の `app_id`。決まらなければ止まる。
- App は Organization の **All repositories** にインストールしておく（新しいリポジトリも自動で対象に入る）。スクリプトはインストール先を追加しない。`/user/installations/...` の API は GitHub App のユーザー用トークンか PAT でしか呼べず、人の `gh` のログイン（OAuth アプリのトークン）では使えないため（2026-10-25 に確認）。
- インストール先の確認: 人の `gh` で `GET /orgs/{org}/installations` から App ID に一致するものを探す（`{org}` は対象リポジトリの持ち主。対象の持ち主が 1 つでなければ止まる）。見つからなければ止まる。`repository_selection` が `all` でなければ、All repositories に変える手順を表示して止まる。
- リポジトリごとに: (1) `op read` の出力を `gh secret set SDD_APP_PRIVATE_KEY -R <repo>` の標準入力へ直接渡す、(2) `board.json` に `app_id` がなければその旨を表示する（書き換えない）。
- 鍵を変数・ファイル・標準出力・標準エラーに出さない。
- `--dry-run` では、各リポジトリで何をするかを表示し、変更しない（`op read` も呼ばない）。
- 何度実行しても結果が同じ。

## 受入条件

- [ ] SAC-1: 認証モードが `app` のとき、`sdd-board.yml` は `actions/create-github-app-token`（`owner` は board.json の `owner`、`repositories` はそのリポジトリ）でトークンを作り、ボードの 3 つの手順（Issue 作成、Issue 終了、PR）にそのトークンを渡す。トークンを作れなければジョブは失敗する。鍵があるのに `app_id` がない（モード `error`）ときもジョブは失敗する（元 Issue: 78-AC1）
- [ ] SAC-2: 認証モードが `pat` のとき、ボードの 3 つの手順は `SDD_PROJECT_TOKEN` を使い、今までどおり動く（元 Issue: 78-AC2）
- [ ] SAC-3: 認証モードが `none` のとき、警告を出してボードの手順を飛ばし、ジョブは成功する。PR の Tier ラベル付けは、どのモードでも標準のトークンで行う（元 Issue: 78-AC3）
- [ ] SAC-4: `integration/ci/sdd-board.yml` と `.github/workflows/sdd-board.yml` の `run:` ブロックに `${{` がない（元 Issue: 78-AC4）
- [ ] SAC-5: docs に GitHub App の作成手順（Webhook なし、権限: Organization の Projects 読み書き・リポジトリの Issues / Pull requests / Metadata 読み取り、インストール先は Organization の All repositories）、鍵の作成と 1Password への保管、`sdd-app-secret.sh` の使い方、リポジトリを足す手順がある。`docs/migration.md` に PAT から App へ移る手順（v3.1）がある（元 Issue: 78-AC5）
- [ ] SAC-6: `sdd-app-secret.sh` が「鍵を配るスクリプト」の規則どおりに動く。鍵の値が標準出力・標準エラーに出ない（元 Issue: 78-AC6）
- [ ] SAC-7: PAT の必要スコープが、`README.md`・`docs/04-issue-tracker.md`・`docs/migration.md`・`integration/issue-tracker/README.md`・`sdd-board.yml` の先頭コメント・`sdd_board.py` の init 失敗時のヒントで「classic、`repo`（private リポジトリの場合）・`project`・`read:org`」になっている。`gh` の失敗時、stderr が権限不足を示す定型文（`missing required scopes`、`INSUFFICIENT_SCOPES`、`Resource not accessible by integration`）を含むときは、警告に「トークンの権限が足りない可能性があります」を加える。stderr そのものは出さない（元 Issue: 78-AC7）
- [ ] SAC-8: 既存のテストがすべて通り、認証モードの判定、`board.json` の `app_id`、`init` のキー保持、スクリプト、権限不足の見分けにテストがある（元 Issue: 78-AC8）

## スコープ外

- `sdd-board.yml` の 6 つの役割の変更、エージェントの `sdd-board.sh sync` の認証の変更
- 1 か所からの見回り、Cloudflare Worker、リポジトリごとの鍵、Team プラン
- PAT と `SDD_PROJECT_TOKEN` の廃止（移行が終わったら別 Issue）
- soro-quest など consumer への適用（submodule を上げたあと、各リポジトリの Tier 0 の作業で行う）

## 制約 / 前提

- Free プラン: private リポジトリは Organization の secret を読めない。鍵はリポジトリの secret に置く（public も同じ扱い）。
- App の秘密鍵を作る API はない。鍵は人が 1 回だけ App の画面で作り、1Password に保管する。
- フォークからの PR には secret が渡らない（モード `none` か、鍵だけ渡らず `pat`/`none` になる）。
- 既存の方針: `run:` に `${{ }}` を埋め込まない、ボード操作の失敗は警告のみ、Python は 3.9 で動く。
- このリポジトリ自身（public、`solvelio/ai-sdd-guide`）は、この feature の中で App の方式に切り替え、PR の CI で実際に App のトークンでボードを更新できることを確かめる。鍵の作成・1Password への保管・Mac でのスクリプト実行は人が行う。
