# Orchestration Rules (all agents)

## Scope assignment

All phases are open to any agent with superpowers installed. The orchestrating agent runs all phases, dispatching independent agents (subagents) where required; a human may assign a specific agent.

| Phase | Requirement | Notes |
|---|---|---|
| brainstorm / spec / plan / tasks | superpowers required | Any agent (Claude, Codex, Gemini) |
| implement | none | Any agent; a fresh agent context (see Autonomous flow) |
| verify | superpowers required | Use sdd-reviewer (see below) |

## Human touchpoints

Humans take part only at these three points. Resolve everything else with independent agents and carry the work through to the PR.

1. **Initial question**: Read the Issue and the relevant code, then ask the human in one message:
   - a Tier proposal with reasons;
   - only those spec unknowns whose answer changes what gets built. Decide the rest yourself and record each decision for the PR decision log.

   Apply the `sdd:tier-N` label from the answer. The human owns the Tier decision.
   Skip the question when the Issue already carries an `sdd:tier-N` label and there are no spec unknowns.
2. **Escalation**: only under `## Escalation conditions`.
3. **PR review and merge**: Never merge. The human reviews, approves and merges the PR.

## Autonomous flow

After the initial question is answered, run these steps in order without stopping between phases:

1. Create the branch `t<Tier>/<Issue番号>-<名前>`.
2. (Tier 2) Design: use the `brainstorming` skill without human dialogue, from the Issue and the initial answer.
3. Write the spec. Tier 2 also writes `plan.md`, `tasks.md` and `traceability.json`.
4. Spec review: obtain `APPROVE` from `spec-reviewer` (see `## Spec review`).
5. Freeze (`sdd-freeze.sh`) and write `handoff.md`.
6. Implement in a fresh agent context that receives only the frozen artifacts and `handoff.md`. Never implement in the same agent context that froze the spec.
7. Verify: `sdd-reviewer` checks the implementation. Handle findings with the `receiving-code-review` discipline.
8. Push and create the PR, with the PR decision log in its body.
9. Check the CI results and report to the human.

At every phase boundary, commit and run:
```bash
bash vendor/ai-sdd-guide/orchestration/tools/sdd-board.sh sync
```
Then continue; do not stop.

`sync` derives the phase from the branch name and `specs/<feature>/` and sets the `Phase`
field of the Issue's card on the GitHub Projects board (`.sdd/board.json`). It only warns
(exit 0) when the network, credentials or config are missing. Push only just before
creating the PR, not at each phase boundary.

Where no independent agent can be started, escalate spec review and verify to the human (`## Escalation conditions` 6).

## Spec review

**Who**: an independent agent that did not write the spec.
- Claude Code: the `spec-reviewer` subagent (`.claude/agents/spec-reviewer.md`).
- Other agents: pass `vendor/ai-sdd-guide/integration/prompts/spec-reviewer-prompt.md` (see `## Running spec-reviewer`).

**When**: once, just before freeze. Tier 1 reviews `spec.md`. Tier 2 reviews `spec.md`, `plan.md`, `tasks.md` and `traceability.json` together.

**Checks**:
- Every AC in the Issue body (Tier 2: `issue-snapshot.json`) maps to a spec AC and is not dropped or weakened.
- The answers to the initial question are reflected.
- Every spec AC is a checkable statement that maps to a test.
- The scope does not exceed the Issue.
- Tier 2: `plan.md`, `tasks.md` and `traceability.json` do not contradict the spec, and every AC has a task and a test.

**Verdicts**:

| Verdict | Meaning | Next |
|---|---|---|
| `APPROVE` | Ready to freeze | Freeze |
| `CHANGES` | Fixes needed (list returned) | The author fixes them and requests another review |
| `ESCALATE` | An escalation condition applies | Escalate to the human |

Limit: 3 rounds. If the third review is not `APPROVE`, escalate to the human.

**Record**: write the verdict and round count in the freeze commit message (e.g. `Spec review: APPROVE (2 rounds)`) and in the PR decision log.

**Changing a spec after freeze**: re-freeze after a new spec review `APPROVE`; no human approval is needed. If the change falls under `## Escalation conditions` 1 or 2, escalate to the human.

## Escalation conditions

Escalate to the human only when one of these applies:

1. An Issue AC must be dropped, weakened, or moved out of scope. This includes every case where an existing rule requires explicit human approval (Tier 2: a spec weaker than the Issue).
2. A decision would contradict the Issue body or the answer to the initial question.
3. Spec review returned `ESCALATE`, or did not reach `APPROVE` within 3 rounds.
4. Review feedback conflicts with the frozen spec and cannot be resolved by changing the spec without hitting condition 1 or 2.
5. An irreversible operation, or one that affects anything outside the repository, is required. Pushing the work branch and creating the PR are excluded. Examples: force push, changes to another repository, secret or settings changes, data deletion.
6. Missing permissions or credentials block progress.

How to escalate:
- If the human is present in the conversation, ask there and wait for the answer.
- Otherwise, comment the reason on the Issue and stop.

## PR decision log

Give the PR body a `## AI の判断` section so the human can check the AI's decisions during PR review. List:
- the spec review verdict and round count;
- decisions the AI made on spec unknowns, with reasons;
- verify and review findings adopted or rejected, with reasons;
- items moved out of scope, with their follow-up Issues.

Template: `templates/pr-body.md` (from a consumer: `vendor/ai-sdd-guide/templates/pr-body.md`).

## Rules for design agents (brainstorm/spec/plan/tasks)

- Use superpowers: brainstorming → writing-plans skills, without human dialogue beyond the initial question.
- Before generating `handoff.md`, verify the following conditions (using
  `sdd-validate.sh` (see #46) when available, otherwise check manually):
  (a) `specs/<feature>/traceability.json` exists and is schema-valid,
  (b) all Issue ACs are tracked (no untracked entries),
  (c) all out-of-scope/deferred entries have a followup_issue URL.
  If any condition fails, fix `traceability.json` before proceeding — do not generate
  a handoff for an incomplete spec.
- **Issue Diff Summary**: Pass the spec reviewer a diff summary comparing the
  original Issue body to the frozen spec, and carry it into the PR decision log. Explicitly
  document what changed, what was dropped, and why. This is mandatory for Tier 2. The
  frozen spec must not be weaker than the Issue unless the human approved it
  (`## Escalation conditions` 1).
- At end of tasks phase, generate `specs/<feature>/handoff.md` from `orchestration/templates/handoff.md.example`.
- Commit, run `vendor/ai-sdd-guide/orchestration/tools/sdd-board.sh sync`, and continue to spec review.

## Rules for implementation agents

- Read `specs/<feature>/handoff.md` before touching any code.
- Implement exactly the tasks in `specs/<feature>/tasks.md`. No more, no less.
- Do NOT modify files under `specs/` (except checking boxes in `tasks.md`) or `orchestration/`.
- When complete, commit, run `vendor/ai-sdd-guide/orchestration/tools/sdd-board.sh sync`, and report back to the orchestrating agent.
- If the spec is wrong, ambiguous, or insufficient:
  1. Stop immediately.
  2. Report the reason to the orchestrating agent.
  3. Do not redesign. The orchestrating agent resolves it through spec review, or escalates (`## Escalation conditions`).

## Running spec-reviewer (before freeze)

**Claude Code:** Use the `spec-reviewer` subagent (`.claude/agents/spec-reviewer.md`).

**Gemini CLI:** Pass the contents of `vendor/ai-sdd-guide/integration/prompts/spec-reviewer-prompt.md` to `@generalist`.

**Codex:** Pass the contents of `vendor/ai-sdd-guide/integration/prompts/spec-reviewer-prompt.md` to `spawn_agent`.

Never let the agent that wrote the spec review it.

## Running sdd-reviewer (verify phase)

**Claude Code:** Use the `sdd-reviewer` subagent (`.claude/agents/sdd-reviewer.md`).

**Gemini CLI:** Pass the contents of `vendor/ai-sdd-guide/integration/prompts/sdd-reviewer-prompt.md` to `@generalist`.

**Codex:** Pass the contents of `vendor/ai-sdd-guide/integration/prompts/sdd-reviewer-prompt.md` to `spawn_agent`.

**Independent Reviewer Requirement**:
- No matter which agent performs design/implementation, the verify phase MUST invoke the `sdd-reviewer` subagent.
- `sdd-reviewer` acts as an independent third party, verifying the diff vs spec from a different context than the implementation agent.
- An adversarial review by an independent reviewer is a mandatory step before handoff is complete.
