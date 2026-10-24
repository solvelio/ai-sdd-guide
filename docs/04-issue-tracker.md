# 04. Issue トラッカー連携

Issue 登録から SDD ワークフロー完了までを、GitHub / GitLab / Bitbucket / Azure DevOps の
いずれでも同じ流れで回すための連携ルール。agent 向けの正本は `rules/issue-intake.md`。

## ステータスはブランチ名と specs/ から割り出す

SDD のステータスは、ブランチ名 `t<Tier>/<Issue番号>-<名前>` と `specs/<Issue番号>-<名前>/` のファイルから
割り出す（記録するファイルはない）。ボードは割り出した結果を**表示するだけ**。

- ボード: GitHub Projects（アカウントで 1 枚、1 Issue = 1 カード）。列は単一選択フィールド `Phase`:
  backlog → brainstorm → spec → plan → tasks → implement → verify → done。
- 設定: `.sdd/board.json`（`owner`・`project`・`tier0_branch_prefixes`）。Actions の secret は `SDD_PROJECT_TOKEN`
  （classic PAT、`project` スコープ）。
- 更新: 手元は `orchestration/tools/sdd-board.sh sync`、CI は `integration/ci/sdd-board.yml`。
- GitLab と Azure DevOps のボードは [#71]・[#72] で扱う。Bitbucket は Issues 廃止のため対象外。

## プラットフォーム機能マッピング

| 機能 | GitHub | GitLab | Bitbucket | Azure DevOps |
|---|---|---|---|---|
| Tier ラベル（sdd:tier-0/1/2） | Labels | Labels | Labels | Tags / Area |
| Issue 間の依存関係 | Relationships（blocks / blocked by） | Linked issues | Linked issues | Links（Predecessor / Successor） |
| PR との紐付け | `closes #N` | `closes #N` | `closes #N` | `AB#N` |
| ステータスのボード | Projects v2（実装済み） | Boards（#71） | 対象外 | Boards（#72） |

プラットフォームごとに違うのは「ラベル」「依存関係リンク」「PR↔Issue リンク」の3つだけ。
Tier ルールも SDD フェーズも全プラットフォーム共通。

## 前提：ブランチ保護の設定

`main` への直接 push を禁止し、すべての変更を PR 経由にする。管理者も例外なし。
設定手順はプラットフォームごとに `integration/issue-tracker/README.md` を参照。

## Issue 登録ルール

**GitHub（基準）:**
- `sdd:tier-0` / `sdd:tier-1` / `sdd:tier-2` ラベルを作成（→ `integration/issue-tracker/labels.sh`）
- 依存関係は Relationship（blocks / blocked by）で登録

**他3プラットフォーム:** 同等の設定方法は `integration/issue-tracker/README.md` を参照。

## Issue → SDD 完了までのフロー

```
Issue 登録（バグ報告・機能要望）
  → Actions がボードに backlog でカードを置く
  → 人間が Tier を判断 → sdd:tier-x ラベルを付与
  → エージェントが Issue を読み、ブランチ t<Tier>/<Issue番号>-<名前> を作って SDD ワークフロー開始
     - Tier 0: そのまま実装 → PR（closes #N）
     - Tier 1: 軽量 spec → 凍結 → 実装 → PR
     - Tier 2: spec → plan → tasks → 凍結 → 実装 → verify → PR
     → フェーズの区切りで commit → sdd-board.sh sync → 止まる
     → 行き詰まったら Issue にコメントで理由を書いて止まる
  → PR マージ → ボードのカードが done → Issue クローズ
```

- Tier の定義は [01. ワークフロー](01-workflow.md) を参照。
- フェーズ境界ごとに `sdd-board.sh sync` でボードを更新する（オーケストレーションの
  停止ルールと同じ。`orchestration/rules/orchestration.md`）。push は PR を作る直前だけ。
- Tier ラベルは PR にも付ける（hooks / CI が参照。`rules/conventions.md`）。

[#71]: https://github.com/toshikimiyagawa/ai-sdd-guide/issues/71
[#72]: https://github.com/toshikimiyagawa/ai-sdd-guide/issues/72
