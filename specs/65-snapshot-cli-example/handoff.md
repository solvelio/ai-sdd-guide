# Handoff: 65-snapshot-cli-example

## Your scope

Implementation phase only (Tier 1: there is no `plan.md` / `tasks.md`). Do not touch `spec.md` or the verify phase.
If the spec needs changes, stop and escalate to a human.

## Done when

- [ ] `docs/migration.md` meets SAC-1 and SAC-2 in `specs/65-snapshot-cli-example/spec.md`
- [ ] The three tests listed under "テスト" in the spec exist in `tests/test_migration_guide.py`, failed before the doc fix, and pass after it
- [ ] Test suite passes (`pytest tests/`)

## Reference files

- spec:  `specs/65-snapshot-cli-example/spec.md`
- Issues: #65, #68 (the PR closes both)

## If the spec is ambiguous or insufficient

1. Stop immediately.
2. Comment the reason on the Issue.
3. Wait for a human to escalate to Claude before resuming.

## Notes

- Only edit `docs/migration.md` and `tests/test_migration_guide.py`.
- "Consumer Update チェックリスト" is in scope. Leave everything from "部分移行禁止チェックリスト" onward untouched.
- SAC-3: get each CLI's options from `python3 integration/ci/<name>.py --help`; tests must not call `gh` or the network.
