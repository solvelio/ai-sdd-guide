# Handoff: 83-migration-dead-schema

## Your scope

Implementation phase only (Tier 1: there is no `plan.md` / `tasks.md`). Do not touch `spec.md` or the verify phase.
If the spec needs changes, stop and escalate to a human.

## Done when

- [ ] `docs/migration.md` meets SAC-1 and SAC-2 in `specs/83-migration-dead-schema/spec.md`
- [ ] The two tests listed under "テスト" in the spec exist in `tests/test_migration_guide.py`, failed before the doc change, and pass after it
- [ ] Test suite passes (`pytest tests/`)

## Reference files

- spec:  `specs/83-migration-dead-schema/spec.md`
- Issue: #83

## If the spec is ambiguous or insufficient

1. Stop immediately.
2. Comment the reason on the Issue.
3. Wait for a human to escalate to Claude before resuming.

## Notes

- Only edit `docs/migration.md` (the body of "## 手順 4:" and the two state.json / tasks.json items of "## Consumer Update チェックリスト") and `tests/test_migration_guide.py`.
- Keep the "## 手順 4:" heading text as-is; `test_migration_guide_has_all_sections` checks it. `test_migration_guide_projects_board_section` needs "state.json" / "tasks.json" to still appear somewhere in the doc (the v3 section already has them).
- Write the new 手順 4 body in the same Japanese style as the "## v3:" section. Keep it short.
- SAC-1 test: scan the whole doc for `vendor/ai-sdd-guide/<path>`; skip paths containing `<`; strip a trailing `...` (and trailing punctuation) before checking existence under the repo root.
