closes #<Issue番号>

## 変更
変更したファイルと内容。各項目に対応する受入条件（SAC-N）を添える。
spec: `specs/<feature>/spec.md`

## Verify
- テスト: <件数> passed
- `sdd-validate`: PASS / FAIL
- 独立 reviewer（`sdd-reviewer`）: PASS / FAIL

## AI の判断
人間が PR レビューで確かめられるように、AI が人間に聞かずに決めたことを書く。

- **spec レビュー**: 判定と回数（例: `Spec review: APPROVE (2 rounds)`）
- **仕様の不明点**: AI が決めたことと、その理由
- **指摘の採否**: verify やレビューの指摘のうち、採用したもの・採用しなかったものと、その理由
- **スコープ外**: スコープ外にしたものと、そのフォローアップの Issue
