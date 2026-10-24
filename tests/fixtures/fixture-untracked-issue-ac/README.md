## fixture-untracked-issue-ac

**再現パターン:** `traceability.json` の `issue_ac` が `issue-snapshot.json` の `stable_acs` に存在しない。

**対応チェック:** Check 8 — `check_issue_snapshot`

**RED確認コマンド:**
```bash
bash integration/ci/sdd-validate.sh --root tests/fixtures/fixture-untracked-issue-ac --branch t2/99-my-feature
# → exit 1, stderr に "traceability AC not in snapshot" が含まれる
```
