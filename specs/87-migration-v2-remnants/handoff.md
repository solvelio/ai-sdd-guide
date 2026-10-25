# Handoff: 87-migration-v2-remnants

## Your scope

Implementation phase only (Tier 1: there is no `plan.md` / `tasks.md`). Do not touch `spec.md` or the verify phase.
If the spec needs changes, stop and escalate to a human.

## Done when

- [ ] `docs/migration.md` meets SAC-1 to SAC-4 in `specs/87-migration-v2-remnants/spec.md`
- [ ] The four tests listed under "テスト" in the spec exist in `tests/test_migration_guide.py`, failed before the doc change, and pass after it
- [ ] Test suite passes (`uv run --no-project --with pytest --with jsonschema python -m pytest tests -q`)

## Reference files

- spec:  `specs/87-migration-v2-remnants/spec.md`
- Issue: #87
- `integration/ci/sdd-check.yml` (actual CI steps), `integration/ci/sdd-validate.py` `main()` (what the validator checks)
- `integration/prompts/sdd-reviewer-prompt.md` (items 3 "Name Consistency" and 4 "Freeze Validity")
- `orchestration/schema/` (existing schemas)

## If the spec is ambiguous or insufficient

1. Stop immediately.
2. Comment the reason on the Issue.
3. Wait for a human to escalate to Claude before resuming.

## Notes

- Only edit the five places listed under "スコープ" in the spec and `tests/test_migration_guide.py`. Leave "影響範囲", "v3", "v3.1" and `--feature ...` examples alone.
- `test_migration_guide_projects_board_section` needs "state.json" / "tasks.json" to still appear somewhere in the doc (the v3 section has them). Existing tests in the file must keep passing.
- Section bodies: reuse the existing `_section_body(text, heading)` helper. "具体例" is `## 具体例`; the partial-migration checklist is `## 部分移行禁止チェックリスト`.
- SAC-2 test: read step names from `integration/ci/sdd-check.yml` (`- name:` values) rather than hard-coding them.
- SAC-4 test: parse schema names from the `orchestration/schema/` checklist line and compare with `orchestration/schema/*.schema.json` as a set.
- Write in the same Japanese style as the surrounding doc. Keep it short.
