## fixture-weakened-ac

**再現パターン:** `issue-snapshot.json` の `stable_acs` に存在する AC が `traceability.json` に追跡されていない。

**対応チェック:** Check 8 — `check_issue_snapshot`

**RED確認コマンド:**
```bash
bash integration/ci/sdd-validate.sh --root tests/fixtures/fixture-weakened-ac --branch t2/99-my-feature
# → exit 1, stderr に "snapshot AC not tracked in traceability" が含まれる
```
