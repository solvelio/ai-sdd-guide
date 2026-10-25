# Issue #83: docs/migration.md 手順 4 が削除済みの state.schema.json / tasks.schema.json を参照している

Tier 1（軽量 spec）。

## 概要

`docs/migration.md` の「手順 4: state.json / tasks.json の schema 準拠確認（#52）」は、#73（f660e0d）で削除された
`orchestration/schema/state.schema.json` / `tasks.schema.json` を参照し、本文も `.sdd/state.json` / `.sdd/tasks.json` を作る v2 の手順のまま残っている。
「Consumer Update チェックリスト」にも両ファイルの schema 準拠を確認する項目があり、v3 の consumer は満たせない。

方針:
- 手順 4 は見出し（`## 手順 4:`。既存テストが見出しの存在を検査する）を残し、本文を v3 の説明に置き換える。
  `.sdd/state.json` / `.sdd/tasks.json` は使わず、Tier・feature・フェーズはブランチ名 `t<Tier>/<Issue番号>-<名前>` と `specs/` から割り出すこと、
  割り出した状態は `python3 vendor/ai-sdd-guide/integration/ci/sdd_state.py phase` で確認できること、v2 からの移行では「v3」節の手順で両ファイルを消すことを書く。
  削除済みスキーマへの参照と、両ファイルの JSON 例は消す。
- 「Consumer Update チェックリスト」の `state.json` / `tasks.json` の 2 項目を、「`.sdd/state.json` / `.sdd/tasks.json` を削除し、作業ブランチ名が `t<Tier>/<Issue番号>-<名前>` になっている」の 1 項目に置き換える。

## 受入条件

- [ ] SAC-1: `docs/migration.md` に書かれた `vendor/ai-sdd-guide/<path>` がすべて guide 内に実在する（`<path>` に `<` を含むプレースホルダは対象外、末尾の `...` は省略記号として除いて判定する）（元 Issue: 83-AC1）
- [ ] SAC-2: `docs/migration.md` の手順 4 と「Consumer Update チェックリスト」に、`.sdd/state.json` / `.sdd/tasks.json` を作る・schema に準拠させる指示がなく、手順 4 はブランチ名と `specs/` からの割り出し（`sdd_state.py phase`）を説明している（元 Issue: 83-AC2）
- [ ] SAC-3: SAC-1 をテストが検査する（元 Issue: 83-AC3）

## スコープ

- `docs/migration.md`: 手順 4 の本文、「Consumer Update チェックリスト」の 2 項目
- `tests/test_migration_guide.py`: SAC-1・SAC-2 のテストを追加

### スコープ外

- 手順 1〜3・5〜7、「具体例」の v2 の記述（`--feature my-feature` 等）
- 「v3」「v3.1」節の内容
- `docs/migration.md` 以外の文書

## テスト

- `tests/test_migration_guide.py::test_submodule_paths_exist_in_guide` — SAC-1, SAC-3
- `tests/test_migration_guide.py::test_step4_and_checklist_follow_v3_state_derivation` — SAC-2
