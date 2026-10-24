# Design: SDD の状態管理を GitHub Projects とファイルからの割り出しに移す

Date: 2026-10-24
Issue: #73（Tier 2）
関連: #18（kanban-web）、#19（issue-tracker）、#22（state.json の並列衝突）、#26（state/tasks の更新漏れ）、#28（PR 前の state リセット）、#64、#66、#71（GitLab）、#72（Azure DevOps）

この文書の「（設計者判断）」は、人と合意したことではなく、設計者が決めたこと。実装前のレビューで見直してよい。

## 1. なぜやるか

- GitHub にボード（Projects）があるのに、`.sdd/tasks.json` + `kanban.sh` / `kanban-html.sh` / `kanban-pages.yml` という同じ機能を自前で持っている。二重開発になっている。
- 状態がずれる。原因は 3 つ:
  1. エージェントが手で JSON を書き換えるため、更新を忘れる（#26: PR マージ後も `state.json` が `implement` のまま、`tasks.json` にエントリなし）。
  2. 完了時の書き方がそろわない（このリポジトリの `tasks.json` は 8 件すべて `completed` だが、`phase` は `verify` 7 件・`implement` 1 件。consumer では `done` にした例もある）。
  3. `tasks.json` はブランチ上で書き換えるので、main からは作業中の状態が見えない。Web 表示（GitHub Pages）は main から作るため、ほぼ `completed` しか出ない。人は一度も見ていない。
- `state.json` にも問題がある:
  - 単一ファイルなので並列作業で衝突する（#22）。
  - PR 前に `{"tier": 0, "phase": "done"}` へ戻す手順が分かりにくい（#28）。
  - **戻した結果、main から作った新しい worktree が最初から Tier 0 扱いになり、`sdd-guard.sh` が spec なしのソース編集を通す**（consumer の soro-quest で確認）。

## 2. ゴール・非ゴール・アンチゴール

### ゴール

- ボードを見れば「**どの Issue が今どのフェーズで止まっているか、どこまで進んでいるか**」が分かる。粒度はフェーズ単位。
- 未着手を含めた**全 Issue** がボードに出る。
- SDD を使うすべてのリポジトリを **1 枚のボード**にまとめる（リポジトリごとの絞り込みは Projects の `repo:` フィルタと保存ビューで行う）。
- `.sdd/state.json` と `.sdd/tasks.json` を**なくす**。状態は「ブランチ名」と「`specs/<feature>/` の中のファイル」から機械的に割り出す。人もエージェントも状態の値を手で書かない。

### 非ゴール

- フェーズの中の進み具合（T3/T7 など）の表示。
- 「エージェントが作業中」と「人の判断待ち」の区別（フェーズの列だけで十分）。
- GitLab / Azure DevOps 対応（#71、#72 で別途）。Bitbucket は Cloud の Issues が 2026 年 8 月中旬に廃止されたため対象外。
- 過去の `specs/<feature>/`（`issue-48`、`traceability-format` など、consumer の `soro-quest-mvp` など）の改名。完了済みの作業はそのまま残す。
- リアルタイム更新。

### アンチゴール（技術的に動いても失敗とみなすもの）

- ローカルの hook（`sdd-guard.sh` など）がネットワークや GitHub の認証に依存する。hook はオフラインで即座に判定できなければならない。
- ボードの更新に失敗したときに作業が止まる。ボードの更新は**警告のみ**で、作業をブロックしない。
- 状態の値を人やエージェントが手で入力する運用が残る。
- 何も宣言していないブランチでソース編集が通る（今の Tier 0 すり抜けの再発）。

## 3. 決まったこと（人と合意済み）

### 3.1 作業の名前: Issue 番号を先頭に付ける

- **すべての作業に Issue を作る。Tier 0 も例外にしない。**
- ブランチ名: `t<Tier>/<Issue番号>-<短い名前>`。例: `t2/1-soro-quest-mvp`、`t0/3-d1-database-id`。
- spec のディレクトリ: `specs/<Issue番号>-<短い名前>/`。ブランチ名の `t<Tier>/` より後ろと同じ文字列。例: `specs/1-soro-quest-mvp/`。
- Tier を途中で上げるときは `git branch -m` で名前を変える。
- Tier 0 は spec のディレクトリを持たない。

### 3.2 凍結: `specs/<feature>/freeze.json`

- 凍結するときに `freeze.json` を作り、凍結したファイルのハッシュ値を記録する。
- `tasks.md` は、チェック欄の状態を正規化してからハッシュを取る（`[x]` → `[ ]`）。凍結後に許される変更はチェック欄だけ、という既存ルール（`rules/core.md`）をそのまま機械的に確かめるため。
- guard は「`freeze.json` があり、ハッシュがすべて一致している」ときだけ、Tier 1/2 のソース編集を許可する。
- 凍結のやり直しは、人の承認のうえで `freeze.json` を作り直す。

### 3.3 Tier と feature の読み取り: ブランチ名

hook はオフラインで判定するため、Issue のラベルは使わずブランチ名を読む。

| 今のブランチ | ソース編集 |
|---|---|
| `t0/<N>-<name>` | 許可 |
| `t1/<N>-<name>` / `t2/<N>-<name>` | `specs/<N>-<name>/freeze.json` が正しいときだけ許可 |
| 形に合わない（`main` を含む） | 「Tier 未分類」として拒否 |

- 既存の「ソース編集は linked worktree からのみ」と `SDD_ALLOW_MAIN_WORKTREE=1`（メンテナンス用の抜け道）はそのまま残す。
- CI は PR のブランチ名を読み、ブランチ名の Tier と PR のラベル `sdd:tier-N` が食い違ったら失敗にする。

### 3.4 ボード: GitHub Projects（アカウントに 1 枚）

- 1 枚のカードが 1 つの Issue。カードは **Issue 番号で直接**見つける（Feature 欄のような追加の鍵は持たない）。
- 列（フェーズ）: 未着手 → brainstorm → spec → plan → tasks → implement → verify → done。

### 3.5 更新の流れ

- **push は PR を作る前だけ。** フェーズの区切りでは push しない。
- **ふだん**: エージェントがフェーズの区切りで止まるときに `sdd-board.sh sync` を実行する。手元のブランチとファイルからフェーズを割り出し、`gh project item-edit` でカードを更新する。ルールの「かんばんを表示して止まる」をこれに置き換える。
- **GitHub Actions（各リポジトリ、Projects 用トークンを secret に置く）**:
  - Issue ができたらボードに入れて「未着手」に置く（Projects の組み込みの自動追加は Free プランだと 1 リポジトリしか対象にできないため、Actions で行う）。
  - PR を作ったとき・更新したとき・マージしたときに、フェーズを割り出し直して上書きする。実行し忘れのずれはここで直る。マージで done。
- 人が画面でカードを動かしてもよい。次に sync か Actions が動いたときに、ファイルの状態に合わせて戻る。

### 3.6 切り替え: 一度に切り替える（移行期間なし）

- guard / validator / CI に `state.json` / `tasks.json` へのフォールバックは持たせない。
- consumer は submodule を上げた瞬間に新しいルールへ切り替わる（hook は submodule から直接動くため）。submodule をいつ上げるかは consumer が選べる。
- 移行手順書に「作業中のブランチを終わらせるか、`t<Tier>/<番号>-<名前>` に名前を変えてから submodule を上げる」と書く。
- このリポジトリ自身も同じく一度に切り替える（順序は plan で決める）。

### 3.7 形に合わないブランチの PR とラベル

- PR のブランチ名が `t<Tier>/<番号>-<名前>` の形に合わなければ CI は失敗。
- 例外: `dependabot/` と `renovate/` で始まるブランチは Tier 0 として通す。例外の接頭辞の一覧は `.sdd/board.json` で変えられる（既定値はこの 2 つ）。
- ラベルはブランチ名を正とする。Actions がブランチ名から `sdd:tier-N` を自動で付ける。ブランチ名と食い違う `sdd:tier-N` ラベルが付いていれば CI は失敗。ラベルを手で付ける必要はない。

### 3.8 すでにある Issue の取り込み

- `sdd-board.sh init` の中で、対象リポジトリの**開いている Issue をすべて**「未着手」としてボードに入れる。
- 同じ処理を、あとから何度でも実行できるサブコマンドとしても用意する（すでにボードにある Issue は変えない。冪等）。
- 閉じた Issue は入れない。

### 3.9 マージされずに終わった作業

- Issue が「完了（completed）」で閉じたら done。
- Issue が「対応しない（not planned）」や「重複（duplicate）」で閉じたら、カードを**アーカイブ**する（ボードから見えなくなるが消えない）。
- PR がマージされずに閉じたら、カードは変えない（Issue が開いている限り作業は続いているとみなす）。
- 列は増やさない。
- そのため Actions は `issues: closed` も受ける。

## 4. フェーズの割り出し規則

入力は「ブランチ名」と「そのブランチ上の `specs/<feature>/` のファイル」と（Actions のみ）「PR の状態」。上から順に最初に当てはまったものを採る。

| 条件 | フェーズ |
|---|---|
| PR がマージ済み（Actions が判定） | done |
| Tier 2 で、`freeze.json` が正しく、`tasks.md` のチェック欄が全部埋まっている | verify |
| Tier 1/2 で、`freeze.json` が正しい | implement |
| Tier 0 のブランチ | implement |
| `tasks.md` がある | tasks |
| `plan.md` がある | plan |
| `spec.md` がある | spec |
| `t1/` か `t2/` のブランチがあり、`specs/<feature>/` がない | brainstorm |
| ブランチがない（Actions が Issue 作成時に判定） | 未着手 |

- Tier 1 は plan / tasks を持たないので、spec → implement と進む。Tier 1 の verify は割り出さない（implement のまま PR → done）。（設計者判断: Tier 1 に verify の判定材料になるファイルがないため）
- `freeze.json` があるのにハッシュが一致しない場合: フェーズは割り出さずエラー。sync は警告してカードを変えない。guard は編集を拒否。CI は失敗。

## 5. 変わるもの

### なくすもの

- `.sdd/state.json`、`.sdd/tasks.json`（このリポジトリ自身のものと、consumer 向けの説明・テンプレート）
- `orchestration/schema/tasks.schema.json`、`orchestration/schema/state.schema.json`、`templates/sdd-state.example.json`、`templates/sdd-state.schema.json`
- `orchestration/tools/kanban.sh`、`orchestration/tools/kanban-html.sh`、`integration/ci/kanban-pages.yml`
- `integration/ci/sdd-check.yml` の orchestration ジョブ（`blocked` の検査、`implement` の `handoff.md` の検査）。`handoff.md` の検査は「`freeze.json` があれば `handoff.md` も必要」として sdd ジョブ側に移す。（設計者判断）
- ルール・ドキュメントの「tasks.json を更新」「かんばんを表示」「PR 前に state.json を done に戻す」の手順

### 作り直すもの

- `integration/hooks/sdd-guard.sh`、`integration/hooks/codex-sdd-guard.sh`: 3.3 の表どおり。
- `integration/hooks/skill-reminder.sh`、`integration/hooks/codex-skill-reminder.sh`: Tier とフェーズを 4 の規則で割り出す。
- `integration/ci/sdd-validate.py`:
  - 対象の feature をブランチ名から決める（CI では `GITHUB_HEAD_REF`、手元では今のブランチ、`--feature` で上書き可）。
  - 消す検査: state.json のスキーマ（チェック 1）、tasks.json（チェック 2）、state と tasks の一致（チェック 4）。
  - 足す検査:
    - ブランチ名の形
    - Tier 1/2 の `freeze.json` が正しい（凍結後に spec / plan / tasks / traceability が変わっていない）
    - Tier 2 の `issue-snapshot.json` の Issue 番号とディレクトリ名の番号が一致する
    - CI では PR ラベルとブランチ名の Tier が一致する
  - main への push（PR ではない実行）では feature の検査を飛ばす。PR では、形に合わないブランチは失敗（例外の接頭辞は 3.7）。
- `integration/agents/sdd-reviewer.md`、`integration/prompts/sdd-reviewer-prompt.md`: 確認項目 3・4（state.json の feature、tasks.json）を「ブランチ名・ディレクトリ名・Issue 番号の一致」と「`freeze.json` が正しい」に置き換える。
- `rules/workflow.md`、`rules/core.md`、`rules/issue-intake.md`、`orchestration/rules/orchestration.md`、`orchestration/integration/AGENTS-patch.md.example`、`orchestration/templates/handoff.md.example`、`README.md`、`docs/01-workflow.md`、`docs/04-issue-tracker.md`、`integration/issue-tracker/README.md`
  - 「状態の正本は tasks.json」を「状態はブランチとファイルから割り出す。ボードは GitHub Projects」に改める。
  - 凍結の手順を `freeze.json` の作成に改める。
  - 止まるときの手順を「commit → `sdd-board.sh sync` → 止まる」に改める。
  - 行き詰まったとき（今の `status: blocked`）は、Issue にコメントで理由を書いて止まる。（設計者判断: ボードの列はフェーズだけにするので、blocked は列にしない）
- `templates/tasks.md`: 「完了の定義」の「CI green」「sdd-reviewer 合格」をチェック欄にしない。state のリセットがなくなると、CI がこの未チェック欄で落ちるため。（設計者判断: 普通の箇条書きにする）
- `integration/update.sh`: 新しいワークフローを配る。`kanban-pages.yml` を配らない。
- テスト: `tests/test_sdd_validate.py`、`tests/test_negative_fixtures.py`、`tests/test_sdd_guard.py`、`tests/test_codex_sdd_guard.py`、`tests/test_rules_freeze_verify.py`、`tests/fixtures/`（`fixture-missing-tasks-entry`、`fixture-phase-mismatch`、`fixture-wrong-state` などの state/tasks 前提のもの）。

### 新しく作るもの

- **割り出しの本体（1 か所）**: ブランチ名の解析、`freeze.json` の作成と確認、フェーズの割り出しを 1 つのモジュールにまとめる。guard、skill-reminder、validator、sdd-board.sh はすべてこれを呼ぶ。同じ規則を何か所にも書かない。（設計者判断: 言語は既存の validator に合わせて Python、hook からは `python3` で呼ぶ。hook は今も jq がなければ python3 にフォールバックしている）
- **凍結のコマンド**: `freeze.json` を作る。人の承認を受けたエージェントか人が実行する。
- **`orchestration/tools/sdd-board.sh`**:
  - `sync`: 今のブランチの Issue のカードを、割り出したフェーズに更新する。カードがなければボードに入れる。ネットワーク・認証・設定がなければ警告して終了コード 0。
  - `init`: ボード（Project）と「Phase」フィールド（単一選択、4 の列）を作り、開いている Issue を取り込む（3.8）。ビュー（リポジトリごとのタブなど）は API で作れないため手順書に書く。（設計者判断）
  - 取り込みだけを行うサブコマンド（3.8）。
- **ボードの設定ファイル**: `.sdd/board.json`（`owner`、Project の番号）。状態ではなく設定なのでコミットしてよい。sync と Actions の両方が読む。（設計者判断）
- **`integration/ci/sdd-board.yml`**（consumer にコピーするワークフロー）:
  - `issues: opened` → ボードに入れて「未着手」。
  - `issues: closed` → 3.9 のとおり done かアーカイブ。
  - `pull_request: opened / synchronize / reopened / closed` → フェーズを割り出して上書き。マージなら done。マージせずに閉じたら何もしない。PR にはブランチ名から `sdd:tier-N` ラベルを付ける（3.7）。
  - トークンは secret `SDD_PROJECT_TOKEN`（classic PAT、`project` スコープ）。（設計者判断: 名前）secret がなければ警告して成功で終わる。
- **移行手順**: `docs/migration.md` に章を足す。consumer は `.sdd/state.json` と `.sdd/tasks.json` を消し、`.sdd/board.json` を置き、secret を入れ、ワークフローを入れる。作業中の feature がある場合の扱いも書く。

## 6. 制約

- hook はオフライン・認証なしで、編集のたびに即座に判定できること。
- 既存の SDD の意図は保つ: 凍結前の実装を防ぐ、凍結後の spec を変えない、すべての AC にテスト、独立した sdd-reviewer。
- consumer はこのリポジトリを submodule（`vendor/ai-sdd-guide`）として使い、`integration/update.sh` で配布物を受け取る。consumer 側で手で直す部分を増やさない。
- GitHub の制約:
  - 標準の `GITHUB_TOKEN` では Projects v2 を操作できない。
  - 組み込みの自動追加はプランごとに数の上限があり、1 つの設定で 1 リポジトリしか対象にできない（Free は 1 つ）。
  - ビューは API で作れない。

## 7. 実装する人に任せること

- 割り出しモジュールのファイル名・関数の分け方。
- `freeze.json` の正確な形（ハッシュの種類、ファイル一覧の持ち方、凍結日時など）。
- `sdd-board.sh` の内部（`gh project` のサブコマンドか GraphQL か）。
- テスト用 fixture の作り直し方。
- このリポジトリ自身の開発中の扱い: この変更は今の仕組み（state.json あり）のもとで進め、最後に自分自身を新しい仕組みへ移行する。途中で guard が自分の変更を止めないよう、順序を plan で決める。

## 8. 関連 Issue への影響

- #22（並列で state.json が衝突）: state.json がなくなり、状態はブランチごとになるので解消。
- #26（更新漏れ）: 状態を手で書かなくなるので解消。ボードの更新漏れは PR とマージのときに Actions が直す。
- #28（PR 前のリセット）: リセット自体がなくなる。
- #64（README の state.json の例がスキーマ違反）: state.json がなくなるので不要になる。
- #66（Tier 2 の validator がフェーズを見ずに凍結前にテストと evidence を求める）: フェーズを割り出せるようになるので、フェーズに応じた検査に直せる。この変更の範囲に含めるかは plan で決める。
