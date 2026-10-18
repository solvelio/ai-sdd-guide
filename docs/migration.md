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

`.github/workflows/` に `integration/ci/sdd-check.yml` をコピーし、`Tests` ステップのコマンドをこのプロジェクトのテストコマンドに差し替える。

```yaml
- name: Tests
  run: pytest tests/ -v  # または npm test / go test ./... 等
```

既存 CI workflow がある場合は `sdd-check.yml` の各ステップを既存 workflow に追加する。sdd-check.yml は以下の 3 段階を実行する:

1. **State reset gate** — PR 作成前に `state.json` が `phase=done` になっていることを確認
2. **Spec gate** — ソース変更がある PR に `specs/<feature>/spec.md` が存在することを確認
3. **Run sdd-validate** — `sdd-validate.sh --root .` を実行してすべての validator チェックを通過させる

---

## 手順 6: hook への sdd-validate 組み込み（#52）

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
