# 73-github-projects-board Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `.sdd/state.json`・`.sdd/tasks.json`・自前かんばんをなくし、SDD の状態をブランチ名と `specs/<feature>/` のファイルから割り出し、ボードを GitHub Projects に任せる。

**Architecture:** 割り出しの規則（ブランチ名、凍結、フェーズ）を Python モジュール `integration/ci/sdd_state.py` の 1 か所に置く。guard・skill-reminder（bash）は `python3` でその CLI を呼び、validator は import する。ボード操作は `integration/ci/sdd_board.py`（`gh` CLI を subprocess で呼ぶ）にまとめ、`orchestration/tools/sdd-board.sh` と Actions のワークフロー `integration/ci/sdd-board.yml` から使う。

**Tech Stack:** Python 3.9+（標準ライブラリのみ。validator は既存どおり jsonschema）、bash、GitHub CLI（`gh project` / `gh issue` / `gh pr`）、GitHub Actions、pytest。

**Spec:** `specs/73-github-projects-board/spec.md`（理由は `_dev/specs/2026-10-24-github-projects-board-design.md`）

## Global Constraints

- ブランチ名の正規表現: `^t(?P<tier>[012])/(?P<issue>[1-9][0-9]*)-(?P<name>[a-z0-9][a-z0-9-]*)$`。feature = `<issue>-<name>`。
- 凍結の対象: Tier 2 は `spec.md`・`plan.md`・`tasks.md`・`traceability.json`、Tier 1 は `spec.md`。`tasks.md` は行頭のチェック欄 `[x]`/`[X]` を `[ ]` に正規化してからハッシュを取る。
- Phase の値（この順）: `backlog`, `brainstorm`, `spec`, `plan`, `tasks`, `implement`, `verify`, `done`。
- `.sdd/board.json` のキー: `owner`（文字列）、`project`（整数）、`tier0_branch_prefixes`（文字列の配列、省略時 `["dependabot/", "renovate/"]`）。
- Actions の secret 名: `SDD_PROJECT_TOKEN`（classic PAT、`project` スコープ）。
- hook はネットワークと `gh` を使わない。
- ボード操作の失敗は警告のみで終了コード 0（`sync` とワークフロー）。
- `state.json`・`tasks.json` へのフォールバックを持たない。
- Python は 3.9 で動くこと（`from __future__ import annotations` を使う。`match` 文や `X | Y` の実行時評価を使わない）。
- 既存の guard の除外パス（`""|*.md|specs/*|*/specs/*|docs/*|*/docs/*|.sdd/*|*/.sdd/*`）と linked worktree 制限は変えない。

## Review Focus

1. **CI の detached HEAD**: `actions/checkout` は PR のマージコミットを detached で取り出すので、`git branch --show-current` は空になる。validator は `GITHUB_HEAD_REF` を優先して読むこと（T4 のテスト `test_branch_from_github_head_ref`）。手元で detached のときは「Tier 未分類」として拒否し、その旨を表示する（T1 のテスト `test_current_branch_detached_is_none`）。
2. **チェック欄の表記ゆれ**: `- [X]`、`* [x]`、字下げしたサブ項目、CRLF の行末でも、チェック欄だけの変更はハッシュを変えない（T1 のテスト `test_tasks_md_checkbox_variants_do_not_change_hash`）。チェック欄以外の 1 文字の変更はハッシュを変える。
3. **ボードの件数**: `gh project item-list` は既定で 30 件しか返さない。全件を見るために `--limit` を渡すこと（T6 のテスト `test_item_lookup_passes_large_limit`）。
4. **1 枚のボードに複数リポジトリ**: 同じ Issue 番号が別リポジトリにもある。カードは番号とリポジトリの両方で見つけること（T6 のテスト `test_item_lookup_matches_repository_and_number`）。
5. **凍結後にファイルが消えた／増えた**: `freeze.json` に記録した対象ファイルが消えたら正しくない扱い。Tier 2 で `freeze.json` の対象一覧が Tier の規則と違う（Tier 1 の freeze.json を Tier 2 のブランチで使う等）ときも正しくない（T1 のテスト `test_freeze_missing_file_is_invalid`、`test_freeze_tier_mismatch_is_invalid`）。

## 方針

- 割り出しは純粋関数にし、ファイルシステムと git の読み取りだけを入力にする。テストは一時ディレクトリと一時 git リポジトリで行う（既存の guard テストと同じやり方）。
- validator には `--branch`（ブランチ名の上書き）、`--pr`（PR としての検査）、`--pr-labels`（カンマ区切りの PR ラベル）を足す。`--feature` は feature だけを上書きする（Tier はブランチ名から）。
  - ブランチは `--branch` → 環境変数 `GITHUB_HEAD_REF` → `git branch --show-current` の順に決める。
  - `--pr` のとき: ブランチ名の形を強制（例外の接頭辞は Tier 0 扱い）、Tier 1/2 の `freeze.json` がないのもエラー、Tier 2 の `tasks.md` に未チェックが残っていればエラー（既存のチェック 5 の意図を PR に移す）、`sdd:tier-N` ラベルの食い違いはエラー。
  - `--pr` でないとき: ブランチが形に合わなければ feature の検査を飛ばして PASS（main への push や手元の main）。`freeze.json` がないのはエラーにしない（設計中）。あるのに正しくなければエラー。
- ボードは `gh` を subprocess で呼ぶ。テストは `PATH` の先頭に偽の `gh`（引数を記録し、用意した JSON を返す Python スクリプト）を置いて行う。
- このリポジトリ自身の移行（T10）は最後に行う。ブランチを `t2/73-github-projects-board` に改名し、`freeze.json` を新しいコマンドで作る（凍結した spec 群は変えていないので、ハッシュは凍結時の内容を表す）。実際のボード作成と secret 登録は外部への操作なので、人の確認を取ってから行う。

## 判断（設計書・spec で決めていなかったもの）

- `SDD_ALLOW_MAIN_WORKTREE=1` のときは、worktree の制限に加えてブランチによる判定も飛ばす。今は main の state が Tier 0 なのでメンテナンスが通っていた。その挙動を保つため。
- Tier 0 の例外接頭辞（`dependabot/` など）は validator（`--pr`）とワークフローだけが使う。guard は使わない（bot は手元で編集しない）。
- `sdd-board.sh init` は Project を作ったら `.sdd/board.json` を書く。`board.json` がすでにあれば作らず、`Phase` フィールドの確認と取り込みだけを行う。
- Actions はボードに触る前に PR に `sdd:tier-N` ラベルを付ける。ラベルの付与には標準の `GITHUB_TOKEN` を使う（`pull-requests: write`、`issues: write`）。ラベルがリポジトリになければ作る。
- フェーズの割り出しで Tier 0 の PR は `implement`、マージで `done`。

## 却下した案

- guard を bash だけで書き直す: ハッシュの正規化を bash と Python の 2 か所に書くことになり、「規則は 1 か所」に反する。
- ボード操作を GraphQL で直接書く: `gh project` サブコマンドで足りる。テストも引数の記録で済む。
- 移行期間のフォールバック: 人の判断で不要（設計書 3.6）。

## リスク

- `gh project` のサブコマンドの出力形式が `gh` の版で変わる。対策: `--format json` を必ず使い、使うキーを最小にする（`items[].id`、`items[].content.number`、`items[].content.repository`、`fields[].id/name/options[]`、Project の `id`）。
- 偽の `gh` によるテストは、本物の `gh` の振る舞いの確認にならない。対策: T10 で実際のボードに対して `init`・`sync` を 1 回ずつ流し、結果を evidence に残す（人の確認のうえ）。
- このリポジトリの Tests ワークフローは `pytest tests/` だけを流す。`sdd-board.yml` はこのリポジトリでも動くが、secret がなければ警告で終わる。
