"""Docs describe one board per repository (#91)."""
import re
from pathlib import Path

ROOT = Path(__file__).parents[1]
README = ROOT / "README.md"
TRACKER = ROOT / "docs" / "04-issue-tracker.md"
INTAKE = ROOT / "rules" / "issue-intake.md"
MIGRATION = ROOT / "docs" / "migration.md"


def read(p):
    return p.read_text(encoding="utf-8")


def test_docs_describe_per_repo_board():
    for p in (README, TRACKER, INTAKE):
        text = read(p)
        assert "アカウントで 1 枚" not in text, p
        assert "one board per account" not in text.lower(), p
        for line in text.splitlines():
            assert not ("board.json" in line and ("コピー" in line or "copy" in line.lower())), \
                "%s: %s" % (p.name, line)
    assert "リポジトリごとに 1 枚" in read(README)
    assert "リポジトリごとに 1 枚" in read(TRACKER)
    assert "one board per repository" in read(INTAKE)


def section(text, heading_re):
    m = re.search(heading_re, text, re.MULTILINE)
    assert m, heading_re
    rest = text[m.end():]
    n = re.search(r"^## ", rest, re.MULTILINE)
    return rest[: n.start()] if n else rest


def test_migration_has_per_repo_section():
    text = read(MIGRATION)
    v41 = section(text, r"^## v4\.1: リポジトリごとのボード（#91）$")
    assert "sdd-board.sh init --new" in v41
    assert "アーカイブ" in v41
    assert "repo:" in v41
    assert "app_id" in v41
    assert re.search(r"鍵[^\n]*配り直し[^\n]*(要らない|不要)", v41)
    v3 = section(text, r"^## v3\b.*$")
    assert "1 アカウントに 1 つ" not in v3
    assert "v4.1" in v3
