"""Migration guide presence and content tests."""
import re
import subprocess
import sys
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


SNAPSHOT_PREFIX = "bash vendor/ai-sdd-guide/integration/ci/sdd-issue-snapshot.sh"
CI_EXAMPLE = re.compile(r"^bash vendor/ai-sdd-guide/integration/ci/([\w.-]+)\.sh\b(.*)$")
GUIDE_PATH = re.compile(r"(?<![\w./-])(?:integration|orchestration)/[\w./-]*")


def test_snapshot_examples_use_submodule_path_without_root():
    lines = [l.strip() for l in GUIDE.read_text().splitlines() if "sdd-issue-snapshot.sh" in l]
    assert lines, "no sdd-issue-snapshot.sh examples in docs/migration.md"
    bad = [l for l in lines if not l.startswith(SNAPSHOT_PREFIX) or "--root" in l]
    assert not bad, f"snapshot examples must start with {SNAPSHOT_PREFIX!r} and not use --root: {bad}"


def test_consumer_sections_use_submodule_paths():
    text = GUIDE.read_text()
    start = text.index("\n## 手順 1")
    end = text.index("\n## 部分移行禁止チェックリスト")
    section = text[start:end]
    bad = [m.group(0) for m in GUIDE_PATH.finditer(section)]
    assert not bad, f"guide paths without vendor/ai-sdd-guide/ prefix: {bad}"


def test_cli_examples_match_cli_options():
    examples = []
    for line in GUIDE.read_text().splitlines():
        m = CI_EXAMPLE.match(line.strip())
        if m:
            examples.append((m.group(1), m.group(2)))
    assert examples, "no bash vendor/ai-sdd-guide/integration/ci/*.sh examples found"
    help_cache = {}
    problems = []
    for name, args in examples:
        sh = ROOT / "integration" / "ci" / f"{name}.sh"
        if not sh.exists():
            problems.append(f"{sh.relative_to(ROOT)} does not exist")
            continue
        if name not in help_cache:
            result = subprocess.run(
                [sys.executable, str(ROOT / "integration" / "ci" / f"{name}.py"), "--help"],
                capture_output=True, text=True, cwd=ROOT,
            )
            assert result.returncode == 0, f"{name}.py --help failed: {result.stderr}"
            help_cache[name] = set(re.findall(r"--[\w-]+", result.stdout))
        for opt in re.findall(r"(?<!\S)--[\w-]+", args):
            if opt not in help_cache[name]:
                problems.append(f"{name}.sh: {opt} not in {name}.py --help")
    assert not problems, problems
