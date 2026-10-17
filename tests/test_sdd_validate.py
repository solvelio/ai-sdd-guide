"""Tests for sdd-validate.py and its JSON schemas."""
import importlib.util
import hashlib
import json
from pathlib import Path

import jsonschema
import pytest

ROOT = Path(__file__).parents[1]
SCHEMA_DIR = ROOT / "orchestration" / "schema"
FIXTURES = ROOT / "tests" / "fixtures"


def load_schema(name: str) -> dict:
    return json.loads((SCHEMA_DIR / name).read_text())


# ---------------------------------------------------------------------------
# state.schema.json
# ---------------------------------------------------------------------------

def test_state_schema_valid_active():
    schema = load_schema("state.schema.json")
    instance = {"tier": 2, "phase": "implement", "feature": "my-feature"}
    jsonschema.validate(instance, schema)


def test_state_schema_valid_done_reset():
    schema = load_schema("state.schema.json")
    instance = {"tier": 0, "phase": "done", "note": "no active feature"}
    jsonschema.validate(instance, schema)


def test_state_schema_active_missing_feature_fails():
    schema = load_schema("state.schema.json")
    instance = {"tier": 2, "phase": "implement"}  # feature 欠落
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance, schema)


def test_state_schema_invalid_phase_fails():
    schema = load_schema("state.schema.json")
    instance = {"tier": 2, "phase": "unknown", "feature": "my-feature"}
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance, schema)


# ---------------------------------------------------------------------------
# tasks.schema.json
# ---------------------------------------------------------------------------

def test_tasks_schema_valid():
    schema = load_schema("tasks.schema.json")
    instance = [{"id": "my-feature", "phase": "implement", "status": "in_progress",
                  "handoff": None, "blocked_reason": None}]
    jsonschema.validate(instance, schema)


def test_tasks_schema_blocked_with_reason_valid():
    schema = load_schema("tasks.schema.json")
    instance = [{"id": "my-feature", "phase": "implement", "status": "blocked",
                  "handoff": None, "blocked_reason": "waiting for external API"}]
    jsonschema.validate(instance, schema)


def test_tasks_schema_blocked_without_reason_fails():
    schema = load_schema("tasks.schema.json")
    instance = [{"id": "my-feature", "phase": "implement", "status": "blocked",
                  "handoff": None, "blocked_reason": None}]
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance, schema)


def test_tasks_schema_not_blocked_with_reason_fails():
    schema = load_schema("tasks.schema.json")
    instance = [{"id": "my-feature", "phase": "implement", "status": "in_progress",
                  "handoff": None, "blocked_reason": "should be null"}]
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance, schema)


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
# check_schema_state
# ---------------------------------------------------------------------------

def test_check_schema_state_valid_active(tmp_path):
    (tmp_path / ".sdd").mkdir()
    (tmp_path / ".sdd" / "state.json").write_text(
        json.dumps({"tier": 2, "phase": "implement", "feature": "my-feature"})
    )
    assert _v.check_schema_state(tmp_path) == []


def test_check_schema_state_valid_done(tmp_path):
    (tmp_path / ".sdd").mkdir()
    (tmp_path / ".sdd" / "state.json").write_text(
        json.dumps({"tier": 0, "phase": "done"})
    )
    assert _v.check_schema_state(tmp_path) == []


def test_check_schema_state_missing_feature_error(tmp_path):
    (tmp_path / ".sdd").mkdir()
    (tmp_path / ".sdd" / "state.json").write_text(
        json.dumps({"tier": 2, "phase": "implement"})
    )
    errors = _v.check_schema_state(tmp_path)
    assert len(errors) == 1


def test_check_schema_state_file_missing_error(tmp_path):
    errors = _v.check_schema_state(tmp_path)
    assert any("not found" in e for e in errors)


# ---------------------------------------------------------------------------
# check_schema_tasks
# ---------------------------------------------------------------------------

def test_check_schema_tasks_no_file_skips(tmp_path):
    assert _v.check_schema_tasks(tmp_path, "my-feature") == []


def test_check_schema_tasks_valid(tmp_path):
    (tmp_path / ".sdd").mkdir()
    (tmp_path / ".sdd" / "tasks.json").write_text(json.dumps([
        {"id": "my-feature", "phase": "implement", "status": "in_progress",
         "handoff": None, "blocked_reason": None}
    ]))
    assert _v.check_schema_tasks(tmp_path, "my-feature") == []


def test_check_schema_tasks_feature_missing_in_tasks(tmp_path):
    (tmp_path / ".sdd").mkdir()
    (tmp_path / ".sdd" / "tasks.json").write_text(json.dumps([
        {"id": "other-feature", "phase": "implement", "status": "in_progress",
         "handoff": None, "blocked_reason": None}
    ]))
    errors = _v.check_schema_tasks(tmp_path, "my-feature")
    assert any("my-feature" in e for e in errors)


# ---------------------------------------------------------------------------
# check_state_tasks_consistency
# ---------------------------------------------------------------------------

def test_check_state_tasks_consistency_no_tasks_file(tmp_path):
    (tmp_path / ".sdd").mkdir()
    (tmp_path / ".sdd" / "state.json").write_text(
        json.dumps({"tier": 2, "phase": "implement", "feature": "foo"})
    )
    assert _v.check_state_tasks_consistency(tmp_path, "foo") == []


def test_check_state_tasks_consistency_match(tmp_path):
    (tmp_path / ".sdd").mkdir()
    (tmp_path / ".sdd" / "state.json").write_text(
        json.dumps({"tier": 2, "phase": "implement", "feature": "foo"})
    )
    (tmp_path / ".sdd" / "tasks.json").write_text(json.dumps([
        {"id": "foo", "phase": "implement", "status": "in_progress",
         "handoff": None, "blocked_reason": None}
    ]))
    assert _v.check_state_tasks_consistency(tmp_path, "foo") == []


def test_check_state_tasks_consistency_mismatch(tmp_path):
    (tmp_path / ".sdd").mkdir()
    (tmp_path / ".sdd" / "state.json").write_text(
        json.dumps({"tier": 2, "phase": "implement", "feature": "foo"})
    )
    (tmp_path / ".sdd" / "tasks.json").write_text(json.dumps([
        {"id": "bar", "phase": "implement", "status": "in_progress",
         "handoff": None, "blocked_reason": None}
    ]))
    errors = _v.check_state_tasks_consistency(tmp_path, "foo")
    assert any("foo" in e for e in errors)


# ---------------------------------------------------------------------------
# check_tasks_md_consistency
# ---------------------------------------------------------------------------

def test_check_tasks_md_not_verify_skips(tmp_path):
    (tmp_path / ".sdd").mkdir()
    (tmp_path / ".sdd" / "state.json").write_text(
        json.dumps({"tier": 2, "phase": "implement", "feature": "foo"})
    )
    assert _v.check_tasks_md_consistency(tmp_path, "foo") == []


def test_check_tasks_md_all_checked(tmp_path):
    (tmp_path / ".sdd").mkdir()
    (tmp_path / ".sdd" / "state.json").write_text(
        json.dumps({"tier": 2, "phase": "verify", "feature": "foo"})
    )
    (tmp_path / "specs" / "foo").mkdir(parents=True)
    (tmp_path / "specs" / "foo" / "tasks.md").write_text(
        "# Tasks\n- [x] T1: done task. AC: SAC-1\n"
    )
    assert _v.check_tasks_md_consistency(tmp_path, "foo") == []


def test_check_tasks_md_unchecked_item_error(tmp_path):
    (tmp_path / ".sdd").mkdir()
    (tmp_path / ".sdd" / "state.json").write_text(
        json.dumps({"tier": 2, "phase": "verify", "feature": "foo"})
    )
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


def test_sh_valid_active_exits_0():
    result = _run_sh("valid-active")
    assert result.returncode == 0


def test_sh_valid_done_exits_0():
    result = _run_sh("valid-done")
    assert result.returncode == 0


def test_sh_invalid_state_mismatch_exits_1():
    result = _run_sh("invalid-state-mismatch")
    assert result.returncode == 1


def test_sh_invalid_traceability_exits_1():
    result = _run_sh("invalid-traceability")
    assert result.returncode == 1


def test_sh_invalid_tasks_incomplete_exits_1():
    result = _run_sh("invalid-tasks-incomplete")
    assert result.returncode == 1


def test_sh_valid_active_snapshot_and_evidence_exits_0():
    result = _run_sh("valid-active")
    assert result.returncode == 0


def test_sh_invalid_snapshot_hash_mismatch_exits_1():
    result = _run_sh("invalid-snapshot-hash-mismatch")
    assert result.returncode == 1
    assert "issue-snapshot.json: body_hash does not match" in result.stderr


def test_sh_invalid_evidence_bad_commit_exits_1():
    result = _run_sh("invalid-evidence-bad-commit")
    assert result.returncode == 1
    assert "evidence.json: commit_sha not found" in result.stderr


def test_sh_missing_state_json_exits_1(tmp_path):
    sh = ROOT / "integration" / "ci" / "sdd-validate.sh"
    result = _subprocess.run(
        ["bash", str(sh), "--root", str(tmp_path)],
        capture_output=True, text=True,
    )
    assert result.returncode == 1


# ---------------------------------------------------------------------------
# Fix 1: check_state_tasks_consistency — phase mismatch detection
# ---------------------------------------------------------------------------

def test_check_state_tasks_consistency_phase_mismatch(tmp_path):
    (tmp_path / ".sdd").mkdir()
    (tmp_path / ".sdd" / "state.json").write_text(
        json.dumps({"tier": 2, "phase": "verify", "feature": "foo"})
    )
    (tmp_path / ".sdd" / "tasks.json").write_text(json.dumps([
        {"id": "foo", "phase": "implement", "status": "in_progress",
         "handoff": None, "blocked_reason": None}
    ]))
    errors = _v.check_state_tasks_consistency(tmp_path, "foo")
    assert any("phase" in e for e in errors)


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
    (tmp_path / ".sdd").mkdir()
    (tmp_path / ".sdd" / "state.json").write_text(json.dumps({
        "tier": 2,
        "phase": "implement",
        "feature": "issue-snapshot",
    }))
    (tmp_path / ".sdd" / "tasks.json").write_text(json.dumps([
        {
            "id": "issue-snapshot",
            "phase": "implement",
            "status": "in_progress",
            "handoff": None,
            "blocked_reason": None,
        }
    ]))
    feature_dir = tmp_path / "specs" / "issue-snapshot"
    feature_dir.mkdir(parents=True)
    (feature_dir / "spec.md").write_text(
        "# Spec\n## 受入条件\n- [ ] SAC-1: criterion one\n"
    )
    (feature_dir / "tasks.md").write_text("# Tasks\n- [x] T1: done\n")
    (feature_dir / "traceability.json").write_text(json.dumps({
        "issue": 53,
        "issue_url": "https://github.com/owner/repo/issues/53",
        "feature": "issue-snapshot",
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
        ["bash", str(ROOT / "integration" / "ci" / "sdd-validate.sh"), "--root", str(tmp_path)],
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
    feature = "evidence-validation"
    (tmp_path / ".sdd").mkdir()
    (tmp_path / ".sdd" / "state.json").write_text(json.dumps({
        "tier": 2,
        "phase": "implement",
        "feature": feature,
    }))
    (tmp_path / ".sdd" / "tasks.json").write_text(json.dumps([
        {
            "id": feature,
            "phase": "implement",
            "status": "in_progress",
            "handoff": None,
            "blocked_reason": None,
        }
    ]))

    feature_dir = tmp_path / "specs" / feature
    feature_dir.mkdir(parents=True)
    (feature_dir / "spec.md").write_text(
        "# Spec\n## 受入条件\n- [ ] SAC-1: criterion one\n"
    )
    (feature_dir / "tasks.md").write_text("# Tasks\n- [x] T1: done\n")
    (feature_dir / "traceability.json").write_text(json.dumps({
        "issue": 54,
        "issue_url": "https://github.com/owner/repo/issues/54",
        "feature": feature,
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
        ["bash", str(ROOT / "integration" / "ci" / "sdd-validate.sh"), "--root", str(tmp_path)],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "evidence.json not found" in result.stderr
