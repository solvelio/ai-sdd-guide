## fixture-missing-freeze

**再現パターン:** `--pr` で検査するのに `freeze.json` がない。

**準備:** 一時ディレクトリへコピーするだけ（`freeze.json` を作らない）。

**確認:** `--pr --branch t2/99-my-feature` で終了コード 1、標準エラーに `freeze.json not found` を含む。
