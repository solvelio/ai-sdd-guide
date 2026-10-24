## fixture-no-test-mapping

**再現パターン:** `traceability.json` の `test` フィールドが存在しないテストファイルを参照している。

**対応チェック:** Check 6 — `check_traceability_internal`

**RED確認コマンド:**
```bash
bash integration/ci/sdd-validate.sh --root tests/fixtures/fixture-no-test-mapping --branch t2/99-my-feature
# → exit 1, stderr に "test file not found" が含まれる
```
