# Issue Intake Rules (all agents)

How an issue tracker feeds the SDD workflow. Works the same on GitHub, GitLab, Bitbucket,
and Azure DevOps — only the label, dependency-link, and PR-link mechanisms differ.

## Status source of truth

SDD status is derived from the branch name `t<Tier>/<Issue番号>-<名前>` and the files under
`specs/<feature>/` (`python3 vendor/ai-sdd-guide/integration/ci/sdd_state.py phase`). The board
only displays it: GitHub Projects (one board per account, one card per Issue, single-select
field `Phase`: backlog → brainstorm → spec → plan → tasks → implement → verify → done),
configured in `.sdd/board.json` and updated with `vendor/ai-sdd-guide/orchestration/tools/sdd-board.sh` and
`integration/ci/sdd-board.yml`. GitLab and Azure DevOps boards are tracked in #71 and #72;
Bitbucket is out of scope (its Issues are being sunset).

## Always

- Do not start design or implementation until the issue carries a human-assigned
  `sdd:tier-{0,1,2}` label. The human owns the Tier decision. If it is missing, ask for it
  and stop.
- Every piece of work needs an Issue, Tier 0 included. On starting an issue, create the
  branch `t<Tier>/<Issue番号>-<名前>` (spec directory `specs/<Issue番号>-<名前>/`). At every
  phase boundary: commit → `vendor/ai-sdd-guide/orchestration/tools/sdd-board.sh sync` → stop — this is the
  orchestration stop rule (`orchestration/rules/orchestration.md`).
- If stuck, comment the reason on the Issue and stop.
- Run the Tier-appropriate flow (see `rules/workflow.md`):
  - Tier 0 — implement → PR (still with an Issue and a `t0/` branch).
  - Tier 1 — lightweight spec → human approval → `vendor/ai-sdd-guide/orchestration/tools/sdd-freeze.sh` (freezes `spec.md`) → `handoff.md` → implement → PR. CI requires `freeze.json` and `handoff.md` on Tier 1 PRs.
  - Tier 2 — spec → plan → tasks → implement → verify → PR.
- Link the PR back to the issue so merging closes it: `closes #N` (GitHub / GitLab /
  Bitbucket) or `AB#N` (Azure DevOps).
- Carry the matching `sdd:tier-{0,1,2}` label onto the PR (`rules/conventions.md`).

## Tier 2 freeze gate (check before running `sdd-freeze.sh`)

- Assign a stable ID to every Issue AC using the `<issue番号>-AC<連番>` format
  defined in `docs/traceability.md`. IDs are assigned in order of appearance;
  no edit to the Issue body is required.
- Create `specs/<feature>/traceability.json` mapping each Issue AC to a spec AC,
  task, and test. See `orchestration/schema/traceability.schema.json` for the schema.
- Every Issue AC must appear in an entry. If any AC is untracked, freeze is blocked.
- Entries with status `out-of-scope` or `deferred` must have a non-empty `reason`
  and an HTTP(S) `followup_issue` URL. No orphaned scope-outs allowed.
- If the frozen spec is weaker than the Issue (criteria removed or softened),
  surface a diff summary and obtain explicit human approval before freezing.

## Never

- Never implement an unlabeled issue — escalate for a Tier first.
- Never treat a board as the status source of truth; status is derived from the branch name and `specs/`.
- Never expand scope beyond the issue. New scope is a new issue + a new spec.
- Never freeze a Tier 2 spec that has untracked Issue ACs or out-of-scope entries
  without a followup_issue URL.

## Per-platform mechanisms

| Concern | GitHub | GitLab | Bitbucket | Azure DevOps |
|---|---|---|---|---|
| Tier label | Labels | Labels | Labels | Tags / Area |
| Issue dependencies | Relationships (blocks / blocked by) | Linked issues | Linked issues | Links (Predecessor / Successor) |
| PR ↔ issue link | `closes #N` | `closes #N` | `closes #N` | `AB#N` |
| Status board | Projects v2 (implemented) | Boards (#71) | out of scope | Boards (#72) |

Setup examples (label creation, per-platform notes): `integration/issue-tracker/`.
