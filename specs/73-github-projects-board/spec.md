# Spec: 73-github-projects-board

- Tier: 2
- Status: frozen
- Feature slug: 73-github-projects-board
- Issue: #73
- Design: [_dev/specs/2026-10-24-github-projects-board-design.md](../../_dev/specs/2026-10-24-github-projects-board-design.md)
- Traceability: [traceability.json](traceability.json)

## 背景 / 意図

SDD の状態を `.sdd/state.json` と `.sdd/tasks.json` に手で書く仕組みをやめる。状態はブランチ名と `specs/<feature>/` の中のファイルから機械的に割り出し、ボードは GitHub Projects（アカウントで 1 枚）に任せる。

解決する課題:
- GitHub Projects と同じ機能（`tasks.json` + `kanban.sh` / `kanban-html.sh` / `kanban-pages.yml`）を自前で持つ二重開発
- 手書きの状態のずれ（#26、`completed` のときの `phase` の揺れ、main から作業中が見えない）
- `state.json` の並列衝突（#22）と、PR 前のリセット（#28）で main から作った worktree が Tier 0 扱いになり、spec なしのソース編集が guard を通る穴

理由と検討の経緯は Design を参照。

## 用語と規則

### ブランチ名

`^t(?P<tier>[012])/(?P<issue>[1-9][0-9]*)-(?P<name>[a-z0-9][a-z0-9-]*)$`

- feature = `<issue>-<name>`（例: ブランチ `t2/73-github-projects-board` → feature `73-github-projects-board`）
- spec のディレクトリ = `specs/<feature>/`
- 形に合わないブランチ（`main` を含む）は「Tier 未分類」

### 凍結

- 凍結コマンドが `specs/<feature>/freeze.json` を作る。凍結の対象ファイルと各ファイルのハッシュを記録する。
- 対象: Tier 2 は `spec.md`・`plan.md`・`tasks.md`・`traceability.json`。Tier 1 は `spec.md`。
- `tasks.md` は、行頭のチェック欄 `- [x]` を `- [ ]` に正規化してからハッシュを取る。
- 「`freeze.json` が正しい」= `freeze.json` があり、記録したすべての対象ファイルが存在して、ハッシュが一致する。

### フェーズ

上から順に、最初に当てはまったものを採る。

| 条件 | フェーズ |
|---|---|
| PR がマージ済み（Actions のみが判定） | done |
| Tier 2、`freeze.json` が正しく、`tasks.md` のチェック欄がすべて `[x]` | verify |
| Tier 1/2、`freeze.json` が正しい | implement |
| Tier 0 | implement |
| `tasks.md` がある | tasks |
| `plan.md` がある | plan |
| `spec.md` がある | spec |
| Tier 1/2 で `specs/<feature>/` がない | brainstorm |
| ブランチがない（Actions が Issue 作成時に置く） | backlog（表示名「未着手」） |

- `freeze.json` があるのに正しくない場合は、フェーズを割り出さずエラーにする。
- Tier 1 は verify を割り出さない。

### ボード

- GitHub Projects（v2）を 1 枚。1 Issue = 1 カード。カードは Issue で見つける。
- 単一選択フィールド `Phase`: `backlog`, `brainstorm`, `spec`, `plan`, `tasks`, `implement`, `verify`, `done`。
- 設定ファイル `.sdd/board.json`（コミットする）: `owner`、Project の番号、Tier 0 として通すブランチの接頭辞（既定 `["dependabot/", "renovate/"]`）。
- Actions は secret `SDD_PROJECT_TOKEN`（classic PAT、`project` スコープ）で Projects を操作する。

## 受入条件

- [ ] SAC-1: `.sdd/state.json`、`.sdd/tasks.json`、`orchestration/schema/state.schema.json`、`orchestration/schema/tasks.schema.json`、`templates/sdd-state.example.json`、`templates/sdd-state.schema.json`、`orchestration/tools/kanban.sh`、`orchestration/tools/kanban-html.sh`、`integration/ci/kanban-pages.yml`、`integration/ci/sdd-check.yml` の orchestration ジョブがない。`rules/`・`orchestration/`・`integration/`・`templates/`・`docs/`・`README.md` に、tasks.json の更新、かんばんの表示、state.json の設定やリセットを指示する記述がない（`docs/migration.md` の移行手順と `_dev/`・過去の `specs/` は除く）（元 Issue: 73-AC1）
- [ ] SAC-2: ブランチ名から Tier・Issue 番号・feature を割り出せる。形に合わない名前（`main`、`feat/x`、`t3/1-x`、`t2/x`、`t2/0-x`、`t2/1-X` など）は「Tier 未分類」になる（元 Issue: 73-AC2）
- [ ] SAC-3: 凍結コマンドが `specs/<feature>/freeze.json` を作り、Tier ごとの対象ファイルとハッシュを記録する。`tasks.md` のチェック欄だけを変えてもハッシュは変わらない（元 Issue: 73-AC3）
- [ ] SAC-4: guard（Claude 用 `sdd-guard.sh`、Codex 用 `codex-sdd-guard.sh`）は、ソースファイルの編集を、`t0/` なら許可し、`t1/`・`t2/` なら `freeze.json` が正しいときだけ許可し、それ以外（`main`、形に合わない名前、`freeze.json` がない・正しくない）は拒否する。既存の除外パス（`*.md`、`specs/*`、`docs/*` など）と linked worktree の制限、`SDD_ALLOW_MAIN_WORKTREE` は保つ。判定にネットワークや `gh` を使わない（元 Issue: 73-AC4）
- [ ] SAC-5: 凍結後に `spec.md`・`plan.md`・`tasks.md`（チェック欄以外）・`traceability.json` のどれかを書き換えると、guard はソース編集を拒否し、validator はエラーを返す（元 Issue: 73-AC5）
- [ ] SAC-6: フェーズが「フェーズ」の表のとおりに割り出される。少なくとも、Tier 0 → implement、Tier 1 の spec → implement、Tier 2 の brainstorm → spec → plan → tasks → implement → verify の各段階と、`freeze.json` が正しくない場合のエラーを確かめる（元 Issue: 73-AC6）
- [ ] SAC-7: skill-reminder（`skill-reminder.sh`、`codex-skill-reminder.sh`）が割り出したフェーズに応じたスキルを促す。Tier 0 と「Tier 未分類」では何も出さない（元 Issue: 73-AC7）
- [ ] SAC-8: validator は対象の feature をブランチ名から決める（CI では `GITHUB_HEAD_REF`、手元では今のブランチ、`--feature` で上書き）。次を検査する: ブランチ名の形、Tier 1/2 の `freeze.json` が正しい、Tier 2 の `issue-snapshot.json` の Issue 番号がディレクトリ名の番号と一致する、`freeze.json` があれば `handoff.md` がある。main への push（PR ではない実行）では feature の検査を飛ばす（元 Issue: 73-AC8）
- [ ] SAC-9: PR の CI は、ブランチ名が形に合わなければ失敗する。`.sdd/board.json` の接頭辞（既定 `dependabot/`・`renovate/`）で始まるブランチは Tier 0 として通す（元 Issue: 73-AC9）
- [ ] SAC-10: Actions は PR にブランチ名の Tier の `sdd:tier-N` ラベルを付ける。ブランチ名と食い違う `sdd:tier-N` ラベルが付いていれば CI は失敗する（元 Issue: 73-AC10）
- [ ] SAC-11: `sdd-board.sh sync` は今のブランチの Issue のカードの `Phase` を割り出したフェーズに更新し、カードがなければボードに入れる。ネットワーク・認証・`.sdd/board.json` のどれかがないとき、または `freeze.json` が正しくないときは、警告を出してカードを変えず、終了コード 0 で終わる（元 Issue: 73-AC11）
- [ ] SAC-12: `sdd-board.sh init` はボードと `Phase` フィールドを作り、対象リポジトリの開いている Issue をすべて `backlog` で取り込む。取り込みだけを行うサブコマンドがあり、すでにボードにあるカードを変えず、2 回実行しても結果が同じ（元 Issue: 73-AC12）
- [ ] SAC-13: Actions のワークフロー `integration/ci/sdd-board.yml` は、Issue 作成でカードを `backlog` に置き、Issue が completed で閉じたら `done`、not planned か duplicate で閉じたらカードをアーカイブし、PR の作成・更新・再オープンでフェーズを割り出し直し、マージで `done` にする。マージせずに閉じた PR ではカードを変えない。`SDD_PROJECT_TOKEN` がなければ警告を出して成功で終わる（元 Issue: 73-AC13）
- [ ] SAC-14: `integration/agents/sdd-reviewer.md` と `integration/prompts/sdd-reviewer-prompt.md` の確認項目に state.json・tasks.json がなく、ブランチ名・ディレクトリ名・Issue 番号の一致と `freeze.json` が正しいことを確かめる項目がある（元 Issue: 73-AC14）
- [ ] SAC-15: `templates/tasks.md` の「CI green」「sdd-reviewer 合格」がチェック欄（`- [ ]`）ではない（元 Issue: 73-AC15）
- [ ] SAC-16: `integration/update.sh` が `sdd-board.yml` を consumer の `.github/workflows/` に配り、`kanban-pages.yml` を配らない（元 Issue: 73-AC16）
- [ ] SAC-17: `docs/migration.md` に、state.json・tasks.json の削除、`.sdd/board.json` の作成、secret `SDD_PROJECT_TOKEN` の登録、ワークフローの導入、`sdd-board.sh init`、作業中ブランチの扱い（終わらせるか改名してから submodule を上げる）、リポジトリごとのビューの作り方の手順がある（元 Issue: 73-AC17）
- [ ] SAC-18: このリポジトリ自身に `.sdd/state.json`・`.sdd/tasks.json` がなく、`.sdd/board.json` と `.github/workflows/` の新しいワークフローがあり、この feature の `freeze.json` が正しく、新しい validator が PASS する（元 Issue: 73-AC18）

## スコープ外

- フェーズの中の進み具合の表示、「作業中」と「判断待ち」の区別
- GitLab（#71）、Azure DevOps（#72）、Bitbucket（Issues 廃止のため対象外。古い説明の掃除も別件）
- 過去の `specs/<feature>/` の改名
- Projects のビューの自動作成（API がない。手順書で扱う）
- #66（Tier 2 の validator が凍結前にテストと evidence を求める）の修正。フェーズに応じた検査への直しは別 Issue

## 制約 / 前提

- hook はオフライン・認証なしで、編集のたびに即座に判定できること。
- ボードの更新の失敗は作業を止めない（警告のみ）。
- 移行期間は設けない。`state.json` / `tasks.json` へのフォールバックを持たない。
- 割り出しの規則（ブランチ名、凍結、フェーズ）は 1 か所に実装し、guard・skill-reminder・validator・sdd-board.sh はそれを使う。
- 標準の `GITHUB_TOKEN` は Projects v2 を操作できない。Projects の組み込み自動追加は Free プランで 1 リポジトリまで。Projects のビューは API で作れない。
- この feature の開発中は、このリポジトリは今の仕組み（state.json あり）で動く。最後に新しい仕組みへ移行する（SAC-18）。
