## fixture-orphan-spec-ac

**再現パターン:** `traceability.json` の `spec_ac` が `spec.md` に定義されていない。

**対応チェック:** Check 6 — `check_traceability_internal`

**RED確認コマンド:**
```bash
bash integration/ci/sdd-validate.sh --root tests/fixtures/fixture-orphan-spec-ac --branch t2/99-my-feature
# → exit 1, stderr に "not found in spec.md" が含まれる
```
