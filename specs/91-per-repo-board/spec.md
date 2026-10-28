# Issue #91: ボードを「アカウントで 1 枚」から「リポジトリごとに 1 枚」に変える

Tier 1（軽量 spec）。

## 概要

今の guide はボードを「アカウント（owner）で 1 枚」とし、同じ owner の 2 つ目以降のリポジトリでは既存の `.sdd/board.json` をコピーして同じ Project を使う。
これを「リポジトリごとに 1 枚」に変える。`sdd-board.sh init` は Project をそのリポジトリにリンクし、共有のボードを使っているリポジトリは自分用の Project に切り替えられるようにする。

最初の質問の回答（2026-10-28）: Tier 1。guide の既定を変え、solvelio の Project #1（ai-sdd-guide と soro-quest で共有）も分ける。分けるのはマージ後の運用作業で、この spec の実装には含めない。

## 用語と規則

### `sdd-board.sh init`（`integration/ci/sdd_board.py` の `cmd_init`）

- `--title` の既定を、リポジトリ名（`gh repo view` の `nameWithOwner` の `/` より後ろ）にする。`--title` を渡せばそれを使う。
- 新しいオプション `--new`: `.sdd/board.json` があっても新しい Project を作る。
  - owner は `--owner`、なければリポジトリの owner（`gh repo view` の `owner.login`）。
  - `board.json` の `owner`・`project` だけを新しい値に書き換え、ほかのキー（`app_id`・`tier0_branch_prefixes` など）は残す。
  - `board.json` がないときの `--new` は、`--new` なしと同じ。
- `board.json` がなく `--new` もないとき（新しく作るとき）は、今と同じく Project を作って `board.json` を書く。
- Project が決まったら（新しく作ったときも、`board.json` の Project を使うときも）、`gh project link <project> --owner <owner> --repo <nameWithOwner>` でリポジトリにリンクする。
  - リンクに失敗しても init は失敗させない。警告（`sdd-board: warning: ...`）を標準エラーに出して続ける（owner が違うなど、リンクできない構成でも Phase フィールドの確認と Issue の取り込みはできるようにする）。
- `gh repo view --json nameWithOwner,owner` が失敗したとき:
  - リポジトリ名や owner が Project を作るのに要る場合（新しく作るときに `--title` か `--owner` を渡していない）は、今と同じくエラー（終了コード 1）。
  - それ以外（`board.json` の Project を使うとき、または `--title` と `--owner` を両方渡したとき）は、リンクだけを飛ばして警告を出し、続ける。
- そのあとの Phase フィールドの確認と、開いている Issue の取り込みは今と同じ。

### 文書

- README（「状態とボード」の節と導入手順 6）、`docs/04-issue-tracker.md`、`rules/issue-intake.md` は「リポジトリごとに 1 枚」とする。各リポジトリで `sdd-board.sh init` を実行すれば、Project の作成・リンク・取り込みが済むと書く。
- 「アカウントで 1 枚」「one board per account」「既存リポジトリの `.sdd/board.json` をコピーしてから init する」指示を消す。
- `docs/04-issue-tracker.md` の「リポジトリを足すとき」は、GitHub App の鍵を配る手順として残す（`board.json` は init が作り、`app_id` を書き足す）。
- `docs/migration.md` の末尾に `## v4.1: リポジトリごとのボード（#91）` を足す。共有のボードからの切り替え手順:
  1. submodule を上げる
  2. `bash vendor/ai-sdd-guide/orchestration/tools/sdd-board.sh init --new` を実行し、`.sdd/board.json` の変更を PR で入れる（`app_id` は残る）
  3. 古い共有のボードから、そのリポジトリのカードをアーカイブする（Projects の画面で `repo:owner/name` で絞り込み、まとめてアーカイブ）
  4. GitHub App を使っている場合、App は Organization の Projects 全体に権限があるので、鍵の配り直しは要らない
- `docs/migration.md` の「v3」節の手順 7 の「ボードは 1 アカウントに 1 つ」の説明は、「v4.1」を参照する文に置き換える。

## 受入条件

- [ ] SAC-1: README・`docs/04-issue-tracker.md`・`rules/issue-intake.md` に「アカウントで 1 枚」「one board per account」の記述がなく、`board.json` と「コピー」（または `copy`）を同じ行に含む行がない。README と `docs/04-issue-tracker.md` は「リポジトリごとに 1 枚」、`rules/issue-intake.md` は `one board per repository` を含む（元 Issue: 91-AC1）
- [ ] SAC-2: `init` が、新しく作るときも `board.json` の Project を使うときも、`gh project link <project> --owner <owner> --repo <nameWithOwner>` を呼ぶ。新しく作る Project の名前の既定はリポジトリ名。リンクが失敗しても、`board.json` があるときに `gh repo view` が失敗しても、終了コード 0 で、警告を出し、Issue の取り込みまで行う（元 Issue: 91-AC2）
- [ ] SAC-3: `init --new` は `board.json` があっても新しい Project を作り、`owner`・`project` を書き換え、`app_id`・`tier0_branch_prefixes` を残す（元 Issue: 91-AC3）
- [ ] SAC-4: `docs/migration.md` に「v4.1」の節があり、`init --new`・カードのアーカイブ・App の鍵の配り直しが要らないことが書かれている。「v3」節に「1 アカウントに 1 つ」の記述がない（元 Issue: 91-AC4）
- [ ] SAC-5: SAC-2・SAC-3 を `tests/test_sdd_board.py` のテストが検査する（元 Issue: 91-AC5）

## スコープ

- `integration/ci/sdd_board.py`: `cmd_init` と `init` の引数
- `tests/test_sdd_board.py`、`tests/fake_gh.py`（必要なら）: SAC-2・SAC-3 のテスト
- `README.md`・`docs/04-issue-tracker.md`・`rules/issue-intake.md`・`docs/migration.md`: SAC-1・SAC-4
- `tests/test_migration_guide.py` か新しいテスト: SAC-1・SAC-4 の文言の検査

### スコープ外

- solvelio の Project #1 を分ける運用作業（soro-quest の `board.json` の変更、カードのアーカイブ）。マージ後に行う
- `sync`・`import`・`set`・`close`・`pr`・`sdd-board.yml`・`sdd-app-secret.sh` の動作
- Projects のビューの自動作成（API がない）

## テスト

- `tests/test_sdd_board.py::test_init_links_new_project_to_repo` — SAC-2
- `tests/test_sdd_board.py::test_init_links_existing_project_to_repo` — SAC-2
- `tests/test_sdd_board.py::test_init_default_title_is_repo_name` — SAC-2
- `tests/test_sdd_board.py::test_init_link_failure_warns_and_continues` — SAC-2
- `tests/test_sdd_board.py::test_init_repo_view_failure_with_board_json_skips_link` — SAC-2
- `tests/test_sdd_board.py::test_init_new_replaces_project_and_keeps_keys` — SAC-3
- `tests/test_board_docs.py::test_docs_describe_per_repo_board` — SAC-1
- `tests/test_board_docs.py::test_migration_has_per_repo_section` — SAC-4
