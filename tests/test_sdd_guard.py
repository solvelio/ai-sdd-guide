import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "integration" / "ci"))
from sdd_state import create_freeze  # noqa: E402


HOOK = ROOT / "integration" / "hooks" / "sdd-guard.sh"
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


def _guard(cwd, file_path, env=None):
    payload = {"tool_name": "Edit", "tool_input": {"file_path": str(file_path)}, "cwd": str(cwd)}
    run_env = {**GIT_ENV, **(env or {})}
    return subprocess.run(
        ["bash", str(HOOK)],
        cwd=cwd,
        input=json.dumps(payload),
        text=True,
        encoding="utf-8",
        capture_output=True,
        env=run_env,
    )


def test_primary_cwd_edit_into_linked_worktree_is_allowed(tmp_path):
    repo, worktree = _make_repo(tmp_path)

    result = _guard(repo, worktree / "src" / "app.py")

    assert result.returncode == 0


def test_worktree_cwd_edit_into_primary_checkout_is_denied(tmp_path):
    repo, worktree = _make_repo(tmp_path)

    result = _guard(worktree, repo / "src" / "app.py")

    assert result.returncode == 2
    assert "リンク worktree からのみ許可" in result.stderr


def test_edit_in_linked_worktree_is_allowed(tmp_path):
    repo, worktree = _make_repo(tmp_path)

    result = _guard(worktree, worktree / "src" / "app.py")

    assert result.returncode == 0


def test_edit_in_primary_checkout_is_denied(tmp_path):
    repo, _ = _make_repo(tmp_path)

    result = _guard(repo, repo / "src" / "app.py")

    assert result.returncode == 2
    assert "リンク worktree からのみ許可" in result.stderr


def test_tier0_branch_in_linked_worktree_is_allowed(tmp_path):
    repo, worktree = _make_repo(tmp_path, "t0/1-feature")

    result = _guard(worktree, worktree / "src" / "app.py")

    assert result.returncode == 0


def test_tier2_branch_without_freeze_is_denied(tmp_path):
    repo, worktree = _make_repo(tmp_path, "t2/1-feature")

    result = _guard(worktree, worktree / "src" / "app.py")

    assert result.returncode == 2
    assert "freeze.json" in result.stderr
    assert "sdd-freeze.sh" in result.stderr


def test_tier2_branch_with_valid_freeze_is_allowed(tmp_path):
    repo, worktree = _make_repo(tmp_path, "t2/1-feature")
    _freeze(worktree)

    result = _guard(worktree, worktree / "src" / "app.py")

    assert result.returncode == 0


def test_edit_after_frozen_spec_changed_is_denied(tmp_path):
    repo, worktree = _make_repo(tmp_path, "t2/1-feature")
    spec = _freeze(worktree)
    (spec / "spec.md").write_text("# changed\n")

    result = _guard(worktree, worktree / "src" / "app.py")

    assert result.returncode == 2
    assert "sdd-freeze.sh" in result.stderr


def test_unclassified_branch_in_linked_worktree_is_denied(tmp_path):
    repo, worktree = _make_repo(tmp_path, "feature")

    result = _guard(worktree, worktree / "src" / "app.py")

    assert result.returncode == 2
    assert "t<Tier>/<Issue番号>-<名前>" in result.stderr


def test_detached_head_is_denied(tmp_path):
    repo, worktree = _make_repo(tmp_path, detach=True)

    result = _guard(worktree, worktree / "src" / "app.py")

    assert result.returncode == 2
    assert "t<Tier>/<Issue番号>-<名前>" in result.stderr


def test_exempt_markdown_path_is_allowed(tmp_path):
    repo, _ = _make_repo(tmp_path)

    result = _guard(repo, repo / "docs" / "notes.md")

    assert result.returncode == 0


def test_allow_main_worktree_env_bypasses_guard(tmp_path):
    repo, _ = _make_repo(tmp_path)

    result = _guard(repo, repo / "src" / "app.py", env={"SDD_ALLOW_MAIN_WORKTREE": "1"})

    assert result.returncode == 0


def test_no_file_path_is_allowed(tmp_path):
    repo, _ = _make_repo(tmp_path)
    payload = {"tool_name": "Bash", "tool_input": {"command": "ls"}, "cwd": str(repo)}
    result = subprocess.run(
        ["bash", str(HOOK)],
        cwd=repo,
        input=json.dumps(payload),
        text=True,
        encoding="utf-8",
        capture_output=True,
        env=GIT_ENV,
    )

    assert result.returncode == 0


def test_copied_hook_without_ci_dir_denies_with_vendor_hint(tmp_path):
    import shutil
    repo, worktree = _make_repo(tmp_path, "t0/1-feature")
    hooks = tmp_path / "copied" / ".claude" / "hooks"
    hooks.mkdir(parents=True)
    shutil.copy(HOOK, hooks / "sdd-guard.sh")
    payload = {"tool_name": "Edit", "tool_input": {"file_path": str(worktree / "src" / "app.py")},
               "cwd": str(worktree)}
    r = subprocess.run(["bash", str(hooks / "sdd-guard.sh")], cwd=worktree, input=json.dumps(payload),
                       text=True, capture_output=True, env=GIT_ENV)
    assert r.returncode == 2
    assert "vendor/ai-sdd-guide/integration/hooks" in r.stderr
