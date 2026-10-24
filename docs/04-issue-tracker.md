# 04. Issue トラッカー連携

Issue 登録から SDD ワークフロー完了までを、GitHub / GitLab / Bitbucket / Azure DevOps の
いずれでも同じ流れで回すための連携ルール。agent 向けの正本は `rules/issue-intake.md`。

## ステータスはブランチ名と specs/ から割り出す

SDD のステータスは、ブランチ名 `t<Tier>/<Issue番号>-<名前>` と `specs/<Issue番号>-<名前>/` のファイルから
割り出す（記録するファイルはない）。ボードは割り出した結果を**表示するだけ**。

- ボード: GitHub Projects（アカウントで 1 枚、1 Issue = 1 カード）。列は単一選択フィールド `Phase`:
  backlog → brainstorm → spec → plan → tasks → implement → verify → done。
- 設定: `.sdd/board.json`（`owner`・`project`・`app_id`・`tier0_branch_prefixes`）。Actions の secret は
  `SDD_APP_PRIVATE_KEY`（GitHub App の鍵）。予備として `SDD_PROJECT_TOKEN`（classic PAT、`repo`（private リポジトリの場合）・`project`・`read:org`）も使える。
  App があれば App、なければ PAT、どちらもなければ警告して更新を飛ばす。App を設定したのにトークンが作れないときはジョブが失敗する。
- 更新: 手元は `orchestration/tools/sdd-board.sh sync`、CI は `integration/ci/sdd-board.yml`。
- GitLab と Azure DevOps のボードは [#71]・[#72] で扱う。Bitbucket は Issues 廃止のため対象外。

## GitHub App で動かす

ボードの更新を個人の PAT ではなく GitHub App で行う。トークンは実行のたびに作られ、短時間で失効する。

### App を作る

1. Organization の Settings → Developer settings → GitHub Apps → New GitHub App。
2. **Webhook** の「Active」のチェックを外す。
3. 権限を次のとおりにする。
   - Organization permissions → Projects: **Read and write**
   - Repository permissions → Issues / Pull requests / Metadata: **Read-only**
4. 作ったら、Organization にインストールする。リポジトリのアクセスは **All repositories** を選ぶ。新しいリポジトリも自動で対象に入る。
5. App の画面で App ID を控える（`board.json` の `app_id` に使う）。

### 鍵を作り、1Password に保管する

1. App の設定画面で「Generate a private key」を押し、ダウンロードされた `.pem` を 1Password に入れる。
2. ダウンロードした `.pem` のファイルは消す。鍵はどこにも貼らない。

### 各リポジトリに設定する

1. `.sdd/board.json` に `app_id`（App ID の整数）を書き、PR で入れる。`owner`・`project` も要る。
2. 鍵をリポジトリの secret `SDD_APP_PRIVATE_KEY` に配る。GitHub Free では private リポジトリが Organization の secret を読めないため、リポジトリごとの secret に入れる。Mac で `op` を 1Password アプリと連携させ、自分の `gh` でログインした状態で実行する。

```bash
# 1 つ、または複数のリポジトリ
bash vendor/ai-sdd-guide/orchestration/tools/sdd-app-secret.sh \
  --op-ref "op://<Vault>/<Item>/<field>" OWNER/NAME [OWNER/NAME ...]
# Organization の全リポジトリ
bash vendor/ai-sdd-guide/orchestration/tools/sdd-app-secret.sh \
  --op-ref "op://<Vault>/<Item>/<field>" --all --org ORG
```

`--dry-run` で配る先だけを確かめられる。`--app-id N` は、インストールの確認に使う App ID を直接指定する（省略すると各リポジトリの `board.json` の `app_id` を使う）。`board.json` に `app_id` がないリポジトリには注意を出す。スクリプトは、App が **All repositories** にインストールされているかを確かめ、そうでなければ案内を出して止まる。リポジトリを App のインストールに足すことはしない。

### リポジトリを足すとき

1. `.sdd/board.json`（`owner`・`project`・`app_id`）を PR で置く。
2. そのリポジトリに対して `sdd-app-secret.sh` を 1 回実行する。

### 予備の PAT

`SDD_PROJECT_TOKEN` は予備。classic PAT で、`repo`（private リポジトリの場合）・`project`・`read:org` を付ける。fine-grained PAT は user 所有の Projects を操作できない。

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

[#71]: https://github.com/solvelio/ai-sdd-guide/issues/71
[#72]: https://github.com/solvelio/ai-sdd-guide/issues/72
