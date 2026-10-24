import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "integration" / "ci"))
from sdd_state import create_freeze  # noqa: E402

CLAUDE = ROOT / "integration" / "hooks" / "skill-reminder.sh"
CODEX = ROOT / "integration" / "hooks" / "codex-skill-reminder.sh"
GIT_ENV = {
    **os.environ,
    "GIT_AUTHOR_NAME": "Test User",
    "GIT_AUTHOR_EMAIL": "test@example.invalid",
    "GIT_COMMITTER_NAME": "Test User",
    "GIT_COMMITTER_EMAIL": "test@example.invalid",
}


def _git(args, cwd):
    subprocess.run(["git"] + args, cwd=cwd, check=True, text=True, env=GIT_ENV,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def _repo(tmp_path, branch):
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(["init"], repo)
    (repo / "a.txt").write_text("x\n")
    _git(["add", "."], repo)
    _git(["commit", "-m", "init"], repo)
    _git(["checkout", "-b", branch], repo)
    return repo


def _spec(repo, feature, files):
    d = repo / "specs" / feature
    d.mkdir(parents=True, exist_ok=True)
    for name in files:
        (d / name).write_text("{}\n" if name.endswith(".json") else "# %s\n- [ ] T1\n" % name)
    return d


def _run(hook, repo):
    payload = json.dumps({"hook_event_name": "UserPromptSubmit"})
    p = subprocess.run(["bash", str(hook)], cwd=repo, input=payload, text=True,
                       capture_output=True, env=GIT_ENV)
    assert p.returncode == 0
    return p.stdout + p.stderr


def _frozen(repo, feature, tier):
    names = ["spec.md", "plan.md", "tasks.md", "traceability.json"] if tier == 2 else ["spec.md"]
    d = _spec(repo, feature, names)
    create_freeze(d, tier, datetime(2026, 1, 1, tzinfo=timezone.utc))


def test_reminder_brainstorm_for_tier2_without_spec_dir(tmp_path):
    repo = _repo(tmp_path, "t2/1-feature")
    assert "brainstorming" in _run(CLAUDE, repo)
    assert "brainstorming" in _run(CODEX, repo)


def test_reminder_plan_phase(tmp_path):
    repo = _repo(tmp_path, "t2/1-feature")
    _spec(repo, "1-feature", ["spec.md", "plan.md"])
    assert "writing-plans" in _run(CLAUDE, repo)
    assert "writing-plans" in _run(CODEX, repo)


def test_reminder_implement_phase(tmp_path):
    repo = _repo(tmp_path, "t2/1-feature")
    _frozen(repo, "1-feature", 2)
    assert "executing-plans" in _run(CLAUDE, repo)
    assert "frozen specs/<feature>/tasks.md" in _run(CODEX, repo)


def test_reminder_tier1_design_phase_is_silent(tmp_path):
    repo = _repo(tmp_path, "t1/1-feature")
    _spec(repo, "1-feature", ["spec.md"])
    assert _run(CLAUDE, repo) == ""
    assert _run(CODEX, repo) == ""


def test_reminder_tier1_implement_phase_reminds(tmp_path):
    repo = _repo(tmp_path, "t1/1-feature")
    _frozen(repo, "1-feature", 1)
    assert "executing-plans" in _run(CLAUDE, repo)


def test_reminder_tier0_is_silent(tmp_path):
    repo = _repo(tmp_path, "t0/1-feature")
    assert _run(CLAUDE, repo) == ""
    assert _run(CODEX, repo) == ""


def test_reminder_unclassified_is_silent(tmp_path):
    repo = _repo(tmp_path, "feature/foo")
    assert _run(CLAUDE, repo) == ""
    assert _run(CODEX, repo) == ""
