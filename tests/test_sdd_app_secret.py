"""sdd-app-secret.sh: distribute the App private key from `op` to repo secrets."""
import json
import os
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "orchestration" / "tools" / "sdd-app-secret.sh"
FAKE_GH = Path(__file__).resolve().parent / "fake_gh.py"
FAKE_OP = Path(__file__).resolve().parent / "fake_op.py"

KEY_BODY = ["MIIEvQIBADANBgkqhkiG9w0BAQEFAAS-DISTINCT-ONE", "zzQ9-DISTINCT-TWO-secretbody"]
KEY = "\n".join(["-----BEGIN RSA PRIVATE KEY-----"] + KEY_BODY + ["-----END RSA PRIVATE KEY-----"]) + "\n"
RAW = "api -H Accept: application/vnd.github.raw repos/%s/contents/.sdd/board.json"
REF = "op://Private/app/key"


class Env:
    def __init__(self, tmp):
        self.tmp = Path(tmp)
        self.bin = self.tmp / "bin"
        self.bin.mkdir()
        for name, src in (("gh", FAKE_GH), ("op", FAKE_OP)):
            link = self.bin / name
            link.write_text("#!/bin/sh\nexec %s %s \"$@\"\n" % (sys.executable, src))
            link.chmod(link.stat().st_mode | stat.S_IEXEC)
        self.log = self.tmp / "gh.log"
        self.oplog = self.tmp / "op.log"
        self.stdin = self.tmp / "stdin.txt"
        self.responses = self.tmp / "resp.json"

    def run(self, table, args, op_output=KEY, op_exit=0):
        self.responses.write_text(json.dumps(table))
        env = dict(os.environ)
        env.update({
            "PATH": "%s:%s" % (self.bin, env["PATH"]),
            "FAKE_GH_LOG": str(self.log), "FAKE_GH_RESPONSES": str(self.responses),
            "FAKE_GH_STDIN": str(self.stdin), "FAKE_OP_LOG": str(self.oplog),
            "FAKE_OP_OUTPUT": op_output, "FAKE_OP_EXIT": str(op_exit),
        })
        for p in (self.log, self.oplog, self.stdin):
            p.write_text("")
        return subprocess.run(["bash", str(SCRIPT)] + args, env=env, capture_output=True,
                              text=True, input="")

    def calls(self):
        return [json.loads(l) for l in self.log.read_text().splitlines() if l]

    def joined(self):
        return [" ".join(c) for c in self.calls()]

    def secret_sets(self):
        return [c for c in self.joined() if c.startswith("secret set")]

    def puts(self):
        return [c for c in self.joined() if "-X PUT" in c]


def table(repo="solvelio/x", board_app_id="42", selection="all"):
    org = repo.split("/")[0]
    return {
        RAW % repo: {"stdout": "%s\n" % board_app_id if board_app_id is not None else "null\n"},
        "api --paginate /orgs/%s/installations" % org:
            {"stdout": ("%s\n" % selection) if selection else ""},
        "secret set SDD_APP_PRIVATE_KEY -R %s" % repo: {"stdout": ""},
    }


class SddAppSecretTest(unittest.TestCase):
    def setUp(self):
        self._t = tempfile.TemporaryDirectory()
        self.addCleanup(self._t.cleanup)
        self.env = Env(self._t.name)

    def test_script_is_executable(self):
        self.assertTrue(os.access(SCRIPT, os.X_OK))

    def test_sets_secret_from_op_via_stdin(self):
        r = self.env.run(table(), ["--op-ref", REF, "solvelio/x"])
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.env.secret_sets(), ["secret set SDD_APP_PRIVATE_KEY -R solvelio/x"])
        self.assertEqual(self.env.stdin.read_text(), KEY)
        self.assertNotIn("--body", " ".join(self.env.joined()))

    def test_key_never_printed(self):
        r = self.env.run(table(), ["--op-ref", REF, "solvelio/x"])
        for line in KEY_BODY:
            self.assertNotIn(line, r.stdout)
            self.assertNotIn(line, r.stderr)

    def test_app_id_from_board_json(self):
        r = self.env.run(table(), ["--op-ref", REF, "solvelio/x"])
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(len(self.env.secret_sets()), 1)

    def test_missing_app_id_fails(self):
        r = self.env.run(table(board_app_id=None), ["--op-ref", REF, "solvelio/x"])
        self.assertEqual(r.returncode, 1)
        self.assertEqual(self.env.secret_sets(), [])

    def test_app_installation_not_found_fails(self):
        r = self.env.run(table(selection=""), ["--op-ref", REF, "solvelio/x"])
        self.assertEqual(r.returncode, 1)
        self.assertEqual(self.env.secret_sets(), [])

    def test_warns_when_board_json_lacks_app_id(self):
        r = self.env.run(table(board_app_id=None), ["--op-ref", REF, "--app-id", "42", "solvelio/x"])
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("app_id", r.stdout + r.stderr)
        self.assertEqual(len(self.env.secret_sets()), 1)
        self.assertFalse([c for c in self.env.joined() if "PUT" in c and "contents" in c])

    def test_all_selects_repos_with_board_json(self):
        t = table()
        t["repo list solvelio"] = {"stdout": "solvelio/x\nsolvelio/nob\n"}
        t[RAW % "solvelio/nob"] = {"stdout": "", "stderr": "HTTP 404", "code": 1}
        r = self.env.run(t, ["--op-ref", REF, "--all", "--org", "solvelio"])
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.env.secret_sets(), ["secret set SDD_APP_PRIVATE_KEY -R solvelio/x"])

    def test_dry_run_changes_nothing(self):
        r = self.env.run(table(), ["--op-ref", REF, "--dry-run", "solvelio/x"])
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.env.puts(), [])
        self.assertEqual(self.env.secret_sets(), [])
        self.assertEqual(self.env.oplog.read_text(), "")
        self.assertIn("solvelio/x", r.stdout)

    def test_op_failure_does_not_set_secret(self):
        r = self.env.run(table(), ["--op-ref", REF, "solvelio/x"], op_output="", op_exit=1)
        self.assertEqual(r.returncode, 1)
        self.assertEqual(self.env.secret_sets(), [])

    def test_non_pem_output_does_not_set_secret(self):
        r = self.env.run(table(), ["--op-ref", REF, "solvelio/x"], op_output="garbage\nmore\n")
        self.assertEqual(r.returncode, 1)
        self.assertEqual(self.env.secret_sets(), [])
        self.assertNotIn("garbage", r.stdout + r.stderr)

    def test_uses_paginate_for_installation_lists(self):
        self.env.run(table(), ["--op-ref", REF, "solvelio/x"])
        pag = [c for c in self.env.calls() if "--paginate" in c]
        self.assertTrue(any("/orgs/solvelio/installations" in c for c in pag))

    def test_selected_installation_fails_with_guidance(self):
        r = self.env.run(table(selection="selected"), ["--op-ref", REF, "solvelio/x"])
        self.assertEqual(r.returncode, 1)
        self.assertIn("All repositories", r.stdout + r.stderr)
        self.assertEqual(self.env.secret_sets(), [])

    def test_never_calls_user_installations_or_put(self):
        self.env.run(table(), ["--op-ref", REF, "solvelio/x"])
        for c in self.env.joined():
            self.assertNotIn("/user/installations", c)
            self.assertNotIn("PUT", c)

    def test_mixed_owners_fail(self):
        r = self.env.run(table(), ["--op-ref", REF, "solvelio/x", "other/y"])
        self.assertEqual(r.returncode, 1)
        self.assertEqual(self.env.secret_sets(), [])

    def test_public_key_or_cert_rejected(self):
        for out in ("-----BEGIN PUBLIC KEY-----\nabc\n-----END PUBLIC KEY-----\n",
                    "-----BEGIN CERTIFICATE-----\nabc\n-----END CERTIFICATE-----\n"):
            r = self.env.run(table(), ["--op-ref", REF, "solvelio/x"], op_output=out)
            self.assertEqual(r.returncode, 1)
            self.assertEqual(self.env.secret_sets(), [])

    def test_secret_set_failure_names_repo(self):
        t = table()
        t["secret set SDD_APP_PRIVATE_KEY -R solvelio/x"] = {"stderr": "boom", "code": 1}
        r = self.env.run(t, ["--op-ref", REF, "solvelio/x"])
        self.assertEqual(r.returncode, 2)
        self.assertIn("solvelio/x", r.stderr)

    def test_bad_args_exit_1(self):
        r = self.env.run(table(), ["solvelio/x"])
        self.assertEqual(r.returncode, 1)


if __name__ == "__main__":
    unittest.main()
