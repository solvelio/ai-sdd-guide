## fixture-scope-out-no-followup

**再現パターン:** `out-of-scope` エントリの `followup_issue` が HTTP(S) URL ではない。

**対応チェック:** Check 7 — `check_scope_out`

**RED確認コマンド:**
```bash
bash integration/ci/sdd-validate.sh --root tests/fixtures/fixture-scope-out-no-followup --branch t2/99-my-feature
# → exit 1, stderr に "missing HTTP(S) followup_issue" が含まれる
```
