#!/usr/bin/env python3
"""GitHub Projects board operations for SDD phases (uses the gh CLI).

Board failures never block work: every subcommand except `init` prints
`sdd-board: warning: <reason>` to stderr and exits 0."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))

from sdd_state import (  # noqa: E402
    PHASES, FreezeError, current_branch, derive_phase, parse_branch,
)

BOARD_FILE = Path(".sdd") / "board.json"
BIG_LIMIT = "10000"
CLOSE_REASONS = ("completed", "not_planned", "duplicate")


class GhError(Exception):
    """A gh call failed (message is a short, token-free reason)."""


class BoardError(Exception):
    """Board precondition is not met."""


_CWD: Optional[Path] = None


def run_gh(args: List[str]) -> str:
    try:
        r = subprocess.run(["gh"] + list(args), capture_output=True, text=True,
                           cwd=str(_CWD) if _CWD else None)
    except OSError:
        raise GhError("gh を実行できません")
    if r.returncode != 0:
        sub = " ".join(a for a in args[:2] if not a.startswith("-"))
        raise GhError("gh %s が失敗しました (終了コード %d)" % (sub, r.returncode))
    return r.stdout


def gh_json(args: List[str]) -> Any:
    out = run_gh(args)
    try:
        return json.loads(out) if out.strip() else {}
    except ValueError:
        raise GhError("gh %s の出力を読めません" % args[0])


def load_board(root: Path) -> Dict[str, Any]:
    p = root / BOARD_FILE
    if not p.is_file():
        raise BoardError("%s がありません。`sdd-board.sh init` を実行してください" % BOARD_FILE)
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        owner, project = data["owner"], data["project"]
    except (ValueError, KeyError, TypeError, OSError):
        raise BoardError("%s を読めません" % BOARD_FILE)
    if not isinstance(owner, str) or isinstance(project, bool) or not isinstance(project, int):
        raise BoardError("%s の owner / project の型が正しくありません" % BOARD_FILE)
    return data


class Board:
    def __init__(self, owner: str, project: int):
        self.owner = owner
        self.project = str(project)
        self._repo: Optional[str] = None
        self._meta: Optional[Dict[str, Any]] = None
        self._items: Optional[List[Dict[str, Any]]] = None

    @property
    def repo(self) -> str:
        if self._repo is None:
            data = gh_json(["repo", "view", "--json", "nameWithOwner,owner"])
            name = data.get("nameWithOwner") if isinstance(data, dict) else None
            if not name:
                raise GhError("リポジトリを特定できません")
            self._repo = name
        return self._repo

    def meta(self) -> Dict[str, Any]:
        if self._meta is None:
            pid = gh_json(["project", "view", self.project, "--owner", self.owner,
                           "--format", "json"]).get("id")
            fields = gh_json(["project", "field-list", self.project, "--owner", self.owner,
                              "--format", "json"]).get("fields", [])
            phase = next((f for f in fields if f.get("name") == "Phase"), None)
            if not pid or phase is None:
                raise GhError("Project か Phase フィールドが見つかりません")
            opts = {o["name"]: o["id"] for o in phase.get("options", [])}
            self._meta = {"project_id": pid, "field_id": phase["id"], "options": opts}
        return self._meta

    def items(self) -> List[Dict[str, Any]]:
        if self._items is None:
            data = gh_json(["project", "item-list", self.project, "--owner", self.owner,
                            "--format", "json", "--limit", BIG_LIMIT])
            self._items = data.get("items", [])
        return self._items

    def find(self, issue: int) -> Optional[str]:
        for it in self.items():
            c = it.get("content") or {}
            if c.get("number") == issue and c.get("repository") == self.repo:
                return it.get("id")
        return None

    def add(self, issue: int, url: Optional[str] = None) -> str:
        if url is None:
            url = gh_json(["issue", "view", str(issue), "--repo", self.repo,
                           "--json", "url"]).get("url")
        if not url:
            raise GhError("Issue #%d の URL を取得できません" % issue)
        item_id = gh_json(["project", "item-add", self.project, "--owner", self.owner,
                           "--url", url, "--format", "json"]).get("id")
        if not item_id:
            raise GhError("カードを追加できません")
        self.items().append({"id": item_id,
                             "content": {"number": issue, "repository": self.repo}})
        return item_id

    def set_phase(self, issue: int, phase: str, url: Optional[str] = None) -> None:
        if phase not in PHASES:
            raise BoardError("未知のフェーズです: %s" % phase)
        meta = self.meta()
        oid = meta["options"].get(phase)
        if not oid:
            raise GhError("Phase フィールドに %s の選択肢がありません" % phase)
        item_id = self.find(issue) or self.add(issue, url)
        run_gh(["project", "item-edit", "--id", item_id, "--project-id", meta["project_id"],
                "--field-id", meta["field_id"], "--single-select-option-id", oid])

    def archive(self, issue: int) -> None:
        item_id = self.find(issue)
        if item_id:
            run_gh(["project", "item-archive", self.project, "--owner", self.owner,
                    "--id", item_id])

    def import_open(self) -> None:
        issues = gh_json(["issue", "list", "--repo", self.repo, "--state", "open",
                          "--json", "number,url", "--limit", "1000"])
        for iss in issues:
            if self.find(iss["number"]) is None:
                self.set_phase(iss["number"], "backlog", iss.get("url"))


def _branch_phase(root: Path, branch: Optional[str]):
    info = parse_branch(branch)
    if info is None:
        raise BoardError("ブランチ %r は t<Tier>/<Issue番号>-<名前> の形ではありません" % branch)
    return info, derive_phase(root, info)


def cmd_sync(board: Board, root: Path, args) -> None:
    info, phase = _branch_phase(root, current_branch(root))
    board.set_phase(info.issue, phase)


def cmd_set(board: Board, root: Path, args) -> None:
    board.set_phase(args.issue, args.phase)


def cmd_import(board: Board, root: Path, args) -> None:
    board.import_open()


def cmd_close(board: Board, root: Path, args) -> None:
    reason = (args.reason or "").lower()
    if reason not in CLOSE_REASONS:
        raise BoardError("未知のクローズ理由です: %s" % reason[:40])
    if reason == "completed":
        if board.find(args.issue) is not None:
            board.set_phase(args.issue, "done")
    else:
        board.archive(args.issue)


def cmd_pr(board: Board, root: Path, args) -> None:
    merged, closed = args.merged == "true", args.closed == "true"
    if not merged and closed:
        return
    info = parse_branch(args.branch)
    if info is None:
        raise BoardError("ブランチ %r は t<Tier>/<Issue番号>-<名前> の形ではありません"
                         % args.branch)
    board.set_phase(info.issue, "done" if merged else derive_phase(root, info))


def cmd_init(root: Path, args) -> int:
    global _CWD
    _CWD = root
    path = root / BOARD_FILE
    try:
        if path.is_file():
            data = load_board(root)
            owner, project = data["owner"], data["project"]
        else:
            owner = args.owner
            if not owner:
                owner = gh_json(["repo", "view", "--json", "nameWithOwner,owner"]) \
                    .get("owner", {}).get("login")
            if not owner:
                raise GhError("owner を特定できません。--owner を指定してください")
            created = gh_json(["project", "create", "--owner", owner, "--title", args.title,
                               "--format", "json"])
            project = created.get("number")
            if not isinstance(project, int):
                raise GhError("Project の番号を取得できません")
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps({"owner": owner, "project": project}, indent=2) + "\n",
                            encoding="utf-8")
        fields = gh_json(["project", "field-list", str(project), "--owner", owner,
                          "--format", "json"]).get("fields", [])
        if not any(f.get("name") == "Phase" for f in fields):
            run_gh(["project", "field-create", str(project), "--owner", owner,
                    "--name", "Phase", "--data-type", "SINGLE_SELECT",
                    "--single-select-options", ",".join(PHASES)])
        Board(owner, project).import_open()
    except (GhError, BoardError) as e:
        print("sdd-board: error: %s" % e, file=sys.stderr)
        return 1
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    global _CWD
    ap = argparse.ArgumentParser(prog="sdd_board.py")
    sub = ap.add_subparsers(dest="cmd", required=True)

    def add(name, *opts):
        p = sub.add_parser(name)
        p.add_argument("--root")
        for o in opts:
            p.add_argument(o[0], **o[1])
        return p

    add("sync")
    p = add("init", ("--title", {"default": "SDD Board"}), ("--owner", {}))
    add("import")
    add("set", ("--issue", {"type": int, "required": True}),
        ("--phase", {"required": True}))
    add("close", ("--issue", {"type": int, "required": True}),
        ("--reason", {"required": True}))
    add("pr", ("--branch", {"required": True}),
        ("--merged", {"required": True, "choices": ["true", "false"]}),
        ("--closed", {"required": True, "choices": ["true", "false"]}))
    args = ap.parse_args(argv)
    root = Path(args.root) if args.root else Path.cwd()

    if args.cmd == "init":
        return cmd_init(root, args)
    _CWD = root
    try:
        data = load_board(root)
        board = Board(data["owner"], data["project"])
        {"sync": cmd_sync, "set": cmd_set, "import": cmd_import,
         "close": cmd_close, "pr": cmd_pr}[args.cmd](board, root, args)
    except (GhError, BoardError, FreezeError) as e:
        print("sdd-board: warning: %s" % e, file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
