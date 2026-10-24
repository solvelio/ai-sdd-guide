"""integration/ci/sdd-board.yml keeps the GitHub Projects board in sync (checked as text)."""
import re
from pathlib import Path

ROOT = Path(__file__).parents[1]
TEXT = (ROOT / "integration" / "ci" / "sdd-board.yml").read_text()
CLI = "vendor/ai-sdd-guide/orchestration/tools/sdd-board.sh"


def _on_block(key: str) -> str:
    m = re.search(rf"^  {key}:\n(.*?)(?=^  \S|^\S|\Z)", TEXT, re.M | re.S)
    assert m, f"trigger '{key}' not found"
    return m.group(1)


def _run_blocks() -> list:
    lines = TEXT.splitlines()
    blocks = []
    for i, line in enumerate(lines):
        if re.match(r"\s*run: \|\s*$", line):
            indent = len(line) - len(line.lstrip())
            body = []
            for nxt in lines[i + 1:]:
                if nxt.strip() and len(nxt) - len(nxt.lstrip()) <= indent:
                    break
                body.append(nxt)
            blocks.append("\n".join(body))
    return blocks


def test_triggers():
    issues = _on_block("issues")
    assert "opened" in issues and "closed" in issues
    pr = _on_block("pull_request")
    for t in ("opened", "synchronize", "reopened", "closed"):
        assert t in pr


def test_uses_project_token_secret():
    assert "secrets.SDD_PROJECT_TOKEN" in TEXT


def test_missing_secret_warns_and_succeeds():
    assert "::warning::" in TEXT
    assert "exit 0" in TEXT


def test_pr_job_adds_tier_label():
    assert "gh pr edit" in TEXT and "--add-label" in TEXT and "sdd:tier-" in TEXT
    assert "gh label create" in TEXT
    assert "github.token" in TEXT
    assert "pull-requests: write" in TEXT and "issues: write" in TEXT


def test_calls_board_subcommands():
    assert f"{CLI} set --issue" in TEXT and "backlog" in TEXT
    assert f"{CLI} close" in TEXT and "github.event.issue.state_reason" in TEXT
    assert f"{CLI} pr --branch" in TEXT
    assert "github.head_ref" in TEXT and "github.event.pull_request.merged" in TEXT


def test_checkout_pr_head_with_submodules():
    assert "github.event.pull_request.head.sha" in TEXT
    assert "submodules: true" in TEXT
    assert "secrets.SDD_GUIDE_TOKEN || github.token" in TEXT


def test_no_expression_interpolation_in_run_scripts():
    blocks = _run_blocks()
    assert blocks
    for block in blocks:
        assert "${{" not in block, block


def test_forbidden_strings_absent():
    for s in ("state.json", "tasks.json", "kanban"):
        assert s not in TEXT
