from pathlib import Path
import json
import re

ROOT = Path(__file__).parents[1]


def read(path):
    return (ROOT / path).read_text()


# --- core.md ---

def test_core_untracked_ac_stop():
    content = read("rules/core.md")
    assert "every Issue AC must appear in" in content
    assert "STOP — do not freeze and do not implement" in content


def test_core_frozen_artifact_immutable():
    content = read("rules/core.md")
    assert "Frozen artifacts" in content
    assert "traceability.json" in content
    assert "only permitted post-freeze edit" in content
    assert "[ ] → [x]" in content
    assert "explicit unfreeze" in content


# --- issue-intake.md ---

def test_intake_freeze_gate_section():
    content = read("rules/issue-intake.md")
    assert "## Tier 2 freeze gate" in content
    assert "<issue番号>-AC<連番>" in content
    assert "traceability.json" in content
    assert "freeze is blocked" in content


def test_intake_out_of_scope_followup_required():
    content = read("rules/issue-intake.md")
    assert "followup_issue" in content
    assert "No orphaned scope-outs allowed" in content


def test_intake_weakened_spec_approval():
    content = read("rules/issue-intake.md")
    assert "weaker than the Issue" in content
    assert "explicit human approval" in content


def test_intake_never_freeze_untracked():
    content = read("rules/issue-intake.md")
    assert "Never freeze a Tier 2 spec that has untracked Issue ACs" in content


# --- workflow.md ---

def test_workflow_freeze_step_3b():
    content = read("rules/workflow.md")
    assert "3b. Traceability" in content
    assert "sdd-validate.sh" in content
    assert "diff summary of Issue ACs vs" in content


def test_workflow_verify_sdd_reviewer_items():
    content = read("rules/workflow.md")
    assert "sdd-reviewer must also verify" in content
    assert "tracked to a spec AC" in content
    assert "followup_issue URL" in content
    assert "branch name" in content
    assert "schema-valid" in content
    assert "All task checkboxes in tasks.md are complete" in content
    assert "runnable test, not a manual/visual check" in content


def test_workflow_freeze_uses_freeze_json():
    content = read("rules/workflow.md")
    assert "sdd-freeze.sh" in content
    assert "freeze.json" in content


# --- orchestration.md ---

def test_orchestration_handoff_gate():
    content = read("orchestration/rules/orchestration.md")
    assert "Before generating" in content
    assert "sdd-validate.sh" in content
    assert "do not generate" in content
    assert "handoff for an incomplete spec" in content


def test_orchestration_issue_diff_summary_and_independent_review():
    content = read("orchestration/rules/orchestration.md")
    assert "Issue Diff Summary" in content
    assert "original Issue body" in content
    assert "frozen spec" in content
    assert "Independent Reviewer Requirement" in content
    assert "MUST invoke the `sdd-reviewer` subagent" in content


def test_orchestration_stop_runs_board_sync():
    content = read("orchestration/rules/orchestration.md")
    assert "sdd-board.sh sync" in content
    assert "display kanban" not in content.lower()


# --- conventions.md ---

def test_conventions_checkbox_only():
    content = read("rules/conventions.md")
    assert "only permitted change to `tasks.md` is checking" in content
    assert "out-of-spec and must be rejected" in content


# --- sdd-reviewer prompts ---

def test_sdd_reviewer_prompt_issue_access_and_traceability_checks():
    for path in [
        "integration/prompts/sdd-reviewer-prompt.md",
        "integration/agents/sdd-reviewer.md",
    ]:
        content = read(path)
        assert "Issue URL" in content
        assert "Issue Body" in content
        assert "Mandatory Issue Traceability Check" in content
        assert "verify the following 8 items" in content
        assert "AC Traceability" in content
        assert "Audit Trail" in content


def test_sdd_reviewer_prompt_bootstrap_and_evidence_count():
    for path in [
        "integration/prompts/sdd-reviewer-prompt.md",
        "integration/agents/sdd-reviewer.md",
    ]:
        content = read(path)
        assert "Bootstrap Exemption Handling" in content
        assert "separate exemption-range findings from non-exempt findings" in content
        assert "Evidence Test Count" in content
        assert "actual test runner execution counts" in content


def test_sdd_reviewer_checks_branch_and_freeze():
    for path in [
        "integration/prompts/sdd-reviewer-prompt.md",
        "integration/agents/sdd-reviewer.md",
    ]:
        content = read(path)
        assert "freeze.json" in content
        assert "t<Tier>/<Issue番号>-<名前>" in content
        assert "state.json" not in content
        assert "tasks.json" not in content


def test_tasks_template_completion_has_no_checkboxes():
    content = read("templates/tasks.md")
    assert "## 完了の定義" in content
    tail = content.split("## 完了の定義", 1)[1]
    assert "- [ ]" not in tail


# --- issue-48 SDD artifacts ---

def test_issue_48_traceability_references_defined_artifacts():
    traceability = json.loads(read("specs/issue-48/traceability.json"))
    spec = read("specs/issue-48/spec.md")
    tasks = read("specs/issue-48/tasks.md")

    for entry in traceability["entries"]:
        spec_ac = entry["spec_ac"]
        task = entry["task"]
        test = entry["test"]

        assert re.search(rf"\b{re.escape(spec_ac)}\b", spec)
        assert re.search(rf"[-\s]\[.\]\s+{re.escape(task)}:", tasks)
        assert (ROOT / test.split("::", 1)[0]).exists()
