"""Tests for sdd-validate.py."""
import importlib.util
import hashlib
import json
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

import jsonschema
import pytest

ROOT = Path(__file__).parents[1]
SCHEMA_DIR = ROOT / "orchestration" / "schema"
FIXTURES = ROOT / "tests" / "fixtures"
sys.path.insert(0, str(ROOT / "integration" / "ci"))
import sdd_state  # noqa: E402


def load_schema(name: str) -> dict:
    return json.loads((SCHEMA_DIR / name).read_text())


# ---------------------------------------------------------------------------
# Import sdd-validate.py (hyphen filename → importlib)
# ---------------------------------------------------------------------------

def _load_module():
    spec = importlib.util.spec_from_file_location(
        "sdd_validate",
        ROOT / "integration" / "ci" / "sdd-validate.py",
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_v = _load_module()


# ---------------------------------------------------------------------------
# check_tasks_md_consistency
# ---------------------------------------------------------------------------

def test_check_tasks_md_all_checked(tmp_path):
    (tmp_path / "specs" / "foo").mkdir(parents=True)
    (tmp_path / "specs" / "foo" / "tasks.md").write_text(
        "# Tasks\n- [x] T1: done task. AC: SAC-1\n"
    )
    assert _v.check_tasks_md_consistency(tmp_path, "foo") == []


def test_check_tasks_md_unchecked_item_error(tmp_path):
    (tmp_path / "specs" / "foo").mkdir(parents=True)
    (tmp_path / "specs" / "foo" / "tasks.md").write_text(
        "# Tasks\n- [ ] T1: incomplete task. AC: SAC-1\n"
    )
    errors = _v.check_tasks_md_consistency(tmp_path, "foo")
    assert any("unchecked" in e for e in errors)


# ---------------------------------------------------------------------------
# check_schema_traceability
# ---------------------------------------------------------------------------

def test_check_schema_traceability_valid(tmp_path):
    (tmp_path / "specs" / "foo").mkdir(parents=True)
    (tmp_path / "specs" / "foo" / "traceability.json").write_text(json.dumps({
        "issue": 99,
        "issue_url": "https://github.com/owner/repo/issues/99",
        "feature": "foo",
        "entries": [{
            "issue_ac": "99-AC1", "spec_ac": "SAC-1",
            "task": "T1", "test": "tests/test_foo.py::test_a",
            "status": "in-scope"
        }]
    }))
    assert _v.check_schema_traceability(tmp_path, "foo") == []


def test_check_schema_traceability_file_missing(tmp_path):
    errors = _v.check_schema_traceability(tmp_path, "foo")
    assert any("not found" in e for e in errors)


def test_check_schema_traceability_invalid_schema(tmp_path):
    (tmp_path / "specs" / "foo").mkdir(parents=True)
    # entries が空 → minItems: 1 に違反
    (tmp_path / "specs" / "foo" / "traceability.json").write_text(json.dumps({
        "issue": 99,
        "issue_url": "https://github.com/owner/repo/issues/99",
        "feature": "foo",
        "entries": []
    }))
    errors = _v.check_schema_traceability(tmp_path, "foo")
    assert len(errors) == 1


# ---------------------------------------------------------------------------
# check_traceability_internal
# ---------------------------------------------------------------------------

def _make_traceability_fixture(tmp_path, entries):
    (tmp_path / "specs" / "foo").mkdir(parents=True)
    (tmp_path / "specs" / "foo" / "traceability.json").write_text(json.dumps({
        "issue": 99,
        "issue_url": "https://github.com/owner/repo/issues/99",
        "feature": "foo",
        "entries": entries,
    }))
    (tmp_path / "specs" / "foo" / "tasks.md").write_text(
        "# Tasks\n- [x] T1: done. AC: SAC-1\n"
    )
    (tmp_path / "specs" / "foo" / "spec.md").write_text(
        "# Spec\n## 受入条件\n- [ ] SAC-1: criterion one\n"
    )


def test_check_traceability_internal_valid(tmp_path):
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_foo.py").write_text("def test_a(): pass")
    _make_traceability_fixture(tmp_path, [{
        "issue_ac": "99-AC1", "spec_ac": "SAC-1",
        "task": "T1", "test": "tests/test_foo.py::test_a",
        "status": "in-scope"
    }])
    assert _v.check_traceability_internal(tmp_path, "foo") == []


def test_check_traceability_internal_duplicate_spec_ac(tmp_path):
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_foo.py").write_text("def test_a(): pass")
    _make_traceability_fixture(tmp_path, [
        {"issue_ac": "99-AC1", "spec_ac": "SAC-1",
         "task": "T1", "test": "tests/test_foo.py::test_a", "status": "in-scope"},
        {"issue_ac": "99-AC2", "spec_ac": "SAC-1",  # duplicate SAC-1
         "task": "T1", "test": "tests/test_foo.py::test_a", "status": "in-scope"},
    ])
    errors = _v.check_traceability_internal(tmp_path, "foo")
    assert any("duplicate" in e for e in errors)


def test_check_traceability_internal_missing_test_file(tmp_path):
    _make_traceability_fixture(tmp_path, [{
        "issue_ac": "99-AC1", "spec_ac": "SAC-1",
        "task": "T1", "test": "tests/test_nonexistent.py::test_a",
        "status": "in-scope"
    }])
    errors = _v.check_traceability_internal(tmp_path, "foo")
    assert any("test_nonexistent.py" in e for e in errors)


def test_check_traceability_internal_missing_task(tmp_path):
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_foo.py").write_text("def test_a(): pass")
    _make_traceability_fixture(tmp_path, [{
        "issue_ac": "99-AC1", "spec_ac": "SAC-1",
        "task": "T99",  # T99 は tasks.md に存在しない
        "test": "tests/test_foo.py::test_a", "status": "in-scope"
    }])
    errors = _v.check_traceability_internal(tmp_path, "foo")
    assert any("T99" in e for e in errors)


# ---------------------------------------------------------------------------
# check_scope_out
# ---------------------------------------------------------------------------

def test_check_scope_out_no_out_of_scope(tmp_path):
    (tmp_path / "specs" / "foo").mkdir(parents=True)
    (tmp_path / "specs" / "foo" / "traceability.json").write_text(json.dumps({
        "issue": 99, "issue_url": "https://github.com/o/r/issues/99",
        "feature": "foo",
        "entries": [{"issue_ac": "99-AC1", "spec_ac": "SAC-1",
                      "task": "T1", "test": "tests/t.py::test_a", "status": "in-scope"}]
    }))
    assert _v.check_scope_out(tmp_path, "foo") == []


def test_check_scope_out_valid_out_of_scope(tmp_path):
    (tmp_path / "specs" / "foo").mkdir(parents=True)
    (tmp_path / "specs" / "foo" / "traceability.json").write_text(json.dumps({
        "issue": 99, "issue_url": "https://github.com/o/r/issues/99",
        "feature": "foo",
        "entries": [{
            "issue_ac": "99-AC1", "spec_ac": None, "task": None, "test": None,
            "status": "out-of-scope",
            "reason": "out of scope for this feature",
            "followup_issue": "https://github.com/o/r/issues/100"
        }]
    }))
    assert _v.check_scope_out(tmp_path, "foo") == []


def test_check_scope_out_missing_followup(tmp_path):
    (tmp_path / "specs" / "foo").mkdir(parents=True)
    (tmp_path / "specs" / "foo" / "traceability.json").write_text(json.dumps({
        "issue": 99, "issue_url": "https://github.com/o/r/issues/99",
        "feature": "foo",
        "entries": [{
            "issue_ac": "99-AC1", "spec_ac": None, "task": None, "test": None,
            "status": "out-of-scope",
            "reason": "out of scope",
            "followup_issue": "mailto:bad@example.com"  # HTTPSでない
        }]
    }))
    errors = _v.check_scope_out(tmp_path, "foo")
    assert any("followup_issue" in e for e in errors)


# ---------------------------------------------------------------------------
# Shell integration tests (subprocess)
# ---------------------------------------------------------------------------

import subprocess as _subprocess


def _run_sh(fixture_name: str, extra_args: list[str] | None = None) -> _subprocess.CompletedProcess:
    sh = ROOT / "integration" / "ci" / "sdd-validate.sh"
    root = FIXTURES / fixture_name
    cmd = ["bash", str(sh), "--root", str(root)] + (extra_args or [])
    return _subprocess.run(cmd, capture_output=True, text=True)


BRANCH = "t2/99-my-feature"


def test_sh_valid_active_exits_0():
    result = _run_sh("valid-active", ["--branch", BRANCH])
    assert result.returncode == 0


def test_sh_invalid_traceability_exits_1():
    result = _run_sh("invalid-traceability", ["--branch", BRANCH])
    assert result.returncode == 1


def test_sh_invalid_tasks_incomplete_exits_1():
    result = _run_sh("invalid-tasks-incomplete", ["--branch", BRANCH, "--pr"])
    assert result.returncode == 1
    assert "unchecked item" in result.stderr


def test_sh_missing_feature_dir_exits_1(tmp_path):
    result = _run_sh_root(tmp_path, ["--branch", BRANCH])
    assert result.returncode == 1


def _run_sh_root(root, extra_args, env=None):
    sh = ROOT / "integration" / "ci" / "sdd-validate.sh"
    full_env = dict(os.environ)
    full_env.pop("GITHUB_HEAD_REF", None)
    full_env.update(env or {})
    return _subprocess.run(
        ["bash", str(sh), "--root", str(root)] + extra_args,
        capture_output=True, text=True, env=full_env,
    )


def _copy_valid(tmp_path):
    dest = tmp_path / "repo"
    shutil.copytree(FIXTURES / "valid-active", dest)
    sdd_state.create_freeze(dest / "specs" / "99-my-feature", 2, datetime.now(timezone.utc))
    return dest


def test_branch_from_github_head_ref(tmp_path):
    root = _copy_valid(tmp_path)
    ok = _run_sh_root(root, [], env={"GITHUB_HEAD_REF": BRANCH})
    assert ok.returncode == 0, ok.stderr
    assert "99-my-feature" in ok.stdout
    (root / "specs" / "99-my-feature" / "traceability.json").write_text("{}")
    bad = _run_sh_root(root, [], env={"GITHUB_HEAD_REF": BRANCH})
    assert bad.returncode == 1


def test_non_pr_unmatched_branch_skips_feature_checks(tmp_path):
    result = _run_sh_root(tmp_path, ["--branch", "main"])
    assert result.returncode == 0
    assert "skipped" in result.stdout


def test_pr_unmatched_branch_fails(tmp_path):
    result = _run_sh_root(tmp_path, ["--pr", "--branch", "feat/x"])
    assert result.returncode == 1
    assert "t<Tier>/<Issue番号>-<名前>" in result.stderr


def test_pr_bot_branch_is_tier0(tmp_path):
    result = _run_sh_root(tmp_path, ["--pr", "--branch", "dependabot/npm/foo"])
    assert result.returncode == 0, result.stderr


def test_pr_bot_prefix_from_board_json(tmp_path):
    (tmp_path / ".sdd").mkdir()
    (tmp_path / ".sdd" / "board.json").write_text(
        json.dumps({"owner": "o", "project": 1, "tier0_branch_prefixes": ["bot/"]})
    )
    assert _run_sh_root(tmp_path, ["--pr", "--branch", "bot/x"]).returncode == 0
    assert _run_sh_root(tmp_path, ["--pr", "--branch", "dependabot/x"]).returncode == 1


def test_pr_label_mismatch_fails(tmp_path):
    root = _copy_valid(tmp_path)
    args = ["--pr", "--branch", BRANCH]
    bad = _run_sh_root(root, args + ["--pr-labels", "sdd:tier-0,bug"])
    assert bad.returncode == 1
    assert "sdd:tier-0" in bad.stderr
    assert _run_sh_root(root, args + ["--pr-labels", "sdd:tier-2"]).returncode == 0
    assert _run_sh_root(root, args + ["--pr-labels", "bug"]).returncode == 0
    assert _run_sh_root(root, args + ["--pr-labels", ""]).returncode == 0


def test_feature_override_keeps_branch_tier(tmp_path):
    root = _copy_valid(tmp_path)
    result = _run_sh_root(root, ["--branch", "t2/99-x", "--feature", "99-my-feature"])
    assert result.returncode == 0, result.stderr
    assert "99-my-feature" in result.stdout
    (root / "specs" / "99-my-feature" / "traceability.json").write_text("{}")
    assert _run_sh_root(
        root, ["--branch", "t2/99-x", "--feature", "99-my-feature"]
    ).returncode == 1


def test_tier0_pr_skips_spec_checks(tmp_path):
    result = _run_sh_root(tmp_path, ["--pr", "--branch", "t0/5-fix"])
    assert result.returncode == 0, result.stderr


def test_tier1_invalid_freeze_fails(tmp_path):
    spec = tmp_path / "specs" / "7-small"
    spec.mkdir(parents=True)
    (spec / "spec.md").write_text("# Spec\n")
    (spec / "handoff.md").write_text("# h\n")
    (spec / "freeze.json").write_text("not json")
    result = _run_sh_root(tmp_path, ["--branch", "t1/7-small"])
    assert result.returncode == 1
    assert "freeze.json" in result.stderr


def test_tier1_missing_freeze_only_fails_in_pr(tmp_path):
    spec = tmp_path / "specs" / "7-small"
    spec.mkdir(parents=True)
    (spec / "spec.md").write_text("# Spec\n")
    assert _run_sh_root(tmp_path, ["--branch", "t1/7-small"]).returncode == 0
    pr = _run_sh_root(tmp_path, ["--pr", "--branch", "t1/7-small"])
    assert pr.returncode == 1
    assert "freeze.json not found" in pr.stderr


# ---------------------------------------------------------------------------
# Fix 2: check_traceability_internal — tasks.md missing is an error
# ---------------------------------------------------------------------------

def test_check_traceability_internal_tasks_md_missing(tmp_path):
    (tmp_path / "specs" / "foo").mkdir(parents=True)
    (tmp_path / "specs" / "foo" / "traceability.json").write_text(json.dumps({
        "issue": 99, "issue_url": "https://github.com/o/r/issues/99",
        "feature": "foo",
        "entries": [{"issue_ac": "99-AC1", "spec_ac": "SAC-1",
                      "task": "T1", "test": "tests/test_foo.py::test_a",
                      "status": "in-scope"}]
    }))
    # tasks.md does not exist
    errors = _v.check_traceability_internal(tmp_path, "foo")
    assert any("tasks.md not found" in e for e in errors)


# ---------------------------------------------------------------------------
# Fix: check_traceability_internal — spec_ac not in spec.md
# ---------------------------------------------------------------------------

def test_check_traceability_internal_spec_ac_not_in_spec_md(tmp_path):
    (tmp_path / "specs" / "foo").mkdir(parents=True)
    (tmp_path / "specs" / "foo" / "spec.md").write_text(
        "# Spec\n## 受入条件\n- [ ] SAC-1: criterion one\n"
    )
    (tmp_path / "specs" / "foo" / "tasks.md").write_text(
        "# Tasks\n- [x] T1: done. AC: SAC-1\n"
    )
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_foo.py").write_text("def test_a(): pass")
    (tmp_path / "specs" / "foo" / "traceability.json").write_text(json.dumps({
        "issue": 99, "issue_url": "https://github.com/o/r/issues/99",
        "feature": "foo",
        "entries": [{
            "issue_ac": "99-AC1", "spec_ac": "SAC-2",  # SAC-2 not in spec.md
            "task": "T1", "test": "tests/test_foo.py::test_a", "status": "in-scope"
        }]
    }))
    errors = _v.check_traceability_internal(tmp_path, "foo")
    assert any("SAC-2" in e for e in errors)


def test_check_traceability_internal_spec_ac_valid_in_spec_md(tmp_path):
    (tmp_path / "specs" / "foo").mkdir(parents=True)
    (tmp_path / "specs" / "foo" / "spec.md").write_text(
        "# Spec\n## 受入条件\n- [ ] SAC-1: criterion one\n"
    )
    (tmp_path / "specs" / "foo" / "tasks.md").write_text(
        "# Tasks\n- [x] T1: done. AC: SAC-1\n"
    )
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_foo.py").write_text("def test_a(): pass")
    (tmp_path / "specs" / "foo" / "traceability.json").write_text(json.dumps({
        "issue": 99, "issue_url": "https://github.com/o/r/issues/99",
        "feature": "foo",
        "entries": [{
            "issue_ac": "99-AC1", "spec_ac": "SAC-1",  # SAC-1 exists in spec.md
            "task": "T1", "test": "tests/test_foo.py::test_a", "status": "in-scope"
        }]
    }))
    errors = _v.check_traceability_internal(tmp_path, "foo")
    assert errors == []


def test_check_traceability_internal_spec_md_missing(tmp_path):
    (tmp_path / "specs" / "foo").mkdir(parents=True)
    # spec.md は作成しない
    (tmp_path / "specs" / "foo" / "tasks.md").write_text(
        "# Tasks\n- [x] T1: done. AC: SAC-1\n"
    )
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_foo.py").write_text("def test_a(): pass")
    (tmp_path / "specs" / "foo" / "traceability.json").write_text(json.dumps({
        "issue": 99, "issue_url": "https://github.com/o/r/issues/99",
        "feature": "foo",
        "entries": [{"issue_ac": "99-AC1", "spec_ac": "SAC-1",
                      "task": "T1", "test": "tests/test_foo.py::test_a",
                      "status": "in-scope"}]
    }))
    errors = _v.check_traceability_internal(tmp_path, "foo")
    assert any("spec.md not found" in e for e in errors)


# ---------------------------------------------------------------------------
# check_issue_snapshot
# ---------------------------------------------------------------------------

def _snapshot_hash(raw_body: str) -> str:
    return hashlib.sha256(raw_body.encode("utf-8")).hexdigest()


def _write_issue_snapshot_fixture(
    tmp_path,
    *,
    snapshot_acs=None,
    traceability_acs=None,
    body_hash=None,
    issue=53,
):
    feature_dir = tmp_path / "specs" / "issue-snapshot"
    feature_dir.mkdir(parents=True)
    raw_body = "## 受入条件\n\n- [ ] first criterion\n- [ ] second criterion\n"
    if snapshot_acs is None:
        snapshot_acs = [
            {"id": "53-AC1", "text": "first criterion"},
            {"id": "53-AC2", "text": "second criterion"},
        ]
    if traceability_acs is None:
        traceability_acs = ["53-AC1", "53-AC2"]

    (feature_dir / "issue-snapshot.json").write_text(json.dumps({
        "issue": issue,
        "url": "https://github.com/owner/repo/issues/53",
        "fetched_at": "2026-06-26T13:50:53Z",
        "raw_body": raw_body,
        "body_hash": body_hash or _snapshot_hash(raw_body),
        "stable_acs": snapshot_acs,
    }))
    (feature_dir / "traceability.json").write_text(json.dumps({
        "issue": issue,
        "issue_url": "https://github.com/owner/repo/issues/53",
        "feature": "issue-snapshot",
        "entries": [
            {
                "issue_ac": issue_ac,
                "spec_ac": f"SAC-{i}",
                "task": "T3",
                "test": "tests/test_sdd_validate.py::test_check_issue_snapshot_valid",
                "status": "in-scope",
            }
            for i, issue_ac in enumerate(traceability_acs, 1)
        ],
    }))


def test_check_issue_snapshot_valid(tmp_path):
    _write_issue_snapshot_fixture(tmp_path)
    assert _v.check_issue_snapshot(tmp_path, "issue-snapshot") == []


def test_check_issue_snapshot_hash_mismatch(tmp_path):
    _write_issue_snapshot_fixture(tmp_path, body_hash="0" * 64)
    errors = _v.check_issue_snapshot(tmp_path, "issue-snapshot")
    assert any("body_hash" in e and "SHA-256" in e for e in errors)


def test_check_issue_snapshot_stable_ac_id_mismatch(tmp_path):
    _write_issue_snapshot_fixture(
        tmp_path,
        snapshot_acs=[{"id": "53-AC2", "text": "first criterion"}],
        traceability_acs=["53-AC2"],
    )
    errors = _v.check_issue_snapshot(tmp_path, "issue-snapshot")
    assert any("53-AC1" in e and "53-AC2" in e for e in errors)


def test_check_issue_snapshot_traceability_mismatch(tmp_path):
    _write_issue_snapshot_fixture(
        tmp_path,
        snapshot_acs=[{"id": "53-AC1", "text": "first criterion"}],
        traceability_acs=["53-AC2"],
    )
    errors = _v.check_issue_snapshot(tmp_path, "issue-snapshot")
    assert any("snapshot AC not tracked" in e and "53-AC1" in e for e in errors)


def test_check_issue_snapshot_untracked_issue_ac(tmp_path):
    _write_issue_snapshot_fixture(
        tmp_path,
        snapshot_acs=[{"id": "53-AC1", "text": "first criterion"}],
        traceability_acs=["53-AC1", "53-AC2"],
    )
    errors = _v.check_issue_snapshot(tmp_path, "issue-snapshot")
    assert any("traceability AC not in snapshot" in e and "53-AC2" in e for e in errors)


def test_check_issue_snapshot_missing_fails_closed(tmp_path):
    (tmp_path / "specs" / "issue-snapshot").mkdir(parents=True)
    errors = _v.check_issue_snapshot(tmp_path, "issue-snapshot")
    assert any("issue-snapshot.json not found" in e for e in errors)


def test_sh_issue_snapshot_missing_exits_1(tmp_path):
    feature_dir = tmp_path / "specs" / "53-issue-snapshot"
    feature_dir.mkdir(parents=True)
    (feature_dir / "spec.md").write_text(
        "# Spec\n## 受入条件\n- [ ] SAC-1: criterion one\n"
    )
    (feature_dir / "tasks.md").write_text("# Tasks\n- [x] T1: done\n")
    (feature_dir / "traceability.json").write_text(json.dumps({
        "issue": 53,
        "issue_url": "https://github.com/owner/repo/issues/53",
        "feature": "53-issue-snapshot",
        "entries": [{
            "issue_ac": "53-AC1",
            "spec_ac": "SAC-1",
            "task": "T1",
            "test": "tests/test_issue_snapshot.py::test_one",
            "status": "in-scope",
        }],
    }))
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_issue_snapshot.py").write_text("def test_one(): pass")

    result = _subprocess.run(
        ["bash", str(ROOT / "integration" / "ci" / "sdd-validate.sh"), "--root", str(tmp_path),
         "--branch", "t2/53-issue-snapshot"],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "issue-snapshot.json not found" in result.stderr


# ---------------------------------------------------------------------------
# check_evidence
# ---------------------------------------------------------------------------

def _init_git_repo(path: Path) -> str:
    _subprocess.run(["git", "init"], cwd=path, check=True, capture_output=True, text=True)
    (path / "README.md").write_text("fixture\n")
    _subprocess.run(["git", "add", "README.md"], cwd=path, check=True)
    _subprocess.run(
        [
            "git",
            "-c",
            "user.email=test@example.com",
            "-c",
            "user.name=Test User",
            "commit",
            "-m",
            "fixture commit",
        ],
        cwd=path,
        check=True,
        capture_output=True,
        text=True,
    )
    result = _subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=path,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _write_evidence_fixture(tmp_path, *, commit_sha: str | None = None) -> str:
    feature_dir = tmp_path / "specs" / "evidence-validation"
    feature_dir.mkdir(parents=True)
    commit_sha = commit_sha or _init_git_repo(tmp_path)
    (feature_dir / "evidence.json").write_text(json.dumps({
        "feature": "evidence-validation",
        "commit_sha": commit_sha,
        "entries": [
            {
                "command_type": "test",
                "command": "pytest -q",
                "result": "1 passed",
                "test_count": 1,
            },
            {
                "command_type": "build",
                "command": "python -m compileall integration",
                "result": "ok",
                "test_count": None,
            },
        ],
    }))
    return commit_sha


def test_check_evidence_valid_existing_commit(tmp_path):
    _write_evidence_fixture(tmp_path)
    assert _v.check_evidence(tmp_path, "evidence-validation") == []


def test_check_evidence_nonexistent_commit_fails(tmp_path):
    _init_git_repo(tmp_path)
    _write_evidence_fixture(tmp_path, commit_sha="0" * 40)
    errors = _v.check_evidence(tmp_path, "evidence-validation")
    assert any("commit_sha" in e and "not found" in e for e in errors)


def test_check_evidence_missing_fails_closed(tmp_path):
    (tmp_path / "specs" / "evidence-validation").mkdir(parents=True)
    errors = _v.check_evidence(tmp_path, "evidence-validation")
    assert any("evidence.json not found" in e for e in errors)


def test_sh_evidence_missing_exits_1(tmp_path):
    feature_dir = tmp_path / "specs" / "54-evidence-validation"
    feature_dir.mkdir(parents=True)
    (feature_dir / "spec.md").write_text(
        "# Spec\n## 受入条件\n- [ ] SAC-1: criterion one\n"
    )
    (feature_dir / "tasks.md").write_text("# Tasks\n- [x] T1: done\n")
    (feature_dir / "traceability.json").write_text(json.dumps({
        "issue": 54,
        "issue_url": "https://github.com/owner/repo/issues/54",
        "feature": "54-evidence-validation",
        "entries": [{
            "issue_ac": "54-AC1",
            "spec_ac": "SAC-1",
            "task": "T1",
            "test": "tests/test_evidence.py::test_one",
            "status": "in-scope",
        }],
    }))
    raw_body = "## 受入条件\n\n- [ ] criterion one\n"
    (feature_dir / "issue-snapshot.json").write_text(json.dumps({
        "issue": 54,
        "url": "https://github.com/owner/repo/issues/54",
        "fetched_at": "2026-06-27T00:00:00Z",
        "raw_body": raw_body,
        "body_hash": _snapshot_hash(raw_body),
        "stable_acs": [{"id": "54-AC1", "text": "criterion one"}],
    }))
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_evidence.py").write_text("def test_one(): pass")

    result = _subprocess.run(
        ["bash", str(ROOT / "integration" / "ci" / "sdd-validate.sh"), "--root", str(tmp_path),
         "--branch", "t2/54-evidence-validation"],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "evidence.json not found" in result.stderr


def test_pr_star_bullet_unchecked_item_fails(tmp_path):
    root = _copy_valid(tmp_path)
    (root / "specs" / "99-my-feature" / "tasks.md").write_text("* [ ] x\n")
    r = _run_sh_root(root, ["--pr", "--branch", BRANCH])
    assert r.returncode == 1
    assert "unchecked" in r.stderr


@pytest.mark.parametrize("prefixes", [[""], [1], []])
def test_empty_or_invalid_tier0_prefixes_fall_back_to_defaults(tmp_path, prefixes):
    (tmp_path / ".sdd").mkdir()
    (tmp_path / ".sdd" / "board.json").write_text(
        json.dumps({"owner": "o", "project": 1, "tier0_branch_prefixes": prefixes})
    )
    assert _run_sh_root(tmp_path, ["--pr", "--branch", "feat/x"]).returncode == 1
    assert _run_sh_root(tmp_path, ["--pr", "--branch", "dependabot/x"]).returncode == 0


def test_non_string_tier0_prefix_entries_are_filtered(tmp_path):
    (tmp_path / ".sdd").mkdir()
    (tmp_path / ".sdd" / "board.json").write_text(
        json.dumps({"owner": "o", "project": 1, "tier0_branch_prefixes": [1, "", "bot/"]})
    )
    assert _run_sh_root(tmp_path, ["--pr", "--branch", "bot/x"]).returncode == 0
    assert _run_sh_root(tmp_path, ["--pr", "--branch", "feat/x"]).returncode == 1
