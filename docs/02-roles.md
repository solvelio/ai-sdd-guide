# 02. 人とagentの分担

## 人間
人間の関与は次の 3 つに絞る。
- **最初の質問**への回答: Tier の決定と、仕様の不明点（答えによって作るものが変わるもの）への回答。
- **問い合わせ**への回答: Issue の AC を削る・弱めるとき、Issue や最初の回答と矛盾する判断が要るとき、spec レビューが `ESCALATE` を返したときなど（`orchestration/rules/orchestration.md` の Escalation conditions）。
- **PR のレビューとマージ**: PR 本文の「AI の判断」を確かめ、承認してマージする。AI はマージしない。

spec の承認は人間ではなく、独立したエージェント `spec-reviewer` が行う。

## 設計担当agent（superpowers必須）
- 最初の質問の後、PR の作成まで止まらずに進める（オーケストレーション）。
- brainstorm → spec → plan → tasks の作成。spec レビュー（spec-reviewer）を受けて凍結する。
- subagent と superpowers を使った深い検討。
- 実装後の検証（sdd-reviewer）。
- Claude Code / Codex CLI / Gemini CLI いずれでも担当可。

## 他のagent（実装担当）
- 凍結 spec を契約として実装。
- 凍結したエージェントとは別の、新しいエージェントのコンテキストで実装する。
- 逸脱しない。曖昧なら止めて、依頼したエージェントに報告する。

## subagent ロール
| ロール | 役割 | 権限 |
|---|---|---|
| researcher | コードベース/先行事例の調査 | 読み取りのみ |
| planner | spec から plan/tasks を起草 | 編集（spec-reviewer の承認前提） |
| spec-reviewer | 凍結の前に spec 一式を照合し `APPROVE` / `CHANGES` / `ESCALATE` を返す | 読み取りのみ |
| sdd-reviewer | 実装の凍結spec適合を監査 | 読み取り＋テスト実行 |

各subagentには会話の文脈が無いので、spec のパスと自己完結したブリーフを渡すこと。

## superpowers（Claude / Codex / Gemini 対応プラグイン）
設計・検証フェーズで活用する。Claude Code・Codex CLI・Gemini CLI でインストールして使える。成果物 `specs/<feature>/` に設計内容を落とし込み、superpowers を持たないagentへ橋渡しする。

SDDフェーズと superpowers スキルの対応：

| SDDフェーズ | superpowers スキル | 成果物 |
|---|---|---|
| brainstorm | `brainstorming` | 合意した設計 |
| spec | （brainstorm出力を整形） | `spec.md` |
| plan & tasks | `writing-plans` | `plan.md` / `tasks.md` |
| 実装(Claude時) | `executing-plans` + `test-driven-development` + `systematic-debugging` | コード+テスト |
| 検証 | `verification-before-completion` + `requesting-code-review` | レビュー結果 |
| レビュー受領 | `receiving-code-review` | 修正コミット or spec逸脱時のエスカレーション |
| subagent活用 | `dispatching-parallel-agents` / `subagent-driven-development` | - |

導入は Claude Code のプラグインとして行う（submoduleとは別）：
```
/plugin install superpowers@claude-plugins-official
```
