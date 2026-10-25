# Handoff: 89-ai-autonomy

## Your scope

Implementation phase only. Do not touch `spec.md`, `plan.md`, `traceability.json`, or the verify phase.
In `tasks.md` you may only check boxes (`- [ ]` → `- [x]`).
If the spec needs changes, stop and escalate to a human.

## Done when

- [ ] All tasks in `specs/89-ai-autonomy/tasks.md` are complete (T1–T4 and the SAC test list checked)
- [ ] Every acceptance criterion in `specs/89-ai-autonomy/spec.md` has a passing test
- [ ] Test suite passes (`uv run --no-project --with pytest --with jsonschema python -m pytest tests -q`)

## Reference files

- spec:  `specs/89-ai-autonomy/spec.md` (the content of the new flow: 人間が関わる場面, 自律で進める範囲, spec レビュー, 問い合わせの条件, PR 本文の「AI の判断」)
- plan:  `specs/89-ai-autonomy/plan.md` (where each part goes, `OLD_STOP_PHRASES`, Global Constraints)
- tasks: `specs/89-ai-autonomy/tasks.md`
- Issue: #89

## If the spec is ambiguous or insufficient

1. Stop immediately.
2. Comment the reason on the Issue.
3. Wait for a human to escalate to Claude before resuming.

## Notes

- This feature is developed under the current (old) rules; the new rules take effect only after merge. Do not follow the new flow while implementing it.
- Follow the existing style: `rules/` English, terse, imperative; `docs/` Japanese in the style of the surrounding text. Keep edits minimal outside the passages that carry the old stop/approval instructions.
- Keep every phrase that `tests/test_rules_freeze_verify.py` checks (e.g. `explicit unfreeze`, `explicit human approval`, `STOP — do not freeze and do not implement`, `Independent Reviewer Requirement`, `sdd-board.sh sync`).
- `integration/agents/` is copied wholesale by `integration/update.sh`; no change to `update.sh` is needed.
- The sdd-guard hook blocks non-doc edits until `freeze.json` is valid; it is valid on this branch.
- Commit per task with messages like `docs(89-ai-autonomy): ...` / `test(89-ai-autonomy): ...`, each ending with a blank line and `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. Do not push, open a PR, or run `sdd-board.sh`.
