from __future__ import annotations

import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
UPDATE = ROOT / "integration" / "update.sh"


def _run(dest: Path):
    env = dict(os.environ)
    env["PATH"] = "/usr/bin:/bin"  # brew なし
    return subprocess.run(
        ["bash", str(UPDATE), str(dest)],
        stdin=subprocess.DEVNULL, capture_output=True, text=True, env=env, timeout=60,
    )


def test_update_sh_copies_board_workflow(tmp_path):
    r = _run(tmp_path)
    assert r.returncode == 0, r.stderr
    assert (tmp_path / ".github/workflows/sdd-board.yml").is_file()
    assert (tmp_path / ".github/workflows/sdd-check.yml").is_file()
    assert not (tmp_path / ".github/workflows/kanban-pages.yml").exists()


def test_update_sh_does_not_overwrite_board_json(tmp_path):
    board = tmp_path / ".sdd" / "board.json"
    board.parent.mkdir()
    board.write_text('{"owner": "me", "project": 7}\n')
    r = _run(tmp_path)
    assert r.returncode == 0, r.stderr
    assert board.read_text() == '{"owner": "me", "project": 7}\n'
