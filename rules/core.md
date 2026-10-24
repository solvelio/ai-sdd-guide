# SDD Core Rules (agent)

Canonical, always-loaded rules. Terse + imperative. Rationale lives in `docs/` (Japanese).

## Scope
- DESIGN phases (spec, plan, tasks, verify) — superpowers required, any agent. Use superpowers + subagents + hooks.
- IMPLEMENTATION phase — any agent. Follow `specs/<feature>/` as the contract. Do not deviate.

## Always
- Classify every task into a Tier before touching code. See `workflow.md`.
- Tier 1/2: no source edits until the spec is frozen (`specs/<feature>/freeze.json`; Tier 2 also needs `plan.md` and `tasks.md`).
- Every acceptance criterion must map to a test. Tests are mandatory for Tier 1+.
- Every piece of work (Tier 0 included) has an Issue. Name the branch `t<Tier>/<Issue番号>-<名前>`; the Tier, feature (`<Issue番号>-<名前>`) and phase are derived from the branch name and the files under `specs/<feature>/` — there is no state file to maintain. Hooks and CI use the same derivation.
- When stuck (spec wrong or insufficient, blocked), comment the reason on the Issue and STOP. Escalate to a human. Never silently redesign during implementation.
- Tier 2: every Issue AC must appear in `specs/<feature>/traceability.json` before freeze.
  If any Issue AC is untracked, STOP — do not freeze and do not implement.
- Frozen artifacts (`spec.md`, `plan.md`, `tasks.md`, `traceability.json`) are immutable after freeze.
  The only permitted post-freeze edit to `tasks.md` is checkbox state ([ ] → [x]).
  Any other post-freeze change (including `traceability.json`) requires explicit unfreeze: human approval, then re-run `orchestration/tools/sdd-freeze.sh` to recreate `freeze.json`.

## Never
- Never edit source code during spec/plan/tasks phases (only specs/docs).
- Never expand scope beyond the approved tasks. New ideas become a new spec.
- Never disable or bypass SDD hooks or CI to make a change pass.
- Never freeze a spec that has no acceptance criteria.
- Never modify files under `specs/` to fit an implementation.

## The contract for other agents
`specs/<feature>/` is the only thing an implementation agent receives. It must be self-contained
enough to implement with zero design-conversation context.
- `spec.md`  — intent + acceptance criteria
- `plan.md`  — approach + affected files + tradeoffs (Tier 2)
- `tasks.md` — ordered, concrete, tool-agnostic steps + the tests that prove each criterion (Tier 2)
