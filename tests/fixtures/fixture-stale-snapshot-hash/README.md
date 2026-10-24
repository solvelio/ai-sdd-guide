## fixture-stale-snapshot-hash

**再現パターン:** `raw_body` を改変したが `body_hash` が更新されていない（SHA-256 不一致）。

**対応チェック:** Check 8 — `check_issue_snapshot`

**RED確認コマンド:**
```bash
bash integration/ci/sdd-validate.sh --root tests/fixtures/fixture-stale-snapshot-hash --branch t2/99-my-feature
# → exit 1, stderr に "body_hash does not match" が含まれる
```
