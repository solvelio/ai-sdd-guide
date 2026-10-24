"""integration/ci/sdd-board.yml keeps the GitHub Projects board in sync (checked as text)."""
import re
from pathlib import Path

ROOT = Path(__file__).parents[1]
TEMPLATE = ROOT / "integration" / "ci" / "sdd-board.yml"
REPO_COPY = ROOT / ".github" / "workflows" / "sdd-board.yml"
TEXT = TEMPLATE.read_text()
REPO_TEXT = REPO_COPY.read_text()
CLI = "vendor/ai-sdd-guide/orchestration/tools/sdd-board.sh"


def _on_block(key: str) -> str:
    m = re.search(rf"^  {key}:\n(.*?)(?=^  \S|^\S|\Z)", TEXT, re.M | re.S)
    assert m, f"trigger '{key}' not found"
    return m.group(1)


def _steps(text: str = None) -> list:
    text = TEXT if text is None else text
    parts = re.split(r"(?m)^      - (?=name:|uses:)", text)[1:]
    return parts


def _step(name: str) -> str:
    for st in _steps():
        if st.startswith(f"name: {name}"):
            return st
    raise AssertionError(f"step '{name}' not found")


BOARD_STEPS = ("Issue opened -> backlog", "Issue closed -> done", "PR event -> board")
TOKEN_EXPR = "${{ steps.app.outputs.token || secrets.SDD_PROJECT_TOKEN }}"


def _run_blocks(text: str = None) -> list:
    lines = (TEXT if text is None else text).splitlines()
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


def test_app_token_step():
    st = _step("Create App token")
    assert "id: app" in st
    assert "if: steps.auth.outputs.mode == 'app'" in st
    for s in (
        "actions/create-github-app-token@v2",
        "app-id: ${{ steps.auth.outputs.app_id }}",
        "private-key: ${{ secrets.SDD_APP_PRIVATE_KEY }}",
        "owner: ${{ steps.auth.outputs.owner }}",
        "repositories: ${{ github.event.repository.name }}",
    ):
        assert s in st
    assert "continue-on-error" not in st


def test_auth_mode_step():
    st = _step("Choose board token")
    assert "id: auth" in st
    assert "auth-mode" in st
    assert "SDD_HAS_APP_KEY" in st and "SDD_HAS_PAT" in st
    assert '>> "$GITHUB_OUTPUT"' in st


def test_board_steps_use_app_or_pat_token():
    for name in BOARD_STEPS:
        assert f"GH_TOKEN: {TOKEN_EXPR}" in _step(name), name


def test_none_mode_warns_and_skips():
    for name in BOARD_STEPS:
        m = re.search(r"(?m)^        if: (.*)$", _step(name))
        assert m, name
        assert "steps.auth.outputs.mode == 'app' || steps.auth.outputs.mode == 'pat'" in m.group(1)


def test_label_step_uses_github_token():
    assert "GH_TOKEN: ${{ github.token }}" in _step("Add tier label to PR")


def test_header_documents_auth_and_pat_scopes():
    header = TEXT.split("\nname:", 1)[0]
    for s in ("SDD_APP_PRIVATE_KEY", "SDD_PROJECT_TOKEN", "repo", "project", "read:org"):
        assert s in header


def test_repo_copy_matches_template():
    def norm(t):
        keep = [
            l.replace("vendor/ai-sdd-guide/", "")
            for l in t.splitlines()
            if "submodules: true" not in l and "SDD_GUIDE_TOKEN" not in l
        ]
        return [l for l in keep if not l.startswith("# Copy to") and not l.startswith("# and the board") and not l.startswith("# Self-hosted")]

    assert norm(TEXT) == norm(REPO_TEXT)


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
    for text in (TEXT, REPO_TEXT):
        blocks = _run_blocks(text)
        assert blocks
        for block in blocks:
            assert "${{" not in block, block


def test_forbidden_strings_absent():
    for s in ("state.json", "tasks.json", "kanban"):
        assert s not in TEXT and s not in REPO_TEXT
