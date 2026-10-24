import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "integration" / "ci"))
from sdd_state import create_freeze  # noqa: E402


HOOK = ROOT / "integration" / "hooks" / "codex-sdd-guard.sh"
GIT_ENV = {
    **os.environ,
    "GIT_AUTHOR_NAME": "Test User",
    "GIT_AUTHOR_EMAIL": "test@example.invalid",
    "GIT_COMMITTER_NAME": "Test User",
    "GIT_COMMITTER_EMAIL": "test@example.invalid",
}


def _run(command, cwd):
    subprocess.run(command, cwd=cwd, check=True, text=True, env=GIT_ENV)


def _make_repo(tmp_path, branch="t0/1-feature", detach=False):
    repo = tmp_path / "repo"
    repo.mkdir()
    _run(["git", "init"], repo)
    _run(["git", "config", "user.email", "test@example.invalid"], repo)
    _run(["git", "config", "user.name", "Test User"], repo)

    (repo / "src").mkdir()
    (repo / "src" / "app.py").write_text("print('hello')\n")
    _run(["git", "add", "."], repo)
    _run(["git", "commit", "-m", "init"], repo)

    worktree = repo / ".worktrees" / "feature"
    if detach:
        _run(["git", "worktree", "add", "--detach", str(worktree)], repo)
    else:
        _run(["git", "worktree", "add", str(worktree), "-b", branch], repo)
    return repo, worktree


def _freeze(worktree, tier=2, feature="1-feature"):
    spec = worktree / "specs" / feature
    spec.mkdir(parents=True)
    for name in ("spec.md", "plan.md", "tasks.md"):
        (spec / name).write_text("# %s\n- [ ] T1\n" % name)
    (spec / "traceability.json").write_text("{}\n")
    create_freeze(spec, tier, datetime(2026, 1, 1, tzinfo=timezone.utc))
    return spec


def _guard(cwd, payload):
    return subprocess.run(
        ["bash", str(HOOK)],
        cwd=cwd,
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        check=True,
        env=GIT_ENV,
    )


def _deny_reason(result):
    if not result.stdout.strip():
        return ""
    return json.loads(result.stdout)["hookSpecificOutput"].get(
        "permissionDecisionReason", ""
    )


def test_apply_patch_absolute_path_in_linked_worktree_is_allowed_from_primary_cwd(tmp_path):
    repo, worktree = _make_repo(tmp_path)
    patch = f"""*** Begin Patch
*** Update File: {worktree / 'src' / 'app.py'}
@@
-print('hello')
+print('hello from worktree')
*** End Patch
"""

    result = _guard(repo, {"tool_name": "apply_patch", "tool_input": {"patch": patch}})

    assert result.stdout == ""


def test_apply_patch_relative_path_uses_tool_workdir_for_worktree_detection(tmp_path):
    repo, worktree = _make_repo(tmp_path)
    patch = """*** Begin Patch
*** Update File: src/app.py
@@
-print('hello')
+print('hello from worktree')
*** End Patch
"""

    result = _guard(
        repo,
        {
            "tool_name": "apply_patch",
            "tool_input": {"patch": patch, "workdir": str(worktree)},
        },
    )

    assert result.stdout == ""


def test_apply_patch_primary_checkout_source_edit_is_denied(tmp_path):
    repo, _ = _make_repo(tmp_path)
    patch = f"""*** Begin Patch
*** Update File: {repo / 'src' / 'app.py'}
@@
-print('hello')
+print('hello from primary')
*** End Patch
"""

    result = _guard(repo, {"tool_name": "apply_patch", "tool_input": {"patch": patch}})

    assert "source edits are only allowed from a linked git worktree" in _deny_reason(result)


def test_bash_read_with_stderr_redirect_is_not_treated_as_write(tmp_path):
    repo, _ = _make_repo(tmp_path)

    result = _guard(
        repo,
        {
            "tool_name": "Bash",
            "tool_input": {
                "command": f"sed -n '1,120p' {repo / 'src' / 'app.py'} 2>/dev/null || true"
            },
        },
    )

    assert result.stdout == ""


def test_bash_explicit_fd_redirect_write_is_detected(tmp_path):
    repo, _ = _make_repo(tmp_path)

    result = _guard(
        repo,
        {
            "tool_name": "Bash",
            "tool_input": {"command": f"echo x 1> {repo / 'src' / 'app.py'}"},
        },
    )

    assert "source edits are only allowed from a linked git worktree" in _deny_reason(result)


def test_bash_plain_redirect_write_is_detected(tmp_path):
    repo, _ = _make_repo(tmp_path)

    result = _guard(
        repo,
        {
            "tool_name": "Bash",
            "tool_input": {"command": f"echo x > {repo / 'src' / 'app.py'}"},
        },
    )

    assert "source edits are only allowed from a linked git worktree" in _deny_reason(result)


def test_bash_stderr_redirect_to_real_file_is_detected(tmp_path):
    repo, _ = _make_repo(tmp_path)

    result = _guard(
        repo,
        {
            "tool_name": "Bash",
            "tool_input": {"command": f"echo log 2> {repo / 'src' / 'out.py'}"},
        },
    )

    assert "source edits are only allowed from a linked git worktree" in _deny_reason(result)


def test_bash_fd_dup_redirect_is_not_treated_as_write(tmp_path):
    repo, _ = _make_repo(tmp_path)

    result = _guard(
        repo,
        {
            "tool_name": "Bash",
            "tool_input": {"command": f"cat {repo / 'src' / 'app.py'} 2>&1"},
        },
    )

    assert result.stdout == ""


def _wt_patch(worktree):
    patch = f"""*** Begin Patch
*** Update File: {worktree / 'src' / 'app.py'}
@@
-print('hello')
+print('x')
*** End Patch
"""
    return patch


def test_tier0_source_edit_in_linked_worktree_is_allowed(tmp_path):
    repo, worktree = _make_repo(tmp_path, "t0/1-feature")

    result = _guard(repo, {"tool_name": "apply_patch", "tool_input": {"patch": _wt_patch(worktree)}})

    assert result.stdout == ""


def test_unclassified_tier_in_linked_worktree_is_denied(tmp_path):
    repo, worktree = _make_repo(tmp_path, "feature")

    result = _guard(repo, {"tool_name": "apply_patch", "tool_input": {"patch": _wt_patch(worktree)}})

    assert "t<Tier>/<Issue番号>-<名前>" in _deny_reason(result)


def test_tier2_branch_with_valid_freeze_is_allowed(tmp_path):
    repo, worktree = _make_repo(tmp_path, "t2/1-feature")
    _freeze(worktree)

    result = _guard(repo, {"tool_name": "apply_patch", "tool_input": {"patch": _wt_patch(worktree)}})

    assert result.stdout == ""


def test_tier2_branch_without_freeze_is_denied(tmp_path):
    repo, worktree = _make_repo(tmp_path, "t2/1-feature")

    reason = _deny_reason(
        _guard(repo, {"tool_name": "apply_patch", "tool_input": {"patch": _wt_patch(worktree)}})
    )

    assert "freeze.json" in reason
    assert "sdd-freeze.sh" in reason


def test_allow_main_worktree_env_bypasses_guard(tmp_path):
    repo, _ = _make_repo(tmp_path)
    patch = _wt_patch(repo)

    result = subprocess.run(
        ["bash", str(HOOK)],
        cwd=repo,
        input=json.dumps({"tool_name": "apply_patch", "tool_input": {"patch": patch}}),
        text=True,
        capture_output=True,
        check=True,
        env={**GIT_ENV, "SDD_ALLOW_MAIN_WORKTREE": "1"},
    )

    assert result.stdout == ""


def test_relative_path_without_workdir_falls_back_to_invocation_root(tmp_path):
    repo, _ = _make_repo(tmp_path)
    patch = """*** Begin Patch
*** Update File: src/app.py
@@
-print('hello')
+print('relative')
*** End Patch
"""

    result = _guard(repo, {"tool_name": "apply_patch", "tool_input": {"patch": patch}})

    assert "source edits are only allowed from a linked git worktree" in _deny_reason(result)


def test_multi_repo_patch_denies_when_any_root_is_primary_checkout(tmp_path):
    repo, worktree = _make_repo(tmp_path)
    patch = f"""*** Begin Patch
*** Update File: {worktree / 'src' / 'app.py'}
@@
-print('hello')
+print('worktree')
*** Update File: {repo / 'src' / 'app.py'}
@@
-print('hello')
+print('primary')
*** End Patch
"""

    result = _guard(repo, {"tool_name": "apply_patch", "tool_input": {"patch": patch}})

    assert "source edits are only allowed from a linked git worktree" in _deny_reason(result)


def test_copied_hook_without_ci_dir_denies_with_vendor_hint(tmp_path):
    import shutil
    repo, worktree = _make_repo(tmp_path, "t0/1-feature")
    hooks = tmp_path / "copied" / ".codex" / "hooks"
    hooks.mkdir(parents=True)
    shutil.copy(HOOK, hooks / "codex-sdd-guard.sh")
    payload = {"tool_name": "apply_patch", "tool_input": {"patch": _wt_patch(worktree)}}
    r = subprocess.run(["bash", str(hooks / "codex-sdd-guard.sh")], cwd=repo,
                       input=json.dumps(payload), text=True, capture_output=True, env=GIT_ENV)
    assert "vendor/ai-sdd-guide/integration/hooks" in _deny_reason(r)
