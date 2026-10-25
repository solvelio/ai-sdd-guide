#!/usr/bin/env bash
# SDD skill reminder hook for Claude Code. Non-blocking nudge — reminds Claude which superpowers skill belongs to the current SDD phase.
# Tier 0 is skipped (no design overhead). Tier 1 reminds only for implement/verify. Tier 2 reminds across all design phases.
# Tier and phase come from `sdd_state.py` (branch name t<Tier>/<Issue>-<name> + specs/<feature>/ files).
set -euo pipefail

# Drain stdin (tool input); we don't read it.
cat >/dev/null

sdd_state="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/../ci/sdd_state.py"
command -v git >/dev/null 2>&1 && command -v python3 >/dev/null 2>&1 || exit 0
root="$(git rev-parse --show-toplevel 2>/dev/null)" || exit 0
branch_json="$(python3 "$sdd_state" branch --root "$root" 2>/dev/null)" || exit 0
phase="$(python3 "$sdd_state" phase --root "$root" 2>/dev/null)" || exit 0
tier="$(printf '%s' "$branch_json" | python3 -c "import json,sys; print(json.load(sys.stdin).get('tier', ''))" 2>/dev/null)" || exit 0

# Tier 0: trivial work, no skill required.
[ "$tier" = "0" ] && exit 0
[ -z "$tier" ] || [ -z "$phase" ] && exit 0

# Tier 1: skip design-phase reminders; only implement/verify reminders apply.
if [ "$tier" = "1" ]; then
  case "$phase" in implement|verify) ;; *) exit 0 ;; esac
fi

case "$phase" in
  brainstorm)
    echo "SDD reminder: brainstorm phase — invoke skill 'brainstorming' (Skill tool) before drafting the spec." >&2
    ;;
  spec)
    echo "SDD reminder: spec phase — capture brainstorm output into specs/<feature>/spec.md with checkable acceptance criteria. Before freezing, get APPROVE from the 'spec-reviewer' subagent." >&2
    ;;
  plan|tasks)
    echo "SDD reminder: $phase phase — invoke skill 'writing-plans' (Skill tool). For parallelism consider 'dispatching-parallel-agents'." >&2
    ;;
  implement)
    echo "SDD reminder: implement phase — invoke skills 'executing-plans' + 'test-driven-development' + 'systematic-debugging' before editing source." >&2
    ;;
  verify)
    echo "SDD reminder: verify phase — invoke 'verification-before-completion'. Use 'receiving-code-review' for any review feedback; spec-conflicting feedback must escalate, not silently absorb." >&2
    ;;
esac
exit 0
