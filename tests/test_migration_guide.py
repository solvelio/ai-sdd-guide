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


SUBMODULE_PATH = re.compile(r"vendor/ai-sdd-guide/([^\s`'\"()]+)")


def test_submodule_paths_exist_in_guide():
    missing = []
    for m in SUBMODULE_PATH.finditer(GUIDE.read_text()):
        path = m.group(1)
        if "<" in path:
            continue
        if path.endswith("..."):
            path = path[:-3]
        path = path.rstrip(".,:;、。）")
        if path and not (ROOT / path).exists():
            missing.append(m.group(0))
    assert not missing, f"vendor/ai-sdd-guide/ paths not found in guide: {missing}"


def _section_body(text, heading):
    start = text.index("\n", text.index("\n" + heading) + 1)
    end = text.find("\n## ", start)
    return text[start:end if end != -1 else len(text)]


def test_step4_and_checklist_follow_v3_state_derivation():
    text = GUIDE.read_text()
    step4 = _section_body(text, "## 手順 4:")
    checklist = _section_body(text, "## Consumer Update チェックリスト")
    for name, section in (("手順 4", step4), ("Consumer Update チェックリスト", checklist)):
        assert "schema" not in section.lower(), f"{name} still mentions a schema"
        assert "準拠" not in section, f"{name} still asks for schema compliance"
        assert "```json" not in section, f"{name} still has a JSON example"
    for s in ["t<Tier>/<Issue番号>-<名前>", "specs/", "sdd_state.py phase"]:
        assert s in step4, f"手順 4 does not explain derivation: {s!r} missing"
    state_lines = [l for l in checklist.splitlines() if "state.json" in l or "tasks.json" in l]
    assert len(state_lines) == 1, f"expected one state.json/tasks.json item: {state_lines}"
    line = state_lines[0]
    for s in [".sdd/state.json", ".sdd/tasks.json", "削除", "t<Tier>/<Issue番号>-<名前>"]:
        assert s in line, f"checklist item missing {s!r}: {line}"


def test_step4_heading_has_no_v2_terms():
    heading = next(l for l in GUIDE.read_text().splitlines() if l.startswith("## 手順 4:"))
    assert "手順 4:" in heading
    for s in ["state.json", "tasks.json", "schema"]:
        assert s not in heading, f"手順 4 heading still mentions {s!r}: {heading}"


def test_step5_describes_actual_sdd_check_steps():
    step5 = _section_body(GUIDE.read_text(), "## 手順 5:")
    for s in ["state.json", "phase=done", "State reset gate", "Spec gate"]:
        assert s not in step5, f"手順 5 still mentions {s!r}"
    yml = (ROOT / "integration" / "ci" / "sdd-check.yml").read_text()
    names = re.findall(r"^\s*- name:\s*(.+?)\s*$", yml, re.MULTILINE)
    assert names, "no step names found in sdd-check.yml"
    missing = [n for n in names if f"**{n}**" not in step5]
    assert not missing, f"手順 5 does not mention sdd-check.yml steps: {missing}"


def test_step7_and_examples_have_no_state_files():
    text = GUIDE.read_text()
    for heading in ("## 手順 7:", "## 具体例"):
        body = _section_body(text, heading)
        for s in ["state.json", "tasks.json"]:
            assert s not in body, f"{heading} still mentions {s!r}"


def test_partial_migration_checklist_lists_existing_schemas():
    body = _section_body(GUIDE.read_text(), "## 部分移行禁止チェックリスト")
    lines = [l for l in body.splitlines() if "`orchestration/schema/`" in l]
    assert len(lines) == 1, f"expected one orchestration/schema/ item: {lines}"
    m = re.search(r"—\s*(.+?)\s+schema\s*$", lines[0])
    assert m, f"cannot parse schema names: {lines[0]}"
    listed = {s.strip() for s in m.group(1).split("/")}
    actual = {p.name[: -len(".schema.json")] for p in (ROOT / "orchestration" / "schema").glob("*.schema.json")}
    assert listed == actual, f"listed {sorted(listed)} != existing {sorted(actual)}"
