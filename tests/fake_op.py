#!/usr/bin/env python3
"""Fake `op` for tests. Logs argv to $FAKE_OP_LOG, prints $FAKE_OP_OUTPUT,
exits with $FAKE_OP_EXIT (default 0)."""
import json
import os
import sys

with open(os.environ["FAKE_OP_LOG"], "a", encoding="utf-8") as f:
    f.write(json.dumps(sys.argv[1:]) + "\n")
code = int(os.environ.get("FAKE_OP_EXIT", "0"))
if code != 0:
    sys.stderr.write("fake op: failure\n")
    sys.exit(code)
sys.stdout.write(os.environ.get("FAKE_OP_OUTPUT", ""))
