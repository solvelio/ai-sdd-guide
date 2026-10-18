"""sdd-check.yml must work when copied into a consumer with the guide at vendor/ai-sdd-guide."""
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).parents[1]
WORKFLOW = ROOT / "integration" / "ci" / "sdd-check.yml"
MIGRATION = ROOT / "docs" / "migration.md"
UPDATE_SH = ROOT / "integration" / "update.sh"
README = ROOT / "README.md"
SUBMODULE_VALIDATOR = "vendor/ai-sdd-guide/integration/ci/sdd-validate.sh"


def _job_block(text: str, job: str) -> str:
    match = re.search(rf"^  {job}:\n(.*?)(?=^  \S|\Z)", text, re.M | re.S)
    assert match, f"job '{job}' not found"
    return match.group(1)


def _step_run_script(text: str, step_name: str) -> str:
    lines = text.splitlines()
    start = next(i for i, line in enumerate(lines) if line.strip() == f"- name: {step_name}")
    run_idx = next(i for i in range(start + 1, len(lines)) if lines[i].strip() == "run: |")
    body_indent = len(lines[run_idx]) - len(lines[run_idx].lstrip()) + 2
    body = []
    for line in lines[run_idx + 1:]:
        if line.strip() and len(line) - len(line.lstrip()) < body_indent:
            break
        body.append(line[body_indent:])
    return "\n".join(body) + "\n"


def _assert_submodule_fix(workflow_text: str) -> None:
    sdd_job = _job_block(workflow_text, "sdd")
    checkout = re.search(r"- uses: actions/checkout@v\d+\n((?:\s{8,}.*\n)*)", sdd_job)
    assert checkout and re.search(r"^\s+submodules: true$", checkout.group(1), re.M), \
        "sdd job checkout must set 'submodules: true'"
    run = _step_run_script(workflow_text, "Run sdd-validate")
    assert f"bash {SUBMODULE_VALIDATOR} --root ." in run


def test_sdd_job_checkout_fetches_submodules():
    _assert_submodule_fix(WORKFLOW.read_text())


def test_sdd_validate_step_runs_in_consumer_layout(tmp_path):
    (tmp_path / "vendor").mkdir()
    (tmp_path / "vendor" / "ai-sdd-guide").symlink_to(ROOT)
    (tmp_path / ".sdd").mkdir()
    (tmp_path / ".sdd" / "state.json").write_text(
        json.dumps({"tier": 0, "phase": "done", "note": "no active feature"})
    )
    script = _step_run_script(WORKFLOW.read_text(), "Run sdd-validate")
    result = subprocess.run(
        ["bash", "-e", "-c", script], cwd=tmp_path, capture_output=True, text=True
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_migration_guide_uses_submodule_validator_path():
    text = MIGRATION.read_text()
    invocations = re.findall(r"^bash (\S*sdd-validate\.sh)", text, re.M)
    assert invocations, "no sdd-validate.sh invocation found in docs/migration.md"
    wrong = [p for p in invocations if p != SUBMODULE_VALIDATOR]
    assert not wrong, f"non-submodule validator paths in docs/migration.md: {wrong}"


def test_update_sh_preserves_submodule_fix(tmp_path):
    result = subprocess.run(
        ["bash", str(UPDATE_SH), str(tmp_path)],
        stdin=subprocess.DEVNULL, capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    copied = tmp_path / ".github" / "workflows" / "sdd-check.yml"
    _assert_submodule_fix(copied.read_text())


def test_readme_states_fixed_submodule_path():
    line = next(l for l in README.read_text().splitlines() if "git submodule add" in l or "submodule として追加" in l)
    assert "vendor/ai-sdd-guide" in line and "固定" in line, line
    assert "任意" not in line, line
