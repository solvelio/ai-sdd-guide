import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "integration" / "ci"))

import sdd_state  # noqa: E402
from sdd_state import BranchInfo, FreezeError  # noqa: E402

SCRIPT = ROOT / "integration" / "ci" / "sdd_state.py"
GIT_ENV = {
    **os.environ,
    "GIT_AUTHOR_NAME": "Test User",
    "GIT_AUTHOR_EMAIL": "test@example.invalid",
    "GIT_COMMITTER_NAME": "Test User",
    "GIT_COMMITTER_EMAIL": "test@example.invalid",
}
NOW = datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc)
TASKS = "# Tasks\n\n- [ ] T1\n* [ ] a\n  - [ ] sub\n"


def _git(args, cwd):
    subprocess.run(["git"] + args, cwd=cwd, check=True, text=True,
                   capture_output=True, env=GIT_ENV)


def _repo(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(["init", "-q"], repo)
    (repo / "f").write_text("x\n")
    _git(["add", "."], repo)
    _git(["commit", "-q", "-m", "init"], repo)
    return repo


def _tier2_files(d, tasks=TASKS):
    d.mkdir(parents=True, exist_ok=True)
    (d / "spec.md").write_text("spec\n")
    (d / "plan.md").write_text("plan\n")
    (d / "tasks.md").write_text(tasks)
    (d / "traceability.json").write_text("{}\n")


def test_parse_branch_valid():
    assert sdd_state.parse_branch("t2/73-github-projects-board") == BranchInfo(
        2, 73, "github-projects-board", "73-github-projects-board")
    assert sdd_state.parse_branch("t0/3-d1-database-id") == BranchInfo(
        0, 3, "d1-database-id", "3-d1-database-id")


@pytest.mark.parametrize("b", ["main", "feat/x", "t3/1-x", "t2/x", "t2/0-x",
                               "t2/1-X", "t2/1-", "", None])
def test_parse_branch_invalid(b):
    assert sdd_state.parse_branch(b) is None


def test_current_branch_detached_is_none(tmp_path):
    repo = _repo(tmp_path)
    assert sdd_state.current_branch(repo) is not None
    _git(["checkout", "-q", "--detach"], repo)
    assert sdd_state.current_branch(repo) is None


def test_current_branch_not_git_is_none(tmp_path):
    assert sdd_state.current_branch(tmp_path) is None


def test_freeze_targets_by_tier():
    assert sdd_state.freeze_targets(2) == [
        "spec.md", "plan.md", "tasks.md", "traceability.json"]
    assert sdd_state.freeze_targets(1) == ["spec.md"]


def test_freeze_creates_file_with_digests(tmp_path):
    d = tmp_path / "specs" / "1-x"
    _tier2_files(d)
    data = sdd_state.create_freeze(d, 2, NOW)
    on_disk = json.loads((d / "freeze.json").read_text())
    assert on_disk == data
    assert data["version"] == 1 and data["tier"] == 2
    assert data["frozen_at"] == "2026-01-02T03:04:05Z"
    assert set(data["files"]) == set(sdd_state.freeze_targets(2))
    assert all(v.startswith("sha256:") for v in data["files"].values())
    assert sdd_state.freeze_status(d, 2)[0] == "valid"


def test_freeze_missing_target_raises(tmp_path):
    d = tmp_path / "specs" / "1-x"
    _tier2_files(d)
    (d / "plan.md").unlink()
    with pytest.raises(FileNotFoundError):
        sdd_state.create_freeze(d, 2, NOW)


def test_tasks_md_checkbox_variants_do_not_change_hash(tmp_path):
    d = tmp_path / "specs" / "1-x"
    _tier2_files(d)
    sdd_state.create_freeze(d, 2, NOW)
    for text in (TASKS.replace("[ ]", "[x]"), TASKS.replace("[ ]", "[X]"),
                 TASKS.replace("[ ]", "[x]").replace("\n", "\r\n")):
        (d / "tasks.md").write_bytes(text.encode())
        assert sdd_state.freeze_status(d, 2)[0] == "valid"


@pytest.mark.parametrize("name,content", [
    ("tasks.md", TASKS.replace("T1", "T2")),
    ("spec.md", "spec!\n"),
    ("plan.md", "plan!\n"),
    ("traceability.json", "{ }\n"),
])
def test_freeze_detects_non_checkbox_edit(tmp_path, name, content):
    d = tmp_path / "specs" / "1-x"
    _tier2_files(d)
    sdd_state.create_freeze(d, 2, NOW)
    (d / name).write_text(content)
    status, reasons = sdd_state.freeze_status(d, 2)
    assert status == "invalid"
    assert any(name in r for r in reasons)


def test_freeze_missing_file_is_invalid(tmp_path):
    d = tmp_path / "specs" / "1-x"
    _tier2_files(d)
    sdd_state.create_freeze(d, 2, NOW)
    (d / "traceability.json").unlink()
    status, reasons = sdd_state.freeze_status(d, 2)
    assert status == "invalid"
    assert any("traceability.json" in r for r in reasons)


def test_freeze_tier_mismatch_is_invalid(tmp_path):
    d = tmp_path / "specs" / "1-x"
    _tier2_files(d)
    sdd_state.create_freeze(d, 1, NOW)
    assert sdd_state.freeze_status(d, 1)[0] == "valid"
    assert sdd_state.freeze_status(d, 2)[0] == "invalid"


def test_freeze_missing_status(tmp_path):
    assert sdd_state.freeze_status(tmp_path, 2) == ("missing", [])


def test_phase_tier0_is_implement(tmp_path):
    assert sdd_state.derive_phase(
        tmp_path, BranchInfo(0, 1, "x", "1-x")) == "implement"


def test_phase_tier2_sequence(tmp_path):
    info = BranchInfo(2, 1, "x", "1-x")
    d = tmp_path / "specs" / "1-x"
    assert sdd_state.derive_phase(tmp_path, info) == "brainstorm"
    d.mkdir(parents=True)
    (d / "spec.md").write_text("spec\n")
    assert sdd_state.derive_phase(tmp_path, info) == "spec"
    (d / "plan.md").write_text("plan\n")
    assert sdd_state.derive_phase(tmp_path, info) == "plan"
    (d / "tasks.md").write_text(TASKS)
    assert sdd_state.derive_phase(tmp_path, info) == "tasks"
    (d / "traceability.json").write_text("{}\n")
    sdd_state.create_freeze(d, 2, NOW)
    assert sdd_state.derive_phase(tmp_path, info) == "implement"
    (d / "tasks.md").write_text(TASKS.replace("[ ]", "[x]"))
    assert sdd_state.derive_phase(tmp_path, info) == "verify"


def test_phase_tier1_spec_then_implement(tmp_path):
    info = BranchInfo(1, 1, "x", "1-x")
    d = tmp_path / "specs" / "1-x"
    d.mkdir(parents=True)
    (d / "spec.md").write_text("spec\n")
    assert sdd_state.derive_phase(tmp_path, info) == "spec"
    sdd_state.create_freeze(d, 1, NOW)
    assert sdd_state.derive_phase(tmp_path, info) == "implement"
    (d / "tasks.md").write_text("- [x] a\n")
    assert sdd_state.derive_phase(tmp_path, info) == "implement"


def test_phase_invalid_freeze_raises(tmp_path):
    info = BranchInfo(2, 1, "x", "1-x")
    d = tmp_path / "specs" / "1-x"
    _tier2_files(d)
    sdd_state.create_freeze(d, 2, NOW)
    (d / "spec.md").write_text("changed\n")
    with pytest.raises(FreezeError):
        sdd_state.derive_phase(tmp_path, info)


def _cli(args, cwd):
    return subprocess.run([sys.executable, str(SCRIPT)] + args, cwd=cwd,
                          capture_output=True, text=True, env=GIT_ENV)


def test_cli_guard_exit_codes(tmp_path):
    repo = _repo(tmp_path)
    _git(["checkout", "-q", "-b", "t0/1-x"], repo)
    assert _cli(["guard", "--root", str(repo)], repo).returncode == 0
    _git(["checkout", "-q", "-b", "t2/1-x"], repo)
    r = _cli(["guard", "--root", str(repo)], repo)
    assert r.returncode == 1 and "sdd-freeze.sh" in r.stderr
    _tier2_files(repo / "specs" / "1-x")
    assert _cli(["freeze", "--root", str(repo)], repo).returncode == 0
    assert _cli(["guard", "--root", str(repo)], repo).returncode == 0
    _git(["checkout", "-q", "-b", "main2"], repo)
    r = _cli(["guard", "--root", str(repo)], repo)
    assert r.returncode == 1 and "t<Tier>/<Issue番号>-<名前>" in r.stderr
    assert _cli(["guard", "--root", str(repo), "--branch", "main"],
                repo).returncode == 1


def test_cli_branch_phase_freeze(tmp_path):
    r = _cli(["branch", "--root", str(tmp_path), "--branch", "t1/5-foo"], tmp_path)
    assert json.loads(r.stdout) == {"tier": 1, "issue": 5, "name": "foo",
                                    "feature": "5-foo"}
    r = _cli(["branch", "--root", str(tmp_path), "--branch", "main"], tmp_path)
    assert r.returncode == 3 and r.stdout == ""
    r = _cli(["phase", "--root", str(tmp_path), "--branch", "t0/5-foo"], tmp_path)
    assert r.returncode == 0 and r.stdout.strip() == "implement"
    assert _cli(["phase", "--root", str(tmp_path), "--branch", "x"],
                tmp_path).returncode == 3
    assert _cli(["freeze", "--root", str(tmp_path), "--branch", "t0/5-foo"],
                tmp_path).returncode == 3
    d = tmp_path / "specs" / "5-foo"
    d.mkdir(parents=True)
    (d / "spec.md").write_text("s\n")
    r = _cli(["freeze", "--root", str(tmp_path), "--branch", "t1/5-foo"], tmp_path)
    assert r.returncode == 0 and r.stdout.strip().endswith("freeze.json")
    (d / "spec.md").write_text("changed\n")
    r = _cli(["phase", "--root", str(tmp_path), "--branch", "t1/5-foo"], tmp_path)
    assert r.returncode == 4 and "spec.md" in r.stderr
