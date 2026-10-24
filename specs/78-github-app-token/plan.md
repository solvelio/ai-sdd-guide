# 78-github-app-token Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `sdd-board.yml` のボード更新を GitHub App のインストールトークンで行い、App の鍵を 1Password からリポジトリへ配るスクリプトを用意し、PAT の必要スコープの記載と権限不足の見分けを直す（#75）。

**Architecture:** トークンの選び方（認証モード）は `integration/ci/sdd_board.py` の新しいサブコマンド `auth-mode` に置き、ワークフローはその出力に従って `actions/create-github-app-token` を呼ぶか PAT を使うかを決める（YAML の中に判定を書かない）。鍵を配るのは `orchestration/tools/sdd-app-secret.sh`（bash + `gh` + `op`）。

**Tech Stack:** Python 3.9+（標準ライブラリ）、bash、GitHub CLI、1Password CLI（`op`）、GitHub Actions（`actions/create-github-app-token@v2`）、pytest。

**Spec:** `specs/78-github-app-token/spec.md`（理由は `_dev/specs/2026-10-25-github-app-board-token-design.md`）

## Global Constraints

- secret 名: `SDD_APP_PRIVATE_KEY`（App の鍵）、`SDD_PROJECT_TOKEN`（PAT、予備）。
- `board.json` の `app_id` は任意の整数（真偽値は不可）。`init` は既存のキーを消さない。
- 認証モードは `app` / `pat` / `none` / `error` の 4 つ。規則は spec の表のとおり。
- App のトークン: `actions/create-github-app-token@v2`、`app-id` は board.json の `app_id`、`owner` は board.json の `owner`、`repositories` はそのリポジトリの名前だけ。`continue-on-error` を付けない（作れなければジョブが失敗する）。
- `run:` ブロックに `${{` を書かない。イベントの値と secret の有無は step の `env:` で渡す。
- 鍵の値を変数・ファイル・標準出力・標準エラーに出さない（スクリプト、ワークフローとも）。
- 権限不足の定型文: `missing required scopes`、`INSUFFICIENT_SCOPES`、`Resource not accessible by integration`。警告に加える文: `トークンの権限が足りない可能性があります`。stderr そのものは出さない。
- PAT の必要スコープの書き方: 「classic、`repo`（private リポジトリの場合）・`project`・`read:org`」。
- テストは本物の `gh`・`op`・ネットワークを使わない（偽のコマンドを PATH の先頭に置く）。
- Python は 3.9 で動くこと。

## Review Focus

1. **フォークからの PR**: secret が渡らないので、`app_id` があっても鍵がない → `none`（警告して成功）。失敗させてはいけない（T1 `test_auth_mode_app_id_without_key_and_pat_is_none`）。
2. **`op read` の失敗**: 1Password がロック中・キャンセル・参照違いだと `op` は失敗する。そのまま `gh secret set` の標準入力に流すと、**空の secret が登録されて App が壊れる**。`op` が失敗したら、または出力の 1 行目が `-----BEGIN` で始まらなければ、`gh secret set` を呼ばずに止まる（T3 `test_op_failure_does_not_set_secret`、`test_non_pem_output_does_not_set_secret`）。
3. **`board.json` の型の誤り**: `"app_id": "123"` や `true` は設定の誤り → `error`（ジョブを失敗させ、理由を出す）。`board.json` がないリポジトリは `none`（T1 `test_auth_mode_invalid_app_id_is_error`、`test_auth_mode_without_board_json_is_none`）。
4. **2 回目の実行**: すでにインストール先に入っているリポジトリに `PUT` を送らない。secret は上書きしてよい（T3 `test_second_run_does_not_reinstall`）。
5. **インストール一覧の件数**: `GET /user/installations` と `GET /user/installations/{id}/repositories` はページ分けされる。`gh api --paginate` を使う（T3 `test_uses_paginate_for_installation_lists`）。

## 方針

- T1 は Python（`sdd_board.py`）だけで完結させ、ワークフロー（T2）とスクリプト（T3）はその上に乗る。
- ワークフローのテストは、既存と同じく文字列で検査する。加えて `integration/ci/sdd-board.yml` と `.github/workflows/sdd-board.yml` が、パスの違い（`vendor/ai-sdd-guide/` の有無と submodule の checkout）以外で一致することを検査する。
- このリポジトリ自身は T5 で App の方式に切り替える。鍵の作成・1Password への保管・Mac でのスクリプトの実行は人が行う（T5 で止まって確認する）。本当に App でボードを更新できるかは、この feature の PR の CI で確かめ、verify の evidence に残す。

## 判断（spec で決めていなかったもの）

- `auth-mode` は `board.json` が読めない（JSON でない、型の誤り）ときは `error`、ファイル自体がないときは `none`。
- `auth-mode` の出力は `GITHUB_OUTPUT` にそのまま足せる `key=value` 形式（`mode`、`app_id`、`owner`）。
- `actions/create-github-app-token` はメジャー版のタグ `@v2` で固定する（既存の `actions/checkout@v4` に合わせる）。
- スクリプトは `op read` の出力を一度もシェル変数に入れない。1 行目の確認だけは行う（PEM の 1 行目は秘密ではない）。

## 却下した案

- 判定を YAML の `if:` 式だけで書く: テストできず、`error` の扱いが書きにくい。
- スクリプトを Python で書く: 人の Mac に Python の環境を求めることになる。`bash`・`gh`・`op` だけにする。

## リスク

- 今の App の権限でボードの全操作が通るかは、本物で動かすまで分からない。対策: T5 と PR の CI で確かめる。足りなければ、権限を足す前に人に確認する（spec の制約）。
- `actions/create-github-app-token` の入力名の変更。対策: `@v2` の README の入力名（`app-id`、`private-key`、`owner`、`repositories`）に合わせ、テストで名前を検査する。
