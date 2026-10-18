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

superpowers がインストールされたエージェントであれば誰でも設計・実装・verify の全フェーズを担当できる。人間が「このタスクをこのエージェントで」と指示し、エージェントはフェーズ完了後に kanban を表示して停止する。

| コンポーネント | パス | 役割 |
|---|---|---|
| エージェントルール | `orchestration/rules/orchestration.md` | フェーズ割り当て・停止ルール（全agent）|
| スキーマ | `orchestration/schema/tasks.schema.json` | `tasks.json` の定義 |
| テンプレート | `orchestration/templates/handoff.md.example` | handoff.md の雛形 |
| Reviewer プロンプト | `integration/prompts/sdd-reviewer-prompt.md` | エージェント非依存の verify 指示文 |
| Kanban | `orchestration/tools/kanban.sh` | `.sdd/tasks.json` をターミナルにKanban表示 |
| Kanban (HTML) | `orchestration/tools/kanban-html.sh` | `.sdd/tasks.json` を静的HTMLとして出力 |
| Kanban Pages | `integration/ci/kanban-pages.yml` | HTMLを生成し GitHub Pages へ自動公開する見本 |

### Kanban 表示

```bash
# ターミナル表示
bash vendor/ai-sdd-guide/orchestration/tools/kanban.sh
```

### Web 可視化（GitHub Pages）

`.sdd/tasks.json` を静的HTMLとして出力し、push のたびに GitHub Pages で公開できる。
`kanban.sh` は変更せず、HTML生成は別スクリプト（単一責任）。

```bash
# 単発でHTMLを生成（stdout または出力ファイル）
bash vendor/ai-sdd-guide/orchestration/tools/kanban-html.sh .sdd/tasks.json kanban.html

# 自動公開する場合（GitHub Actions + Pages）
mkdir -p .github/workflows
cp vendor/ai-sdd-guide/integration/ci/kanban-pages.yml .github/workflows/
# その後 Settings → Pages → Source を "GitHub Actions" にする
```

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
流れで回せる。**ステータスの正本は `.sdd/tasks.json`（SDD かんばん）に統一**し、プラット
フォームのネイティブボードは任意のミラー扱い。

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
```

設計フェーズで superpowers を使う場合は、Claude Code のプラグインとして別途導入する（submoduleとは別）：
```
/plugin install superpowers@claude-plugins-official
```
スキルとSDDフェーズの対応は `docs/02-roles.md` を参照。

`.sdd/state.json`（Tier/フェーズの状態。hooks・CIが参照）は作業中に agent が作成・更新する。
雛形は `templates/sdd-state.example.json`、値の定義は `templates/sdd-state.schema.json`。

### 初回導入時の注意

SDD導入自体が hooks と CI の対象になる（鶏と卵問題）。初回コミット時は
`.sdd/state.json` を Tier 0 で作成してから作業すること：
```bash
mkdir -p .sdd
cat > .sdd/state.json << 'EOF'
{
  "feature": "integrate-ai-sdd-guide",
  "tier": 0,
  "phase": "implement",
  "justification": "SDD infrastructure setup — no application logic changed"
}
EOF
```

また、CI テンプレート (`sdd-check.yml`) の exempt パターンはそのまま使えるが、
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
