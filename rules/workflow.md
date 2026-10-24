# SDD Workflow Rules (agent)

## Step 0 — classify Tier (always first)
- Tier 0 — trivial (typo, comment, docs-only, formatting): implement directly. No artifacts.
- Tier 1 — small (localized bugfix, small change): lightweight spec (intent + acceptance criteria) + tests. Skip plan/tasks.
- Tier 2 — medium/large (new feature, multi-file, design change, public API): full flow below.
- When unsure, pick the higher Tier.
- Every piece of work has an Issue, Tier 0 included. The Tier is encoded in the branch name `t<Tier>/<Issue番号>-<名前>` (e.g. `t2/73-github-projects-board`); the PR label `sdd:tier-{0,1,2}` must match it.
- State is derived, never recorded: Tier, feature (`<Issue番号>-<名前>`) and phase come from the branch name plus the files under `specs/<feature>/`. Phases, in order: `backlog`, `brainstorm`, `spec`, `plan`, `tasks`, `implement`, `verify`, `done`. Show the derived phase with `python3 vendor/ai-sdd-guide/integration/ci/sdd_state.py phase`.

## Design phases (superpowers required)
Drive these with superpowers skills (requires the superpowers plugin).
Capture each skill's output into the portable `specs/<feature>/` artifacts.

1. Brainstorm — skill `brainstorming`. Clarify intent with the human, explore alternatives. Output: an agreed design.
2. Spec — write `specs/<feature>/spec.md` from the agreed design. Acceptance criteria as checkable statements. Get human approval.
   - If `.sdd/catalog.json` exists: register new catalog entries as `planned` in `docs/design/` (see `catalog/rules/catalog.md`). Update to `confirmed` in the verify phase.
3. Plan & Tasks — skill `writing-plans` (bite-sized ordered steps). Capture into `plan.md` (approach, affected files, tradeoffs, alternatives) and `tasks.md` (concrete steps + the test proving each acceptance criterion). (Tier 2)
3b. Traceability — Before freezing, complete `specs/<feature>/traceability.json`
   (schema: `orchestration/schema/traceability.schema.json`). Verify the following
   conditions (using `sdd-validate.sh` (see #46) when available, otherwise check
   manually): all Issue ACs are tracked, no orphaned out-of-scope entries exist.
   When presenting for human approval, include a diff summary of Issue ACs vs
   frozen spec ACs — not just the design body.
4. Freeze — after human approval, run `orchestration/tools/sdd-freeze.sh`; it writes `specs/<feature>/freeze.json` (target files + hashes). This is the handoff gate to other agents. To redo a freeze, get human approval again and re-run the command.
   STOP. Do not begin implementation in the same session as freeze.
   Wait for an explicit instruction to implement before proceeding.

For exploration/parallelism use skills `dispatching-parallel-agents` / `subagent-driven-development`. See `subagents.md`.

## Implementation phase (any agent)
- Read `specs/<feature>/`. Implement exactly the frozen tasks — no more, no less.
- Map every acceptance criterion to a passing test.
- When Claude implements: use skills `executing-plans` + `test-driven-development` (RED-GREEN-REFACTOR) + `systematic-debugging`. Other agents follow `tasks.md` directly.
- If the spec is wrong, ambiguous, or insufficient: STOP and escalate. Do not redesign.
- When implementation is complete: check every box in `tasks.md` (Tier 2); the phase becomes `verify` automatically. Commit, then run `orchestration/tools/sdd-board.sh sync` and stop (see `orchestration/rules/orchestration.md`).

## Verify phase (superpowers required)
- Skill `verification-before-completion`. Run tests; spawn the `sdd-reviewer` subagent to check conformance to the frozen spec.
- The sdd-reviewer must also verify (in addition to spec conformance):
  1. Every Issue AC appears in traceability.json and is tracked to a spec AC.
  2. Every out-of-scope/deferred entry has a followup_issue URL.
  3. The branch name (`t<Tier>/<Issue番号>-<名前>`), the `specs/` directory name and the Issue number in `issue-snapshot.json` all agree.
  4. `freeze.json` is valid (`sdd_state.py phase` does not error) and traceability.json is schema-valid.
  5. All task checkboxes in tasks.md are complete (no unchecked items).
  6. Each AC maps to a runnable test, not a manual/visual check.
- When sdd-reviewer or any code review returns feedback: skill `receiving-code-review`. Evaluate each item against the frozen spec before acting. If feedback conflicts with the frozen spec, STOP and escalate to the human — do not silently redesign. Scope-expanding suggestions become a new spec, not a quiet addition.
- Push only just before creating the PR (not at each phase boundary). The board moves to `done` when the PR is merged.
- Create the PR. If CI is configured, wait for completion and confirm all checks pass and the PR is mergeable before declaring completion. Never declare completion without verifying CI results.
- Optionally `requesting-code-review` / `finishing-a-development-branch`.
- CI is authoritative: it independently re-checks spec presence + tests.

## Tier exemptions
- Tier 0: hooks and CI skip the spec requirement.
- Tier 1: lightweight spec required; plan/tasks skipped.
- Tier 2: nothing skipped.
- Exemptions are declared by the branch name (`t0/`, `t1/`) + the matching PR label, so hooks/CI can verify them.

## Parallel features

To work on multiple features simultaneously, use a separate git worktree per feature.
Each worktree is on its own branch, so the derived Tier and phase are automatically isolated. Use the `superpowers:using-git-worktrees` skill to create the worktree.

Never share a single worktree across two features in progress at the same time.
