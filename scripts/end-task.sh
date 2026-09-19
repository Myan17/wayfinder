#!/usr/bin/env bash
# Close a task: final log entry, remove the worktree, leave the branch to be merged by the reviewer.
# usage: scripts/end-task.sh [--merged <sha>]
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
source scripts/lib.sh

BRANCH="$(git rev-parse --abbrev-ref HEAD)"
TASK="$(echo "$BRANCH" | tr '/' '-')"
LOG="$(log_path "$TASK")"
[[ -f "$LOG" ]] || die "no log at $LOG"

MERGED=""
[[ "${1:-}" == "--merged" ]] && MERGED="${2:-}"

{
  printf '\n### %s · HANDOFF · %s · %s · %s\n' "$(now_utc)" "$(operator)" "$(agent)" "$(git rev-parse --short HEAD)"
  if [[ -n "$MERGED" ]]; then
    printf 'Task closed; merged as %s.\n' "$MERGED"
  else
    printf 'Task closed locally; pull request open for review.\n'
  fi
} >> "$LOG"

python3 - "$LOG" <<'PY'
import pathlib, sys
p = pathlib.Path(sys.argv[1]); t = p.read_text()
p.write_text(t.replace("| Status | open |", "| Status | closed |", 1))
PY

git add "$LOG"
git commit -m "docs(agents): close task log for $TASK" --quiet || true

WT="../wayfinder-wt/$TASK"
cat <<EOF
Log closed: $LOG
Push the branch, then let the reviewer merge (squash).
When the pull request is merged, remove the worktree from the main clone:
  git worktree remove $WT
  git branch -d $BRANCH
EOF
