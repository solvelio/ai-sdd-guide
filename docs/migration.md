# SDD Migration Guide — v2 契約への移行手順

このガイドは ai-sdd-guide の #43 子 issue 群で実装した変更を consumer repository に適用するための手順書です。

## 影響範囲

| Issue | 変更内容 |
|-------|---------|
| #44 | `traceability.json` の canonical 機械検査可能形式 |
| #45 | core/workflow/orchestration/conventions/issue-intake rules への freeze/verify 条件追加 |
| #52 | `state.json` / `tasks.json` JSON Schema + single validator (`sdd-validate.sh`) + CI/hook 連携 |
| #53 | Issue snapshot CLI + `issue-snapshot.json` JSON Schema + snapshot validator 拡張 |
| #54 | Verification evidence JSON Schema + evidence validator 拡張 |
| #48 | sdd-reviewer / agent prompt への元 Issue 差分検査追加 |

## 移行方針

- **完了済み spec は遡及変更しない。** freeze 済みの `specs/<feature>/` ディレクトリには触れない。遡及変更が必要な場合は新 issue を起票する。
- **部分移行は禁止する。** validator、schemas、rules、templates、hooks、CI、reviewer は同じ guide revision として一括更新する。個別コンポーネントのみの更新は行わない。
- **新規 Tier 1/2 feature から新 traceability contract を必須化する。**
- **進行中 feature は方針を選択する。** 旧 guide revision で完了させるか、snapshot/traceability を作成して human 再承認後に新 gate へ移行するかを決める。

---

## 手順 1: traceability.json の追加（#44）

新規 Tier 2 feature の freeze 前に `specs/<feature>/traceability.json` を作成する。

スキーマ: `orchestration/schema/traceability.schema.json`

```json
{
  "issue": 99,
  "issue_url": "https://github.com/your-org/your-repo/issues/99",
  "feature": "my-feature",
  "entries": [
    {
      "issue_ac": "99-AC1",
      "spec_ac": "SAC-1",
      "task": "T1",
      "test": "tests/test_my_feature.py::test_something",
      "status": "in-scope"
    },
    {
      "issue_ac": "99-AC2",
      "spec_ac": null,
      "task": null,
      "test": null,
      "status": "out-of-scope",
      "reason": "スコープ外とした理由",
      "followup_issue": "https://github.com/your-org/your-repo/issues/100"
    }
  ]
}
```

Issue AC ID は `<issue番号>-AC<出現順>` 形式で付番する（Issue 本文の編集は不要）。すべての Issue AC がいずれかの entry に含まれていなければ freeze は禁止される。

---

## 手順 2: Issue snapshot の作成（#53）

freeze 前に Issue 本文のスナップショットを `specs/<feature>/issue-snapshot.json` として保存する。

**CLI を使用する場合:**

```bash
bash integration/ci/sdd-issue-snapshot.sh --issue 99 --feature my-feature --root .
```

**手動作成の場合:** スキーマ `orchestration/schema/issue-snapshot.schema.json` に準拠した JSON を作成し、`body_hash` は `raw_body` の SHA-256 hex digest を設定する。

```python
import hashlib
body_hash = hashlib.sha256(raw_body.encode('utf-8')).hexdigest()
```

`stable_acs` には Issue 本文に出現する受入条件を出現順に `{"id": "99-AC1", "text": "..."}` 形式でリストする。

---

## 手順 3: verification evidence の作成（#54）

verify フェーズで `specs/<feature>/evidence.json` を作成する。

スキーマ: `orchestration/schema/evidence.schema.json`

```json
{
  "feature": "my-feature",
  "commit_sha": "<git rev-parse HEAD の 40 桁 SHA>",
  "entries": [
    {
      "command_type": "test",
      "command": "pytest tests/ -v",
      "result": "100 passed",
      "test_count": 100
    }
  ]
}
```

`commit_sha` は `git rev-parse HEAD` で取得する。実際のリポジトリ内に存在するコミット SHA でなければ validator が失敗する。

---

## 手順 4: state.json / tasks.json の schema 準拠確認（#52）

> v3 で置き換え済み（`state.json` / `tasks.json` はもう使わない。下の「v3」を参照）。

スキーマ: `orchestration/schema/state.schema.json` / `orchestration/schema/tasks.schema.json`

`.sdd/state.json` の形式:

```json
{"tier": 2, "phase": "implement", "feature": "my-feature"}
```

`.sdd/tasks.json` の各エントリ形式:

```json
{
  "id": "my-feature",
  "phase": "implement",
  "status": "in_progress",
  "handoff": "specs/my-feature/handoff.md",
  "blocked_reason": null
}
```

validator で確認する:

```bash
bash vendor/ai-sdd-guide/integration/ci/sdd-validate.sh --root .
```

---

## 手順 5: CI への sdd-validate 組み込み（#52）

> v3 で置き換え済み（`update.sh` が `sdd-check.yml` を配る。下の「v3」を参照）。

`.github/workflows/` に `integration/ci/sdd-check.yml` をコピーし、`Tests` ステップのコマンドをこのプロジェクトのテストコマンドに差し替える。

```yaml
- name: Tests
  run: pytest tests/ -v  # または npm test / go test ./... 等
```

既存 CI workflow がある場合は `sdd-check.yml` の各ステップを既存 workflow に追加する。sdd-check.yml は以下の 3 段階を実行する:

1. **State reset gate** — PR 作成前に `state.json` が `phase=done` になっていることを確認
2. **Spec gate** — ソース変更がある PR に `specs/<feature>/spec.md` が存在することを確認
3. **Run sdd-validate** — `sdd-validate.sh --root .` を実行してすべての validator チェックを通過させる

guide を private な fork や社内ミラーとして submodule にしている場合、デフォルトの `GITHUB_TOKEN` では submodule を取得できない。PAT をリポジトリ secret `SDD_GUIDE_TOKEN` に登録する。`sdd-check.yml` は secret があればそれを使い、なければ `GITHUB_TOKEN` を使うので、yml を編集する必要はない（`update.sh` で上書きされても設定は消えない）。

- checkout はこの token で consumer リポジトリ本体と submodule の両方を取得する。token には **consumer リポジトリと guide の両方** への Contents: read が必要。
- consumer と guide が同じオーナー（user / org）配下なら fine-grained PAT で両方を選べる。オーナーが異なる場合、fine-grained PAT は 1 つのオーナーにしか効かないため classic PAT（`repo` scope）を使う。
- GitHub App の installation token は 1 時間で失効するため、secret に固定値として登録することはできない。
- fork からの PR と Dependabot の PR には repository secret が渡されないため、`GITHUB_TOKEN` にフォールバックして submodule の取得に失敗する。Dependabot には Dependabot secrets 側に同名の secret を登録する。fork からの PR は private な guide では検査できない。

---

## 手順 6: hook への sdd-validate 組み込み（#52）

> v3 で置き換え済み。hook をコピーしてはいけない。`vendor/ai-sdd-guide/integration/hooks/...` を直接参照し、コピー済みの hook は削除する（下の「v3」を参照）。

`integration/hooks/sdd-validate-hook.sh` をコピーして hook に登録する。

**Claude Code の場合** (`.claude/settings.json`):

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [{"type": "command", "command": "bash .claude/hooks/sdd-guard.sh"}]
      }
    ]
  }
}
```

既存 hook がある場合は `integration/hooks/README.md` を参照して統合する。hook の詳細設定は `orchestration/integration/settings-patch.json` も参照。

---

## 手順 7: sdd-reviewer prompt の更新（#48）

> v3 で置き換え済み（reviewer は `freeze.json` と branch 名から状態を読む。下の「v3」を参照）。

`integration/prompts/sdd-reviewer-prompt.md` を consumer repository の reviewer 設定に反映する。

AGENTS.md への組み込み例は `orchestration/integration/AGENTS-patch.md.example` を参照。reviewer は spec 適合に加えて以下を確認するよう更新されている:

1. 元 Issue の全 AC が `traceability.json` に追跡されている
2. scope 外 AC に `followup_issue` URL がある
3. `state.json` が対象 feature / tier / phase を指している
4. `tasks.json` に対象 feature のエントリがあり schema valid である
5. `tasks.md` の完了状態と完了報告が一致する
6. 各 AC が実行可能なテストに対応している

---

## 具体例

### 例 A: 新規 feature への全手順適用

issue #150 から feature `auth-refresh` を新規に開始する場合:

```bash
# 1. Issue snapshot を取得
bash integration/ci/sdd-issue-snapshot.sh --issue 150 --feature auth-refresh --root .

# 2. spec.md / plan.md / tasks.md を作成（通常の SDD Tier 2 フロー）

# 3. traceability.json を作成
#    specs/auth-refresh/traceability.json に 150-AC1 〜 150-ACn を漏れなく記載

# 4. sdd-validate で確認してから freeze
bash vendor/ai-sdd-guide/integration/ci/sdd-validate.sh --root .
# exit 0 を確認してから state.json を phase=implement に変更

# 5. 実装後 verify フェーズで evidence.json を作成
git rev-parse HEAD  # 40 桁 SHA を取得して evidence.json に記載
```

### 例 B: 進行中 feature を新 gate へ移行

すでに `spec.md` / `plan.md` / `tasks.md` が存在する feature に snapshot/traceability を追加する場合:

```bash
# 1. Issue snapshot を取得（freeze 前でも実施可能）
bash integration/ci/sdd-issue-snapshot.sh --issue 99 --feature my-feature --root .

# 2. traceability.json を作成
#    既存 spec.md の SAC と Issue AC を対応させる
#    スコープ外化した AC には reason と followup_issue を付与

# 3. human に traceability を提示して再承認を得る
#    元 Issue と frozen spec の差分を明示すること

# 4. sdd-validate で確認
bash vendor/ai-sdd-guide/integration/ci/sdd-validate.sh --root .
```

**完了済み spec（PR merge 済み）は変更しない。** 遡及変更が必要な場合は新 issue を起票する。

---

## Consumer Update チェックリスト

feature ごとに以下を確認する:

- [ ] `specs/<feature>/issue-snapshot.json` を作成した（新規・移行対象 feature）
- [ ] `specs/<feature>/traceability.json` を作成した（新規・移行対象 feature）
- [ ] verify フェーズで `specs/<feature>/evidence.json` を作成した
- [ ] `.sdd/state.json` が新 schema に準拠している
- [ ] `.sdd/tasks.json` が新 schema に準拠している
- [ ] CI workflow に `integration/ci/sdd-check.yml` の手順を組み込んだ
- [ ] hook に `integration/hooks/sdd-validate-hook.sh` を組み込んだ
- [ ] `integration/prompts/sdd-reviewer-prompt.md` を reviewer 設定に反映した

---

## 部分移行禁止チェックリスト

以下のコンポーネントは同じ guide revision として一括更新する。いずれか 1 項目でも未対応の場合は移行を完了とみなさない:

- [ ] `orchestration/schema/` — state / tasks / traceability / issue-snapshot / evidence schema
- [ ] `integration/ci/sdd-validate.sh` — single validator
- [ ] `integration/ci/sdd-check.yml` — CI template
- [ ] `integration/hooks/sdd-validate-hook.sh` — hook
- [ ] `integration/prompts/sdd-reviewer-prompt.md` — reviewer prompt
- [ ] `rules/` — core / workflow / orchestration / conventions / issue-intake の freeze/verify 条件

---

## v3: GitHub Projects とファイルからの割り出し

進捗の管理を `.sdd/state.json` / `.sdd/tasks.json` から、GitHub Projects のボードと「ブランチ名・`specs/` のファイル」からの割り出しに切り替える。一括で切り替える（`state.json` / `tasks.json` へのフォールバックはない）。仕組みは [README](../README.md) と各 docs、用語と規則は `specs/73-github-projects-board/spec.md` の「用語と規則」を参照。

consumer repo では次の順に行う。

1. **作業中のブランチを終わらせるか、改名する。** 仕掛かりのブランチは merge して終わらせるか、`git branch -m t<Tier>/<Issue番号>-<名前>`（例: `git branch -m t2/42-add-login`）で新しい名前にする。旧名のままだと guard が通らない。
   - 改名だけでは足りない。進行中の feature は次も行う: `git mv specs/<旧名> specs/<Issue番号>-<名前>`、`issue-snapshot.json` の Issue 番号がブランチの Issue 番号と一致していることの確認（Tier 2）、人間の承認、`sdd-freeze.sh` の実行（`freeze.json` を作る）、`handoff.md` がなければ追加。
2. **hook は vendor のパスから参照する。** `.claude/settings.json` などの hook は `vendor/ai-sdd-guide/integration/hooks/...` を直接指す（`integration/settings.json.example` 参照）。旧手順でコピーした hook は削除する。コピーした hook は `../ci/sdd_state.py` を見つけられず、編集がすべて拒否される。
3. **submodule を上げる。** `git submodule update --remote vendor/ai-sdd-guide`（または目的の revision を checkout）して、親 repo でコミットする。
4. **`update.sh` を実行する。** `bash vendor/ai-sdd-guide/integration/update.sh`。`.github/workflows/sdd-check.yml` と `.github/workflows/sdd-board.yml` が毎回上書きされる。`.sdd/board.json` は触らない。
5. **`.sdd/state.json` と `.sdd/tasks.json` を消す。** もう読まれない。あわせて、kanban を使っていた場合は `.github/workflows/kanban-pages.yml` を消し、GitHub Pages を無効にする。
6. **`SDD_PROJECT_TOKEN` を登録する。** classic PAT（`repo`（private リポジトリの場合）・`project`・`read:org`）を作り、repo secret `SDD_PROJECT_TOKEN` に登録する（`sdd-board.yml` が使う）。v3.1 以降は GitHub App を使うのが望ましい（下の「v3.1」）。
7. **`sdd-board.sh init` を実行する。** `bash vendor/ai-sdd-guide/orchestration/tools/sdd-board.sh init [--owner OWNER] [--title TITLE]`。Project と Phase フィールドを作り、`.sdd/board.json`（`owner`・`project`・任意で `tier0_branch_prefixes`）を書き、open な Issue をボードに取り込む。`.sdd/board.json` はコミットする。
   - ボードは 1 アカウントに 1 つ。アカウントにすでに SDD のボードがあるときは、`init` の前にその `owner` / `project` を `.sdd/board.json` に書いておく（`{"owner": "...", "project": 3}`）。そうすれば `init` は新しい Project を作らず、Phase フィールドの確認と Issue の取り込みだけを行う。書かずに実行すると 2 つ目の Project ができる。
   - ローカルの `gh` には `project` スコープが要る: `gh auth refresh -s project`。
8. **リポジトリごとのビューを作る。** Projects の画面でビューを足し、絞り込みに `repo:owner/name` を指定する。
9. **以降、新しい作業にはすべて Issue が要る。** Tier 0 も例外ではない（`t0/<Issue番号>-<名前>`）。dependabot / renovate などの bot ブランチは `tier0_branch_prefixes` で除外される。

既存の完了済み `specs/<feature>/` ディレクトリは改名しない。新しい仕組みの feature 名は `<Issue番号>-<名前>` だが、過去分はそのまま残す。

---

## v3.1: PAT から GitHub App へ

ボードの更新に使うトークンを、個人の PAT（`SDD_PROJECT_TOKEN`）から GitHub App に切り替える。App があれば App、なければ PAT が使われるので、段階的に移せる。手順の詳細は [04-issue-tracker](04-issue-tracker.md) の「GitHub App で動かす」。

1. **App を作る。** Webhook の Active を外し、Organization の Projects を Read and write、リポジトリの Issues / Pull requests / Metadata を Read-only にして、Organization に **All repositories** でインストールする。
2. **鍵を 1Password へ入れる。** 秘密鍵を生成して `.pem` を 1Password に保管し、ダウンロードしたファイルは消す。
3. **各リポジトリの `.sdd/board.json` に `app_id` を書く。** PR で入れる。
4. **鍵を配る。** Mac で `bash vendor/ai-sdd-guide/orchestration/tools/sdd-app-secret.sh --op-ref "op://<保管庫>/<項目>/<欄>" OWNER/NAME`（Organization 全体なら `--all --org ORG`）を実行し、repo secret `SDD_APP_PRIVATE_KEY` を登録する。
5. **PR の CI で App で動くことを確かめる。** `sdd-board.yml` の実行で、App のトークンが作られてボードが更新されていること。
6. **`SDD_PROJECT_TOKEN` を消し、PAT を無効にする。** 確かめたあと、repo secret `SDD_PROJECT_TOKEN` を削除し、GitHub の画面で PAT を無効にする。
