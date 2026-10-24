## fixture-duplicate-spec-ac

**再現パターン:** `traceability.json` の2エントリが同一の `spec_ac` ID を持つ。

**対応チェック:** Check 6 — `check_traceability_internal`

**RED確認コマンド:**
```bash
bash integration/ci/sdd-validate.sh --root tests/fixtures/fixture-duplicate-spec-ac --branch t2/99-my-feature
# → exit 1, stderr に "duplicate spec_ac" が含まれる
```
