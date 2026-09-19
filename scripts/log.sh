#!/usr/bin/env bash
# Append an entry to the current task log.
# usage: scripts/log.sh <TYPE> "<body>"        TYPE: READ|PLAN|EDIT|TEST|DECIDE|BLOCKED|HANDOFF|COMMIT
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
source scripts/lib.sh

[[ $# -ge 2 ]] || die "usage: scripts/log.sh <TYPE> \"<body>\"  (TYPE: READ PLAN EDIT TEST DECIDE BLOCKED HANDOFF COMMIT)"
TYPE="$(echo "$1" | tr '[:lower:]' '[:upper:]')"; shift; BODY="$*"
case "$TYPE" in READ|PLAN|EDIT|TEST|DECIDE|BLOCKED|HANDOFF|COMMIT) ;; *) die "unknown entry type '$TYPE'";; esac

BRANCH="$(git rev-parse --abbrev-ref HEAD)"
TASK="$(echo "$BRANCH" | tr '/' '-')"
LOG="$(log_path "$TASK")"
[[ -f "$LOG" ]] || die "no log at $LOG — start work with scripts/new-task.sh (branch '$BRANCH' looks unmanaged)"

SHA="$(git rev-parse --short HEAD 2>/dev/null || echo 0000000)"
{
  printf '\n### %s · %s · %s · %s · %s\n' "$(now_utc)" "$TYPE" "$(operator)" "$(agent)" "$SHA"
  printf '%s\n' "$BODY"
} >> "$LOG"

echo "logged $TYPE → $LOG"
