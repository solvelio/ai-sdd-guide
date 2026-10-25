# Issue #87: docs/migration.md に v2（state.json / tasks.json）前提の記述が残っている

Tier 1（軽量 spec）。

## 概要

#83 で `docs/migration.md` の手順 4 の本文と「Consumer Update チェックリスト」を v3 に直したが、次の v2 の記述が残っている。

1. 手順 4 の見出しが `## 手順 4: state.json / tasks.json の schema 準拠確認（#52）` のままで、本文（ブランチ名と `specs/` からの割り出し）と合わない。
2. 手順 5 が `sdd-check.yml` を「State reset gate（`state.json` が `phase=done`）」「Spec gate」「Run sdd-validate」の 3 段階と説明しているが、
   実際の `integration/ci/sdd-check.yml` のステップは `Install dependencies` / `Run sdd-validate` / `Tests` だけである。
3. 手順 7 の reviewer の確認項目に「`state.json` が対象 feature / tier / phase を指している」「`tasks.json` に対象 feature のエントリがあり schema valid である」がある。
   `integration/prompts/sdd-reviewer-prompt.md` の該当項目は「名前の一致」（ブランチ名・`specs/` のディレクトリ名・`issue-snapshot.json` の Issue 番号）と「freeze の有効性」（`sdd_state.py phase` がエラーにならない）である。
4. 具体例 A に `# exit 0 を確認してから state.json を phase=implement に変更` がある。v3 では spec の承認後に `sdd-freeze.sh` で `freeze.json` を作る。
5. 部分移行禁止チェックリストの `orchestration/schema/` の項目が、#73 で削除された state / tasks の schema を挙げている。

方針:
- 手順 4 の見出しを `## 手順 4: 状態の割り出しの確認（#52）` にする（`手順 4:` は既存テストが検査するので残す）。
- 手順 5 の「3 段階」の説明を、`sdd-check.yml` の実際のステップ（`Install dependencies`・`Run sdd-validate`・`Tests`）の説明に置き換える。
  `Run sdd-validate` は `sdd-validate.sh --root . --pr --branch <PR のブランチ> --pr-labels <PR のラベル>` を実行し、ブランチ名の形・PR の Tier ラベルとブランチの Tier の一致・`freeze.json` と `handoff.md`（Tier 1/2）・Tier 2 の traceability / issue snapshot / evidence を検査する、と書く。
- 手順 7 の項目 3・4 を、reviewer prompt の「名前の一致」「freeze の有効性」に置き換える。
- 具体例 A の手順 4 のコメントを、spec の承認後に `bash vendor/ai-sdd-guide/orchestration/tools/sdd-freeze.sh` で凍結する、に置き換える。
- 部分移行禁止チェックリストの `orchestration/schema/` の項目を `traceability / issue-snapshot / evidence schema` にする。

## 受入条件

- [ ] SAC-1: 手順 4 の見出し行が `手順 4:` を含み、`state.json`・`tasks.json`・`schema` を含まない（元 Issue: 87-AC1）
- [ ] SAC-2: 手順 5 の本文が `state.json`・`phase=done`・`State reset gate`・`Spec gate` を含まず、`integration/ci/sdd-check.yml` のステップ名（`- name:` の値）をすべて含む（元 Issue: 87-AC2）
- [ ] SAC-3: 手順 7 と「具体例」の本文が `state.json`・`tasks.json` を含まない（元 Issue: 87-AC3）
- [ ] SAC-4: 部分移行禁止チェックリストの `orchestration/schema/` の項目が挙げる schema 名がすべて `orchestration/schema/<名前>.schema.json` として実在し、実在する schema をすべて挙げている（元 Issue: 87-AC4）
- [ ] SAC-5: SAC-1〜SAC-4 をテストが検査する（元 Issue: 87-AC5）

## スコープ

- `docs/migration.md`: 手順 4 の見出し、手順 5 の sdd-check.yml の説明、手順 7 の項目 3・4、具体例 A の手順 4 のコメント、部分移行禁止チェックリストの `orchestration/schema/` の項目
- `tests/test_migration_guide.py`: SAC-1〜SAC-4 のテストを追加

### スコープ外

- 「影響範囲」の表と「v3」「v3.1」節の `state.json` / `tasks.json` への言及（移行の経緯として残す）
- 具体例・手順 1〜3 の `--feature my-feature` 等の feature 名（`sdd-issue-snapshot.sh` の `--feature` は今も有効なオプション）
- `docs/migration.md` 以外の文書、`sdd-check.yml`・reviewer prompt の内容変更

## テスト

- `tests/test_migration_guide.py::test_step4_heading_has_no_v2_terms` — SAC-1, SAC-5
- `tests/test_migration_guide.py::test_step5_describes_actual_sdd_check_steps` — SAC-2, SAC-5
- `tests/test_migration_guide.py::test_step7_and_examples_have_no_state_files` — SAC-3, SAC-5
- `tests/test_migration_guide.py::test_partial_migration_checklist_lists_existing_schemas` — SAC-4, SAC-5
