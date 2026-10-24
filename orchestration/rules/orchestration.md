# Orchestration Rules (all agents)

## Scope assignment

All phases are open to any agent with superpowers installed. The human decides which agent handles which phase.

| Phase | Requirement | Notes |
|---|---|---|
| brainstorm / spec / plan / tasks | superpowers required | Any agent (Claude, Codex, Gemini) |
| implement | none | Any agent; human assigns explicitly |
| verify | superpowers required | Use sdd-reviewer (see below) |

## Phase stopping rule

Every agent MUST stop after completing a phase and wait for explicit human instruction before starting the next phase. Never cross a phase boundary automatically.

- Design complete (tasks.md created, `freeze.json` written after human approval): generate handoff.md → commit → `sdd-board.sh sync` → stop. Do NOT start implementing.
- Task implementation complete: commit → `sdd-board.sh sync` → stop. Do NOT start verify.
- Verify complete: report results → commit → `sdd-board.sh sync` → stop.

Update the board by running:
```bash
bash vendor/ai-sdd-guide/orchestration/tools/sdd-board.sh sync
```

`sync` derives the phase from the branch name and `specs/<feature>/` and sets the `Phase`
field of the Issue's card on the GitHub Projects board (`.sdd/board.json`). It only warns
(exit 0) when the network, credentials or config are missing. Push only just before
creating the PR, not at each stop.

If stuck at any point, comment the reason on the Issue and stop.

## Rules for design agents (brainstorm/spec/plan/tasks)

- Use superpowers: brainstorming → writing-plans skills.
- Before generating `handoff.md`, verify the following conditions (using
  `sdd-validate.sh` (see #46) when available, otherwise check manually):
  (a) `specs/<feature>/traceability.json` exists and is schema-valid,
  (b) all Issue ACs are tracked (no untracked entries),
  (c) all out-of-scope/deferred entries have a followup_issue URL.
  If any condition fails, fix `traceability.json` before proceeding — do not generate
  a handoff for an incomplete spec.
- **Issue Diff Summary**: When presenting the frozen spec for human approval, include
  a diff summary comparing the original Issue body to the frozen spec. Explicitly
  document what changed, what was dropped, and why. This is mandatory for Tier 2.
- At end of tasks phase, generate `specs/<feature>/handoff.md` from `orchestration/templates/handoff.md.example`.
- Commit, run `vendor/ai-sdd-guide/orchestration/tools/sdd-board.sh sync`, and stop.

## Rules for implementation agents

- Read `specs/<feature>/handoff.md` before touching any code.
- Implement exactly the tasks in `specs/<feature>/tasks.md`. No more, no less.
- Do NOT modify files under `specs/` (except checking boxes in `tasks.md`) or `orchestration/`.
- When complete, commit, run `vendor/ai-sdd-guide/orchestration/tools/sdd-board.sh sync`, and stop.
- If the spec is wrong, ambiguous, or insufficient:
  1. Stop immediately.
  2. Comment the reason on the Issue.
  3. Do not redesign — wait for a human to escalate.

## Running sdd-reviewer (verify phase)

**Claude Code:** Use the `sdd-reviewer` subagent (`.claude/agents/sdd-reviewer.md`).

**Gemini CLI:** Pass the contents of `vendor/ai-sdd-guide/integration/prompts/sdd-reviewer-prompt.md` to `@generalist`.

**Codex:** Pass the contents of `vendor/ai-sdd-guide/integration/prompts/sdd-reviewer-prompt.md` to `spawn_agent`.

**Independent Reviewer Requirement**:
- No matter which agent performs design/implementation, the verify phase MUST invoke the `sdd-reviewer` subagent.
- `sdd-reviewer` acts as an independent third party, verifying the diff vs spec from a different context than the implementation agent.
- An adversarial review by an independent reviewer is a mandatory step before handoff is complete.
