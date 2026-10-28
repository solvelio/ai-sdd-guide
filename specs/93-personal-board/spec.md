# Issue #93: transfer に合わせてボードを個人アカウントの Project に切り替える

Tier 1（軽量 spec）。

## 概要

2026-10-28 にこのリポジトリを solvelio から toshikimiyagawa に transfer した。`.sdd/board.json` は solvelio の Project #1 と GitHub App（`app_id`）を指したままで、個人アカウントでは App で Projects を操作できない。
このリポジトリ用の Project を個人アカウントに作って切り替え、`app_id` を外す。ボードの自動更新は classic PAT（secret `SDD_PROJECT_TOKEN`）で続ける（2026-10-28、人間と確認済み。Project は新しく作る、solvelio Organization は残す）。

## 用語と規則

- 新しい Project は `bash orchestration/tools/sdd-board.sh init --new --owner toshikimiyagawa` で作る（#91 の `init --new`）。名前はリポジトリ名 `ai-sdd-guide` になり、このリポジトリにリンクされ、Phase フィールドが作られ、開いている Issue が backlog で取り込まれる。
- `init --new` は `app_id` を残すので、そのあと `.sdd/board.json` から `app_id` を手で消す。`tier0_branch_prefixes` などほかのキーはない（今の `board.json` は `owner`・`project`・`app_id` だけ）。
- 結果の `.sdd/board.json` は `{"owner": "toshikimiyagawa", "project": <新しい番号>}`（2 スペースのインデント、末尾に改行）。
- `docs/04-issue-tracker.md` の参照リンク `[#71]`・`[#72]` の URL を `https://github.com/toshikimiyagawa/ai-sdd-guide/issues/<番号>` にする。
- solvelio の Project #1 と、そこに残るこのリポジトリのカードは触らない（Organization ごと残す）。

## 受入条件

- [ ] SAC-1: `.sdd/board.json` の `owner` が `toshikimiyagawa`、`project` が整数で、`app_id` のキーがない（元 Issue: 93-AC1）
- [ ] SAC-2: `.sdd/board.json` の Project が存在し、タイトルが `ai-sdd-guide`、このリポジトリにリンクされ、`Phase` フィールドがあり、このリポジトリの開いている Issue がすべてカードになっている（実装時に `gh` で確認し、verify の証跡に残す。ネットワークが要るのでテストにはしない）（元 Issue: 93-AC1）
- [ ] SAC-3: `specs/`・`_dev/`・`.git/` 以外のファイルに `github.com/solvelio/` という文字列がない（元 Issue: 93-AC2）
- [ ] SAC-4: SAC-1 と SAC-3 をテストが検査する（元 Issue: 93-AC3）

## スコープ

- `.sdd/board.json`
- `tests/test_self_migration.py`: `test_board_json_has_app_id` を `test_board_json_is_personal_without_app_id` に置き換える（SAC-1）。`test_no_solvelio_urls` を足す（SAC-3）
- `docs/04-issue-tracker.md`: 参照リンク 2 つ

### スコープ外

- secret の削除と PAT の登録（人間の作業。Issue に記載）
- soro-quest・acn-devcontainer・suumo-crawler の変更、ローカルのディレクトリの移動
- `tests/test_sdd_app_secret.py` などのテストデータに出てくる `solvelio/x`（URL ではないので SAC-3 に当たらない）
- GitHub App の仕組み（`sdd-app-secret.sh`、App のトークン）。Organization で使う構成として残す

## テスト

- `tests/test_self_migration.py::test_board_json_is_personal_without_app_id` — SAC-1, SAC-4
- `tests/test_self_migration.py::test_no_solvelio_urls` — SAC-3, SAC-4
