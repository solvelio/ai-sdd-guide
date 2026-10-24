#!/usr/bin/env python3
"""Fake `gh` for tests. Logs every call as a JSON line to $FAKE_GH_LOG and answers
from the table in $FAKE_GH_RESPONSES (JSON object: space-joined arg prefix ->
{"stdout": str, "code": int}). Longest matching prefix wins. Unknown calls fail loudly."""
import json
import os
import sys

args = sys.argv[1:]
with open(os.environ["FAKE_GH_LOG"], "a", encoding="utf-8") as f:
    f.write(json.dumps(args) + "\n")
table = json.load(open(os.environ["FAKE_GH_RESPONSES"], encoding="utf-8"))
line = " ".join(args)
best = None
for prefix in table:
    if line == prefix or line.startswith(prefix + " "):
        if best is None or len(prefix) > len(best):
            best = prefix
if best is None:
    sys.stderr.write("fake gh: unexpected call: %s\n" % line)
    sys.exit(99)
resp = table[best]
sys.stdout.write(resp.get("stdout", ""))
if resp.get("stderr"):
    sys.stderr.write(resp["stderr"])
sys.exit(resp.get("code", 0))
