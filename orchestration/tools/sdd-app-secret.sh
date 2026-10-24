#!/usr/bin/env bash
# Distribute the GitHub App private key from 1Password to each repository's
# Actions secret SDD_APP_PRIVATE_KEY (adding the repo to the App installation
# when needed). Needs only bash, gh (human login) and op. Reads no repo files.
# The key goes op -> gh over a pipe: never to stdout/stderr/files, and only its
# PEM header line is ever held in a shell variable.
#
# Usage: sdd-app-secret.sh --op-ref op://... [--app-id N] [--dry-run] \
#          (OWNER/NAME... | --all --org ORG)
# Exit: 0 ok, 1 bad input / App not found / op failure, 2 unexpected failure.
set -Eeuo pipefail
trap 'exit 2' ERR

SECRET=SDD_APP_PRIVATE_KEY
REF=""; APP_ID=""; DRY=0; ALL=0; ORG=""; TARGETS=()

die() { echo "エラー: $*" >&2; exit 1; }

while [ $# -gt 0 ]; do
  case "$1" in
    --op-ref) [ $# -ge 2 ] || die "--op-ref に値がありません"; REF="$2"; shift 2 ;;
    --app-id) [ $# -ge 2 ] || die "--app-id に値がありません"; APP_ID="$2"; shift 2 ;;
    --org)    [ $# -ge 2 ] || die "--org に値がありません"; ORG="$2"; shift 2 ;;
    --all)    ALL=1; shift ;;
    --dry-run) DRY=1; shift ;;
    -*) die "不明なオプション: $1" ;;
    */*) TARGETS+=("$1"); shift ;;
    *) die "対象は OWNER/NAME の形で指定してください: $1" ;;
  esac
done

[ -n "$REF" ] || die "--op-ref は必須です"
case "$APP_ID" in ''|*[!0-9]*) [ -z "$APP_ID" ] || die "--app-id は整数で指定してください" ;; esac
if [ "$ALL" -eq 1 ]; then
  [ -n "$ORG" ] || die "--all には --org が必要です"
  [ ${#TARGETS[@]} -eq 0 ] || die "--all と OWNER/NAME は同時に指定できません"
else
  [ -z "$ORG" ] || die "--org は --all と一緒に指定してください"
  [ ${#TARGETS[@]} -gt 0 ] || die "対象のリポジトリを指定してください"
fi

# Prints board.json's app_id (digits only) or nothing; returns 1 if no board.json.
board_app_id() {
  local out
  out=$(gh api -H 'Accept: application/vnd.github.raw' \
    "repos/$1/contents/.sdd/board.json" --jq .app_id 2>/dev/null) || return 1
  case "$out" in ''|*[!0-9]*) out="" ;; esac
  printf '%s' "$out"
}

if [ "$ALL" -eq 1 ]; then
  list=$(gh repo list "$ORG" --json nameWithOwner --limit 1000 --jq '.[].nameWithOwner')
  TARGETS=()
  for r in $list; do
    if board_app_id "$r" >/dev/null; then TARGETS+=("$r"); fi
  done
  [ ${#TARGETS[@]} -gt 0 ] || die "$ORG に .sdd/board.json を持つリポジトリがありません"
fi

# Resolve App ID: flag, else first target's board.json.
if [ -z "$APP_ID" ]; then
  for r in "${TARGETS[@]}"; do
    id=$(board_app_id "$r" || true)
    if [ -n "$id" ]; then APP_ID="$id"; break; fi
  done
  [ -n "$APP_ID" ] || die "App ID が決まりません。--app-id を指定するか board.json に app_id を書いてください"
fi

# Find the installation for this App.
inst=$(gh api --paginate /user/installations \
  --jq ".installations[] | select(.app_id == $APP_ID) | .id")
inst="${inst%%$'\n'*}"
[ -n "$inst" ] || die "App ID $APP_ID のインストール先が見つかりません"

for repo in "${TARGETS[@]}"; do
  echo "== $repo"
  repo_id=$(gh api "repos/$repo" --jq .id)
  installed=$(gh api --paginate "/user/installations/$inst/repositories" \
    --jq '.repositories[].full_name')
  has_inst=0
  if printf '%s\n' "$installed" | grep -Fxq -- "$repo"; then has_inst=1; fi
  bid=$(board_app_id "$repo" || true)

  if [ "$DRY" -eq 1 ]; then
    [ "$has_inst" -eq 1 ] || echo "  [dry-run] App のインストール先に追加する"
    echo "  [dry-run] $SECRET を $repo に設定する（op read $REF）"
    [ -n "$bid" ] || echo "  [dry-run] 注意: board.json に app_id がありません（書き換えません）"
    continue
  fi

  if [ "$has_inst" -eq 0 ]; then
    gh api -X PUT "/user/installations/$inst/repositories/$repo_id" >/dev/null
    echo "  App のインストール先に追加しました"
  fi

  # op -> (check PEM header) -> gh secret set. Nothing is set unless the first
  # line is a PEM header; reader exits 3 in that case.
  trap - ERR
  set +e
  op read "$REF" | {
    IFS= read -r first || true
    case "$first" in -----BEGIN*) ;; *) exit 3 ;; esac
    { printf '%s\n' "$first"; cat; } | gh secret set "$SECRET" -R "$repo"
  }
  st=("${PIPESTATUS[@]}")
  set -e
  trap 'exit 2' ERR
  if [ "${st[1]}" -eq 3 ]; then
    if [ "${st[0]}" -ne 0 ]; then die "op read が失敗しました"; fi
    die "op read の出力が PEM 形式ではありません。$SECRET は設定していません"
  fi
  [ "${st[0]}" -eq 0 ] || die "op read が失敗しました（$SECRET の値を確認してください）"
  [ "${st[1]}" -eq 0 ] || exit 2
  echo "  $SECRET を設定しました"

  [ -n "$bid" ] || echo "  注意: board.json に app_id がありません。追記してください（このスクリプトは書き換えません）"
done
