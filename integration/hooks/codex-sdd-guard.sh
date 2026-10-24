#!/usr/bin/env bash
# SDD PreToolUse guard for Codex. A nudge, not a wall — CI is the real enforcement.
# Blocks detected source edits unless the branch is Tier 0 or its spec is frozen (freeze.json).
# The decision lives in integration/ci/sdd_state.py (branch name t<Tier>/<Issue>-<name>).
# Prefers jq; falls back to python3.
set -euo pipefail

input="$(cat)"
invocation_root="$(git rev-parse --show-toplevel 2>/dev/null || printf '%s' "${PWD}")"

if command -v jq >/dev/null 2>&1; then
  tool_name="$(printf '%s' "$input" | jq -r '.tool_name // empty' 2>/dev/null || true)"
  command="$(printf '%s' "$input" | jq -r '.tool_input.command // .tool_input.patch // empty' 2>/dev/null || true)"
  tool_workdir="$(printf '%s' "$input" | jq -r '.tool_input.workdir // .tool_input.cwd // .cwd // empty' 2>/dev/null || true)"
else
  tool_name="$(printf '%s' "$input" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('tool_name') or '')" 2>/dev/null || true)"
  command="$(printf '%s' "$input" | python3 -c "import json,sys; d=json.load(sys.stdin); ti=d.get('tool_input',{}); print(ti.get('command') or ti.get('patch') or '')" 2>/dev/null || true)"
  tool_workdir="$(printf '%s' "$input" | python3 -c "import json,sys; d=json.load(sys.stdin); ti=d.get('tool_input',{}); print(ti.get('workdir') or ti.get('cwd') or d.get('cwd') or '')" 2>/dev/null || true)"
fi

base_dir="${tool_workdir:-$invocation_root}"

is_exempt_path() {
  case "$1" in
    ""|*.md|specs/*|*/specs/*|docs/*|*/docs/*|.sdd/*|*/.sdd/*) return 0 ;;
    *) return 1 ;;
  esac
}

print_context() {
  if command -v jq >/dev/null 2>&1; then
    jq -cn --arg msg "$1" '{hookSpecificOutput:{hookEventName:"PreToolUse",additionalContext:$msg}}'
  else
    python3 -c "import json,sys; print(json.dumps({'hookSpecificOutput':{'hookEventName':'PreToolUse','additionalContext':sys.argv[1]}}))" "$1"
  fi
}

deny() {
  if command -v jq >/dev/null 2>&1; then
    jq -cn --arg reason "$1" '{hookSpecificOutput:{hookEventName:"PreToolUse",permissionDecision:"deny",permissionDecisionReason:$reason}}'
  else
    python3 -c "import json,sys; print(json.dumps({'hookSpecificOutput':{'hookEventName':'PreToolUse','permissionDecision':'deny','permissionDecisionReason':sys.argv[1]}}))" "$1"
  fi
}

join_paths() {
  printf '%b' "$1" | sed '/^$/d' | paste -sd ',' - | sed 's/,/, /g'
}

patch_paths() {
  printf '%s\n' "$command" | sed -nE \
    -e 's/^\*\*\* (Add|Update|Delete) File: //p' \
    -e 's/^\*\*\* Move to: //p' \
    -e 's/^\+\+\+ b\///p' \
    -e 's/^--- a\///p' | sed '/^\/dev\/null$/d'
}

bash_paths() {
  printf '%s\n' "$command" | grep -Eo '/?([A-Za-z0-9_.@+-]+/)*[A-Za-z0-9_.@+-]+\.(c|cc|cpp|css|go|h|hpp|html|java|js|json|jsx|php|py|rb|rs|scss|sh|tf|toml|ts|tsx|yaml|yml)' || true
}

looks_like_write_bash() {
  printf '%s' "$command" | grep -Eq '(apply_patch|\bsed\b[^\n]*[[:space:]]-i|\bperl\b[^\n]*[[:space:]]-pi|\b(rm|mv|cp|touch)\b)' && return 0
  # A redirect to a real file is a write. Strip /dev/null targets and fd dups
  # (2>&1, >&2) first so reads like `sed ... 2>/dev/null` are not flagged.
  local redir
  redir="$(printf '%s' "$command" | sed -E 's#[0-9]*>>?[[:space:]]*/dev/null##g; s#&>>?[[:space:]]*/dev/null##g; s#[0-9]*>&[0-9-]*##g')"
  printf '%s' "$redir" | grep -Eq '>>?'
}

resolve_path() {
  case "$1" in
    /*) printf '%s\n' "$1" ;;
    *) printf '%s/%s\n' "$base_dir" "$1" ;;
  esac
}

existing_parent() {
  local target="$1" dir
  if [ -d "$target" ]; then
    dir="$target"
  else
    dir="$(dirname "$target")"
  fi
  while [ ! -d "$dir" ] && [ "$dir" != "/" ]; do
    dir="$(dirname "$dir")"
  done
  printf '%s\n' "$dir"
}

repo_root_for_path() {
  local path dir
  path="$(resolve_path "$1")"
  dir="$(existing_parent "$path")"
  git -C "$dir" rev-parse --show-toplevel 2>/dev/null || printf '%s\n' "$invocation_root"
}

git_abs_path() {
  local root="$1" git_path="$2"
  case "$git_path" in
    /*) printf '%s\n' "$git_path" ;;
    *) printf '%s/%s\n' "$root" "$git_path" ;;
  esac
}

paths=""
case "$tool_name" in
  apply_patch)
    paths="$(patch_paths | sort -u)"
    ;;
  Bash)
    if printf '%s' "$command" | grep -q 'apply_patch'; then
      paths="$(patch_paths | sort -u)"
    elif looks_like_write_bash; then
      paths="$(bash_paths | sort -u)"
    else
      exit 0
    fi
    ;;
  *)
    exit 0
    ;;
esac

non_exempt=""
while IFS= read -r path; do
  [ -n "$path" ] || continue
  if ! is_exempt_path "$path"; then
    non_exempt="${non_exempt}${path}\n"
  fi
done <<EOF
$paths
EOF

if [ -z "$non_exempt" ]; then
  if [ -z "$paths" ] && [ "$tool_name" = "Bash" ] && looks_like_write_bash; then
    print_context "SDD reminder: this Bash command appears to write files. If it edits source, ensure the branch is t<Tier>/<Issue番号>-<名前> and the spec is frozen (vendor/ai-sdd-guide/orchestration/tools/sdd-freeze.sh)."
  fi
  exit 0
fi

roots=""
while IFS= read -r path; do
  [ -n "$path" ] || continue
  roots="${roots}$(repo_root_for_path "$path")\n"
done <<EOF
$(printf '%b' "$non_exempt")
EOF
roots="$(printf '%b' "$roots" | sed '/^$/d' | sort -u)"

# Block source edits from the primary checkout; linked worktrees only.
if [ "${SDD_ALLOW_MAIN_WORKTREE:-}" != "1" ]; then
  while IFS= read -r check_root; do
    [ -n "$check_root" ] || continue
    if git -C "$check_root" rev-parse --git-dir >/dev/null 2>&1; then
      _git_dir="$(git_abs_path "$check_root" "$(git -C "$check_root" rev-parse --git-dir)")"
      _git_common="$(git_abs_path "$check_root" "$(git -C "$check_root" rev-parse --git-common-dir)")"
      _git_dir="$(cd "$_git_dir" && pwd -P)"
      _git_common="$(cd "$_git_common" && pwd -P)"
      _superproject="$(git -C "$check_root" rev-parse --show-superproject-working-tree 2>/dev/null || true)"
      if [ "$_git_dir" = "$_git_common" ] && [ -z "$_superproject" ]; then
        deny "SDD: source edits are only allowed from a linked git worktree. Create one with: git worktree add .worktrees/<branch> -b <branch>. For maintenance, set SDD_ALLOW_MAIN_WORKTREE=1."
        exit 0
      fi
    fi
  done <<EOF
$roots
EOF
fi

# Maintenance escape hatch: skip the branch/freeze decision as well.
[ "${SDD_ALLOW_MAIN_WORKTREE:-}" = "1" ] && exit 0

if ! command -v python3 >/dev/null 2>&1; then
  deny "SDD: python3 not found, cannot check the frozen spec state. Install python3. Detected source path(s): $(join_paths "$non_exempt")"
  exit 0
fi

sdd_state="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/../ci/sdd_state.py"
if [ ! -f "$sdd_state" ]; then
  deny "SDD: guard の判定スクリプト (../ci/sdd_state.py) が見つかりません。hook をコピーして使っていませんか。hook は vendor/ai-sdd-guide/integration/hooks/codex-sdd-guard.sh を直接指し、コピーした hook は削除してください。"
  exit 0
fi
while IFS= read -r check_root; do
  [ -n "$check_root" ] || continue
  if ! reason="$(python3 "$sdd_state" guard --root "$check_root" 2>&1)"; then
    deny "SDD: source edits are blocked. ${reason} Detected source path(s): $(join_paths "$non_exempt")"
    exit 0
  fi
done <<EOF
$roots
EOF

exit 0
