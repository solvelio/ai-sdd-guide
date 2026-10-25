"""README install steps (導入手順) tests: optional board step and workflow set."""
import re
from pathlib import Path

ROOT = Path(__file__).parents[1]
README = ROOT / "README.md"
UPDATE_SH = ROOT / "integration" / "update.sh"
HEADING = "## 導入手順（取り込み側プロジェクト）"


def install_section() -> str:
    text = README.read_text(encoding="utf-8")
    start = text.index(HEADING)
    rest = text[start + len(HEADING):]
    m = re.search(r"^## ", rest, re.MULTILINE)
    return rest[: m.start()] if m else rest


def test_install_steps_include_optional_board_setup():
    section = install_section()
    assert re.search(r"^# \d+\. （任意）ボード", section, re.MULTILINE), \
        "導入手順に「（任意）ボード」のステップがない"
    required = [
        "sdd-board.sh init",
        ".sdd/board.json",
        "GitHub App",
        "SDD_APP_PRIVATE_KEY",
        "app_id",
        "classic PAT",
        "SDD_PROJECT_TOKEN",
        "Organization",
        "個人",
        "docs/04-issue-tracker.md",
    ]
    missing = [s for s in required if s not in section]
    assert not missing, f"導入手順に足りない記述: {missing}"


def test_install_steps_explain_no_board_and_tier_label():
    section = install_section()
    assert re.search(r"\.sdd/board\.json[^\n]*(なければ|ない場合)[^\n]*(飛ば|スキップ)", section), \
        "board.json がなければボードの処理が飛ばされることが書かれていない"
    assert re.search(r"sdd-board\.yml[^\n]*Tier[^\n]*ラベル", section), \
        "PR の Tier ラベルを付けるのが sdd-board.yml であることが書かれていない"
    assert re.search(r"Tier[^\n]*ラベル[^\n]*手で", section), \
        "sdd-board.yml を入れない場合は Tier ラベルを手で付けることが書かれていない"


def test_install_workflows_match_update_sh():
    update_set = set(re.findall(r'cp "\$INTEGRATION/ci/([\w.-]+\.yml)"', UPDATE_SH.read_text(encoding="utf-8")))
    readme_set = set(re.findall(
        r"cp vendor/ai-sdd-guide/integration/ci/([\w.-]+\.yml) \.github/workflows/", install_section()))
    assert update_set, "update.sh からワークフローのコピーを読み取れない"
    assert readme_set == update_set, \
        f"導入手順のワークフロー {sorted(readme_set)} と update.sh の {sorted(update_set)} が一致しない"
