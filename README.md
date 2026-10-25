# ai-sdd-guide

AIを使ったスペック駆動開発 (SDD: Spec-Driven Development) のガイドライン。

各プロジェクトに `git submodule` で **正本** として取り込み、
AIエージェントと人間が同じルールで開発するための土台を提供する。

## 中心思想：設計と実装の分離
- **設計 (spec/plan/tasks/レビュー) = superpowers 必須（どのエージェントでも可）**（superpowers + subagent + hooks をフル活用）
- **実装 = どのエージェントでも可**（`specs/<feature>/` を契約として渡す）

## 構成
| パス | 対象 | 言語 | 役割 |
|---|---|---|---|
| `rules/` | agent | 英語 | 常時参照する強制ルール（命令形・簡潔） |
| `docs/` | 人間 | 日本語 | 方法論の解説 |
| `templates/` | 両方 | - | spec / plan / tasks 雛形 |
| `integration/` | 取り込み側 | - | ルート入口・hooks・CI・subagent定義の見本 |
| `orchestration/` | 両方 | - | マルチエージェント・オーケストレーション |
| `catalog/` | 両方 | - | 機能単位カタログ |

## ワークフロー（Tier制）
| Tier | 対象 | 作るもの |
|---|---|---|
| 0 | typo・docのみ・自明な修正 | 何も作らず実施 |
| 1 | 小さなbugfix・小機能 | 軽量spec＋テスト |
| 2 | 中〜大機能・設計変更 | spec → plan → tasks → 実装 → 検証 |

## 守らせる仕組み（多層）
1. **Claude hooks** — `sdd-guard.sh` が設計フェーズの逸脱をローカルで弾き、`skill-reminder.sh` が現在の Tier/phase に応じた superpowers skill を案内する（速い注意喚起・バイパス可）
2. **Codex hooks** — `codex-sdd-guard.sh` が検出可能な source edit をローカルで弾き、`codex-skill-reminder.sh` が Tier/phase に応じた SDD 注意を developer context に注入する（Codex hook の検出範囲内でのみ有効）
3. **CI** — 全agent共通の権威ある門番（spec有無・テスト）。バイパス不可
4. **sdd-reviewer subagent** — 実装が凍結specに適合するか独立監査。レビューフィードバックの吸収が scope creep になっていないか（`receiving-code-review` 規律の痕跡）も確認

## マルチエージェント・オーケストレーション

superpowers がインストールされたエージェントであれば誰でも設計・実装・verify の全フェーズを担当できる。人間が「このタスクをこのエージェントで」と指示し、エージェントはフェーズ完了後に commit → `sdd-board.sh sync` を実行して停止する。

| コンポーネント | パス | 役割 |
|---|---|---|
| エージェントルール | `orchestration/rules/orchestration.md` | フェーズ割り当て・停止ルール（全agent）|
| テンプレート | `orchestration/templates/handoff.md.example` | handoff.md の雛形 |
| Reviewer プロンプト | `integration/prompts/sdd-reviewer-prompt.md` | エージェント非依存の verify 指示文 |
| 凍結コマンド | `orchestration/tools/sdd-freeze.sh` | `specs/<feature>/freeze.json` を作る（対象ファイルのハッシュを記録）|
| ボード操作 | `orchestration/tools/sdd-board.sh` | GitHub Projects のボードを `sync` / `init` / `import` / `set` / `close` / `pr` で操作 |
| ボード Actions | `integration/ci/sdd-board.yml` | Issue・PR のイベントでボードを更新する見本 |

### 状態とボード

状態ファイルは持たない。Tier・feature・フェーズは、ブランチ名 `t<Tier>/<Issue番号>-<名前>` と
`specs/<Issue番号>-<名前>/` のファイルから割り出す（`python3 vendor/ai-sdd-guide/integration/ci/sdd_state.py phase`）。
ボードは GitHub Projects（アカウントで 1 枚）で、割り出したフェーズを表示するだけ。

```bash
# ボードを作り、開いている Issue を backlog で取り込む（初回のみ）
bash vendor/ai-sdd-guide/orchestration/tools/sdd-board.sh init
# 今のブランチの Issue のカードのフェーズを更新
bash vendor/ai-sdd-guide/orchestration/tools/sdd-board.sh sync

# Actions で自動更新する場合（GitHub App の鍵 SDD_APP_PRIVATE_KEY。予備として secret SDD_PROJECT_TOKEN: classic PAT、`repo`（private リポジトリの場合）・`project`・`read:org`）。手順は docs/04-issue-tracker.md
mkdir -p .github/workflows
cp vendor/ai-sdd-guide/integration/ci/sdd-board.yml .github/workflows/
```

設定は `.sdd/board.json`（`owner`・`project`・`app_id`・`tier0_branch_prefixes`）。GitLab・Azure DevOps は #71・#72、Bitbucket は Issues 廃止のため対象外。

## 機能単位カタログ

画面一覧・API一覧・テーブル一覧などのシステム全体カタログを `catalog/` モジュールで管理できる。
superpowers が使えるエージェントが spec 作成時（planned）と verify 完了時（confirmed）に自動更新する。

| コンポーネント | パス | 役割 |
|---|---|---|
| エージェントルール | `catalog/rules/catalog.md` | カタログ更新のタイミングと手順 |
| スキーマ | `catalog/schema/catalog.schema.json` | `.sdd/catalog.json` の定義 |
| テンプレート | `catalog/templates/` | 設定例・一覧・定義書の雛形 |

## Issue トラッカー連携

GitHub / GitLab / Bitbucket / Azure DevOps のいずれでも、Issue 登録から SDD 完了まで同じ
流れで回せる。**ステータスはブランチ名と `specs/` から割り出し**、
ボード（GitHub Projects）は表示だけを担う。

| コンポーネント | パス | 役割 |
|---|---|---|
| エージェントルール | `rules/issue-intake.md` | Issue → SDD のインテークフロー（全agent）|
| 解説 | `docs/04-issue-tracker.md` | プラットフォーム機能マッピングとフロー（日本語）|
| セットアップ例 | `integration/issue-tracker/` | Tier ラベル作成スクリプト・各プラットフォーム手順 |

```bash
# GitHub: Tier ラベルを作成（冪等）
bash vendor/ai-sdd-guide/integration/issue-tracker/labels.sh
```

## 導入手順（取り込み側プロジェクト）
```bash
# 1. submodule として追加（配置パスは vendor/ai-sdd-guide 固定。sdd-check.yml がこのパスを前提にする）
git submodule add <this-repo-url> vendor/ai-sdd-guide

# 2. ルートに薄い入口を配置（一度だけコピー）
cp vendor/ai-sdd-guide/integration/AGENTS.md.example ./AGENTS.md
ln -s AGENTS.md CLAUDE.md        # CLAUDE.md は AGENTS.md のシンボリックリンクとして管理

# 3. Claude hooks と subagent を取り込む（Claude 利用時）
mkdir -p .claude
cp vendor/ai-sdd-guide/integration/settings.json.example .claude/settings.json
cp -r vendor/ai-sdd-guide/integration/agents .claude/agents

# 4. Codex hooks を取り込む（Codex 利用時）
mkdir -p .codex
cp vendor/ai-sdd-guide/integration/codex/config.toml.example .codex/config.toml
# 初回または hook 変更後は Codex TUI の /hooks で review/trust する

# 5. CI を取り込む（テストコマンドはプロジェクトに合わせて差し替え）
mkdir -p .github/workflows
cp vendor/ai-sdd-guide/integration/ci/sdd-check.yml .github/workflows/
cp vendor/ai-sdd-guide/integration/ci/sdd-board.yml .github/workflows/
#    guide が private な場合は、このリポジトリと guide の両方を読める PAT をリポジトリ secret SDD_GUIDE_TOKEN に登録する（docs/migration.md 手順 5）

# 6. （任意）ボードを使う: GitHub Projects のボードを作り、.sdd/board.json を作成する
bash vendor/ai-sdd-guide/orchestration/tools/sdd-board.sh init
#    Actions の認証は次から選ぶ（手順は docs/04-issue-tracker.md）
#    - Organization のリポジトリ: GitHub App。鍵を secret SDD_APP_PRIVATE_KEY に、App ID を board.json の app_id に書く
#    - 個人アカウントの Project: classic PAT（repo（private リポジトリの場合）・project・read:org）を secret SDD_PROJECT_TOKEN に登録する
```

`integration/update.sh` も `sdd-check.yml` と `sdd-board.yml` の両方をコピーする。
`.sdd/board.json` がなければ、`sdd-board.sh sync` とワークフローのボードの処理は警告を出して飛ばされる。
PR にブランチ名から Tier ラベル（`sdd:tier-*`）を自動で付けるのは `sdd-board.yml` で、これはボードの有無に関係なく動く。`sdd-board.yml` を入れない場合、PR の Tier ラベルは手で付ける。

設計フェーズで superpowers を使う場合は、Claude Code のプラグインとして別途導入する（submoduleとは別）：
```
/plugin install superpowers@claude-plugins-official
```
スキルとSDDフェーズの対応は `docs/02-roles.md` を参照。

ブランチ名を `t<Tier>/<Issue番号>-<名前>` にすれば、Tier とフェーズは自動で割り出される（状態ファイルは不要）。

### 初回導入時の注意

SDD導入自体が hooks と CI の対象になる（鶏と卵問題）。導入の Issue を作り、Tier 0 のブランチ（例: `t0/1-integrate-ai-sdd-guide`）で作業すること。

CI テンプレート (`sdd-check.yml`) の exempt パターンはそのまま使えるが、
プロジェクト固有のリンター設定（`.yamllint` 等）で既存コードとの整合を取る必要がある場合がある。
Codex の project-local hooks は trusted project でのみ読み込まれ、初回または hook 変更後に `/hooks` で trust が必要。

`CLAUDE.md` / `AGENTS.md` はプロジェクトルートに無いとagentが自動で読まないため、
submodule（サブパス）には置かず、ルートの薄い入口から submodule 内の正本を参照させる。

## 更新の反映
```bash
git submodule update --remote vendor/ai-sdd-guide
vendor/ai-sdd-guide/integration/update.sh
```

正本を更新すれば、各プロジェクトはこのコマンドで一括追従できる。`update.sh` は `.claude/agents/` と CI を上書きし、`AGENTS.md` / `.claude/settings.json` / `.codex/config.toml` は保護対象として作成または差分表示する。破壊的変更はタグ (semver) で管理する。

詳細は `docs/`（人間向け）と `rules/`（agent向け正本）を参照。
