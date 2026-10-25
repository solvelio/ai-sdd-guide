# Handoff: 84-readme-board-setup

## Your scope

Implementation phase only (Tier 1: there is no `plan.md` / `tasks.md`). Do not touch `spec.md` or the verify phase.
If the spec needs changes, stop and escalate to a human.

## Done when

- [ ] `README.md` meets SAC-1 and SAC-2 in `specs/84-readme-board-setup/spec.md`
- [ ] The three tests listed under "テスト" in the spec exist in `tests/test_readme_install.py`, failed before the README change, and pass after it
- [ ] Test suite passes (`pytest tests/`)

## Reference files

- spec:  `specs/84-readme-board-setup/spec.md`
- Issue: #84

## If the spec is ambiguous or insufficient

1. Stop immediately.
2. Comment the reason on the Issue.
3. Wait for a human to escalate to Claude before resuming.

## Notes

- Only edit `README.md` (the "導入手順（取り込み側プロジェクト）" section) and create `tests/test_readme_install.py`.
- Facts to state accurately: `integration/update.sh` copies `integration/ci/sdd-check.yml` and `integration/ci/sdd-board.yml`; without `.sdd/board.json`, `sdd-board.sh sync` and the workflow's board steps only warn and skip; the "Add tier label to PR" step in `sdd-board.yml` runs regardless of the board.
- SAC-3: derive the update.sh set from its `cp "$INTEGRATION/ci/<file>.yml"` lines, and the README set from `cp vendor/ai-sdd-guide/integration/ci/<file>.yml .github/workflows/` lines inside the 導入手順 section; tests must not call `gh` or the network.
