# Issue #63: sdd-check.yml を consumer にコピーすると sdd-validate のパスと submodule checkout が合わず失敗する

Tier 1（軽量 spec）。

## 概要

`integration/ci/sdd-check.yml` は consumer repository の `.github/workflows/` にコピーして使う前提だが、
validator を guide 内パス（`integration/ci/sdd-validate.sh`）で呼び、checkout も submodule を取得しないため、
consumer では `Run sdd-validate` が失敗する。テンプレート自体を consumer 前提に直し、
`update.sh` による上書きでも修正が保たれるようにする。

submodule の配置パスは README の導入例どおり `vendor/ai-sdd-guide` に固定する（人間の判断）。

## 受入条件

- [x] SAC-1: `sdd-check.yml` の `Run sdd-validate` は `vendor/ai-sdd-guide/integration/ci/sdd-validate.sh` を実行し、consumer 構成（`vendor/ai-sdd-guide` 配下に guide）で exit 0 になる（元 Issue: 63-AC1）
- [x] SAC-2: `sdd-check.yml` の `sdd` job の checkout が `submodules: true` を指定する（元 Issue: 63-AC2）
- [x] SAC-3: `docs/migration.md` の `sdd-validate.sh` 実行例がすべて `vendor/ai-sdd-guide/integration/ci/sdd-validate.sh` で書かれている（元 Issue: 63-AC3）
- [x] SAC-4: `integration/update.sh` を consumer に対して実行した後の `.github/workflows/sdd-check.yml` が SAC-1・SAC-2 を満たす（元 Issue: 63-AC4）
- [x] SAC-5: `README.md` の導入手順が submodule 配置パスを `vendor/ai-sdd-guide` 固定と明記し、「任意」と書かない（Issue 外。review 指摘を受け人間が今回の PR に含めると承認）

## スコープ

- `integration/ci/sdd-check.yml`: `sdd` job の checkout に `submodules: true`、validator パスを submodule パスへ
- `docs/migration.md`: `sdd-validate.sh` 実行例 3 箇所のパス
- `README.md`: 導入手順の submodule 配置パスの記述
- `integration/update.sh`: 変更しない（テンプレートを修正すれば上書き後も修正が保たれる）

### スコープ外

- 任意の submodule 配置パスへの対応（`vendor/ai-sdd-guide` 固定と決定済み）
- `docs/migration.md` の他スクリプト（`sdd-issue-snapshot.sh` 等）のパス表記

## テスト

- `tests/test_sdd_check_submodule.py::test_sdd_validate_step_runs_in_consumer_layout` — SAC-1
- `tests/test_sdd_check_submodule.py::test_sdd_job_checkout_fetches_submodules` — SAC-2
- `tests/test_sdd_check_submodule.py::test_migration_guide_uses_submodule_validator_path` — SAC-3
- `tests/test_sdd_check_submodule.py::test_update_sh_preserves_submodule_fix` — SAC-4
- `tests/test_sdd_check_submodule.py::test_readme_states_fixed_submodule_path` — SAC-5
