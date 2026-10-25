# Tasks: 89-ai-autonomy

> 他 agent が設計コンテキスト無しで実装できるよう、各タスクは具体的に書く。共通の制約と書く内容は plan.md を参照。
> テストは `uv run --no-project --with pytest --with jsonschema python -m pytest tests -q` で全体を流す。
> 各タスクは、テストを先に書いて失敗を確かめ、文書を直して通す（RED → GREEN）。タスクごとにコミットする。

## 実装タスク（順序付き）
- [x] T1: rules の流れを書き換える。`orchestration/rules/orchestration.md`（`## Phase stopping rule` を削除し、`## Human touchpoints`・`## Autonomous flow`・`## Spec review`・`## Escalation conditions`・`## PR decision log`・`## Running spec-reviewer` を足す。設計・実装エージェントの節を plan.md のとおり直す）、`rules/core.md`、`rules/workflow.md`、`rules/issue-intake.md`、`rules/subagents.md`。テストは `tests/test_ai_autonomy.py` に `OLD_STOP_PHRASES`（plan.md）と次を書く:
  - `test_orchestration_defines_human_touchpoints_and_autonomous_flow`: `orchestration.md` に 5 つの見出しがあり、`never merge`（大文字小文字を区別しない）を含み、`Initial question`・`sdd:tier-N`・`sdd-board.sh sync` を含む
  - `test_escalation_conditions_listed_and_referenced`: `## Escalation conditions` の節に `1.`〜`6.` の番号付きの項目があり、`comment the reason on the Issue` を含む。`rules/core.md`・`rules/workflow.md`・`rules/issue-intake.md` が `Escalation conditions` を含む
  - `test_rules_have_no_old_stop_phrases`: 上の 5 ファイルに `OLD_STOP_PHRASES` がない
  - `test_rules_require_spec_review_before_freeze`: `rules/workflow.md`・`rules/issue-intake.md`・`rules/subagents.md`・`orchestration.md` が `spec-reviewer` を含み、`rules/workflow.md` と `orchestration.md` が `APPROVE` を含む
  - `test_weakening_acs_still_needs_human_approval`: `rules/issue-intake.md` が `explicit human approval` を含む
  - 既存の `tests/test_rules_freeze_verify.py` は全部通ったままにする。対応AC: SAC-1, SAC-2, SAC-3, SAC-6
- [x] T2: spec-reviewer と PR 本文の雛形を作る。`integration/agents/spec-reviewer.md`（frontmatter は `integration/agents/sdd-reviewer.md` と同じ形、name `spec-reviewer`、読み取りのみ）と `integration/prompts/spec-reviewer-prompt.md`（spec「spec レビュー」の照合の 5 項目、判定の表、3 rounds、記録の例 `Spec review: APPROVE (2 rounds)`、`ESCALATE` を返す条件として問い合わせの条件の参照）。`templates/pr-body.md`（`closes #N`、変更、verify、`## AI の判断` に 4 項目: spec レビューの判定と回数、仕様の不明点について AI が決めたことと理由、指摘の採否と理由、スコープ外にしたものとフォローアップの Issue）。テスト:
  - `test_spec_reviewer_files_define_verdicts_and_limit`: 2 ファイルが `APPROVE`・`CHANGES`・`ESCALATE`・`3 rounds`・`Spec review: APPROVE`・`issue-snapshot.json`・`traceability.json` を含み、ファイルの編集をしないこと（`Do NOT` と `edit`）を含む
  - `test_pr_body_template_has_ai_decision_log`: `templates/pr-body.md` が `## AI の判断`・`spec レビュー`・`不明点`・`指摘`・`スコープ外` を含み、`orchestration.md` が `templates/pr-body.md` を含む。対応AC: SAC-3, SAC-4, SAC-6
- [x] T3: 周りの文書を新しい流れに合わせる。`integration/hooks/skill-reminder.sh` と `integration/hooks/codex-skill-reminder.sh` の spec フェーズのメッセージ（human approval → spec-reviewer の `APPROVE`）、`integration/AGENTS.md.example`、`orchestration/integration/AGENTS-patch.md.example`、`orchestration/templates/handoff.md.example`（停止したら orchestrating agent に報告。人間を待つ文を消す）、`integration/agents/sdd-reviewer.md` と `integration/prompts/sdd-reviewer-prompt.md`（「The human will provide」→ 依頼した側が渡す）、`docs/00-overview.md`〜`docs/04-issue-tracker.md`（`01-workflow.md` のフェーズ、`02-roles.md` の人間の役割と subagent の表に spec-reviewer、`03-faq.md`、`04-issue-tracker.md` のフロー図）、`README.md`（「フェーズ割り当て・停止ルール」、オーケストレーションの説明文、Reviewer の表に spec-reviewer）。テスト:
  - `test_surrounding_docs_have_no_old_stop_phrases`: 上の全ファイルに `OLD_STOP_PHRASES` がない
  - `test_spec_phase_reminder_mentions_spec_reviewer`: 両 hook を spec フェーズで動かした出力（既存の `tests/test_skill_reminder.py` の動かし方に合わせる）が `spec-reviewer` を含み `human approval` を含まない
  - `test_docs_describe_human_touchpoints`: `docs/02-roles.md` の `## 人間` の節が `最初の質問`・`問い合わせ`・`PR` を含み、`docs/01-workflow.md` が `spec-reviewer` を含む。対応AC: SAC-5, SAC-6
- [ ] T4: `docs/migration.md` の末尾に `## v4: 人間の関与を最初の質問と PR レビューに絞る（#89）` を足す（人間の関与が最初の質問・問い合わせ・PR レビューに移ったこと、`spec-reviewer` が `update.sh` で `.claude/agents/` に配られること、Claude 以外のエージェントは `vendor/ai-sdd-guide/integration/prompts/spec-reviewer-prompt.md` を使うこと、PR 本文の雛形 `vendor/ai-sdd-guide/templates/pr-body.md`）。テスト:
  - `test_migration_has_v4_section`: その節が `最初の質問`・`問い合わせ`・`PR レビュー`・`spec-reviewer`・`update.sh`・`.claude/agents/`・`spec-reviewer-prompt.md` を含む
  - `test_update_sh_distributes_spec_reviewer`: `tests/test_update_sh.py` の既存の動かし方で `update.sh` を実行し、consumer の `.claude/agents/spec-reviewer.md` ができる（`tests/test_update_sh.py` に足す）。対応AC: SAC-7, SAC-6

## テスト（受入条件との対応・必須）
- [x] SAC-1 → `tests/test_ai_autonomy.py::test_orchestration_defines_human_touchpoints_and_autonomous_flow`, `::test_rules_have_no_old_stop_phrases`
- [x] SAC-2 → `tests/test_ai_autonomy.py::test_escalation_conditions_listed_and_referenced`, `::test_weakening_acs_still_needs_human_approval`
- [x] SAC-3 → `tests/test_ai_autonomy.py::test_spec_reviewer_files_define_verdicts_and_limit`, `::test_rules_require_spec_review_before_freeze`
- [x] SAC-4 → `tests/test_ai_autonomy.py::test_pr_body_template_has_ai_decision_log`
- [x] SAC-5 → `tests/test_ai_autonomy.py::test_surrounding_docs_have_no_old_stop_phrases`, `::test_spec_phase_reminder_mentions_spec_reviewer`, `::test_docs_describe_human_touchpoints`
- [ ] SAC-6 → 上のテストすべてと、既存の `tests/test_rules_freeze_verify.py` が通る
- [ ] SAC-7 → `tests/test_ai_autonomy.py::test_migration_has_v4_section`, `tests/test_update_sh.py::test_update_sh_distributes_spec_reviewer`

## 完了の定義
- 全テスト green（`uv run --no-project --with pytest --with jsonschema python -m pytest tests -q`）
- `uv run -q --no-project --with jsonschema python integration/ci/sdd-validate.py --root . --pr --pr-labels sdd:tier-2` が PASS
- CI green / sdd-reviewer 合格（verify フェーズで確認）
