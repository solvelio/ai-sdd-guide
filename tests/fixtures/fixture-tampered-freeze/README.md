## fixture-tampered-freeze

**再現パターン:** 凍結後に `spec.md` が変更されている。

**準備:** fixture を一時ディレクトリへコピー → `create_freeze` で `freeze.json` を作る → `spec.md` に追記する。

**確認:** `--branch t2/99-my-feature` で終了コード 1、標準エラーに `freeze.json` を含む。
