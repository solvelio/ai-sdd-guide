#!/usr/bin/env python3
"""Derive SDD state (tier, feature, freeze validity, phase) from the branch name
and files under specs/<feature>/. Offline; no network, no gh."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Tuple

PHASES = ("backlog", "brainstorm", "spec", "plan", "tasks", "implement", "verify", "done")

BRANCH_RE = re.compile(
    r"^t(?P<tier>[012])/(?P<issue>[1-9][0-9]*)-(?P<name>[a-z0-9][a-z0-9-]*)$"
)
_CHECKED_RE = re.compile(r"^(\s*[-*]\s+\[)[xX](\])", re.MULTILINE)
_CHECKBOX_RE = re.compile(r"^\s*[-*]\s+\[([ xX])\]", re.MULTILINE)

BRANCH_SHAPE = "t<Tier>/<Issue番号>-<名前>"
FREEZE_TOOL = "vendor/ai-sdd-guide/orchestration/tools/sdd-freeze.sh"


@dataclass(frozen=True)
class BranchInfo:
    tier: int
    issue: int
    name: str
    feature: str


class FreezeError(Exception):
    """freeze.json is present but not valid."""


def parse_branch(branch: Optional[str]) -> Optional[BranchInfo]:
    if not branch:
        return None
    m = BRANCH_RE.match(branch)
    if not m:
        return None
    issue, name = int(m.group("issue")), m.group("name")
    return BranchInfo(int(m.group("tier")), issue, name, "%d-%s" % (issue, name))


def _git(root: Path, args: List[str]) -> Optional[str]:
    try:
        r = subprocess.run(["git"] + args, cwd=str(root), capture_output=True, text=True)
    except OSError:
        return None
    if r.returncode != 0:
        return None
    return r.stdout.strip()


def current_branch(root: Path) -> Optional[str]:
    out = _git(root, ["branch", "--show-current"])
    return out or None


def freeze_targets(tier: int) -> List[str]:
    if tier == 2:
        return ["spec.md", "plan.md", "tasks.md", "traceability.json"]
    if tier == 1:
        return ["spec.md"]
    return []


def normalize_tasks_md(text: str) -> str:
    text = text.replace("\r\n", "\n")
    return _CHECKED_RE.sub(r"\1 \2", text)


def file_digest(path: Path) -> str:
    data = path.read_bytes()
    if path.name == "tasks.md":
        data = normalize_tasks_md(data.decode("utf-8")).encode("utf-8")
    return "sha256:" + hashlib.sha256(data).hexdigest()


def create_freeze(spec_dir: Path, tier: int, now: datetime) -> dict:
    files = {}
    for name in freeze_targets(tier):
        p = spec_dir / name
        if not p.is_file():
            raise FileNotFoundError(str(p))
        files[name] = file_digest(p)
    data = {
        "version": 1,
        "tier": tier,
        "frozen_at": now.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "files": files,
    }
    (spec_dir / "freeze.json").write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return data


def freeze_status(spec_dir: Path, tier: int) -> Tuple[str, List[str]]:
    fp = spec_dir / "freeze.json"
    if not fp.is_file():
        return "missing", []
    try:
        data = json.loads(fp.read_text(encoding="utf-8"))
    except (ValueError, OSError) as e:
        return "invalid", ["freeze.json を読めません: %s" % e]
    if not isinstance(data, dict) or not isinstance(data.get("files"), dict):
        return "invalid", ["freeze.json の形が正しくありません"]
    reasons: List[str] = []
    if data.get("tier") != tier:
        reasons.append("freeze.json の tier (%r) がブランチの Tier (%d) と違います"
                       % (data.get("tier"), tier))
    recorded = data["files"]
    for name in freeze_targets(tier):
        if name not in recorded:
            reasons.append("%s が freeze.json に記録されていません" % name)
            continue
        p = spec_dir / name
        if not p.is_file():
            reasons.append("%s がありません" % name)
        elif file_digest(p) != recorded[name]:
            reasons.append("%s が凍結後に変更されています" % name)
    return ("invalid", reasons) if reasons else ("valid", [])


def checkbox_states(text: str) -> List[str]:
    """Return the check marks (' ', 'x', 'X') of every task checkbox in tasks.md text."""
    return _CHECKBOX_RE.findall(text)


def _tasks_all_checked(path: Path) -> bool:
    boxes = checkbox_states(path.read_text(encoding="utf-8"))
    return bool(boxes) and all(b in "xX" for b in boxes)


def derive_phase(root: Path, info: BranchInfo) -> str:
    if info.tier == 0:
        return "implement"
    spec_dir = Path(root) / "specs" / info.feature
    status, reasons = freeze_status(spec_dir, info.tier)
    if status == "invalid":
        raise FreezeError("; ".join(reasons))
    if status == "valid":
        if info.tier == 2 and _tasks_all_checked(spec_dir / "tasks.md"):
            return "verify"
        return "implement"
    if info.tier == 2:
        if (spec_dir / "tasks.md").is_file():
            return "tasks"
        if (spec_dir / "plan.md").is_file():
            return "plan"
    if (spec_dir / "spec.md").is_file():
        return "spec"
    return "brainstorm"


def root_from(arg: Optional[str]) -> Path:
    if arg:
        return Path(arg)
    out = _git(Path.cwd(), ["rev-parse", "--show-toplevel"])
    return Path(out) if out else Path.cwd()


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(prog="sdd_state.py")
    ap.add_argument("cmd", choices=["branch", "phase", "freeze", "guard"])
    ap.add_argument("--root")
    ap.add_argument("--branch")
    args = ap.parse_args(argv)

    root = root_from(args.root)
    branch = args.branch if args.branch is not None else current_branch(root)
    info = parse_branch(branch)

    if args.cmd == "guard":
        if info is None:
            print("ブランチ %r は Tier 未分類です。ブランチ名を %s の形にしてください。"
                  % (branch, BRANCH_SHAPE), file=sys.stderr)
            return 1
        if info.tier == 0:
            return 0
        status, reasons = freeze_status(root / "specs" / info.feature, info.tier)
        if status == "valid":
            return 0
        why = "freeze.json がありません" if status == "missing" else "; ".join(reasons)
        print("%s。%s で凍結してからソースを編集してください。" % (why, FREEZE_TOOL),
              file=sys.stderr)
        return 1

    if info is None:
        return 3

    if args.cmd == "branch":
        print(json.dumps({"tier": info.tier, "issue": info.issue,
                          "name": info.name, "feature": info.feature}))
        return 0
    if args.cmd == "phase":
        try:
            print(derive_phase(root, info))
        except FreezeError as e:
            print(str(e), file=sys.stderr)
            return 4
        return 0
    # freeze
    if info.tier == 0:
        return 3
    spec_dir = root / "specs" / info.feature
    try:
        create_freeze(spec_dir, info.tier, datetime.now(timezone.utc))
    except FileNotFoundError as e:
        print("凍結の対象ファイルがありません: %s" % e, file=sys.stderr)
        return 2
    print(spec_dir / "freeze.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
