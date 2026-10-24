from pathlib import Path
import re

ROOT = Path(__file__).parents[1]

LEGACY_FILES = [
    "orchestration/schema/state.schema.json",
    "orchestration/schema/tasks.schema.json",
    "templates/sdd-state.example.json",
    "templates/sdd-state.schema.json",
    "orchestration/tools/kanban.sh",
    "orchestration/tools/kanban-html.sh",
    "integration/ci/kanban-pages.yml",
]

SCAN = ["rules", "orchestration", "integration", "templates", "docs", "README.md"]
PATTERN = re.compile(r"state\.json|tasks\.json|kanban", re.IGNORECASE)


def test_legacy_files_removed():
    for path in LEGACY_FILES:
        assert not (ROOT / path).exists(), path


def test_no_legacy_instructions():
    hits = []
    for entry in SCAN:
        base = ROOT / entry
        files = [base] if base.is_file() else sorted(p for p in base.rglob("*") if p.is_file())
        for f in files:
            rel = f.relative_to(ROOT).as_posix()
            if rel == "docs/migration.md" or "__pycache__" in rel:
                continue
            try:
                text = f.read_text()
            except UnicodeDecodeError:
                continue
            for n, line in enumerate(text.splitlines(), 1):
                if PATTERN.search(line):
                    hits.append(f"{rel}:{n}")
    assert not hits, hits
