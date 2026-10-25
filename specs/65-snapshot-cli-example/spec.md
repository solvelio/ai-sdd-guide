# Issue #65 + #68: migration.md の snapshot 作成例と guide ファイルのパスを consumer で実行できる形にする

Tier 1（軽量 spec）。#65 と #68 は同じ行を直すため、この feature でまとめて扱い、PR で両方を閉じる（人間の判断）。

## 概要

`docs/migration.md` は consumer 向けの手順書だが、次の 2 点でそのままでは動かない。

- Issue snapshot の作成例（3 箇所）が、`sdd-issue-snapshot.py` に存在しない `--root` オプションを使っている（#65）。
  出力先の既定はカレントディレクトリ基準の `specs/<feature>/issue-snapshot.json` なので、consumer のルートで実行すれば `--root` は不要。
- snapshot の作成例やコピー元のパスが guide 内パス（`integration/...`）で書かれている（#68）。
  consumer では guide は `vendor/ai-sdd-guide/` 配下にある（README で配置パスは固定済み）。

## 受入条件

- [ ] SAC-1: `docs/migration.md` の `sdd-issue-snapshot.sh` 実行例がすべて `bash vendor/ai-sdd-guide/integration/ci/sdd-issue-snapshot.sh` で始まり、`--root` を含まない（元 Issue: 65-AC1, 65-AC2, 68-AC1）
- [ ] SAC-2: `docs/migration.md` の consumer 向け手順（「手順 1」から「Consumer Update チェックリスト」まで）で guide のファイルを指すパス（`integration/...`・`orchestration/...`）がすべて `vendor/ai-sdd-guide/` 付きで書かれている（元 Issue: 68-AC2）
- [ ] SAC-3: `docs/migration.md` の `bash vendor/ai-sdd-guide/integration/ci/<name>.sh` 実行例すべてについて、スクリプトが存在し、使っているオプションが対応する `<name>.py` の `--help` に載っていることをテストが検査する（元 Issue: 65-AC3）
- [ ] SAC-4: SAC-1・SAC-2 をテストが検査する（元 Issue: 68-AC3）

## スコープ

- `docs/migration.md`: 上記 3 箇所の snapshot 実行例と、consumer 向け手順内の guide パス（計 17 箇所）
- `tests/test_migration_guide.py`: SAC-1〜3 のテストを追加

### スコープ外

- 「部分移行禁止チェックリスト」の項目（consumer の手順ではなく、guide の構成要素の一覧のため）
- 例の `--feature my-feature` / `auth-refresh` を v3 の命名（`<Issue番号>-<名前>`）に合わせること、v2 の記述（`state.json` 等）の書き換え

## テスト

- `tests/test_migration_guide.py::test_snapshot_examples_use_submodule_path_without_root` — SAC-1
- `tests/test_migration_guide.py::test_consumer_sections_use_submodule_paths` — SAC-2
- `tests/test_migration_guide.py::test_cli_examples_match_cli_options` — SAC-3
