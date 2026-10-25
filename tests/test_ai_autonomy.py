"""Checks for the AI-autonomous default flow (#89).

Human involvement is limited to the initial question, escalation, and PR
review/merge. Everything else is wording in rules/docs, so these tests check
that required phrases are present and old stop/approval phrases are gone.
"""
import re
from pathlib import Path

ROOT = Path(__file__).parents[1]

ORCHESTRATION = "orchestration/rules/orchestration.md"

OLD_STOP_PHRASES = [
    "Phase stopping rule",
    "wait for explicit human instruction",
    "Never cross a phase boundary automatically",
    "same session as freeze",
    "Human approves before freezing",
    "human approval before freezing",
    "after human approval",
    "Wait for a human to escalate",
    "Do NOT start implementing",
    "Do NOT start verify",
    "人間の承認のあと",
    "人間承認を得る",
    "同一セッション",
    "人間から「実装して」",
    "sdd-board.sh sync → 止まる",
]

RULE_FILES = [
    "rules/core.md",
    "rules/workflow.md",
    "rules/issue-intake.md",
    "rules/subagents.md",
    ORCHESTRATION,
]


def read(path):
    return (ROOT / path).read_text()


def section(text, heading):
    """Return the body of a `## ` section (up to the next `## ` heading)."""
    m = re.search(rf"^{re.escape(heading)}$", text, re.M)
    assert m, heading
    rest = text[m.end():]
    m = re.search(r"^## ", rest, re.M)
    return rest[: m.start()] if m else rest


def assert_no_old_stop_phrases(paths):
    found = []
    for path in paths:
        text = read(path).lower()
        for phrase in OLD_STOP_PHRASES:
            if phrase.lower() in text:
                found.append((path, phrase))
    assert found == []


# --- T1: rules ---

def test_orchestration_defines_human_touchpoints_and_autonomous_flow():
    content = read(ORCHESTRATION)
    for heading in [
        "## Human touchpoints",
        "## Autonomous flow",
        "## Spec review",
        "## Escalation conditions",
        "## PR decision log",
    ]:
        assert re.search(rf"^{re.escape(heading)}$", content, re.M), heading
    assert "never merge" in content.lower()
    assert "Initial question" in content
    assert "sdd:tier-N" in content
    assert "sdd-board.sh sync" in content


def test_escalation_conditions_listed_and_referenced():
    body = section(read(ORCHESTRATION), "## Escalation conditions")
    for n in range(1, 7):
        assert re.search(rf"^{n}\. ", body, re.M), n
    assert "comment the reason on the Issue" in body
    for path in ["rules/core.md", "rules/workflow.md", "rules/issue-intake.md"]:
        assert "Escalation conditions" in read(path), path


def test_rules_have_no_old_stop_phrases():
    assert_no_old_stop_phrases(RULE_FILES)


def test_rules_require_spec_review_before_freeze():
    for path in ["rules/workflow.md", "rules/issue-intake.md", "rules/subagents.md", ORCHESTRATION]:
        assert "spec-reviewer" in read(path), path
    for path in ["rules/workflow.md", ORCHESTRATION]:
        assert "APPROVE" in read(path), path


def test_weakening_acs_still_needs_human_approval():
    assert "explicit human approval" in read("rules/issue-intake.md")


# --- T2: spec-reviewer and PR body template ---

SPEC_REVIEWER_FILES = [
    "integration/agents/spec-reviewer.md",
    "integration/prompts/spec-reviewer-prompt.md",
]


def test_spec_reviewer_files_define_verdicts_and_limit():
    for path in SPEC_REVIEWER_FILES:
        content = read(path)
        for phrase in [
            "APPROVE",
            "CHANGES",
            "ESCALATE",
            "3 rounds",
            "Spec review: APPROVE",
            "issue-snapshot.json",
            "traceability.json",
        ]:
            assert phrase in content, (path, phrase)
        assert re.search(r"Do NOT[^\n]*edit", content), path


def test_pr_body_template_has_ai_decision_log():
    content = read("templates/pr-body.md")
    for phrase in ["## AI の判断", "spec レビュー", "不明点", "指摘", "スコープ外"]:
        assert phrase in content, phrase
    assert "templates/pr-body.md" in read(ORCHESTRATION)


# --- T3: surrounding docs, hooks, templates ---

SURROUNDING_FILES = [
    "integration/hooks/skill-reminder.sh",
    "integration/hooks/codex-skill-reminder.sh",
    "integration/AGENTS.md.example",
    "orchestration/integration/AGENTS-patch.md.example",
    "orchestration/templates/handoff.md.example",
    "integration/agents/sdd-reviewer.md",
    "integration/prompts/sdd-reviewer-prompt.md",
    "docs/00-overview.md",
    "docs/01-workflow.md",
    "docs/02-roles.md",
    "docs/03-faq.md",
    "docs/04-issue-tracker.md",
    "README.md",
]


def test_surrounding_docs_have_no_old_stop_phrases():
    assert_no_old_stop_phrases(SURROUNDING_FILES)


def test_spec_phase_reminder_mentions_spec_reviewer(tmp_path):
    from test_skill_reminder import CLAUDE, CODEX, _repo, _run, _spec

    repo = _repo(tmp_path, "t2/1-feature")
    _spec(repo, "1-feature", ["spec.md"])
    for hook in [CLAUDE, CODEX]:
        out = _run(hook, repo)
        assert "spec-reviewer" in out, hook
        assert "human approval" not in out.lower(), hook


def test_docs_describe_human_touchpoints():
    body = section(read("docs/02-roles.md"), "## 人間")
    for phrase in ["最初の質問", "問い合わせ", "PR"]:
        assert phrase in body, phrase
    assert "spec-reviewer" in read("docs/01-workflow.md")
