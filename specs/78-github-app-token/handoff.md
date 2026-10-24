# Handoff: 78-github-app-token

## Your scope

Implementation phase only. Do not touch `spec.md`, `plan.md`, or the verify phase.
If the spec needs changes, stop and escalate to a human.

## Done when

- [ ] All tasks in `specs/78-github-app-token/tasks.md` are complete
- [ ] Every acceptance criterion in `specs/78-github-app-token/spec.md` has a passing test
- [ ] Test suite passes

## Reference files

- spec:  `specs/78-github-app-token/spec.md`
- plan:  `specs/78-github-app-token/plan.md`
- tasks: `specs/78-github-app-token/tasks.md`

## If the spec is ambiguous or insufficient

1. Stop immediately.
2. Comment the reason on the Issue.
3. Wait for a human to escalate to Claude before resuming.

## Notes

- T5 Step 4 requires the human: create the App private key, store it in 1Password, and run `sdd-app-secret.sh` on the Mac. Stop there and ask.
- Tests must never call the real `gh`, `op`, or the network.
