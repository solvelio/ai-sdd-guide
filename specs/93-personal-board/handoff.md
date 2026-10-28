# Handoff: 93-personal-board

## Your scope

Implementation phase only (Tier 1: there is no `plan.md` / `tasks.md`). Do not touch `spec.md` or the verify phase.
If the spec needs changes, stop and report the reason to the orchestrating agent.

## Done when

- [ ] SAC-1 to SAC-4 in `specs/93-personal-board/spec.md` are met
- [ ] The two tests under "テスト" exist, failed before the change, and pass after it
- [ ] Test suite passes (`uv run --no-project --with pytest --with jsonschema python -m pytest tests -q`)
- [ ] SAC-2 evidence collected with `gh` (project title, linked repositories, Phase field, open-issue cards vs `gh issue list --state open`) and included in your report

## Reference files

- spec:  `specs/93-personal-board/spec.md`
- Issue: https://github.com/toshikimiyagawa/ai-sdd-guide/issues/93
- `integration/ci/sdd_board.py` (`cmd_init`, `--new`), `tests/test_self_migration.py`, `docs/04-issue-tracker.md`

## If the spec is ambiguous or insufficient

1. Stop immediately.
2. Report the reason to the orchestrating agent.
3. Do not redesign. The orchestrating agent resolves it through spec review, or escalates (`orchestration/rules/orchestration.md` `## Escalation conditions`).

## Notes

- Write the tests first and confirm they fail, then run `bash orchestration/tools/sdd-board.sh init --new --owner toshikimiyagawa` (this creates the Project on GitHub — run it exactly once; if it fails, report instead of retrying blindly), then delete `app_id` from `.sdd/board.json`.
- `test_no_solvelio_urls` must not contain the literal string it searches for (build it, e.g. `"github.com/" + "solvelio/"`), and should scan only tracked files (`git ls-files`), excluding `specs/` and `_dev/`.
- Replace `test_board_json_has_app_id`; do not keep it.
- Commit with messages like `chore(93-personal-board): ...` / `test(93-personal-board): ...`, ending with a blank line and `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. Do not push, open a PR, or run `sdd-board.sh` other than the single `init --new`.
