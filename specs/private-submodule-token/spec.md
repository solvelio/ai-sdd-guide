# Issue #69: sdd-check.yml の submodules: true は private な guide では GITHUB_TOKEN で取得できない

Tier 1（軽量 spec）。

## 概要

`integration/ci/sdd-check.yml` の `sdd` job は `submodules: true` で guide を取得するが、デフォルトの
`GITHUB_TOKEN` は consumer 自身のリポジトリにしか権限がないため、guide が private な fork や社内ミラーだと
取得に失敗する。`update.sh` は `sdd-check.yml` を上書きするので、consumer が yml を手で直す方式は使えない。

checkout の `token` を `${{ secrets.SDD_GUIDE_TOKEN || github.token }}` にし、private な guide を使う consumer は
リポジトリ secret `SDD_GUIDE_TOKEN` を登録するだけで済むようにする（人間の判断）。

## 受入条件

- [x] SAC-1: `sdd-check.yml` の `sdd` job の checkout が `token: ${{ secrets.SDD_GUIDE_TOKEN || github.token }}` を指定し、private な guide では secret `SDD_GUIDE_TOKEN` に guide を読める token を登録することがコメントで示されている（元 Issue: 69-AC1）
- [x] SAC-2: `README.md` と `docs/migration.md` の CI 導入手順に、private な guide を使う場合は secret `SDD_GUIDE_TOKEN` を登録することが書かれている（元 Issue: 69-AC2）
- [x] SAC-3: secret 未登録時は `github.token` にフォールバックし、`integration/update.sh` で上書きした後の `sdd-check.yml` も SAC-1 の設定を保つ（元 Issue: 69-AC3）
- [x] SAC-4: `sdd-check.yml` の `sdd` job の checkout が `persist-credentials: false` を指定し、PAT が `.git/config` に残って後続ステップ（PR 側のコード）から読めないようにする（Issue 外。review 指摘を受け人間が今回の PR に含めると承認）

## スコープ

- `integration/ci/sdd-check.yml`: `sdd` job の checkout に `token`・`persist-credentials: false` とコメントを追加
- `README.md`: 導入手順「5. CI を取り込む」に注意を追記
- `docs/migration.md`: 手順 5 に注意を追記

### スコープ外

- `orchestration` job（submodule を取得しないため対象外）
- SSH deploy key（`ssh-key:`）方式のサポート

## テスト

- `tests/test_sdd_check_submodule.py::test_sdd_job_checkout_uses_guide_token_secret` — SAC-1
- `tests/test_sdd_check_submodule.py::test_ci_docs_explain_guide_token_secret` — SAC-2
- `tests/test_sdd_check_submodule.py::test_update_sh_preserves_guide_token_fallback` — SAC-3
- `tests/test_sdd_check_submodule.py::test_sdd_job_checkout_does_not_persist_credentials` — SAC-4
