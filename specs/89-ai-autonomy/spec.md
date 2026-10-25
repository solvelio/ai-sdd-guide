# Spec: 89-ai-autonomy

- Tier: 2
- Feature slug: 89-ai-autonomy
- Issue: #89
- Traceability: [traceability.json](traceability.json)

## 背景 / 意図

今の rules は、Issue の対応中に人間の判断を何度も求める。フェーズが終わるたびに停止して指示を待ち、spec は人間が承認してから凍結し、凍結と実装は別のセッションで行う。
実際の運用では 1 つの Issue に人間が 5 回前後入っている（Tier の回答 → spec 承認 → 実装の指示 → verify と PR の指示 → マージの指示）。

guide の既定の流れを変え、人間の関与を次の 3 つに絞る。それ以外は AI が独立したエージェント（サブエージェント）を使って解決し、PR の作成まで進める。

1. 最初の質問
2. どうしても判断できないときの問い合わせ
3. PR のレビューとマージ

方針（2026-10-25、人間と確認済み）: 選択式ではなく guide の既定を変える。最初の質問は Tier と仕様の不明点。spec の承認は AI のレビュアー。

## 用語と規則

### 人間が関わる場面

1. **最初の質問**: AI は Issue と関係するコードを読み、次を 1 つのメッセージにまとめて人間に聞く。
   - Tier の案とその理由
   - 仕様の不明点（答えによって作るものが変わるものだけ。AI が妥当に決められるものは聞かず、「AI の判断」として記録する）

   人間の回答に従い、AI が `sdd:tier-N` ラベルを付ける。Tier を決めるのは人間のまま。
   Issue にすでに `sdd:tier-N` ラベルがあり、仕様の不明点もなければ、質問を省いてよい。
2. **問い合わせ**: 下の「問い合わせの条件」に当てはまるときだけ。
3. **PR のレビューとマージ**: 人間が PR をレビューし、承認してマージする。AI はマージしない。

### 自律で進める範囲

最初の質問の回答の後、AI はフェーズごとに止まらずに次の順で進める。

1. ブランチを作る
2. （Tier 2）設計: brainstorming スキルを、人間との対話なしで、Issue と最初の回答をもとに使う
3. spec を書く。Tier 2 は plan・tasks・traceability も書く
4. spec レビュー
5. 凍結し、handoff を書く
6. 実装: 凍結した成果物と handoff だけを渡した、新しいエージェントのコンテキストで行う
7. verify: `sdd-reviewer` が確かめる。指摘は `receiving-code-review` の規律で扱う
8. push して PR を作る
9. CI の結果を確かめ、人間に報告する

各フェーズの境目では、今と同じく commit → `sdd-board.sh sync` を行う。ただし停止しない。
「凍結と実装を同じセッションで行わない」は、「凍結と実装を同じエージェントのコンテキストで行わない」に置き換える。凍結の後の実装は新しいエージェントで行う。

### spec レビュー（spec の AI 承認）

**誰が**

spec を書いていない独立したエージェントが行う。
- Claude Code: サブエージェント `spec-reviewer`（`integration/agents/spec-reviewer.md`）
- そのほかのエージェント: `integration/prompts/spec-reviewer-prompt.md` を渡す

**いつ**

凍結の直前に 1 回行う。Tier 1 は `spec.md` を見る。Tier 2 は `spec.md`・`plan.md`・`tasks.md`・`traceability.json` をまとめて見る。

**何と照合するか**

- Issue の本文（Tier 2 は `issue-snapshot.json`）の AC が spec の AC にすべて対応し、削られたり弱められたりしていない
- 最初の質問の回答が反映されている
- spec の AC が確かめられる文で、テストに対応づけられる
- スコープが Issue を超えていない
- Tier 2: plan・tasks・traceability が spec と矛盾せず、各 AC にタスクとテストがある

**判定**

| 判定 | 意味 | 次の動き |
|---|---|---|
| `APPROVE` | 凍結してよい | 凍結する |
| `CHANGES` | 直す点がある（一覧を返す） | 書いた側が直して、もう一度レビューを受ける |
| `ESCALATE` | 問い合わせの条件に当たる | 人間に問い合わせる |

`CHANGES` は 3 回まで。3 回目のレビューでも `APPROVE` にならなければ人間に問い合わせる。

**記録**

凍結のコミットのメッセージに、判定と回数を書く（例: `Spec review: APPROVE (2 rounds)`）。PR 本文の「AI の判断」にも載せる。

**凍結後に spec を変えるとき**

spec レビューで再び `APPROVE` を得て凍結し直せば、人間の承認は要らない。ただし、変更が下の問い合わせの条件 1・2 に当たる場合は人間に問い合わせる。

### 問い合わせの条件

次のどれかに当たるときだけ、人間に問い合わせる。

1. Issue の AC を削る・弱める・スコープ外にする必要がある。Tier 2 で既存の「明示の人間承認」の規則が求める場面も含む
2. Issue の本文や最初の回答と矛盾する判断が必要になる
3. spec レビューが `ESCALATE` を返した、または 3 回のレビューで `APPROVE` にならない
4. レビューの指摘が凍結した spec と衝突し、spec を変えても条件 1・2 に当たらずには解けない
5. 取り消せない操作、またはリポジトリの外に影響する操作が必要になる。作業ブランチの push と PR の作成は除く。例: force push、他のリポジトリの変更、secret や設定の変更、データの削除
6. 権限や認証がなくて進めない

**問い合わせ方**

- 人間が対話の場にいれば、その場で聞いて回答を待つ
- いなければ、Issue に理由をコメントして停止する

### PR 本文の「AI の判断」

PR 本文に「AI の判断」の節を設け、人間が PR レビューで確かめられるように次を書く。

- spec レビューの判定と回数
- 仕様の不明点について AI が決めたこととその理由
- verify やレビューの指摘のうち、採用したもの・採用しなかったものとその理由
- スコープ外にしたものと、そのフォローアップの Issue

PR 本文の雛形は `templates/pr-body.md` に置く。

## 受入条件

- [ ] SAC-1: `rules/core.md`・`rules/workflow.md`・`rules/issue-intake.md`・`rules/subagents.md`・`orchestration/rules/orchestration.md` が「人間が関わる場面」と「自律で進める範囲」の流れを定めている。次の記述がない: フェーズの境目で停止して人間の指示を待つ、spec を凍結する前に人間の承認を得る（問い合わせの条件 1・2 の場面を除く）、凍結と実装を同じセッションで行わない。AI がマージしないことが書かれている（元 Issue: 89-AC1）
- [ ] SAC-2: 「問い合わせの条件」の 6 項目と問い合わせ方が `orchestration/rules/orchestration.md` に列挙され、ほかの rules はそこを参照する。Issue の AC を削る・弱める・スコープ外にするときに明示の人間承認が要ることは残っている（元 Issue: 89-AC2）
- [ ] SAC-3: `integration/agents/spec-reviewer.md` と `integration/prompts/spec-reviewer-prompt.md` があり、照合する項目、判定（`APPROVE` / `CHANGES` / `ESCALATE`）、3 回の上限、記録の仕方が書かれている。rules が凍結の前に spec レビューの `APPROVE` を求めている（元 Issue: 89-AC3）
- [ ] SAC-4: rules が PR 本文の「AI の判断」を求めている。`templates/pr-body.md` にその節と 4 つの項目がある（元 Issue: 89-AC4）
- [ ] SAC-5: 次のファイルに「凍結の前に人間の承認を得る」「人間が Claude に上げるまで待つ」などの旧い停止・承認の指示がなく、新しい流れと矛盾しない: `integration/hooks/skill-reminder.sh`、`integration/hooks/codex-skill-reminder.sh`、`integration/AGENTS.md.example`、`orchestration/integration/AGENTS-patch.md.example`、`orchestration/templates/handoff.md.example`、`integration/agents/sdd-reviewer.md`、`integration/prompts/sdd-reviewer-prompt.md`、`docs/00-overview.md`〜`docs/04-issue-tracker.md`、`README.md`（元 Issue: 89-AC5）
- [ ] SAC-6: 旧い停止・承認の文言を検査していた既存のテストが新しい流れに合わせて更新され、SAC-1〜SAC-5 と SAC-7 の要点をテストが検査する（元 Issue: 89-AC6）
- [ ] SAC-7: `docs/migration.md` に、既存の consumer 向けの変更点が書かれている。人間の関与が「最初の質問・問い合わせ・PR レビュー」に移ったこと、`spec-reviewer` が `update.sh` で `.claude/agents/` に配られること、Claude 以外のエージェントでは `spec-reviewer-prompt.md` を使うこと（元 Issue: 89-AC7）

## スコープ外

- CI・validator・`sdd_state.py`・guard の動作の変更。`freeze.json` は誰が承認したかを持たないので、AI の承認でも同じ形で作れる
- spec レビューの結果を機械的に検査できるファイルに残すこと（CI でゲートにすること）
- Tier を AI が決めること（Tier の決定は人間のまま）
- 過去の `specs/` と `_dev/` の書き換え
- GitHub 以外のトラッカー固有の問い合わせ方

## 制約 / 前提

- エージェントに依存しない書き方にする（Claude Code・Codex・Gemini で同じ流れ）。独立したエージェントを起動できない環境では、spec レビューと verify は人間に問い合わせる（問い合わせの条件 6）
- `rules/` は英語で命令形・簡潔、`docs/` は日本語（`rules/conventions.md`）
- この feature の開発中は、このリポジトリは今の rules（フェーズごとの停止と人間の承認）で動く
