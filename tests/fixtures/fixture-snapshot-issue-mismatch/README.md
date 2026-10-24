## fixture-snapshot-issue-mismatch

**再現パターン:** `issue-snapshot.json` の `issue` が 98 で、ブランチの Issue 番号 (99) と違う。

**準備:** 一時ディレクトリへコピー → `create_freeze` で `freeze.json` を作る。

**確認:** 終了コード 1、標準エラーに `does not match directory` を含む。
