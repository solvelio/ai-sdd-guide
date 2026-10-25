# 01. ワークフロー

## 人間が関わる場面
人間の関与は次の 3 つだけ。それ以外は AI が独立したエージェント（サブエージェント）を使って解決し、PR の作成まで進める（正本: `orchestration/rules/orchestration.md`）。

1. **最初の質問** — AI が Issue と関係するコードを読み、Tier の案とその理由、仕様の不明点（答えによって作るものが変わるものだけ）を 1 つのメッセージで聞く。回答に従って AI が `sdd:tier-N` ラベルを付ける。Tier を決めるのは人間。ラベルがあり不明点もなければ省く。
2. **問い合わせ** — 「問い合わせの条件」（Issue の AC を削る・弱める必要がある、Issue や最初の回答と矛盾する、spec レビューが `ESCALATE` を返した など 6 項目）に当たるときだけ。人間がその場にいればその場で聞き、いなければ Issue に理由をコメントして停止する。
3. **PR のレビューとマージ** — 人間が PR をレビューし、承認してマージする。AI はマージしない。

## Tier制（規模に応じて省略可）
全タスクは最初に Tier を判定する（AI が案を出し、人間が決める）。迷ったら上位を選ぶ。

| Tier | 対象 | 作るもの |
|---|---|---|
| 0 | typo・コメント・docのみ・整形 | 何も作らず実施 |
| 1 | 局所的なbugfix・小さな変更 | 軽量spec（意図＋受入条件）＋テスト。plan/tasks は省略 |
| 2 | 新機能・複数ファイル・設計変更・公開API | spec → plan → tasks → 実装 → 検証 をフル |

すべての作業に Issue を作る（Tier 0 も）。判定した Tier は**ブランチ名** `t<Tier>/<Issue番号>-<名前>`
（例: `t2/73-github-projects-board`）に入れ、PRラベル `sdd:tier-N` をそれに合わせる（hooks/CI が参照）。
状態ファイルは持たない。Tier・feature（`<Issue番号>-<名前>`）・フェーズは、ブランチ名と `specs/<feature>/` のファイルから割り出す。

## フェーズ
最初の質問の回答の後、AI はフェーズごとに止まらずに進める。各フェーズの境目では commit → `orchestration/tools/sdd-board.sh sync` を行い、そのまま次へ進む。

### 設計（superpowers必須）
1. **brainstorm** — Issue と最初の回答をもとに、人間との対話なしで設計する（superpowers）。
2. **spec** — `specs/<feature>/spec.md`。受入条件を「チェック可能な文」で書く。AI が決めた不明点は PR の「AI の判断」に載せる。
3. **plan** — `plan.md`。アプローチ・影響ファイル・トレードオフ・代替案。(Tier 2)
4. **tasks** — `tasks.md`。順序付きの具体タスク＋各受入条件に対応するテスト。(Tier 2)
5. **spec レビュー** — spec を書いていない独立したエージェント `spec-reviewer`（Claude 以外は `integration/prompts/spec-reviewer-prompt.md`）が、Issue の AC・最初の回答・テストへの対応・スコープを照合する。Tier 1 は `spec.md`、Tier 2 は `spec.md`・`plan.md`・`tasks.md`・`traceability.json` を見る。判定は `APPROVE`（凍結してよい）/ `CHANGES`（直してもう一度）/ `ESCALATE`（人間に問い合わせる）。3 回で `APPROVE` にならなければ人間に問い合わせる。
6. **freeze** — `APPROVE` の後 `orchestration/tools/sdd-freeze.sh` で `specs/<feature>/freeze.json` を作る。ここが他agentへの引き渡しゲート。判定と回数は凍結のコミットのメッセージに書く（例: `Spec review: APPROVE (2 rounds)`）。凍結のやり直しも spec レビューの `APPROVE` を得て作り直す（AC を削る・弱める変更なら人間に問い合わせる）。
   凍結の後の実装は、凍結した成果物と `handoff.md` だけを渡した**新しいエージェントのコンテキスト**で行う。凍結したエージェントのコンテキストで実装しない。

### 実装（任意のagent）
- `specs/<feature>/` を読み、凍結された tasks を**そのまま**実装する（過不足なく）。
- 受入条件は必ずテストに対応させる。
- spec が間違っていたら**止めて、依頼した（オーケストレーションする）エージェントに報告**する。勝手に再設計しない。依頼した側が spec レビューで直すか、人間に問い合わせる。
- 実装が完了したら `tasks.md` のチェック欄をすべて `[x]` にする（Tier 2。フェーズは自動で verify になる）。commit → `orchestration/tools/sdd-board.sh sync` → 検証へ進む。

### 検証（superpowers必須）
- テスト実行。`sdd-reviewer` subagent で凍結specへの適合を独立監査。指摘は `receiving-code-review` の規律で扱う。
- push は PR を作る直前だけ行う。PR がマージされるとボードは done になる。
- PR を作成し、CI が全てパスしてマージ可能な状態であることを確認してから人間に報告する。マージは人間が行う。
- PR 本文には「AI の判断」の節を設ける（雛形 `templates/pr-body.md`）: spec レビューの判定と回数、仕様の不明点について AI が決めたこととその理由、指摘の採否とその理由、スコープ外にしたものとそのフォローアップの Issue。
- 最終的な合否は CI が独立に再判定する。

## 省略の基準
- Tier 0：spec不要（hooks/CIも免除）。
- Tier 1：軽量spec必須、plan/tasks省略可。流れは 軽量spec → spec レビュー（`spec-reviewer` の `APPROVE`）→ `sdd-freeze.sh`（`spec.md` を凍結）→ `handoff.md` → 実装 → PR。PR では CI が `freeze.json` と `handoff.md` を求める。
- Tier 2：省略しない。

「小さいから省く」判断はブランチ名（`t0/`・`t1/`）と PRラベルで宣言し、後から検証できる形にする。
これにより hooks（ローカル）と CI（権威）が機械的に Tier を判定できる。

## 状態の割り出し
状態は記録せず、毎回ブランチ名と `specs/<feature>/` から割り出す。`python3 vendor/ai-sdd-guide/integration/ci/sdd_state.py phase` で確認できる。

| 条件（上から順に最初に当てはまったもの） | フェーズ |
|---|---|
| PR がマージ済み（Actions のみが判定） | done |
| Tier 2、`freeze.json` が正しく、`tasks.md` のチェック欄がすべて `[x]` | verify |
| Tier 1/2、`freeze.json` が正しい | implement |
| Tier 0 | implement |
| `tasks.md` がある | tasks |
| `plan.md` がある | plan |
| `spec.md` がある | spec |
| Tier 1/2 で `specs/<feature>/` がない | brainstorm |
| ブランチがない（Actions が Issue 作成時にカードを置く） | backlog |

- 凍結対象は Tier 2 が `spec.md`・`plan.md`・`tasks.md`・`traceability.json`、Tier 1 が `spec.md`。`freeze.json` に各ファイルのハッシュを記録する（`tasks.md` はチェック欄を正規化してから）。
- `freeze.json` があるのに正しくない（対象ファイルが書き換わった・消えた）場合は、フェーズを割り出さずエラーになる。
- ボード（GitHub Projects）の `Phase` 列は backlog → brainstorm → spec → plan → tasks → implement → verify → done。

## 並列作業

複数の feature を同時に進める場合は、**feature ごとに git worktree を分ける**。
各 worktree が独立したブランチにいるため、割り出される Tier・フェーズが混ざらない。

```bash
# worktree 作成（using-git-worktrees スキルで自動化も可）
git worktree add .worktrees/73-feature-b -b t2/73-feature-b
```

1つの worktree に複数の feature を混在させてはいけない。
