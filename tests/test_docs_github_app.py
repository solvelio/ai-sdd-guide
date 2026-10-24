"""Docs for running the SDD board with a GitHub App (78-github-app-token, SAC-5/SAC-7)."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def read(rel):
    return (ROOT / rel).read_text(encoding="utf-8")


def test_issue_tracker_doc_has_app_section():
    text = read("docs/04-issue-tracker.md")
    for word in ("Read and write", "Read-only", "Webhook", "1Password",
                 "sdd-app-secret.sh", "app_id", "All repositories"):
        assert word in text, word
    assert "Only select repositories" not in text


def test_migration_has_v31_section():
    text = read("docs/migration.md")
    for word in ("v3.1", "SDD_APP_PRIVATE_KEY", "sdd-app-secret.sh", "SDD_PROJECT_TOKEN",
                 "All repositories"):
        assert word in text, word
    assert "Only select repositories" not in text


def _pat_sentence_ok(text):
    """Some SDD_PROJECT_TOKEN line, within +-3 lines, states classic/repo/project/read:org."""
    lines = text.splitlines()
    for n, line in enumerate(lines):
        if "SDD_PROJECT_TOKEN" in line:
            window = "\n".join(lines[max(0, n - 3):n + 4])
            if all(w in window for w in ("classic", "`repo`", "`project`", "`read:org`")):
                return True
    return False


def test_pat_scope_wording():
    for rel in ("README.md", "docs/04-issue-tracker.md", "docs/migration.md",
                "integration/issue-tracker/README.md", "integration/ci/sdd-board.yml"):
        text = read(rel)
        if "SDD_PROJECT_TOKEN" in text:
            assert _pat_sentence_ok(text), rel
    hint = read("integration/ci/sdd_board.py")
    for word in ("repo", "project", "read:org"):
        assert word in hint, word
