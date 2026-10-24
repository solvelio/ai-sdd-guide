## fixture-missing-handoff

**再現パターン:** `freeze.json` があるのに `handoff.md` がない。

**準備:** 一時ディレクトリへコピー → `create_freeze` で `freeze.json` を作る。

**確認:** 終了コード 1、標準エラーに `handoff.md` を含む。
