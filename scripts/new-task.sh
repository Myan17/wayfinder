#!/usr/bin/env bash
# Start a task: check ownership, create branch + worktree + log, print required reading.
# usage: scripts/new-task.sh <module> <slug> "<task description>"
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
source scripts/lib.sh

[[ $# -ge 3 ]] || die "usage: scripts/new-task.sh <module> <slug> \"<task description>\""
MODULE="$1"; SLUG="$2"; shift 2; DESC="$*"
OP="$(operator)"; AGENT="$(agent)"; SESSION="$(session)"

OWNER="$(module_owner "$MODULE")"
[[ "$OWNER" != "unknown" ]] || die "module '$MODULE' is not in docs/team/OWNERSHIP.md"
if [[ "$OWNER" != "$OP" && "$OWNER" != "joint" ]]; then
  die "module '$MODULE' is owned by '$OWNER', not '$OP'.
Open a Boundary Change Request instead: cp docs/context/boundary/TEMPLATE-BCR.md docs/context/boundary/BCR-<n>-<slug>.md"
fi
[[ "$OWNER" != "joint" ]] && JOINT_NOTE="" || JOINT_NOTE="
NOTE: '$MODULE' is JOINT. Both owners must approve this pull request."

BRANCH="$OP/$MODULE/$SLUG"
TASK="$OP-$MODULE-$SLUG"
WT="../wayfinder-wt/$TASK"
LOG="$(log_path "$TASK")"

git show-ref --verify --quiet "refs/heads/$BRANCH" && die "branch $BRANCH already exists"

# Branch from origin/main when there is a remote, from local main before the repository is pushed.
if git remote get-url origin >/dev/null 2>&1; then
  git fetch origin main --quiet
  BASE="origin/main"
else
  BASE="main"
  echo "note: no 'origin' remote yet — branching from local main" >&2
fi
git worktree add -b "$BRANCH" "$WT" "$BASE"

# Create the log in the worktree so the first commit carries it.
mkdir -p "$WT/docs/agent-log"
sed -e "s|<TASK>|$TASK|g" -e "s|<DESC>|$DESC|g" -e "s|<BRANCH>|$BRANCH|g" \
    -e "s|<WORKTREE>|$WT|g" -e "s|<OPERATOR>|$OP|g" -e "s|<AGENT>|$AGENT|g" \
    -e "s|<SESSION>|$SESSION|g" -e "s|<MODULE>|$MODULE|g" -e "s|<STARTED>|$(now_utc)|g" \
    docs/agent-log/TEMPLATE.md > "$WT/$LOG"

# Required reading: this module's card plus the cards of everything it depends on.
CARD="docs/context/modules/$MODULE.md"
DEPS="$(python3 - "$CARD" <<'PY'
import re, sys, pathlib
p = pathlib.Path(sys.argv[1])
if not p.exists(): sys.exit(0)
fm = re.search(r"^---\n(.*?)\n---", p.read_text(), re.S)
if not fm: sys.exit(0)
dep = re.search(r"depends_on:\n((?:\s*-\s*.+\n)+)", fm.group(1))
if dep:
    for line in dep.group(1).strip().splitlines():
        name = line.split("#", 1)[0].strip().lstrip("-").strip()
        if name:
            print(name)
PY
)"

cat <<EOF

Task ready.
  branch    $BRANCH
  worktree  $WT
  log       $LOG
  operator  $OP   agent  $AGENT   session  $SESSION$JOINT_NOTE

Required reading before your first edit:
  - AGENTS.md (§3 context protocol, §5 logging)
  - $CARD
EOF
while IFS= read -r d; do
  [[ -n "$d" ]] && echo "  - docs/context/modules/$d.md   (dependency: read the card, not the code)"
done <<< "$DEPS"
cat <<EOF

Then:
  cd $WT
  scripts/log.sh PLAN "<approach, and the alternative you rejected>"

EOF
