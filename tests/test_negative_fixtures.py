"""Negative fixture tests: validator must ERROR on invalid fixtures, PASS on valid ones."""
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "integration" / "ci"))
import sdd_state  # noqa: E402

FIXTURES = ROOT / "tests" / "fixtures"
VALIDATOR = ROOT / "integration" / "ci" / "sdd-validate.sh"
BRANCH = "t2/99-my-feature"
FEATURE = "99-my-feature"
NO_FREEZE = {"fixture-missing-freeze"}
PR_CASES = {"fixture-incomplete-tasks", "fixture-incomplete-tasks-valid", "fixture-missing-freeze", "fixture-missing-freeze-valid"}


def _run_validator(fixture_path: Path, pr: bool = False) -> subprocess.CompletedProcess:
    cmd = ["bash", str(VALIDATOR), "--root", str(fixture_path), "--branch", BRANCH]
    if pr:
        cmd.append("--pr")
    return subprocess.run(cmd, capture_output=True, text=True)


def _prepare(fixture_name: str, tmp_path: Path) -> Path:
    """Copy fixture to tmp_path, inject real HEAD SHA into evidence.json,
    create freeze.json, and apply per-fixture tampering (see each README)."""
    src = FIXTURES / fixture_name
    dest = tmp_path / fixture_name
    shutil.copytree(src, dest)
    spec_dir = dest / "specs" / FEATURE
    evidence_path = spec_dir / "evidence.json"
    if evidence_path.exists():
        try:
            sha = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                capture_output=True, text=True, check=True,
                cwd=str(ROOT),
            ).stdout.strip()
        except subprocess.CalledProcessError:
            pytest.skip("git rev-parse HEAD failed — skipping fixture needing evidence SHA")
        evidence = json.loads(evidence_path.read_text())
        if fixture_name != "fixture-invalid-evidence-commit":
            evidence["commit_sha"] = sha
        evidence_path.write_text(json.dumps(evidence, indent=2))
    if fixture_name not in NO_FREEZE:
        sdd_state.create_freeze(spec_dir, 2, datetime.now(timezone.utc))
    if fixture_name == "fixture-tampered-freeze":
        with open(spec_dir / "spec.md", "a", encoding="utf-8") as f:
            f.write("\n- SAC-3: added after freeze\n")
    return dest


# ---------------------------------------------------------------------------
# Negative fixtures — validator must exit 1 with expected error fragment
# ---------------------------------------------------------------------------

NEGATIVE_CASES = [
    ("fixture-incomplete-tasks",    "unchecked item"),
    ("fixture-no-test-mapping",     "test file not found"),
    ("fixture-orphan-spec-ac",      "not found in spec.md"),
    ("fixture-duplicate-spec-ac",         "duplicate spec_ac"),
    ("fixture-scope-out-no-followup",     "missing HTTP(S) followup_issue"),
    ("fixture-weakened-ac",               "snapshot AC not tracked in traceability"),
    ("fixture-stale-snapshot-hash",       "body_hash does not match"),
    ("fixture-untracked-issue-ac",        "traceability AC not in snapshot"),
    ("fixture-invalid-evidence-commit",   "commit_sha not found in git repository"),
    ("fixture-non-test-count",            "is not of type 'null'"),
    ("fixture-missing-test-count",        "is not of type 'integer'"),
    ("fixture-tampered-freeze",           "freeze.json"),
    ("fixture-snapshot-issue-mismatch",   "does not match directory"),
    ("fixture-missing-handoff",           "handoff.md"),
    ("fixture-missing-freeze",            "freeze.json not found"),
]


@pytest.mark.parametrize("fixture_name,expected_fragment", NEGATIVE_CASES)
def test_negative_fixture_fails(fixture_name, expected_fragment, tmp_path):
    fixture_path = _prepare(fixture_name, tmp_path)
    result = _run_validator(fixture_path, pr=fixture_name in PR_CASES)
    assert result.returncode == 1, (
        f"{fixture_name}: expected exit 1, got {result.returncode}\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )
    assert expected_fragment in result.stderr, (
        f"{fixture_name}: expected '{expected_fragment}' in stderr\n"
        f"stderr: {result.stderr}"
    )


# ---------------------------------------------------------------------------
# Valid fixtures — validator must exit 0
# ---------------------------------------------------------------------------

VALID_CASES = [
    "fixture-incomplete-tasks-valid",
    "fixture-no-test-mapping-valid",
    "fixture-orphan-spec-ac-valid",
    "fixture-duplicate-spec-ac-valid",
    "fixture-scope-out-no-followup-valid",
    "fixture-weakened-ac-valid",
    "fixture-stale-snapshot-hash-valid",
    "fixture-untracked-issue-ac-valid",
    "fixture-invalid-evidence-commit-valid",
    "fixture-non-test-count-valid",
    "fixture-missing-test-count-valid",
    "fixture-tampered-freeze-valid",
    "fixture-snapshot-issue-mismatch-valid",
    "fixture-missing-handoff-valid",
    "fixture-missing-freeze-valid",
]


@pytest.mark.parametrize("fixture_name", VALID_CASES)
def test_valid_fixture_passes(fixture_name, tmp_path):
    fixture_path = _prepare(fixture_name, tmp_path)
    result = _run_validator(fixture_path, pr=fixture_name in PR_CASES)
    assert result.returncode == 0, (
        f"{fixture_name}: expected exit 0, got {result.returncode}\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )
