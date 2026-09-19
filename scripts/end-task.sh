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
  printf 'TASK CLOSED. '
  if [[ -n "$MERGED" ]]; then
    printf 'Merged as %s.\n' "$MERGED"
  else
    printf 'Pull request open for review.\n'
  fi
} >> "$LOG"

# The log is append-only (AGENTS.md 5.1), so closing a task appends an entry rather than editing the
# header. A task is closed when its last entry says so; the digest and the reviewer read entries.
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
