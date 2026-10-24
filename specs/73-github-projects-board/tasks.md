# Tasks: 73-github-projects-board

> 他 agent が設計コンテキスト無しで実装できるよう、各タスクは具体的に書く。共通の制約は plan.md の Global Constraints を参照。
> テストは `python -m pytest tests/ -q` で全体を流す（このリポジトリの CI と同じ）。

## 実装タスク（順序付き）
- [ ] T1: 割り出しの本体 `integration/ci/sdd_state.py` と凍結コマンド。対応AC: SAC-2, SAC-3, SAC-6
- [ ] T2: guard（Claude / Codex）をブランチ名と `freeze.json` で判定する。対応AC: SAC-4, SAC-5
- [ ] T3: skill-reminder（Claude / Codex）を割り出したフェーズで動かす。対応AC: SAC-7
- [ ] T4: validator をブランチ基準にし、fixture を作り直す。対応AC: SAC-5, SAC-8, SAC-9, SAC-10
- [ ] T5: `integration/ci/sdd-check.yml` を新しい validator に合わせる。対応AC: SAC-1, SAC-9, SAC-10
- [ ] T6: ボード操作 `integration/ci/sdd_board.py` と `orchestration/tools/sdd-board.sh`。対応AC: SAC-11, SAC-12
- [ ] T7: Actions のワークフロー `integration/ci/sdd-board.yml`。対応AC: SAC-10, SAC-13
- [ ] T8: 旧ファイルの削除と、ルール・ドキュメント・テンプレート・reviewer の書き換え。対応AC: SAC-1, SAC-14, SAC-15
- [ ] T9: `integration/update.sh` と `docs/migration.md`。対応AC: SAC-16, SAC-17
- [ ] T10: このリポジトリ自身の移行。対応AC: SAC-18

## テスト（受入条件との対応・必須）
- [ ] SAC-1 → `tests/test_no_legacy_state.py`
- [ ] SAC-2 → `tests/test_sdd_state.py::test_parse_branch_*`
- [ ] SAC-3 → `tests/test_sdd_state.py::test_freeze_*`, `test_tasks_md_checkbox_variants_do_not_change_hash`
- [ ] SAC-4 → `tests/test_sdd_guard.py`, `tests/test_codex_sdd_guard.py`
- [ ] SAC-5 → `tests/test_sdd_guard.py::test_edit_after_frozen_spec_changed_is_denied`, `tests/test_negative_fixtures.py`（fixture-tampered-freeze）
- [ ] SAC-6 → `tests/test_sdd_state.py::test_phase_*`
- [ ] SAC-7 → `tests/test_skill_reminder.py`
- [ ] SAC-8 → `tests/test_sdd_validate.py`, `tests/test_negative_fixtures.py`
- [ ] SAC-9 → `tests/test_sdd_validate.py::test_pr_*_branch_*`
- [ ] SAC-10 → `tests/test_sdd_validate.py::test_pr_label_mismatch_fails`, `tests/test_sdd_board_workflow.py::test_pr_job_adds_tier_label`
- [ ] SAC-11 → `tests/test_sdd_board.py::test_sync_*`
- [ ] SAC-12 → `tests/test_sdd_board.py::test_init_*`, `test_import_*`
- [ ] SAC-13 → `tests/test_sdd_board.py::test_event_*`, `tests/test_sdd_board_workflow.py`
- [ ] SAC-14 → `tests/test_rules_freeze_verify.py::test_sdd_reviewer_checks_branch_and_freeze`
- [ ] SAC-15 → `tests/test_rules_freeze_verify.py::test_tasks_template_completion_has_no_checkboxes`
- [ ] SAC-16 → `tests/test_update_sh.py`
- [ ] SAC-17 → `tests/test_migration_guide.py::test_migration_guide_projects_board_section`
- [ ] SAC-18 → `tests/test_self_migration.py`

## 完了の定義
- 全 AC 対応テストが green（`python -m pytest tests/ -q`）
- CI green
- sdd-reviewer 合格

---

### T1: 割り出しの本体と凍結コマンド

**Files:**
- Create: `integration/ci/sdd_state.py`
- Create: `orchestration/tools/sdd-freeze.sh`（`exec python3 "$(dirname "$0")/../../integration/ci/sdd_state.py" freeze "$@"`）
- Test: `tests/test_sdd_state.py`

**Interfaces（Produces）:**
```python
PHASES = ("backlog", "brainstorm", "spec", "plan", "tasks", "implement", "verify", "done")

@dataclass(frozen=True)
class BranchInfo:
    tier: int        # 0, 1, 2
    issue: int
    name: str
    feature: str     # f"{issue}-{name}"

class FreezeError(Exception): ...          # freeze.json が正しくない

def parse_branch(branch: str | None) -> BranchInfo | None
def current_branch(root: Path) -> str | None            # git branch --show-current。detached・git でない場合は None
def freeze_targets(tier: int) -> list[str]              # 2: ["spec.md","plan.md","tasks.md","traceability.json"], 1: ["spec.md"]
def normalize_tasks_md(text: str) -> str                # CRLF→LF、行頭チェック欄 [x]/[X] → [ ]（"-" と "*"、字下げを許す）
def file_digest(path: Path) -> str                      # "sha256:<hex>"。tasks.md は正規化後の内容で計算
def create_freeze(spec_dir: Path, tier: int, now: datetime) -> dict   # freeze.json を書いて内容を返す。対象ファイルがなければ FileNotFoundError
def freeze_status(spec_dir: Path, tier: int) -> tuple[str, list[str]] # ("missing"|"valid"|"invalid", 理由の一覧)
def derive_phase(root: Path, info: BranchInfo) -> str   # spec.md の「フェーズ」表（done/backlog 以外）。freeze が invalid なら FreezeError
```
`freeze.json` の形: `{"version": 1, "tier": <int>, "frozen_at": "<ISO8601 UTC>", "files": {"spec.md": "sha256:...", ...}}`。

CLI（`python3 integration/ci/sdd_state.py <cmd> [--root R] [--branch B]`。`--root` 既定は `git rev-parse --show-toplevel`、`--branch` 既定は `current_branch(root)`）:
- `branch` → 標準出力に JSON `{"tier":..,"issue":..,"name":..,"feature":..}`。形に合わなければ終了コード 3、出力なし。
- `phase` → 標準出力にフェーズ名。形に合わなければ終了コード 3。freeze が invalid なら理由を標準エラーに出して終了コード 4。
- `freeze` → `specs/<feature>/freeze.json` を作り、パスを出力。Tier 0 や形に合わないブランチでは終了コード 3。
- `guard` → 許可なら終了コード 0。拒否なら理由を標準エラーに出して終了コード 1（未分類・detached・freeze がない／正しくない）。

- [ ] **Step 1: テストを書く**（`tests/test_sdd_state.py`。一時ディレクトリと、必要なら一時 git リポジトリを使う）
  - `test_parse_branch_valid`: `parse_branch("t2/73-github-projects-board") == BranchInfo(2, 73, "github-projects-board", "73-github-projects-board")`、`t0/3-d1-database-id` も同様
  - `test_parse_branch_invalid`: `main`, `feat/x`, `t3/1-x`, `t2/x`, `t2/0-x`, `t2/1-X`, `t2/1-`, `""`, `None` がすべて `None`
  - `test_current_branch_detached_is_none`: `git checkout --detach` 後に `None`
  - `test_freeze_targets_by_tier`: Tier 2 と Tier 1 の一覧が Global Constraints どおり
  - `test_freeze_creates_file_with_digests`: Tier 2 の 4 ファイルを置いて `create_freeze` → `freeze.json` の `files` のキーが 4 つ、値が `sha256:` で始まる、`freeze_status(...)[0] == "valid"`
  - `test_freeze_missing_target_raises`: `plan.md` がないと `create_freeze` が `FileNotFoundError`
  - `test_tasks_md_checkbox_variants_do_not_change_hash`: `- [ ] T1`、`* [ ] a`、`  - [ ] sub` を含む tasks.md で凍結 → `[x]`・`[X]` に変え、行末を CRLF にしても `valid`
  - `test_freeze_detects_non_checkbox_edit`: tasks.md の本文 1 文字・spec.md・plan.md・traceability.json のどれかを変えると `invalid`、理由にファイル名が入る
  - `test_freeze_missing_file_is_invalid`: 凍結後に `traceability.json` を消すと `invalid`
  - `test_freeze_tier_mismatch_is_invalid`: Tier 1 で作った freeze.json を `freeze_status(dir, 2)` で見ると `invalid`
  - `test_phase_tier0_is_implement`
  - `test_phase_tier2_sequence`: ディレクトリなし→`brainstorm`、spec.md→`spec`、+plan.md→`plan`、+tasks.md→`tasks`、+traceability.json と freeze→`implement`、tasks.md を全部 `[x]`→`verify`
  - `test_phase_tier1_spec_then_implement`: spec.md→`spec`、freeze→`implement`、Tier 1 は `verify` にならない
  - `test_phase_invalid_freeze_raises`: 凍結後に spec.md を変えると `FreezeError`
  - `test_cli_guard_exit_codes`: 一時 git リポジトリで、`t0/1-x`→0、`t2/1-x` freeze なし→1、freeze あり→0、`main`→1
- [ ] **Step 2: 失敗を確認**: `python -m pytest tests/test_sdd_state.py -q` → ImportError / FAIL
- [ ] **Step 3: 実装**: 上の Interfaces。git の呼び出しは `subprocess.run([...], capture_output=True, text=True)` で、失敗したら `None`。
- [ ] **Step 4: 通ることを確認**: `python -m pytest tests/test_sdd_state.py -q` → PASS、全体 `python -m pytest tests/ -q` も PASS
- [ ] **Step 5: コミット**: `feat(73-github-projects-board): ブランチ名と freeze.json から SDD の状態を割り出す`

### T2: guard をブランチ名と freeze.json で判定する

**Files:**
- Modify: `integration/hooks/sdd-guard.sh`（88〜116 行の state.json による判定）
- Modify: `integration/hooks/codex-sdd-guard.sh`（178〜200 行の state.json による判定）
- Test: `tests/test_sdd_guard.py`、`tests/test_codex_sdd_guard.py`

**Interfaces:** Consumes T1 の CLI `sdd_state.py guard --root <target_root>`。スクリプトの場所はフックの位置から `"$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/../ci/sdd_state.py"`。

- [ ] **Step 1: テストを直す・足す**: `_make_repo` は state.json を作らず、worktree を `t1/1-feature` などのブランチで作る。`_set_state` を廃止し、代わりに `specs/1-feature/` と freeze.json を用意するヘルパーを使う（freeze.json は T1 の `create_freeze` で作る）。
  - `test_tier0_branch_in_linked_worktree_is_allowed`（`t0/1-feature`）
  - `test_tier2_branch_without_freeze_is_denied`（標準エラーに `freeze.json` を含む）
  - `test_tier2_branch_with_valid_freeze_is_allowed`
  - `test_edit_after_frozen_spec_changed_is_denied`（凍結後に spec.md を変更）
  - `test_unclassified_branch_in_linked_worktree_is_denied`（`feature` という名前のブランチ。標準エラーに `t<Tier>/<Issue番号>-<名前>` を含む）
  - `test_detached_head_is_denied`
  - `test_allow_main_worktree_env_bypasses_guard`: `SDD_ALLOW_MAIN_WORKTREE=1` なら main の primary checkout でも許可（plan の判断）
  - 既存の worktree・除外パス・`no_file_path` のテストは期待値を変えずに残す
  - Codex 側も同じ観点（`test_tier0_source_edit_in_linked_worktree_is_allowed`、`test_unclassified_tier_in_linked_worktree_is_denied` を新しい前提に書き換え、`test_tier2_branch_with_valid_freeze_is_allowed`・`test_tier2_branch_without_freeze_is_denied` を足す）。複数 root のパッチでは root ごとに判定する既存の構造を保つ
- [ ] **Step 2: 失敗を確認**: `python -m pytest tests/test_sdd_guard.py tests/test_codex_sdd_guard.py -q` → FAIL
- [ ] **Step 3: 実装**: state.json と `json_get` の Tier/phase 判定を、`python3 sdd_state.py guard --root "$target_root"` の終了コードに置き換える。拒否の文言には、ブランチ名の形（`t<Tier>/<Issue番号>-<名前>`）と凍結コマンド（`orchestration/tools/sdd-freeze.sh`）を書く。`python3` がなければ拒否し、その旨を出す。
- [ ] **Step 4: 通ることを確認**: 同じコマンド → PASS、全体 PASS
- [ ] **Step 5: コミット**: `feat(73-github-projects-board): guard をブランチ名と freeze.json で判定する`

### T3: skill-reminder を割り出したフェーズで動かす

**Files:**
- Modify: `integration/hooks/skill-reminder.sh`、`integration/hooks/codex-skill-reminder.sh`
- Create: `tests/test_skill_reminder.py`

**Interfaces:** Consumes T1 の CLI `sdd_state.py branch` と `sdd_state.py phase`。

- [ ] **Step 1: テストを書く**（一時 git リポジトリでブランチとファイルを用意し、フックを `bash` で実行して標準エラー／出力を見る）
  - `test_reminder_brainstorm_for_tier2_without_spec_dir`: `brainstorming` を含む
  - `test_reminder_plan_phase`: plan.md まであると `writing-plans` を含む
  - `test_reminder_implement_phase`: freeze 後に `executing-plans`（Claude）／`frozen specs/<feature>/tasks.md`（Codex）を含む
  - `test_reminder_tier1_design_phase_is_silent`: Tier 1 の spec 段階では何も出ない
  - `test_reminder_tier0_is_silent`、`test_reminder_unclassified_is_silent`
- [ ] **Step 2: 失敗を確認**: `python -m pytest tests/test_skill_reminder.py -q` → FAIL
- [ ] **Step 3: 実装**: state.json の読み取りを CLI の呼び出しに置き換える。CLI が 0 以外で終わったら何も出さず終了コード 0。各フェーズの文言は今のものを使う。
- [ ] **Step 4: 通ることを確認** → PASS、全体 PASS
- [ ] **Step 5: コミット**: `feat(73-github-projects-board): skill-reminder を割り出したフェーズで動かす`

### T4: validator をブランチ基準にし、fixture を作り直す

**Files:**
- Modify: `integration/ci/sdd-validate.py`
- Modify: `tests/test_sdd_validate.py`、`tests/test_negative_fixtures.py`
- Modify/Delete/Create: `tests/fixtures/`

**Interfaces:**
- Consumes: T1 の `parse_branch`, `current_branch`, `freeze_status`, `freeze_targets`, `create_freeze`（テストのみ）
- Produces: CLI `sdd-validate.sh [--root R] [--branch B] [--feature F] [--pr] [--pr-labels "a,b"]`。終了コード: 0 PASS、1 検査エラー、2 内部エラー（既存どおり）。

- [ ] **Step 1: fixture を作り直す**
  - すべての fixture から `.sdd/state.json`・`.sdd/tasks.json` を消し、`specs/my-feature/` を `specs/99-my-feature/` に改名する（snapshot の Issue は 99）。fixture 内の JSON の `feature` 値（traceability・snapshot・evidence）も `99-my-feature` に直す。freeze を作る fixture には `handoff.md` を置く（`fixture-missing-handoff` を除く）。
  - 削除: `fixture-wrong-state(-valid)`、`fixture-missing-tasks-entry(-valid)`、`fixture-phase-mismatch(-valid)`、`invalid-state-mismatch`、`valid-done`。
  - 追加（negative / valid の組）: `fixture-tampered-freeze`（凍結後に spec.md を変更）、`fixture-snapshot-issue-mismatch`（snapshot の Issue が 98）、`fixture-missing-handoff`（freeze.json あり、handoff.md なし）、`fixture-missing-freeze`（`--pr` で freeze.json なし）。
  - freeze.json は fixture に置かず、テストの準備で一時ディレクトリへコピーしたあと `create_freeze` で作る。改ざん系の fixture は、作ったあとに変更を加える。fixture ごとの準備の違いは各 fixture の `README.md` に書く。
- [ ] **Step 2: テストを書く・直す**
  - `test_negative_fixtures.py`: validator を `--branch t2/99-my-feature` で呼ぶ。`NEGATIVE_CASES` から state/tasks 系 3 件を消し、`("fixture-tampered-freeze", "freeze.json")`、`("fixture-snapshot-issue-mismatch", "does not match directory")`、`("fixture-missing-handoff", "handoff.md")`、`("fixture-missing-freeze", "freeze.json not found")`（`--pr` 付き）を足す。`fixture-incomplete-tasks` は `--pr` 付きで `unchecked item`。
  - `test_sdd_validate.py`: state.json を前提にしたテストを消すか書き換え、次を足す
    - `test_branch_from_github_head_ref`: `GITHUB_HEAD_REF=t2/99-my-feature` で `--branch` なしでも対象が決まる
    - `test_non_pr_unmatched_branch_skips_feature_checks`: `--branch main` で PASS、標準出力に `skipped`
    - `test_pr_unmatched_branch_fails`: `--pr --branch feat/x` で 1、標準エラーに `t<Tier>/<Issue番号>-<名前>`
    - `test_pr_bot_branch_is_tier0`: `--pr --branch dependabot/npm/foo` で PASS
    - `test_pr_bot_prefix_from_board_json`: `.sdd/board.json` の `tier0_branch_prefixes: ["bot/"]` で `bot/x` が PASS、`dependabot/x` は失敗
    - `test_pr_label_mismatch_fails`: `--pr --branch t2/99-my-feature --pr-labels "sdd:tier-0,bug"` で 1、`sdd:tier-2` が付いていれば PASS、`sdd:tier-*` がなければ PASS
    - `test_feature_override_keeps_branch_tier`: `--branch t2/99-x --feature 99-my-feature` で `specs/99-my-feature/` を検査
    - `test_tier0_pr_skips_spec_checks`: `--pr --branch t0/5-fix` で specs がなくても PASS
- [ ] **Step 3: 失敗を確認**: `python -m pytest tests/test_sdd_validate.py tests/test_negative_fixtures.py -q` → FAIL
- [ ] **Step 4: 実装**
  - `check_schema_state`・`check_schema_tasks`・`check_state_tasks_consistency` を消す。`main()` の state.json 読み取りを、ブランチの決定（`--branch` → `GITHUB_HEAD_REF` → `current_branch`）と `parse_branch` に置き換える。
  - 形に合わないブランチ: `--pr` なら Tier 0 の例外接頭辞（`.sdd/board.json`、既定 `["dependabot/", "renovate/"]`）に当たれば PASS、当たらなければエラー。`--pr` なしなら `sdd-validate: no SDD branch — feature checks skipped. PASS` と出して 0。
  - Tier 0: feature の検査を飛ばす（ラベル検査は行う）。
  - Tier 1/2: `freeze_status` が `invalid` ならエラー（理由を含める）。`missing` は `--pr` のときだけエラー `freeze.json not found`。`freeze.json` があるのに `handoff.md` がなければエラー。
  - Tier 2: 既存のチェック 3・6・7・8・9 を残す。チェック 8 に「snapshot の `issue` がブランチの Issue 番号と一致しなければ `issue-snapshot issue <n> does not match directory <feature>`」を足す。チェック 5 は `--pr` のときだけ未チェックをエラーにする。
  - ラベル検査（`--pr-labels` があるとき）: `sdd:tier-N` の N がブランチの Tier と違うものがあればエラー。
- [ ] **Step 5: 通ることを確認** → PASS、全体 PASS
- [ ] **Step 6: コミット**: `feat(73-github-projects-board): validator をブランチ基準にし fixture を作り直す`

### T5: sdd-check.yml を新しい validator に合わせる

**Files:**
- Modify: `integration/ci/sdd-check.yml`
- Modify: `tests/test_sdd_check_submodule.py`

- [ ] **Step 1: テストを直す・足す**（YAML を `yaml` なしで読むため、既存テストと同じく文字列で検査する）
  - `test_no_state_reset_gate`: `State reset gate` と `state.json` を含まない
  - `test_no_orchestration_job`: `orchestration:` ジョブと `tasks.json` を含まない
  - `test_validate_step_passes_pr_context`: `--pr`、`GITHUB_HEAD_REF`（または `github.head_ref`）、`--pr-labels` を含む
  - `test_sdd_validate_step_runs_in_consumer_layout` を state.json なしの前提に書き換える（一時ディレクトリに consumer の配置を作り、`--branch t0/1-x --pr` で PASS）
- [ ] **Step 2: 失敗を確認** → FAIL
- [ ] **Step 3: 実装**: 「State reset gate」と「Spec gate」と orchestration ジョブを消す。「Run sdd-validate」を `bash vendor/ai-sdd-guide/integration/ci/sdd-validate.sh --root . --pr --branch "${{ github.head_ref }}" --pr-labels "${{ join(github.event.pull_request.labels.*.name, ',') }}"` にする（state.json の有無による skip を消す）。`SDD_GUIDE_TOKEN`、`persist-credentials: false`、submodule の取得は変えない。
- [ ] **Step 4: 通ることを確認** → PASS、全体 PASS
- [ ] **Step 5: コミット**: `feat(73-github-projects-board): sdd-check.yml を新しい validator に合わせる`

### T6: ボード操作 sdd_board.py と sdd-board.sh

**Files:**
- Create: `integration/ci/sdd_board.py`
- Create: `orchestration/tools/sdd-board.sh`（`exec python3 "$(dirname "$0")/../../integration/ci/sdd_board.py" "$@"`）
- Test: `tests/test_sdd_board.py`、`tests/fake_gh.py`（偽の `gh`）

**Interfaces:**
- Consumes: T1 の `parse_branch`, `current_branch`, `derive_phase`, `FreezeError`
- Produces（CLI。すべて `--root R` を受ける。設定は `<root>/.sdd/board.json`）:
  - `sync` — 今のブランチの Issue のカードを `derive_phase` の結果にする。カードがなければ追加。
  - `init [--title T]` — `board.json` がなければ `gh project create --owner <owner> --title T --format json` で作って `board.json` を書く（`owner` は `--owner` 引数、なければ `gh repo view --json owner`）。`Phase` フィールドがなければ `gh project field-create ... --name Phase --data-type SINGLE_SELECT --single-select-options backlog,brainstorm,spec,plan,tasks,implement,verify,done`。最後に `import` と同じ処理。
  - `import` — `gh issue list --repo <repo> --state open --json number,url --limit 1000` の Issue のうちボードにないものを追加し `backlog` にする。ボードにあるものは変えない。
  - `set --issue N --phase P` — カードを P にする（なければ追加）。
  - `close --issue N --reason completed|not_planned|duplicate` — completed なら `done`、それ以外は `gh project item-archive`。カードがなければ何もしない。
  - `pr --branch B --merged true|false --closed true|false` — マージ済みなら `done`、マージせずに閉じたら何もしない、それ以外は `derive_phase`。形に合わないブランチは何もしない。
  - 共通: `gh` の失敗・`board.json` がない・ブランチが形に合わない・`FreezeError` のときは `sdd-board: warning: <理由>` を標準エラーに出して終了コード 0。`init` だけは失敗を終了コード 1 で返す（人が実行するため）。
- 使う `gh` サブコマンド: `project view <n> --owner <o> --format json`（Project の id）、`project field-list <n> --owner <o> --format json`、`project item-list <n> --owner <o> --format json --limit <大きい値>`、`project item-add <n> --owner <o> --url <issue url> --format json`、`project item-edit --id <item> --project-id <pid> --field-id <fid> --single-select-option-id <oid>`、`project item-archive <n> --owner <o> --id <item>`、`repo view --json nameWithOwner,owner`、`issue view <n> --repo <r> --json url`。

- [ ] **Step 1: 偽の gh とテストを書く**: `fake_gh.py` は環境変数 `FAKE_GH_LOG`（呼び出しを JSON 行で追記）と `FAKE_GH_RESPONSES`（サブコマンドの前方一致 → 標準出力と終了コードの対応表の JSON ファイル）を読む。テストは一時ディレクトリに実行可能な `gh` を置いて `PATH` の先頭に足す。
  - `test_sync_updates_phase_from_branch`: `t2/7-x` で freeze 済み → `item-edit` に `implement` の option id
  - `test_sync_adds_missing_card`: カードがなければ `item-add` のあと `item-edit`
  - `test_sync_warns_without_board_json`、`test_sync_warns_when_gh_fails`、`test_sync_warns_on_unmatched_branch`、`test_sync_warns_on_invalid_freeze`: いずれも終了コード 0、標準エラーに `warning`、`item-edit` が呼ばれない
  - `test_item_lookup_passes_large_limit`: `item-list` の引数に `--limit` があり値が 1000 以上
  - `test_item_lookup_matches_repository_and_number`: 別リポジトリの同じ番号のカードを更新しない
  - `test_init_creates_project_field_and_board_json`: `project create`・`field-create`（8 つの選択肢がこの順）を呼び、`board.json` に `owner` と `project` を書く
  - `test_init_with_existing_board_json_does_not_create`
  - `test_import_adds_only_missing_open_issues_as_backlog`、`test_import_twice_is_idempotent`（2 回目は `item-add`・`item-edit` を呼ばない）
  - `test_event_close_completed_sets_done`、`test_event_close_not_planned_archives`、`test_event_close_duplicate_archives`
  - `test_event_pr_merged_sets_done`、`test_event_pr_closed_unmerged_is_noop`、`test_event_pr_open_derives_phase`、`test_event_pr_bot_branch_is_noop`
  - `test_set_phase`
- [ ] **Step 2: 失敗を確認**: `python -m pytest tests/test_sdd_board.py -q` → FAIL
- [ ] **Step 3: 実装**: 上の Interfaces。`gh` の呼び出しは 1 つの関数 `run_gh(args: list[str]) -> str` に集め、失敗は `GhError` にする。カードの検索は `content.number` と `content.repository`（`owner/name`）の両方で一致させる。
- [ ] **Step 4: 通ることを確認** → PASS、全体 PASS
- [ ] **Step 5: コミット**: `feat(73-github-projects-board): GitHub Projects のボード操作を追加する`

### T7: Actions のワークフロー sdd-board.yml

**Files:**
- Create: `integration/ci/sdd-board.yml`
- Test: `tests/test_sdd_board_workflow.py`

**Interfaces:** Consumes T6 の CLI（consumer の配置 `vendor/ai-sdd-guide/orchestration/tools/sdd-board.sh`）。

- [ ] **Step 1: テストを書く**（文字列で検査）
  - `test_triggers`: `issues:` に `opened` と `closed`、`pull_request:` に `opened`・`synchronize`・`reopened`・`closed`
  - `test_uses_project_token_secret`: `secrets.SDD_PROJECT_TOKEN` を含む
  - `test_missing_secret_warns_and_succeeds`: secret が空のとき `::warning::` を出して `exit 0` する分岐がある
  - `test_pr_job_adds_tier_label`: `gh pr edit` と `--add-label` と `sdd:tier-` を含み、`GITHUB_TOKEN`（`github.token`）を使う。`permissions` に `pull-requests: write` と `issues: write`
  - `test_calls_board_subcommands`: `sdd-board.sh set --issue`（opened、`backlog`）、`sdd-board.sh close`（`github.event.issue.state_reason`）、`sdd-board.sh pr --branch`（`github.head_ref`、`github.event.pull_request.merged`）を含む
  - `test_checkout_pr_head_with_submodules`: PR のときは head を checkout し、`submodules: true` と `SDD_GUIDE_TOKEN` のフォールバックを持つ
- [ ] **Step 2: 失敗を確認** → FAIL
- [ ] **Step 3: 実装**: ジョブ 1 つ。最初のステップで `SDD_PROJECT_TOKEN` の有無を見て、なければ警告して以降をスキップ（ラベル付与は secret がなくても行う）。ラベルがリポジトリになければ `gh label create sdd:tier-N` で作る。`state_reason` は `completed`／`not_planned`／`duplicate` をそのまま `--reason` に渡す（GitHub の値は小文字。`NOT_PLANNED` などの大文字が来ても小文字にする）。
- [ ] **Step 4: 通ることを確認** → PASS、全体 PASS
- [ ] **Step 5: コミット**: `feat(73-github-projects-board): ボードを更新する Actions ワークフローを追加する`

### T8: 旧ファイルの削除と、ルール・ドキュメント・テンプレート・reviewer の書き換え

**Files:**
- Delete: `orchestration/schema/state.schema.json`、`orchestration/schema/tasks.schema.json`、`templates/sdd-state.example.json`、`templates/sdd-state.schema.json`、`orchestration/tools/kanban.sh`、`orchestration/tools/kanban-html.sh`、`integration/ci/kanban-pages.yml`
- Modify: `rules/core.md`、`rules/workflow.md`、`rules/issue-intake.md`、`rules/conventions.md`（該当があれば）、`orchestration/rules/orchestration.md`、`orchestration/integration/AGENTS-patch.md.example`、`orchestration/templates/handoff.md.example`、`integration/agents/sdd-reviewer.md`、`integration/prompts/sdd-reviewer-prompt.md`、`integration/issue-tracker/README.md`、`templates/tasks.md`、`README.md`、`docs/01-workflow.md`、`docs/03-faq.md`、`docs/04-issue-tracker.md`、`integration/hooks/README.md`、`rules/repo-agent-routing.md`、`orchestration/schema/traceability.schema.json`（`feature` の説明文）、`integration/AGENTS.md.example`・`integration/CLAUDE.md.example`（該当があれば）。T2〜T4 で変えたフック・validator のコメントにも旧ファイル名を残さない（`test_no_legacy_instructions` が `integration/` 全体を見るため）
- Create: `tests/test_no_legacy_state.py`
- Modify: `tests/test_rules_freeze_verify.py`

書き換えの中身:
- 状態はブランチ名 `t<Tier>/<Issue番号>-<名前>` と `specs/<Issue番号>-<名前>/` のファイルから割り出す。すべての作業に Issue を作る（Tier 0 も）。
- 凍結 = 人の承認のあと `orchestration/tools/sdd-freeze.sh` で `freeze.json` を作る。凍結のやり直しも人の承認のうえで作り直す。
- フェーズの区切りで止まるとき: commit → `orchestration/tools/sdd-board.sh sync` → 止まる。push は PR を作る前だけ。
- 行き詰まったら、Issue にコメントで理由を書いて止まる。
- ボードは GitHub Projects（アカウントで 1 枚）。GitLab・Azure DevOps は #71・#72。Bitbucket は Issues 廃止のため対象外とだけ書く（掃除は別件）。
- `templates/tasks.md` の「完了の定義」はチェック欄でない箇条書き。
- sdd-reviewer の確認項目 3・4 を「ブランチ名・`specs/` のディレクトリ名・`issue-snapshot.json` の Issue 番号が一致する」「`freeze.json` が正しい（`sdd_state.py phase` がエラーにならない）」に置き換える。

- [ ] **Step 1: テストを書く**
  - `tests/test_no_legacy_state.py::test_legacy_files_removed`: 上の Delete のファイルが存在しない
  - `tests/test_no_legacy_state.py::test_no_legacy_instructions`: `rules/`・`orchestration/`・`integration/`・`templates/`・`docs/`・`README.md` の中で（`docs/migration.md` を除く）、`state.json`・`tasks.json`・`kanban` を含む行がない
  - `tests/test_rules_freeze_verify.py`: state.json の文言を前提にしたアサーションを新しい文言に合わせる。足すテスト:
    - `test_workflow_freeze_uses_freeze_json`: `rules/workflow.md` に `sdd-freeze.sh` と `freeze.json`
    - `test_orchestration_stop_runs_board_sync`: `orchestration/rules/orchestration.md` に `sdd-board.sh sync`、`display kanban` がない
    - `test_sdd_reviewer_checks_branch_and_freeze`: reviewer の 2 ファイルに `freeze.json` とブランチ名の形を含み、`state.json`・`tasks.json` を含まない
    - `test_tasks_template_completion_has_no_checkboxes`: `templates/tasks.md` の「## 完了の定義」以降に `- [ ]` がない
- [ ] **Step 2: 失敗を確認** → FAIL
- [ ] **Step 3: 削除と書き換え**
- [ ] **Step 4: 通ることを確認** → PASS、全体 PASS
- [ ] **Step 5: コミット**: `refactor(73-github-projects-board): state.json・tasks.json・自前かんばんを削除しルールを書き換える`

### T9: update.sh と migration.md

**Files:**
- Modify: `integration/update.sh`、`docs/migration.md`
- Create: `tests/test_update_sh.py`
- Modify: `tests/test_migration_guide.py`

- [ ] **Step 1: テストを書く**
  - `test_update_sh_copies_board_workflow`: 一時ディレクトリを consumer として `bash integration/update.sh <dir>` を実行（`jq`・`gh` がない環境でも動くこと）→ `<dir>/.github/workflows/sdd-board.yml` がある、`kanban-pages.yml` がない
  - `test_update_sh_does_not_overwrite_board_json`: `<dir>/.sdd/board.json` がすでにあれば変えない
  - `test_migration_guide_projects_board_section`: `docs/migration.md` に `state.json`、`tasks.json`、`.sdd/board.json`、`SDD_PROJECT_TOKEN`、`sdd-board.yml`、`sdd-board.sh init`、`git branch -m`、`repo:` を含む
- [ ] **Step 2: 失敗を確認** → FAIL
- [ ] **Step 3: 実装**: `update.sh` の Managed に `sdd-board.yml` を足す（`sdd-check.yml` と同じく毎回上書き）。`docs/migration.md` に章「v3: GitHub Projects とファイルからの割り出し」を足す。手順: 作業中ブランチを終わらせるか `git branch -m` で改名 → submodule を上げる → `update.sh` → `.sdd/state.json`・`.sdd/tasks.json` を消す → `SDD_PROJECT_TOKEN` を登録 → `sdd-board.sh init` → Projects の画面でリポジトリごとのビュー（`repo:owner/name` の絞り込み）を作る。
- [ ] **Step 4: 通ることを確認** → PASS、全体 PASS
- [ ] **Step 5: コミット**: `docs(73-github-projects-board): 移行手順と update.sh を新しい仕組みに合わせる`

### T10: このリポジトリ自身の移行

**Files:**
- Delete: `.sdd/state.json`、`.sdd/tasks.json`
- Create: `.sdd/board.json`、`.github/workflows/sdd-board.yml`（`integration/ci/sdd-board.yml` のパスをこのリポジトリの配置 `orchestration/tools/sdd-board.sh` に直したもの）、`specs/73-github-projects-board/freeze.json`
- Create: `tests/test_self_migration.py`

- [ ] **Step 1: テストを書く**: `tests/test_self_migration.py`
  - `test_legacy_state_files_absent`: `.sdd/state.json`・`.sdd/tasks.json` がない
  - `test_board_json_present`: `.sdd/board.json` に `owner` と整数の `project`
  - `test_board_workflow_present`: `.github/workflows/sdd-board.yml` があり `orchestration/tools/sdd-board.sh` を呼ぶ
  - `test_feature_freeze_valid`: `freeze_status(ROOT/"specs/73-github-projects-board", 2)[0] == "valid"`
  - `test_validator_passes_for_this_feature`: `sdd-validate.sh --root ROOT --branch t2/73-github-projects-board` が 0
- [ ] **Step 2: 失敗を確認** → FAIL
- [ ] **Step 3: 人に確認する（止まる）**: 次の外部への操作の許可を取る。`sdd-board.sh init --owner toshikimiyagawa`（実際の Project の作成と、このリポジトリの開いている Issue の取り込み）、このリポジトリへの secret `SDD_PROJECT_TOKEN` の登録（値は人が入れる）。
- [ ] **Step 4: 移行**: ブランチを `git branch -m t2/73-github-projects-board` で改名 → `sdd-freeze.sh` で freeze.json を作る（spec 群は凍結時から変えていないこと。tasks.md はチェック欄だけの変更）→ `.sdd/state.json`・`.sdd/tasks.json` を消す → ワークフローを置く → 許可を得て `init` を実行し `.sdd/board.json` を得る → `sdd-board.sh sync`
- [ ] **Step 5: 通ることを確認**: `python -m pytest tests/ -q` → PASS
- [ ] **Step 6: コミット**: `chore(73-github-projects-board): このリポジトリを新しい状態管理に移行する`
