#!/usr/bin/env bash
set -euo pipefail

INTEGRATION="$(cd "$(dirname "$0")" && pwd)"
PROJECT="${1:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"

log() { printf '[update.sh] %s\n' "$*"; }

# --- Dependency check ---

check_dep() {
  local cmd="$1" brew_pkg="${2:-$1}" apt_pkg="${3:-$1}" dnf_pkg="${4:-$1}"
  command -v "$cmd" >/dev/null 2>&1 && return 0
  log "WARNING: $cmd が見つかりません"
  if command -v brew >/dev/null 2>&1; then
    read -r -p "[update.sh] brew install $brew_pkg を実行しますか？ [y/N] " yn || true
    if [[ "${yn:-N}" =~ ^[Yy]$ ]]; then
      brew install "$brew_pkg" && return 0
    fi
  elif command -v apt-get >/dev/null 2>&1; then
    log "インストール: sudo apt-get install -y $apt_pkg"
    [[ "$cmd" == "gh" ]] && log "  (gh の公式手順: https://cli.github.com/)"
  elif command -v dnf >/dev/null 2>&1; then
    log "インストール: sudo dnf install -y $dnf_pkg"
    [[ "$cmd" == "gh" ]] && log "  (gh の公式手順: https://cli.github.com/)"
  elif command -v yum >/dev/null 2>&1; then
    log "インストール: sudo yum install -y $dnf_pkg"
    [[ "$cmd" == "gh" ]] && log "  (gh の公式手順: https://cli.github.com/)"
  else
    log "インストール手順: https://stedolan.github.io/jq/download/ (jq) / https://cli.github.com/ (gh)"
  fi
  return 1
}

check_dep jq jq jq jq || true
check_dep gh gh gh gh || true

# --- Managed: always overwrite ---

if [[ -d "$INTEGRATION/agents" ]]; then
  mkdir -p "$PROJECT/.claude"
  rm -rf "$PROJECT/.claude/agents"
  cp -r "$INTEGRATION/agents" "$PROJECT/.claude/agents"
  log "updated .claude/agents/"
fi

if [[ -f "$INTEGRATION/ci/sdd-check.yml" ]]; then
  mkdir -p "$PROJECT/.github/workflows"
  cp "$INTEGRATION/ci/sdd-check.yml" "$PROJECT/.github/workflows/sdd-check.yml"
  log "updated .github/workflows/sdd-check.yml"
fi

if [[ -f "$INTEGRATION/ci/sdd-board.yml" ]]; then
  mkdir -p "$PROJECT/.github/workflows"
  cp "$INTEGRATION/ci/sdd-board.yml" "$PROJECT/.github/workflows/sdd-board.yml"
  log "updated .github/workflows/sdd-board.yml"
fi

# --- Protected: create if absent, diff if changed ---

protected=(
  "AGENTS.md:$INTEGRATION/AGENTS.md.example"
  ".claude/settings.json:$INTEGRATION/settings.json.example"
  ".codex/config.toml:$INTEGRATION/codex/config.toml.example"
)

for entry in "${protected[@]}"; do
  rel="${entry%%:*}"
  src="${entry#*:}"
  dest="$PROJECT/$rel"

  if [[ ! -f "$src" ]]; then continue; fi

  if [[ ! -f "$dest" ]]; then
    mkdir -p "$(dirname "$dest")"
    cp "$src" "$dest"
    log "created $rel (was absent)"
  elif ! diff -q "$src" "$dest" >/dev/null 2>&1; then
    log "diff (protected — review manually): $rel"
    diff "$dest" "$src" || true
  fi
done

# --- CLAUDE.md: must be a symlink to AGENTS.md ---

CLAUDE="$PROJECT/CLAUDE.md"
if [[ -L "$CLAUDE" ]]; then
  : # already a symlink — leave it
elif [[ ! -e "$CLAUDE" ]]; then
  ln -s AGENTS.md "$CLAUDE"
  log "created CLAUDE.md → AGENTS.md symlink"
else
  log "WARNING: CLAUDE.md exists but is not a symlink — run: rm CLAUDE.md && ln -s AGENTS.md CLAUDE.md"
fi

log "done"
