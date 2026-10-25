# Subagent Rules (Claude Code)

Use subagents to protect the main context and to get independent judgment.
In "When to spawn" situations below, spawning a subagent is mandatory, not optional.
Implementation by external agents does not use these.

## Roles
| Role | Purpose | Permissions |
|---|---|---|
| researcher | Explore the codebase / prior art; return findings | read-only, no edits |
| planner | Draft `plan.md` / `tasks.md` from a spec | edits draft, spec-reviewer approves |
| spec-reviewer | Approve spec artifacts before freeze (`APPROVE` / `CHANGES` / `ESCALATE`) | read-only, no edits |
| sdd-reviewer | Verify an implementation conforms to the frozen spec | read + run tests, no fixes |

## When to spawn
- Codebase exploration spanning more than ~3 lookups → researcher.
- Tier 2 planning → planner (optional).
- Every freeze → spec-reviewer (independent of the agent that wrote the spec; see `## Spec review` in `orchestration/rules/orchestration.md`).
- Every implementation after freeze → a fresh agent context given only the frozen artifacts and `handoff.md`.
- Every verify phase → sdd-reviewer (independent read of the diff vs spec).

## Contract
- Give each subagent the spec path + a self-contained brief; it has no conversation context.
- Subagents must never freeze specs or disable checks.

superpowers may provide additional design-phase subagent patterns; prefer them where they fit.
