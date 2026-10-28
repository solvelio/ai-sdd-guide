# Handoff: 91-per-repo-board

## Your scope

Implementation phase only (Tier 1: there is no `plan.md` / `tasks.md`). Do not touch `spec.md` or the verify phase.
If the spec needs changes, stop and report the reason to the orchestrating agent.

## Done when

- [ ] `integration/ci/sdd_board.py` and the docs meet SAC-1 to SAC-4 in `specs/91-per-repo-board/spec.md`
- [ ] The tests listed under "テスト" in the spec exist, failed before the change, and pass after it
- [ ] Test suite passes (`uv run --no-project --with pytest --with jsonschema python -m pytest tests -q`)

## Reference files

- spec:  `specs/91-per-repo-board/spec.md`
- Issue: #91
- `integration/ci/sdd_board.py` (`cmd_init`, `main`), `tests/test_sdd_board.py` (existing init tests, `Env`, `base_responses`), `tests/fake_gh.py`

## If the spec is ambiguous or insufficient

1. Stop immediately.
2. Report the reason to the orchestrating agent.
3. Do not redesign. The orchestrating agent resolves it through spec review, or escalates (`orchestration/rules/orchestration.md` `## Escalation conditions`).

## Notes

- Existing init tests (`test_init_creates_project_field_and_board_json`, `test_init_with_existing_board_json_does_not_create`, `test_init_preserves_existing_keys`, `test_init_failure_hints_project_scope`, etc.) will need fake responses for `repo view` and `project link`; update them without weakening their assertions.
- `fake_gh` answers by command prefix and can return a non-zero code (see `test_init_failure_exits_1`).
- Keep phrases other tests check: README must still satisfy `tests/test_readme_install.py` (e.g. `.sdd/board.json`, `sdd-board.sh init`, auth options); `docs/migration.md` must still satisfy `tests/test_migration_guide.py`.
- Docs are Japanese in the surrounding style; `rules/` is English, terse.
- Commit with messages like `feat(91-per-repo-board): ...` / `docs(91-per-repo-board): ...`, each ending with a blank line and `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. Do not push, open a PR, or run `sdd-board.sh`.
