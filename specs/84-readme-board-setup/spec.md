# Issue #84: README の導入手順にボード（sdd-board.yml・board.json）のステップがない

Tier 1（軽量 spec）。

## 概要

README の「導入手順（取り込み側プロジェクト）」は 1〜5 で終わり、ボードのステップがない。ボードの手順は別の節「状態とボード」にだけあり、導入手順からの案内もない。
一方 `integration/update.sh` は `sdd-check.yml` と `sdd-board.yml` を常にコピーするので、導入手順に従った直後と `update.sh` 実行後でワークフローの構成が変わる。
また `sdd-board.yml` には、ボードと関係なく PR にブランチ名から `sdd:tier-*` ラベルを付けるステップがある。

方針:
- 手順 5（CI）で `sdd-check.yml` と `sdd-board.yml` の両方をコピーする（`update.sh` と同じ構成）。`sdd-board.yml` は `.sdd/board.json` がなければボードの処理を飛ばし、PR の Tier ラベル付けだけを行う。
- 手順 6 を「（任意）ボードを使う」として追加し、`sdd-board.sh init` で `.sdd/board.json` を作ること、認証の選び方（Organization → GitHub App、個人アカウントの Project → classic PAT）、詳細は `docs/04-issue-tracker.md` を案内する。

## 受入条件

- [ ] SAC-1: README の導入手順に「（任意）ボード」のステップがあり、`sdd-board.sh init`（`.sdd/board.json` の作成）、GitHub App（`SDD_APP_PRIVATE_KEY`・`board.json` の `app_id`）と classic PAT（`SDD_PROJECT_TOKEN`）の選び方、`docs/04-issue-tracker.md` への案内を含む（元 Issue: 84-AC1）
- [ ] SAC-2: README の導入手順に、`.sdd/board.json` がなければボードの処理は飛ばされること、PR の Tier ラベルを自動で付けるのは `sdd-board.yml` であること（入れない場合は手で付ける）が書かれている（元 Issue: 84-AC2）
- [ ] SAC-3: README の導入手順で `.github/workflows/` にコピーするワークフローの集合と、`integration/update.sh` がコピーするワークフローの集合が一致することをテストが検査する（元 Issue: 84-AC3）

## スコープ

- `README.md`: 「導入手順（取り込み側プロジェクト）」の手順 5 に `sdd-board.yml` のコピーを追加、手順 6（任意のボード）と説明を追加
- `tests/test_readme_install.py`（新規）: SAC-1〜3 のテスト

### スコープ外

- 「状態とボード」節の書き換え（重複は残してよい。導入手順から参照する）
- `docs/04-issue-tracker.md` の内容変更
- `sdd-board.yml`・`update.sh` の動作変更

## テスト

- `tests/test_readme_install.py::test_install_steps_include_optional_board_setup` — SAC-1
- `tests/test_readme_install.py::test_install_steps_explain_no_board_and_tier_label` — SAC-2
- `tests/test_readme_install.py::test_install_workflows_match_update_sh` — SAC-3
