## fixture-incomplete-tasks

**再現パターン:** `--pr` で検査するとき `tasks.md` に未完了 checkbox が残っている。

**対応チェック:** Check 5 — `check_tasks_md_consistency`

**RED確認コマンド:**
```bash
bash integration/ci/sdd-validate.sh --root tests/fixtures/fixture-incomplete-tasks --pr --branch t2/99-my-feature
# → exit 1, stderr に "unchecked item" が含まれる
```

**GREEN確認コマンド (valid版):**
```bash
# pytest が tmp_path にコピーして evidence SHA を差し替えてから実行
pytest tests/test_negative_fixtures.py::test_valid_fixture_passes[fixture-incomplete-tasks-valid] -v
```
