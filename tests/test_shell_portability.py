import re
from pathlib import Path

ROOT = Path(__file__).parents[1]
DIRS = ["orchestration/tools", "integration/hooks", "integration/ci"]
PATTERN = re.compile(r"\$[A-Za-z_][A-Za-z0-9_]*(?=[^\x00-\x7f])")


def test_no_unbraced_var_before_non_ascii():
    # bash 3.2 (macOS) + UTF-8 locale treats non-ASCII bytes after $NAME as part of the name.
    hits = []
    for d in DIRS:
        for path in sorted((ROOT / d).rglob("*.sh")):
            text = path.read_text(encoding="utf-8")
            for n, line in enumerate(text.splitlines(), 1):
                for m in PATTERN.finditer(line):
                    hits.append(f"{path.relative_to(ROOT)}:{n}: {m.group(0)}")
    assert not hits, "use ${NAME} before non-ASCII chars:\n" + "\n".join(hits)
