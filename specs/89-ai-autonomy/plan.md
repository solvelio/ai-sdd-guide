# 89-ai-autonomy Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** guide の既定の流れを、人間の関与を「最初の質問・問い合わせ・PR のレビューとマージ」に絞り、それ以外は AI が独立したエージェントを使って PR の作成まで進める流れに変える。

**Architecture:** 新しい流れの正本は `orchestration/rules/orchestration.md` に置く（節: `## Human touchpoints`・`## Autonomous flow`・`## Spec review`・`## Escalation conditions`・`## PR decision log`）。ほかの rules はそれを参照し、旧い停止・承認の指示を消す。spec レビューの役割は `sdd-reviewer` と同じ形で、Claude 用サブエージェント定義とエージェント非依存のプロンプトの 2 ファイルにする。docs・hooks・テンプレートは文言だけを合わせる。コードの動作（CI・validator・guard・`sdd_state.py`）は変えない。

**Tech Stack:** Markdown（rules は英語、docs は日本語）、bash（hook のメッセージ文字列のみ）、pytest（文言の検査）。

**Spec:** `specs/89-ai-autonomy/spec.md`

## Global Constraints

- `rules/`・`orchestration/rules/`・`integration/agents/`・`integration/prompts/`・hook のメッセージは英語で命令形・簡潔。`docs/`・`templates/pr-body.md`・`docs/migration.md` は日本語（`rules/conventions.md`）。
- エージェントに依存しない書き方にする。Claude Code はサブエージェント、Codex は `spawn_agent`、Gemini CLI は `@generalist` にプロンプトを渡す（`sdd-reviewer` の既存の書き方に合わせる）。
- Tier を決めるのは人間のまま。`rules/issue-intake.md` の「human-assigned `sdd:tier-{0,1,2}` label」の規則は残す（最初の質問で聞く形に変える）。
- Issue の AC を弱めるときの「explicit human approval」の規則は残す（`tests/test_rules_freeze_verify.py::test_intake_weakened_spec_approval`）。
- 判定の名前: `APPROVE`・`CHANGES`・`ESCALATE`。`CHANGES` の上限は 3 回（"3 rounds"）。記録の例: `Spec review: APPROVE (2 rounds)`。
- PR 本文の節の見出し: `## AI の判断`。
- 既存のテスト（`tests/test_rules_freeze_verify.py` など）が検査している文言は、旧い停止・承認の指示でない限り消さない。
- CI・validator・guard・`sdd_state.py`・過去の `specs/`・`_dev/` は変えない。

## 新しい rules の要点（T1 で書く内容）

`orchestration/rules/orchestration.md`:

- `## Scope assignment`: 表は残す。「The human decides which agent handles which phase」を、「The orchestrating agent runs all phases, dispatching independent agents (subagents) where required; a human may assign a specific agent」に変える。
- `## Phase stopping rule` を削除し、次の節に置き換える。
- `## Human touchpoints`: 3 つの場面。
  1. Initial question: Tier proposal with reasons + only those spec unknowns whose answer changes what gets built, in one message. Apply the `sdd:tier-N` label from the answer. Skip when the label exists and there are no unknowns. Record decisions made without asking.
  2. Escalation: only under `## Escalation conditions`.
  3. PR review and merge: never merge; the human reviews, approves and merges.
- `## Autonomous flow`: spec「自律で進める範囲」の 1〜9 をそのまま列挙する。各フェーズの境目で commit → `sdd-board.sh sync`、ただし停止しない。凍結後の実装は新しいエージェントのコンテキストで行う（`Never implement in the same agent context that froze the spec`）。
- `## Spec review`: spec「spec レビュー」の誰が・いつ・照合・判定・3 rounds・記録・凍結後の変更。
- `## Escalation conditions`: spec の 6 項目と問い合わせ方（対話の場にいればその場で聞く、いなければ Issue にコメントして停止）。
- `## PR decision log`: PR 本文の `## AI の判断` に 4 項目を書く。雛形 `templates/pr-body.md`（consumer からは `vendor/ai-sdd-guide/templates/pr-body.md`）。
- `## Rules for design agents`: 「Commit, run sync, and stop」を「commit, run sync, and continue to spec review」に。Issue Diff Summary は「presenting for human approval」でなく、spec レビューに渡し PR の decision log に載せる。
- `## Rules for implementation agents`: 「When complete, ... and stop」を「report back to the orchestrating agent」に。spec が不十分なら、停止して orchestrating agent に報告し、orchestrating agent が spec レビューか問い合わせで解決する。
- `## Running sdd-reviewer`: そのまま。同じ形で `## Running spec-reviewer` を足す。

`rules/core.md`・`rules/workflow.md`・`rules/issue-intake.md`・`rules/subagents.md`:

- 「comment the reason on the Issue and STOP. Escalate to a human」→ `## Escalation conditions` を参照する文へ。
- `workflow.md` の 1（Brainstorm: clarify intent with the human）→ 最初の質問の回答をもとに、人間との対話なしで行う。2（Get human approval）→ spec レビュー。4（after human approval / STOP / same session）→ `APPROVE` の後に凍結、新しいエージェントで実装。実装完了の「and stop」、verify の「STOP and escalate to the human」→ 問い合わせの条件 4 を参照。Tier 1 の流れ（`lightweight spec → human approval → ...`）→ `lightweight spec → spec review → ...`。
- `core.md` の unfreeze（`requires explicit unfreeze: human approval`）→ spec レビューの `APPROVE` で凍結し直す。ただし問い合わせの条件 1・2 に当たれば人間の承認。`explicit unfreeze` の語は残す（既存テスト）。
- `issue-intake.md` の Always: Tier ラベルがなければ最初の質問で聞く。「At every phase boundary: commit → sync → stop」→ 停止しない。Tier 1・2 の流れの「human approval」→ spec review。
- `subagents.md` の表: `spec-reviewer` を足す（purpose: approve spec artifacts before freeze; permissions: read-only, no edits）。`planner` の「human approves」→「spec-reviewer approves」。When to spawn に「Every freeze → spec-reviewer」を足す。

## テストの方針

新しいテストファイル `tests/test_ai_autonomy.py` に置く。文言の検査なので、各テストは「必須の語句がある」「禁止の語句がない」を見る。禁止の語句の一覧はモジュールの定数にして T1・T3 で共有する:

```python
OLD_STOP_PHRASES = [
    "Phase stopping rule",
    "wait for explicit human instruction",
    "Never cross a phase boundary automatically",
    "same session as freeze",
    "Human approves before freezing",
    "human approval before freezing",
    "after human approval",
    "Wait for a human to escalate",
    "Do NOT start implementing",
    "Do NOT start verify",
    "人間の承認のあと",
    "人間承認を得る",
    "同一セッション",
    "人間から「実装して」",
    "sdd-board.sh sync → 止まる",
]
```

大文字小文字を区別せずに検査する（`phrase.lower() in text.lower()`）。

## Review Focus

- 旧い停止の指示が 1 か所でも残ると、エージェントはその場所で止まる。禁止の語句の検査は SAC-1・SAC-5 の全ファイルを対象にする（T1・T3）。
- 「explicit human approval」を全部消すと、AC を弱める判断まで AI が進めてしまう。`rules/issue-intake.md` に残っていることを検査する（T1）。
- 「AI はマージしない」が抜けると、PR の作成の後に AI がマージまで進む。`orchestration.md` に `never merge` があることを検査する（T1）。
- spec レビューの記録の例と判定の名前が rules と spec-reviewer の 2 ファイルでずれると、記録が揃わない。両方で `APPROVE`・`CHANGES`・`ESCALATE`・`3 rounds`・`Spec review: APPROVE` を検査する（T2）。
- `update.sh` は `integration/agents/` を丸ごと `.claude/agents/` に写すので、`spec-reviewer.md` が配られることを `update.sh` のテストで確かめる（T4）。
