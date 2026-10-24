# Tasks: 78-github-app-token

> 共通の制約は plan.md の Global Constraints を参照。テストは `python -m pytest tests/ -q` で全体を流す（jsonschema が入った python3 を PATH の先頭に置く）。

## 実装タスク（順序付き）
- [ ] T1: `sdd_board.py` に認証モードの判定、`app_id` の検査、`init` のキー保持、権限不足の見分けを足す。対応AC: SAC-1, SAC-2, SAC-3, SAC-7, SAC-8
- [ ] T2: `sdd-board.yml`（配布用とこのリポジトリ用）を認証モードに従って動かす。対応AC: SAC-1, SAC-2, SAC-3, SAC-4, SAC-7
- [ ] T3: 鍵を配るスクリプト `orchestration/tools/sdd-app-secret.sh`。対応AC: SAC-6, SAC-8
- [ ] T4: 文書（App の作り方、スクリプトの使い方、v3.1 の移行手順、PAT のスコープ）。対応AC: SAC-5, SAC-7
- [ ] T5: このリポジトリを App の方式に切り替える。対応AC: SAC-1, SAC-8

## テスト（受入条件との対応・必須）
- [ ] SAC-1 → `tests/test_sdd_board.py::test_auth_mode_*`、`tests/test_sdd_board_workflow.py::test_app_token_step`
- [ ] SAC-2 → `tests/test_sdd_board.py::test_auth_mode_pat_*`、`tests/test_sdd_board_workflow.py::test_board_steps_use_app_or_pat_token`
- [ ] SAC-3 → `tests/test_sdd_board.py::test_auth_mode_none_*`、`tests/test_sdd_board_workflow.py::test_none_mode_warns_and_skips`
- [ ] SAC-4 → `tests/test_sdd_board_workflow.py::test_no_expression_interpolation_in_run_scripts`
- [ ] SAC-5 → `tests/test_docs_github_app.py`
- [ ] SAC-6 → `tests/test_sdd_app_secret.py`
- [ ] SAC-7 → `tests/test_docs_github_app.py::test_pat_scope_wording`、`tests/test_sdd_board.py::test_scope_hint_*`
- [ ] SAC-8 → 全体（`python -m pytest tests/ -q`）、`tests/test_self_migration.py::test_board_json_has_app_id`

## 完了の定義
- 全 AC 対応テストが green
- PR の CI で、このリポジトリのボード更新が App のトークンで成功している
- sdd-reviewer 合格

---

### T1: sdd_board.py — 認証モード・app_id・init のキー保持・権限不足の見分け

**Files:**
- Modify: `integration/ci/sdd_board.py`
- Modify: `tests/test_sdd_board.py`、必要なら `tests/fake_gh.py`（stderr を返せるようにする）

**Interfaces（Produces）:**
- CLI: `python3 integration/ci/sdd_board.py auth-mode [--root R] --has-app-key true|false --has-pat true|false`
  - 標準出力（`GITHUB_OUTPUT` に足せる形）: `mode=<app|pat|none>`、`app_id=<N または空>`、`owner=<owner または空>` の 3 行。終了コード 0。
  - `none` のときは標準エラーに `::warning::` で始まる 1 行（理由）。
  - `error` のときは標準エラーに `::error::` で始まる 1 行（理由）を出し、標準出力に `mode=error`、終了コード 1。
- `load_board(root)` は `app_id`（任意、`int` で `bool` でない）を受け付け、型が違えば `BoardError`。
- `cmd_init` は既存の `board.json` があれば、そのキーを保ったまま `owner`・`project` を書く（既存の値があればそれを使う）。
- `run_gh` は失敗時に stderr を見て、権限不足の定型文があれば `GhError` の文に `トークンの権限が足りない可能性があります` を加える。stderr の中身は文に入れない。

- [ ] **Step 1: テストを書く**（`tests/test_sdd_board.py` に追加。`auth-mode` は gh を呼ばない）
  - `test_auth_mode_app_when_app_id_and_key`: board.json `{"owner":"o","project":1,"app_id":123}`、`--has-app-key true --has-pat false` → 出力に `mode=app`、`app_id=123`、`owner=o`、終了コード 0
  - `test_auth_mode_app_preferred_over_pat`: 鍵も PAT もある → `mode=app`
  - `test_auth_mode_key_without_app_id_is_error`: app_id なし、鍵あり → 終了コード 1、標準出力に `mode=error`、標準エラーに `::error::`
  - `test_auth_mode_pat_without_app_id`: app_id なし、鍵なし、PAT あり → `mode=pat`
  - `test_auth_mode_pat_when_app_id_but_no_key`: app_id あり、鍵なし、PAT あり → `mode=pat`
  - `test_auth_mode_app_id_without_key_and_pat_is_none`: app_id あり、鍵・PAT なし → `mode=none`、標準エラーに `::warning::`、終了コード 0
  - `test_auth_mode_none_without_anything`: app_id・鍵・PAT なし → `mode=none`
  - `test_auth_mode_without_board_json_is_none`: board.json がない（鍵あり）→ `mode=none`
  - `test_auth_mode_invalid_app_id_is_error`: `"app_id": "123"` と `"app_id": true` → `mode=error`、終了コード 1
  - `test_load_board_accepts_int_app_id`、`test_load_board_rejects_bool_app_id`
  - `test_init_preserves_existing_keys`: `{"owner":"o","project":1,"app_id":5,"tier0_branch_prefixes":["bot/"]}` がある状態で `init` → `app_id` と `tier0_branch_prefixes` が残る、`project create` を呼ばない
  - `test_scope_hint_on_missing_scopes`: 偽の gh が stderr に `missing required scopes [read:org]` を出して終了コード 1 → `sync` の警告に `トークンの権限が足りない可能性があります`、警告に `read:org` の文字列（stderr の中身）を含まない、終了コード 0
  - `test_scope_hint_on_integration_forbidden`: stderr `Resource not accessible by integration` でも同じ
  - `test_no_scope_hint_on_other_failure`: stderr `something else` → 権限の文を加えない
- [ ] **Step 2: 失敗を確認**: `python -m pytest tests/test_sdd_board.py -q` → FAIL
- [ ] **Step 3: 実装**: 上の Interfaces。`auth-mode` は `main()` の既存のサブコマンドと同じ引数の仕組みに足し、例外を warning に変える既存の catch-all の外で終了コードを返す。
- [ ] **Step 4: 通ることを確認**: 同じコマンド → PASS、全体 PASS
- [ ] **Step 5: コミット**: `feat(78-github-app-token): 認証モードの判定と app_id、権限不足の見分けを sdd_board.py に足す`

### T2: sdd-board.yml を認証モードに従って動かす

**Files:**
- Modify: `integration/ci/sdd-board.yml`、`.github/workflows/sdd-board.yml`
- Modify: `tests/test_sdd_board_workflow.py`

**Interfaces:** Consumes T1 の `auth-mode`。

ワークフローの形（手順の順）:
1. checkout（今のまま）
2. **Choose board token**（`id: auth`）: `env:` に `SDD_HAS_APP_KEY: ${{ secrets.SDD_APP_PRIVATE_KEY != '' }}`、`SDD_HAS_PAT: ${{ secrets.SDD_PROJECT_TOKEN != '' }}`。`run:` で `python3 <guide>/integration/ci/sdd_board.py auth-mode --has-app-key "$SDD_HAS_APP_KEY" --has-pat "$SDD_HAS_PAT" >> "$GITHUB_OUTPUT"`。`error` なら終了コード 1 でジョブが失敗する。
3. **Add tier label to PR**（今のまま）
4. **Create App token**（`id: app`）: `if: steps.auth.outputs.mode == 'app'`、`uses: actions/create-github-app-token@v2`、`with:` に `app-id: ${{ steps.auth.outputs.app_id }}`、`private-key: ${{ secrets.SDD_APP_PRIVATE_KEY }}`、`owner: ${{ steps.auth.outputs.owner }}`、`repositories: ${{ github.event.repository.name }}`。`continue-on-error` は付けない。
5. ボードの 3 つの手順: `if:` を `steps.auth.outputs.mode == 'app' || steps.auth.outputs.mode == 'pat'`（と既存のイベント条件）にし、`GH_TOKEN: ${{ steps.app.outputs.token || secrets.SDD_PROJECT_TOKEN }}`。
6. 先頭のコメント: 認証の選び方（App → PAT → なし）、PAT のスコープ（Global Constraints の書き方）、同じリポジトリの PR では PR 側のスクリプトがトークンを持って動くこと。

- [ ] **Step 1: テストを書く・直す**
  - `test_uses_project_token_secret` を残し、`test_app_token_step`: `actions/create-github-app-token@v2`、`app-id: ${{ steps.auth.outputs.app_id }}`、`private-key: ${{ secrets.SDD_APP_PRIVATE_KEY }}`、`owner: ${{ steps.auth.outputs.owner }}`、`repositories: ${{ github.event.repository.name }}` を含み、その step に `continue-on-error` がない
  - `test_auth_mode_step`: `auth-mode` と `SDD_HAS_APP_KEY`・`SDD_HAS_PAT` を含み、`>> "$GITHUB_OUTPUT"` に書く
  - `test_board_steps_use_app_or_pat_token`: ボードの 3 つの手順の `GH_TOKEN` がすべて `${{ steps.app.outputs.token || secrets.SDD_PROJECT_TOKEN }}`
  - `test_none_mode_warns_and_skips`: ボードの手順の `if:` に `steps.auth.outputs.mode` の条件がある
  - `test_label_step_uses_github_token`: ラベルの手順は `github.token`
  - `test_header_documents_auth_and_pat_scopes`: 先頭のコメントに `SDD_APP_PRIVATE_KEY`、`repo`、`project`、`read:org`
  - `test_repo_copy_matches_template`: 2 つのファイルが、`vendor/ai-sdd-guide/` の接頭辞と checkout の submodule 関係の行を除いて一致する
  - 既存の `test_no_expression_interpolation_in_run_scripts` が両ファイルで通る
- [ ] **Step 2: 失敗を確認** → FAIL
- [ ] **Step 3: 実装**: 上の形。
- [ ] **Step 4: 通ることを確認** → PASS、全体 PASS
- [ ] **Step 5: コミット**: `feat(78-github-app-token): sdd-board.yml を GitHub App のトークンで動かす`

### T3: 鍵を配るスクリプト sdd-app-secret.sh

**Files:**
- Create: `orchestration/tools/sdd-app-secret.sh`（実行可能）
- Create: `tests/test_sdd_app_secret.py`、`tests/fake_op.py`（偽の `op`）。偽の `gh` は `tests/fake_gh.py` を拡張するか、このテスト専用に用意する

**Interfaces（Produces）:** CLI は spec の「鍵を配るスクリプト」のとおり。
- `sdd-app-secret.sh --op-ref REF [--app-id N] [--dry-run] (OWNER/NAME... | --all --org ORG)`
- 使う `gh`: `repo list ORG --json nameWithOwner --limit 1000`、`api repos/OWNER/NAME/contents/.sdd/board.json`（`--all` の判定と `app_id` の読み取り）、`api --paginate /user/installations`、`api repos/OWNER/NAME --jq .id`、`api --paginate /user/installations/{id}/repositories`、`api -X PUT /user/installations/{id}/repositories/{repo_id}`、`secret set SDD_APP_PRIVATE_KEY -R OWNER/NAME`（値は標準入力）。
- 終了コード: 0 成功、1 入力の誤り・App が見つからない・`op` の失敗、2 予期しない失敗。

- [ ] **Step 1: テストを書く**（偽の `op` は `FAKE_OP_OUTPUT` の内容を出す。`FAKE_OP_EXIT` で失敗させられる。偽の `gh` は `secret set` の標準入力を記録ファイルに書く）
  - `test_sets_secret_from_op_via_stdin`: 対象 1 つ → `gh secret set SDD_APP_PRIVATE_KEY -R solvelio/x` が 1 回呼ばれ、その標準入力が偽の鍵と一致する
  - `test_key_never_printed`: 偽の鍵の文字列（`-----BEGIN` 以外の行）が標準出力・標準エラーに出ない
  - `test_installs_repo_when_missing`: インストール先にないリポジトリに `PUT /user/installations/{id}/repositories/{repo_id}` を送る
  - `test_second_run_does_not_reinstall`: すでに入っていれば `PUT` を送らない
  - `test_app_id_from_board_json`: `--app-id` なしで board.json の `app_id` を使う
  - `test_missing_app_id_fails`: `--app-id` も board.json の `app_id` もない → 終了コード 1、`secret set` を呼ばない
  - `test_app_installation_not_found_fails`: `/user/installations` に一致がない → 終了コード 1
  - `test_warns_when_board_json_lacks_app_id`: `--app-id` 指定で board.json に `app_id` がない → その旨を表示、書き換えない
  - `test_all_selects_repos_with_board_json`: `--all --org solvelio` → board.json を持つリポジトリだけが対象
  - `test_dry_run_changes_nothing`: `--dry-run` → `PUT`・`secret set`・`op` を呼ばない、計画を表示
  - `test_op_failure_does_not_set_secret`: 偽の `op` が終了コード 1 → `secret set` を呼ばない、終了コード 1
  - `test_non_pem_output_does_not_set_secret`: 偽の `op` の出力の 1 行目が `-----BEGIN` で始まらない → `secret set` を呼ばない
  - `test_uses_paginate_for_installation_lists`: 2 つの一覧の呼び出しに `--paginate`
- [ ] **Step 2: 失敗を確認**: `python -m pytest tests/test_sdd_app_secret.py -q` → FAIL
- [ ] **Step 3: 実装**: `set -euo pipefail`。鍵は `op read --no-newline` ではなく PEM の改行を保つ `op read "$REF"` を使い、1 行目を確かめてから残りと合わせて `gh secret set` の標準入力に流す（シェル変数に入れるのは 1 行目だけ）。
- [ ] **Step 4: 通ることを確認** → PASS、全体 PASS
- [ ] **Step 5: コミット**: `feat(78-github-app-token): App の鍵を 1Password から配るスクリプトを足す`

### T4: 文書

**Files:**
- Modify: `README.md`、`docs/04-issue-tracker.md`、`docs/migration.md`、`integration/issue-tracker/README.md`
- Create: `tests/test_docs_github_app.py`
- Modify: `tests/test_migration_guide.py`（既存のテストが通ることを確かめる。必要なら v3.1 の検査を足す）

書く内容:
- `docs/04-issue-tracker.md` に「GitHub App で動かす」節: App の作り方（Webhook のチェックを外す、権限: Organization の Projects = Read and write、リポジトリの Issues / Pull requests / Metadata = Read-only、インストール先は Only select repositories）、鍵の作り方と 1Password への保管（画面からダウンロードした `.pem` を 1Password に入れ、ファイルは消す）、`board.json` に `app_id` を書くこと、`sdd-app-secret.sh` の使い方（Mac で `op` を 1Password アプリと連携させて実行）、リポジトリを足す手順（board.json を置く → スクリプトを 1 回実行）。
- `docs/migration.md` に「v3.1: PAT から GitHub App へ」: App を作る → 鍵を 1Password へ → 各リポジトリの board.json に `app_id`（PR）→ スクリプトで鍵を配る → PR の CI で App で動くことを確かめる → `SDD_PROJECT_TOKEN` を消し、PAT を無効にする。
- PAT のスコープの書き方（Global Constraints）を、spec の SAC-7 に挙げたファイルすべてで直す。

- [ ] **Step 1: テストを書く**: `tests/test_docs_github_app.py`
  - `test_issue_tracker_doc_has_app_section`: `docs/04-issue-tracker.md` に `Read and write`、`Read-only`、`Webhook`、`1Password`、`sdd-app-secret.sh`、`app_id`
  - `test_migration_has_v31_section`: `docs/migration.md` に `v3.1`、`SDD_APP_PRIVATE_KEY`、`sdd-app-secret.sh`、`SDD_PROJECT_TOKEN`
  - `test_pat_scope_wording`: `README.md`、`docs/04-issue-tracker.md`、`docs/migration.md`、`integration/issue-tracker/README.md`、`integration/ci/sdd-board.yml` のそれぞれで、`SDD_PROJECT_TOKEN` に触れているなら `read:org` も含む。`sdd_board.py` の init 失敗のヒントに `read:org`
- [ ] **Step 2: 失敗を確認** → FAIL
- [ ] **Step 3: 書く**
- [ ] **Step 4: 通ることを確認** → PASS、全体 PASS
- [ ] **Step 5: コミット**: `docs(78-github-app-token): GitHub App の手順と PAT のスコープを書く`

### T5: このリポジトリを App の方式に切り替える

**Files:**
- Modify: `.sdd/board.json`（`app_id` を足す）
- Modify: `tests/test_self_migration.py`

- [ ] **Step 1: テストを書く**: `test_board_json_has_app_id`: `.sdd/board.json` の `app_id` が整数
- [ ] **Step 2: 失敗を確認** → FAIL
- [ ] **Step 3: App ID を調べて書く**: `gh api --paginate /user/installations`（人の `gh`）で `app_slug == "solvelio-sdd-board"` の `app_id` を読み、`board.json` に書く
- [ ] **Step 4: 人に頼む（止まる）**: (1) App の画面で秘密鍵を作り、1Password に保管して `.pem` を消す、(2) Mac で `sdd-app-secret.sh --op-ref <参照> solvelio/ai-sdd-guide` を実行する（先に `--dry-run`）。終わったら `gh secret list -R solvelio/ai-sdd-guide` に `SDD_APP_PRIVATE_KEY` があることを確かめる
- [ ] **Step 5: 通ることを確認**: 全体 PASS
- [ ] **Step 6: コミット**: `chore(78-github-app-token): このリポジトリのボード更新を GitHub App に切り替える`
