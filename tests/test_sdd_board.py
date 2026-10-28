import json
import os
import stat
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "integration" / "ci"))

import sdd_state  # noqa: E402

SCRIPT = ROOT / "integration" / "ci" / "sdd_board.py"
WRAPPER = ROOT / "orchestration" / "tools" / "sdd-board.sh"
FAKE = ROOT / "tests" / "fake_gh.py"
NOW = datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc)
GIT_ENV = {
    "GIT_AUTHOR_NAME": "Test User", "GIT_AUTHOR_EMAIL": "test@example.invalid",
    "GIT_COMMITTER_NAME": "Test User", "GIT_COMMITTER_EMAIL": "test@example.invalid",
}
PHASES = ["backlog", "brainstorm", "spec", "plan", "tasks", "implement", "verify", "done"]
REPO = "acme/widgets"
URL = "https://github.com/acme/widgets/issues/%d"


def J(obj, code=0):
    return {"stdout": json.dumps(obj), "code": code}


def item(item_id, number, repo=REPO):
    return {"id": item_id, "content": {"number": number, "repository": repo, "type": "Issue"}}


def base_responses(items=None, issues=None):
    r = {
        "project view 5 --owner acme": J({"id": "PID"}),
        "project field-list 5 --owner acme": J({"fields": [
            {"id": "F_OTHER", "name": "Status", "type": "ProjectV2SingleSelectField"},
            {"id": "FID", "name": "Phase", "type": "ProjectV2SingleSelectField",
             "options": [{"id": "O_" + p, "name": p} for p in PHASES]}]}),
        "project item-list 5 --owner acme": J({"items": items or []}),
        "repo view": J({"nameWithOwner": REPO, "owner": {"login": "acme"}}),
        "project item-edit": {"stdout": "{}"},
        "project item-archive": {"stdout": "{}"},
        "project item-add 5 --owner acme": J({"id": "NEW"}),
    }
    for n in (issues or [7, 8, 9]):
        r["issue view %d --repo %s --json url" % (n, REPO)] = J({"url": URL % n})
    return r


class Env:
    def __init__(self, tmp_path, monkeypatch):
        self.tmp = tmp_path
        self.bin = tmp_path / "bin"
        self.bin.mkdir()
        gh = self.bin / "gh"
        gh.write_text("#!/bin/sh\nexec %s %s \"$@\"\n" % (sys.executable, FAKE))
        gh.chmod(gh.stat().st_mode | stat.S_IXUSR)
        self.log = tmp_path / "gh.log"
        self.responses = tmp_path / "responses.json"
        self.root = tmp_path / "repo"
        self.root.mkdir()
        monkeypatch.setenv("PATH", str(self.bin) + os.pathsep + os.environ["PATH"])
        monkeypatch.setenv("FAKE_GH_LOG", str(self.log))
        monkeypatch.setenv("FAKE_GH_RESPONSES", str(self.responses))
        for k, v in GIT_ENV.items():
            monkeypatch.setenv(k, v)
        self.respond({})

    def respond(self, table):
        self.responses.write_text(json.dumps(table))

    def board(self, **extra):
        (self.root / ".sdd").mkdir(exist_ok=True)
        (self.root / ".sdd" / "board.json").write_text(
            json.dumps({"owner": "acme", "project": 5, **extra}))

    def git_branch(self, name):
        for a in (["init", "-q"], ["checkout", "-q", "-b", name]):
            subprocess.run(["git"] + a, cwd=self.root, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-q", "--allow-empty", "-m", "i"], cwd=self.root,
                       check=True, capture_output=True)

    def freeze_t2(self, feature):
        d = self.root / "specs" / feature
        d.mkdir(parents=True)
        for n, t in (("spec.md", "s\n"), ("plan.md", "p\n"), ("tasks.md", "- [ ] T1\n"),
                     ("traceability.json", "{}\n")):
            (d / n).write_text(t)
        sdd_state.create_freeze(d, 2, NOW)

    def run(self, *args):
        return subprocess.run([sys.executable, str(SCRIPT)] + list(args) + ["--root", str(self.root)],
                              capture_output=True, text=True)

    def calls(self):
        if not self.log.exists():
            return []
        return [json.loads(l) for l in self.log.read_text().splitlines()]

    def sub(self, *prefix):
        p = list(prefix)
        return [c for c in self.calls() if c[:len(p)] == p]


@pytest.fixture
def env(tmp_path, monkeypatch):
    return Env(tmp_path, monkeypatch)


def edit_option(call):
    return call[call.index("--single-select-option-id") + 1]


def test_wrapper_runs_script(env):
    r = subprocess.run(["bash", str(WRAPPER), "set", "--issue", "7", "--phase", "spec",
                        "--root", str(env.root)], capture_output=True, text=True)
    assert r.returncode == 0
    assert "warning" in r.stderr


def test_sync_updates_phase_from_branch(env):
    env.git_branch("t2/7-x")
    env.freeze_t2("7-x")
    env.board()
    env.respond(base_responses(items=[item("IT7", 7)]))
    r = env.run("sync")
    assert r.returncode == 0, r.stderr
    edits = env.sub("project", "item-edit")
    assert len(edits) == 1
    assert edit_option(edits[0]) == "O_implement"
    assert edits[0][edits[0].index("--id") + 1] == "IT7"
    assert edits[0][edits[0].index("--project-id") + 1] == "PID"
    assert edits[0][edits[0].index("--field-id") + 1] == "FID"
    assert env.sub("project", "item-add") == []


def test_sync_adds_missing_card(env):
    env.git_branch("t2/7-x")
    env.freeze_t2("7-x")
    env.board()
    env.respond(base_responses(items=[]))
    r = env.run("sync")
    assert r.returncode == 0, r.stderr
    names = [c[:2] for c in env.calls() if c[0] == "project" and c[1] in ("item-add", "item-edit")]
    assert names == [["project", "item-add"], ["project", "item-edit"]]
    add = env.sub("project", "item-add")[0]
    assert add[add.index("--url") + 1] == URL % 7
    assert edit_option(env.sub("project", "item-edit")[0]) == "O_implement"
    assert env.sub("project", "item-edit")[0][env.sub("project", "item-edit")[0].index("--id") + 1] == "NEW"


def test_sync_warns_without_board_json(env):
    env.git_branch("t2/7-x")
    env.freeze_t2("7-x")
    env.respond(base_responses(items=[item("IT7", 7)]))
    r = env.run("sync")
    assert r.returncode == 0
    assert "warning" in r.stderr
    assert env.sub("project", "item-edit") == []


def test_sync_warns_when_gh_fails(env):
    env.git_branch("t2/7-x")
    env.freeze_t2("7-x")
    env.board()
    table = base_responses(items=[item("IT7", 7)])
    table["project view 5 --owner acme"] = {"stdout": "", "code": 1, "stderr": "token ghp_SECRET"}
    env.respond(table)
    r = env.run("sync")
    assert r.returncode == 0
    assert "warning" in r.stderr
    assert "ghp_SECRET" not in r.stderr
    assert env.sub("project", "item-edit") == []


def test_sync_warns_on_unmatched_branch(env):
    env.git_branch("feat/whatever")
    env.board()
    env.respond(base_responses(items=[item("IT7", 7)]))
    r = env.run("sync")
    assert r.returncode == 0
    assert "warning" in r.stderr
    assert env.sub("project", "item-edit") == []


def test_sync_warns_on_invalid_freeze(env):
    env.git_branch("t2/7-x")
    env.freeze_t2("7-x")
    (env.root / "specs" / "7-x" / "spec.md").write_text("changed\n")
    env.board()
    env.respond(base_responses(items=[item("IT7", 7)]))
    r = env.run("sync")
    assert r.returncode == 0
    assert "warning" in r.stderr
    assert env.sub("project", "item-edit") == []


def test_item_lookup_passes_large_limit(env):
    env.board()
    env.respond(base_responses(items=[item("IT7", 7)]))
    assert env.run("set", "--issue", "7", "--phase", "spec").returncode == 0
    lst = env.sub("project", "item-list")[0]
    assert "--limit" in lst
    assert int(lst[lst.index("--limit") + 1]) >= 1000


def test_item_lookup_matches_repository_and_number(env):
    env.board()
    env.respond(base_responses(items=[item("OTHER", 7, repo="acme/other")]))
    r = env.run("set", "--issue", "7", "--phase", "spec")
    assert r.returncode == 0, r.stderr
    assert len(env.sub("project", "item-add")) == 1
    edits = env.sub("project", "item-edit")
    assert len(edits) == 1
    assert edits[0][edits[0].index("--id") + 1] == "NEW"


def test_init_creates_project_field_and_board_json(env):
    table = base_responses()
    table["project create"] = J({"number": 5})
    table["project field-list 5 --owner acme"] = J({"fields": [
        {"id": "F_OTHER", "name": "Status", "type": "ProjectV2SingleSelectField"}]})
    table["project field-create"] = J({"id": "FID"})
    table["issue list"] = J([])
    env.respond(table)
    r = env.run("init", "--owner", "acme")
    assert r.returncode == 0, r.stderr
    create = env.sub("project", "create")[0]
    assert create[create.index("--owner") + 1] == "acme"
    fc = env.sub("project", "field-create")[0]
    assert fc[fc.index("--name") + 1] == "Phase"
    assert fc[fc.index("--data-type") + 1] == "SINGLE_SELECT"
    assert fc[fc.index("--single-select-options") + 1].split(",") == PHASES
    data = json.loads((env.root / ".sdd" / "board.json").read_text())
    assert data["owner"] == "acme" and data["project"] == 5


def test_init_derives_owner_from_repo(env):
    table = base_responses()
    table["project create"] = J({"number": 5})
    table["project field-list"] = J({"fields": [
        {"id": "FID", "name": "Phase", "type": "ProjectV2SingleSelectField",
         "options": [{"id": "O_" + p, "name": p} for p in PHASES]}]})
    table["issue list"] = J([])
    env.respond(table)
    r = env.run("init")
    assert r.returncode == 0, r.stderr
    assert env.sub("project", "field-create") == []
    assert json.loads((env.root / ".sdd" / "board.json").read_text())["owner"] == "acme"


def test_init_failure_exits_1(env):
    env.respond({"repo view": J({"nameWithOwner": REPO, "owner": {"login": "acme"}}),
                 "project create": {"stdout": "", "code": 1}})
    r = env.run("init")
    assert r.returncode == 1
    assert not (env.root / ".sdd" / "board.json").exists()


def test_init_with_existing_board_json_does_not_create(env):
    env.board()
    table = base_responses()
    table["issue list"] = J([])
    env.respond(table)
    r = env.run("init")
    assert r.returncode == 0, r.stderr
    assert env.sub("project", "create") == []


def import_table(items):
    t = base_responses(items=items, issues=[7, 8, 9])
    t["issue list"] = J([{"number": 7, "url": URL % 7}, {"number": 8, "url": URL % 8}])
    return t


def test_import_adds_only_missing_open_issues_as_backlog(env):
    env.board()
    env.respond(import_table([item("IT7", 7)]))
    r = env.run("import")
    assert r.returncode == 0, r.stderr
    adds = env.sub("project", "item-add")
    assert len(adds) == 1 and adds[0][adds[0].index("--url") + 1] == URL % 8
    edits = env.sub("project", "item-edit")
    assert len(edits) == 1 and edit_option(edits[0]) == "O_backlog"
    il = env.sub("issue", "list")[0]
    assert il[il.index("--repo") + 1] == REPO
    assert "open" in il and il[il.index("--limit") + 1] == "1000"


def test_import_twice_is_idempotent(env):
    env.board()
    env.respond(import_table([item("IT7", 7), item("IT8", 8)]))
    assert env.run("import").returncode == 0
    assert env.sub("project", "item-add") == []
    assert env.sub("project", "item-edit") == []


def test_event_close_completed_sets_done(env):
    env.board()
    env.respond(base_responses(items=[item("IT7", 7)]))
    assert env.run("close", "--issue", "7", "--reason", "COMPLETED").returncode == 0
    edits = env.sub("project", "item-edit")
    assert len(edits) == 1 and edit_option(edits[0]) == "O_done"
    assert env.sub("project", "item-archive") == []


@pytest.mark.parametrize("reason", ["not_planned", "duplicate", "NOT_PLANNED"])
def test_event_close_not_planned_archives(env, reason):
    env.board()
    env.respond(base_responses(items=[item("IT7", 7)]))
    assert env.run("close", "--issue", "7", "--reason", reason).returncode == 0
    arch = env.sub("project", "item-archive")
    assert len(arch) == 1 and arch[0][arch[0].index("--id") + 1] == "IT7"
    assert env.sub("project", "item-edit") == []


def test_event_close_duplicate_archives(env):
    test_event_close_not_planned_archives(env, "duplicate")


def test_event_close_without_card_is_noop(env):
    env.board()
    env.respond(base_responses(items=[]))
    assert env.run("close", "--issue", "7", "--reason", "completed").returncode == 0
    assert env.sub("project", "item-edit") == [] and env.sub("project", "item-add") == []


def test_event_close_unknown_reason_warns(env):
    env.board()
    env.respond(base_responses(items=[item("IT7", 7)]))
    r = env.run("close", "--issue", "7", "--reason", "weird")
    assert r.returncode == 0 and "warning" in r.stderr
    assert env.sub("project", "item-edit") == [] and env.sub("project", "item-archive") == []


def pr(env, branch, merged, closed):
    return env.run("pr", "--branch", branch, "--merged", merged, "--closed", closed)


def test_event_pr_merged_sets_done(env):
    env.board()
    env.respond(base_responses(items=[item("IT7", 7)]))
    assert pr(env, "t2/7-x", "true", "true").returncode == 0
    edits = env.sub("project", "item-edit")
    assert len(edits) == 1 and edit_option(edits[0]) == "O_done"


def test_event_pr_closed_unmerged_is_noop(env):
    env.board()
    env.respond(base_responses(items=[item("IT7", 7)]))
    assert pr(env, "t2/7-x", "false", "true").returncode == 0
    assert env.sub("project", "item-edit") == []


def test_event_pr_open_derives_phase(env):
    env.freeze_t2("7-x")
    env.board()
    env.respond(base_responses(items=[item("IT7", 7)]))
    assert pr(env, "t2/7-x", "false", "false").returncode == 0
    edits = env.sub("project", "item-edit")
    assert len(edits) == 1 and edit_option(edits[0]) == "O_implement"


def test_event_pr_bot_branch_is_noop(env):
    env.board()
    env.respond(base_responses(items=[item("IT7", 7)]))
    r = pr(env, "dependabot/npm/foo", "false", "false")
    assert r.returncode == 0
    assert env.sub("project", "item-edit") == []


def test_set_phase(env):
    env.board()
    env.respond(base_responses(items=[item("IT7", 7)]))
    assert env.run("set", "--issue", "7", "--phase", "plan").returncode == 0
    edits = env.sub("project", "item-edit")
    assert len(edits) == 1 and edit_option(edits[0]) == "O_plan"


def test_set_invalid_phase_warns(env):
    env.board()
    env.respond(base_responses(items=[item("IT7", 7)]))
    r = env.run("set", "--issue", "7", "--phase", "nope")
    assert r.returncode == 0 and "warning" in r.stderr
    assert env.sub("project", "item-edit") == []


# --- final-review fixes ---

def test_sync_warns_on_unexpected_gh_shape(env):
    env.git_branch("t2/7-x")
    env.freeze_t2("7-x")
    env.board()
    table = base_responses()
    table["project item-list 5 --owner acme"] = {"stdout": "[]"}
    env.respond(table)
    r = env.run("sync")
    assert r.returncode == 0
    assert "warning" in r.stderr
    assert "Traceback" not in r.stderr


def test_import_warns_on_missing_keys(env):
    env.board()
    table = base_responses()
    table["issue list --repo %s" % REPO] = J([{"url": "u"}])
    env.respond(table)
    r = env.run("import")
    assert r.returncode == 0
    assert "warning" in r.stderr
    assert "Traceback" not in r.stderr


def test_sync_warns_on_non_utf8_tasks_md(env):
    env.git_branch("t2/7-x")
    env.freeze_t2("7-x")
    env.board()
    (env.root / "specs" / "7-x" / "tasks.md").write_bytes(b"\xff\xfe\x00bad\n")
    env.respond(base_responses(items=[item("IT7", 7)]))
    r = env.run("sync")
    assert r.returncode == 0
    assert "warning" in r.stderr
    assert "Traceback" not in r.stderr


def test_init_unexpected_error_is_clean_exit_1(env):
    table = base_responses()
    table["repo view"] = {"stdout": "[]"}
    env.respond(table)
    r = env.run("init")
    assert r.returncode == 1
    assert "Traceback" not in r.stderr
    assert "error" in r.stderr


def test_init_failure_hints_project_scope(env):
    env.respond({"repo view": J({"nameWithOwner": REPO, "owner": {"login": "acme"}}),
                 "project create": {"stdout": "", "code": 1}})
    r = env.run("init")
    assert r.returncode == 1
    assert "gh auth refresh -s project" in r.stderr


def test_sync_from_subdirectory_finds_board_json(env):
    env.git_branch("t2/7-x")
    env.freeze_t2("7-x")
    env.board()
    sub = env.root / "src" / "deep"
    sub.mkdir(parents=True)
    env.respond(base_responses(items=[item("IT7", 7)]))
    r = subprocess.run([sys.executable, str(SCRIPT), "sync"], cwd=sub,
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert "warning" not in r.stderr
    assert len(env.sub("project", "item-edit")) == 1


# --- auth-mode (78-github-app-token) ---

def write_board(env, data):
    (env.root / ".sdd").mkdir(exist_ok=True)
    (env.root / ".sdd" / "board.json").write_text(json.dumps(data))


def auth(env, key, pat):
    r = env.run("auth-mode", "--has-app-key", key, "--has-pat", pat)
    assert env.calls() == []
    return r


def test_auth_mode_app_when_app_id_and_key(env):
    write_board(env, {"owner": "o", "project": 1, "app_id": 123})
    r = auth(env, "true", "false")
    assert r.returncode == 0, r.stderr
    assert r.stdout.splitlines() == ["mode=app", "app_id=123", "owner=o"]


def test_auth_mode_app_preferred_over_pat(env):
    write_board(env, {"owner": "o", "project": 1, "app_id": 123})
    r = auth(env, "true", "true")
    assert r.returncode == 0
    assert "mode=app" in r.stdout.splitlines()


def test_auth_mode_key_without_app_id_is_error(env):
    write_board(env, {"owner": "o", "project": 1})
    r = auth(env, "true", "false")
    assert r.returncode == 1
    assert "mode=error" in r.stdout
    assert "::error::" in r.stderr


def test_auth_mode_pat_without_app_id(env):
    write_board(env, {"owner": "o", "project": 1})
    r = auth(env, "false", "true")
    assert r.returncode == 0
    assert "mode=pat" in r.stdout.splitlines()


def test_auth_mode_pat_when_app_id_but_no_key(env):
    write_board(env, {"owner": "o", "project": 1, "app_id": 123})
    r = auth(env, "false", "true")
    assert r.returncode == 0
    assert "mode=pat" in r.stdout.splitlines()


def test_auth_mode_app_id_without_key_and_pat_is_none(env):
    write_board(env, {"owner": "o", "project": 1, "app_id": 123})
    r = auth(env, "false", "false")
    assert r.returncode == 0
    assert "mode=none" in r.stdout.splitlines()
    assert r.stderr.startswith("::warning::")


def test_auth_mode_none_without_anything(env):
    write_board(env, {"owner": "o", "project": 1})
    r = auth(env, "false", "false")
    assert r.returncode == 0
    assert "mode=none" in r.stdout.splitlines()


def test_auth_mode_without_board_json_is_none(env):
    r = auth(env, "true", "false")
    assert r.returncode == 0
    assert r.stdout.splitlines() == ["mode=none", "app_id=", "owner="]
    assert "::warning::" in r.stderr


@pytest.mark.parametrize("bad", ["123", True])
def test_auth_mode_invalid_app_id_is_error(env, bad):
    write_board(env, {"owner": "o", "project": 1, "app_id": bad})
    r = auth(env, "true", "false")
    assert r.returncode == 1
    assert "mode=error" in r.stdout
    assert "::error::" in r.stderr


def test_load_board_accepts_int_app_id(env):
    write_board(env, {"owner": "o", "project": 1, "app_id": 5})
    import sdd_board
    assert sdd_board.load_board(env.root)["app_id"] == 5


def test_load_board_rejects_bool_app_id(env):
    write_board(env, {"owner": "o", "project": 1, "app_id": True})
    import sdd_board
    with pytest.raises(sdd_board.BoardError):
        sdd_board.load_board(env.root)


def test_init_preserves_existing_keys(env):
    write_board(env, {"owner": "o", "project": 1, "app_id": 5,
                      "tier0_branch_prefixes": ["bot/"]})
    table = base_responses()
    table["project field-list 1 --owner o"] = table["project field-list 5 --owner acme"]
    table["project item-list 1 --owner o"] = J({"items": []})
    table["issue list"] = J([])
    env.respond(table)
    r = env.run("init")
    assert r.returncode == 0, r.stderr
    data = json.loads((env.root / ".sdd" / "board.json").read_text())
    assert data["app_id"] == 5 and data["tier0_branch_prefixes"] == ["bot/"]
    assert env.sub("project", "create") == []


HINT = "トークンの権限が足りない可能性があります"


def sync_with_stderr(env, stderr):
    env.git_branch("t2/7-x")
    env.freeze_t2("7-x")
    env.board()
    table = base_responses(items=[item("IT7", 7)])
    table["project view 5 --owner acme"] = {"stdout": "", "code": 1, "stderr": stderr}
    env.respond(table)
    return env.run("sync")


def test_scope_hint_on_missing_scopes(env):
    r = sync_with_stderr(env, "error: missing required scopes [read:org]")
    assert r.returncode == 0
    assert HINT in r.stderr
    assert "read:org" not in r.stderr


def test_scope_hint_on_integration_forbidden(env):
    r = sync_with_stderr(env, "Resource not accessible by integration")
    assert r.returncode == 0
    assert HINT in r.stderr
    assert "accessible by integration" not in r.stderr


def test_no_scope_hint_on_other_failure(env):
    r = sync_with_stderr(env, "something else")
    assert r.returncode == 0
    assert "warning" in r.stderr
    assert HINT not in r.stderr


def init_table(number=5, owner="acme"):
    t = base_responses()
    t["project field-list %d --owner %s" % (number, owner)] = \
        t["project field-list 5 --owner acme"]
    t["project item-list %d --owner %s" % (number, owner)] = J({"items": []})
    t["project view %d --owner %s" % (number, owner)] = J({"id": "PID"})
    t["project item-add %d --owner %s" % (number, owner)] = J({"id": "NEW"})
    t["project link"] = {"stdout": "{}"}
    t["issue list"] = J([{"number": 7, "url": URL % 7}])
    return t


def link_args(env):
    links = env.sub("project", "link")
    assert len(links) == 1, env.calls()
    return links[0]


def test_init_links_new_project_to_repo(env):
    table = init_table()
    table["project create"] = J({"number": 5})
    env.respond(table)
    r = env.run("init")
    assert r.returncode == 0, r.stderr
    assert link_args(env) == ["project", "link", "5", "--owner", "acme", "--repo", REPO]


def test_init_links_existing_project_to_repo(env):
    env.board()
    env.respond(init_table())
    r = env.run("init")
    assert r.returncode == 0, r.stderr
    assert env.sub("project", "create") == []
    assert link_args(env) == ["project", "link", "5", "--owner", "acme", "--repo", REPO]


def test_init_default_title_is_repo_name(env):
    table = init_table()
    table["project create"] = J({"number": 5})
    env.respond(table)
    r = env.run("init")
    assert r.returncode == 0, r.stderr
    create = env.sub("project", "create")[0]
    assert create[create.index("--title") + 1] == "widgets"
    r = env.run("init", "--title", "Custom", "--new")
    assert r.returncode == 0, r.stderr
    create = env.sub("project", "create")[1]
    assert create[create.index("--title") + 1] == "Custom"


def test_init_link_failure_warns_and_continues(env):
    env.board()
    table = init_table()
    table["project link"] = {"stdout": "", "code": 1}
    env.respond(table)
    r = env.run("init")
    assert r.returncode == 0, r.stderr
    assert "sdd-board: warning:" in r.stderr
    assert len(env.sub("project", "link")) == 1
    assert len(env.sub("issue", "list")) == 1
    assert len(env.sub("project", "item-add")) == 1


def test_init_repo_view_failure_exits_1(env):
    env.board()
    table = init_table()
    table["repo view"] = {"stdout": "", "code": 1}
    env.respond(table)
    r = env.run("init")
    assert r.returncode == 1
    assert "sdd-board: error:" in r.stderr
    assert "Traceback" not in r.stderr
    assert env.sub("project") == []  # fails before touching the Project
    data = json.loads((env.root / ".sdd" / "board.json").read_text())
    assert data == {"owner": "acme", "project": 5}


def test_init_new_replaces_project_and_keeps_keys(env):
    write_board(env, {"owner": "old", "project": 1, "app_id": 5,
                      "tier0_branch_prefixes": ["bot/"]})
    table = init_table(number=9)
    table["project create"] = J({"number": 9})
    env.respond(table)
    r = env.run("init", "--new")
    assert r.returncode == 0, r.stderr
    create = env.sub("project", "create")
    assert len(create) == 1
    assert create[0][create[0].index("--owner") + 1] == "acme"
    data = json.loads((env.root / ".sdd" / "board.json").read_text())
    assert data == {"owner": "acme", "project": 9, "app_id": 5,
                    "tier0_branch_prefixes": ["bot/"]}
    assert link_args(env) == ["project", "link", "9", "--owner", "acme", "--repo", REPO]
