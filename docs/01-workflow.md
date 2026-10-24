# 01. ワークフロー

## Tier制（規模に応じて省略可）
全タスクは最初に Tier を判定する。迷ったら上位を選ぶ。

| Tier | 対象 | 作るもの |
|---|---|---|
| 0 | typo・コメント・docのみ・整形 | 何も作らず実施 |
| 1 | 局所的なbugfix・小さな変更 | 軽量spec（意図＋受入条件）＋テスト。plan/tasks は省略 |
| 2 | 新機能・複数ファイル・設計変更・公開API | spec → plan → tasks → 実装 → 検証 をフル |

すべての作業に Issue を作る（Tier 0 も）。判定した Tier は**ブランチ名** `t<Tier>/<Issue番号>-<名前>`
（例: `t2/73-github-projects-board`）に入れ、PRラベル `sdd:tier-N` をそれに合わせる（hooks/CI が参照）。
状態ファイルは持たない。Tier・feature（`<Issue番号>-<名前>`）・フェーズは、ブランチ名と `specs/<feature>/` のファイルから割り出す。

## フェーズ

### 設計（superpowers必須）
1. **brainstorm** — 人間と意図をすり合わせる（superpowers）。
2. **spec** — `specs/<feature>/spec.md`。受入条件を「チェック可能な文」で書き、人間承認を得る。
3. **plan** — `plan.md`。アプローチ・影響ファイル・トレードオフ・代替案。(Tier 2)
4. **tasks** — `tasks.md`。順序付きの具体タスク＋各受入条件に対応するテスト。(Tier 2)
5. **freeze** — 人間の承認のあと `orchestration/tools/sdd-freeze.sh` で `specs/<feature>/freeze.json` を作る。ここが他agentへの引き渡しゲート。凍結のやり直しも人間の承認のうえで作り直す。
   **STOP：freeze と同一セッションで実装を開始してはいけない。人間から「実装して」と明示的に指示を受けてから実装フェーズに入ること。**

### 実装（任意のagent）
- `specs/<feature>/` を読み、凍結された tasks を**そのまま**実装する（過不足なく）。
- 受入条件は必ずテストに対応させる。
- spec が間違っていたら**止めて人間にエスカレーション**。勝手に再設計しない。
- 実装が完了したら `tasks.md` のチェック欄をすべて `[x]` にする（Tier 2。フェーズは自動で verify になる）。commit → `orchestration/tools/sdd-board.sh sync` → 止まる。
- 行き詰まったら、Issue にコメントで理由を書いて止まる。

### 検証（superpowers必須）
- テスト実行。`sdd-reviewer` subagent で凍結specへの適合を独立監査。
- push は PR を作る直前だけ行う。PR がマージされるとボードは done になる。
- PR を作成し、CI が全てパスしてマージ可能な状態であることを確認してから完了とする。
- 最終的な合否は CI が独立に再判定する。

## 省略の基準
- Tier 0：spec不要（hooks/CIも免除）。
- Tier 1：軽量spec必須、plan/tasks省略可。
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
