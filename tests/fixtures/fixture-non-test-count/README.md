## fixture-non-test-count

**再現パターン:** `lint` コマンドの `test_count` が `null` ではなく整数値（スキーマ違反）。

**対応チェック:** Check 9 — `check_evidence` (schema validation)

**RED確認コマンド:**
```bash
bash integration/ci/sdd-validate.sh --root tests/fixtures/fixture-non-test-count --branch t2/99-my-feature
# → exit 1, stderr に "test_count" が含まれる
```
