# SDD Hooks

Claude Code and Codex hook scripts that enforce SDD workflow rules locally.

## Files

| File | Platform | Type | Purpose |
|---|---|---|---|
| `sdd-guard.sh` | Claude Code | PreToolUse | Blocks source edits before spec is frozen; requires linked worktree |
| `skill-reminder.sh` | Claude Code | PostToolUse | Reminds which superpowers skill belongs to the current SDD phase |
| `codex-sdd-guard.sh` | Codex | PreToolUse | Same as sdd-guard.sh for Codex |
| `codex-skill-reminder.sh` | Codex | UserPromptSubmit | Same as skill-reminder.sh for Codex |

## Worktree requirement

These hooks block source edits when run from the **primary git checkout**.
All feature work must be done inside a **linked git worktree**:

```bash
git worktree add .worktrees/<branch-name> -b <branch-name>
cd .worktrees/<branch-name>
```

Each worktree is on its own branch, so the derived Tier and phase are automatically isolated per feature.

### Why

The Tier and phase are derived from the branch name, so parallel features in one checkout would clash.
By requiring a linked worktree, each feature has its own branch by construction.

## Escape hatch

For maintenance work (updating hooks, debugging, one-off edits):

```bash
SDD_ALLOW_MAIN_WORKTREE=1 <tool>
```

## Codex: trusting hooks after install

After copying hooks to your project's `.codex/` configuration,
Codex requires explicit trust. Run:

```
/hooks
```

inside a Codex session and confirm the hook files listed there.
Re-run `/hooks` whenever you update the hook scripts.

## Dependencies

- `python3` — required: the guard derives the SDD state with `integration/ci/sdd_state.py`
- `jq` (preferred) or `python3` (fallback) — for JSON parsing
- `git` — for worktree detection

Both are checked and installed by `integration/update.sh` if missing.
