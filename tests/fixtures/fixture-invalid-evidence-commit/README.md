## fixture-invalid-evidence-commit

**再現パターン:** `evidence.json` の `commit_sha` が git リポジトリに存在しない SHA。

**対応チェック:** Check 9 — `check_evidence`

**RED確認コマンド:**
```bash
bash integration/ci/sdd-validate.sh --root tests/fixtures/fixture-invalid-evidence-commit --branch t2/99-my-feature
# → exit 1, stderr に "commit_sha not found in git repository" が含まれる
```
