"""This repository itself uses the new SDD state model (branch name + freeze.json + board)."""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "integration" / "ci"))

from sdd_state import freeze_status  # noqa: E402

FEATURE = "73-github-projects-board"


def test_legacy_state_files_absent():
    assert not (ROOT / ".sdd" / "state.json").exists()
    assert not (ROOT / ".sdd" / "tasks.json").exists()


def test_board_json_present():
    data = json.loads((ROOT / ".sdd" / "board.json").read_text(encoding="utf-8"))
    assert isinstance(data["owner"], str) and data["owner"]
    assert isinstance(data["project"], int) and not isinstance(data["project"], bool)


def test_board_workflow_present():
    wf = ROOT / ".github" / "workflows" / "sdd-board.yml"
    assert wf.is_file()
    assert "orchestration/tools/sdd-board.sh" in wf.read_text(encoding="utf-8")


def test_feature_freeze_valid():
    assert freeze_status(ROOT / "specs" / FEATURE, 2)[0] == "valid"


def test_validator_passes_for_this_feature():
    r = subprocess.run(
        ["bash", str(ROOT / "integration" / "ci" / "sdd-validate.sh"),
         "--root", str(ROOT), "--branch", "t2/" + FEATURE],
        capture_output=True, text=True)
    if (ROOT / "specs" / FEATURE / "evidence.json").exists():
        assert r.returncode == 0, r.stderr
    else:
        # evidence.json is a verify-phase artifact; nothing else may fail.
        assert r.returncode == 1, r.stderr
        errors = [l for l in r.stderr.splitlines() if l.startswith("ERROR:")]
        assert len(errors) == 1 and "evidence.json not found" in errors[0], r.stderr
