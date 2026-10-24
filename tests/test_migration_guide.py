"""Migration guide presence and content tests."""
from pathlib import Path

ROOT = Path(__file__).parents[1]
GUIDE = ROOT / "docs" / "migration.md"


def test_migration_guide_exists():
    assert GUIDE.exists(), "docs/migration.md does not exist"


def test_migration_guide_has_all_sections():
    text = GUIDE.read_text()
    required = [
        "手順 1:",
        "手順 2:",
        "手順 3:",
        "手順 4:",
        "手順 5:",
        "手順 6:",
        "手順 7:",
    ]
    missing = [s for s in required if s not in text]
    assert not missing, f"Missing sections in docs/migration.md: {missing}"


def test_migration_guide_has_consumer_checklist():
    text = GUIDE.read_text()
    assert "Consumer Update チェックリスト" in text or "consumer update チェックリスト" in text.lower(), \
        "Consumer update checklist not found in docs/migration.md"


def test_migration_guide_has_examples():
    text = GUIDE.read_text()
    assert "例 A" in text or "例A" in text, "Example A (new feature) not found"
    assert "例 B" in text or "例B" in text, "Example B (in-progress feature) not found"


def test_migration_guide_no_retroactive_policy():
    text = GUIDE.read_text()
    assert "遡及変更" in text, "No-retroactive-change policy not stated in docs/migration.md"


def test_migration_guide_no_partial_migration():
    text = GUIDE.read_text()
    assert "部分移行" in text, "No-partial-migration policy not stated in docs/migration.md"


def test_migration_guide_projects_board_section():
    text = (Path(__file__).resolve().parent.parent / "docs" / "migration.md").read_text()
    for s in ["state.json", "tasks.json", ".sdd/board.json", "SDD_PROJECT_TOKEN",
              "sdd-board.yml", "sdd-board.sh init", "git branch -m", "repo:"]:
        assert s in text, s
