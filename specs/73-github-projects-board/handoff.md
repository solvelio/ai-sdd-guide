# Handoff: 73-github-projects-board

## Your scope

Implementation phase only. Do not touch `spec.md`, `plan.md`, `traceability.json`, or the verify phase.
The only permitted edit to `tasks.md` is checkbox state ([ ] → [x]).
If the spec needs changes, stop and escalate to a human.

## Done when

- [ ] All tasks in `specs/73-github-projects-board/tasks.md` are complete
- [ ] Every acceptance criterion in `specs/73-github-projects-board/spec.md` has a passing test
- [ ] Test suite passes (`python -m pytest tests/ -q`)

## Reference files

- spec:  `specs/73-github-projects-board/spec.md`
- plan:  `specs/73-github-projects-board/plan.md`
- tasks: `specs/73-github-projects-board/tasks.md`
- design (rationale): `_dev/specs/2026-10-24-github-projects-board-design.md`

## Notes

- This repository still runs on the current system (`.sdd/state.json`) until T10 migrates it.
- T10 Step 3 requires human approval before creating the real GitHub Project and registering the secret.

## If the spec is ambiguous or insufficient

1. Stop immediately.
2. Set `.sdd/tasks.json` status to `"blocked"`.
3. Fill in `blocked_reason`.
4. Wait for a human to escalate to Claude before resuming.
