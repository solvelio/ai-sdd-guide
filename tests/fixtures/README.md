# Fixture roots for `sdd-validate.sh`

Run any fixture with:

```bash
bash integration/ci/sdd-validate.sh --root tests/fixtures/<fixture-name>
```

Fixtures:

- `valid-active`: shared Tier 2 happy-path tree with valid `traceability.json`, `issue-snapshot.json`, and `evidence.json`.
- `valid-done`: done-reset tree; feature checks are skipped.
- `invalid-state-mismatch`: `.sdd/state.json` feature does not match `.sdd/tasks.json`.
- `invalid-tasks-incomplete`: verify-phase `tasks.md` still contains an unchecked task.
- `invalid-traceability`: `traceability.json` includes duplicate `spec_ac` entries and missing test files.
- `invalid-snapshot-hash-mismatch`: `issue-snapshot.json` has a `body_hash` that does not match `raw_body`.
- `invalid-evidence-bad-commit`: `evidence.json` references a `commit_sha` that does not exist in the repository.

## Expected Validator Results

| Fixture | Reproduces | Expected check / stderr | Expected exit |
|---|---|---|---|
| `valid-active` | Correct active Tier 2 feature with snapshot and evidence. | `sdd-validate: all checks passed for feature 'my-feature'` | 0 |
| `valid-done` | Done-reset state with no active feature. | `sdd-validate: tier=0 phase=done` | 0 |
| `invalid-state-mismatch` | `.sdd/state.json` points to a feature that is missing from `.sdd/tasks.json`. | `state.json feature='feature-a' has no matching entry in tasks.json` | 1 |
| `invalid-tasks-incomplete` | Verify-phase `tasks.md` still has an unchecked task. | `tasks.md line 3: unchecked item` | 1 |
| `invalid-traceability` | Duplicate `spec_ac` and missing runnable test files. | `traceability.json: duplicate spec_ac 'SAC-1'` | 1 |
| `invalid-snapshot-hash-mismatch` | Snapshot body changed without updating `body_hash`. | `issue-snapshot.json: body_hash does not match raw_body SHA-256` | 1 |
| `invalid-evidence-bad-commit` | Evidence references a commit SHA that is not present. | `evidence.json: commit_sha not found in git repository` | 1 |

## RED/GREEN Evidence

Recorded for PR #59. The evidence commit column records the commit SHA used by the fixture under test.

| Case | Command | Result | Evidence commit |
|---|---|---|---|
| RED snapshot fixture | `bash integration/ci/sdd-validate.sh --root tests/fixtures/invalid-snapshot-hash-mismatch` | exit 1, `body_hash does not match` | `f43630a7a7a47c5bedd06595129740fa164aa126` |
| RED evidence fixture | `bash integration/ci/sdd-validate.sh --root tests/fixtures/invalid-evidence-bad-commit` | exit 1, `commit_sha not found` | `0000000000000000000000000000000000000000` |
| GREEN valid counterpart | `bash integration/ci/sdd-validate.sh --root tests/fixtures/valid-active` | exit 0, all checks passed | `f43630a7a7a47c5bedd06595129740fa164aa126` |
| Automated shell tests | `pytest -q tests/test_sdd_validate.py -k 'sh_'` | 12 shell fixture tests passed | PR branch |
