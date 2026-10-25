#!/usr/bin/env bash
# SDD UserPromptSubmit reminder hook for Codex. Non-blocking context injection.
# Tier and phase come from `sdd_state.py` (branch name t<Tier>/<Issue>-<name> + specs/<feature>/ files).
# Prefers jq for JSON output; falls back to python3.
set -euo pipefail

input="$(cat)"
command -v git >/dev/null 2>&1 && command -v python3 >/dev/null 2>&1 || exit 0

if command -v jq >/dev/null 2>&1; then
  event="$(printf '%s' "$input" | jq -r '.hook_event_name // "UserPromptSubmit"' 2>/dev/null || printf 'UserPromptSubmit')"
else
  event="$(printf '%s' "$input" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('hook_event_name') or 'UserPromptSubmit')" 2>/dev/null || printf 'UserPromptSubmit')"
fi
sdd_state="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/../ci/sdd_state.py"
root="$(git rev-parse --show-toplevel 2>/dev/null)" || exit 0
branch_json="$(python3 "$sdd_state" branch --root "$root" 2>/dev/null)" || exit 0
phase="$(python3 "$sdd_state" phase --root "$root" 2>/dev/null)" || exit 0
tier="$(printf '%s' "$branch_json" | python3 -c "import json,sys; print(json.load(sys.stdin).get('tier', ''))" 2>/dev/null)" || exit 0

[ "$tier" = "0" ] && exit 0
[ -z "$tier" ] || [ -z "$phase" ] && exit 0

if [ "$tier" = "1" ]; then
  case "$phase" in implement|verify) ;; *) exit 0 ;; esac
fi

msg=""
case "$phase" in
  brainstorm)
    msg="SDD reminder: brainstorm phase. Use the superpowers 'brainstorming' skill before drafting the spec; if this agent cannot use it, stop and hand off design work."
    ;;
  spec)
    msg="SDD reminder: spec phase. Capture brainstorm output into specs/<feature>/spec.md with checkable acceptance criteria, then get APPROVE from an independent spec-reviewer (vendor/ai-sdd-guide/integration/prompts/spec-reviewer-prompt.md via spawn_agent) before freezing."
    ;;
  plan|tasks)
    msg="SDD reminder: ${phase} phase. Use the superpowers 'writing-plans' skill; for parallel work consider dispatching parallel agents."
    ;;
  implement)
    msg="SDD reminder: implement phase. Implement only the frozen specs/<feature>/tasks.md; every acceptance criterion must map to a passing test. Do not modify specs/ to fit implementation."
    ;;
  verify)
    msg="SDD reminder: verify phase. Run the sdd-reviewer prompt/subagent against the diff. Review feedback that expands scope must escalate to a new spec, not be silently absorbed."
    ;;
esac

[ -n "$msg" ] || exit 0
if command -v jq >/dev/null 2>&1; then
  jq -cn --arg event "$event" --arg msg "$msg" '{hookSpecificOutput:{hookEventName:$event,additionalContext:$msg}}'
else
  python3 -c "import json,sys; print(json.dumps({'hookSpecificOutput':{'hookEventName':sys.argv[1],'additionalContext':sys.argv[2]}}))" "$event" "$msg"
fi
