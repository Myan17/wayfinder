# Task log — myan-agreements-line-limit-exception

| Field | Value |
|---|---|
| Task | Record the task-log exception to the 400-line limit and make the limit enforceable |
| Module | agreements |
| Branch | `myan/agreements/line-limit-exception` |
| Worktree | `../wayfinder-wt/myan-agreements-line-limit-exception` |
| Operator | myan |
| Agent | claude-code/opus-5 |
| Session | 2026-09-20T04:45Z/agreements |
| Started | 2026-09-20T16:15:49Z |
| Closed when | the last entry says TASK CLOSED (the header is never edited - this file is append-only) |

**Append-only.** Corrections are new entries. Entries are written by `scripts/log.sh` and the
`post-commit` hook; CI rejects a rewritten log (`scripts/check_agent_log.py`).

## Cards read

- (listed by `new-task.sh`; add any you read later as `READ` entries)

## Timeline

### 2026-09-20T16:15:49Z · PLAN · myan · claude-code/opus-5 · cc0efbd
Record the reviewer's agreed exception in AGENTS.md and the working agreement, and add a check that enforces the limit. Rejected documenting it alone: an unenforced rule is the same defect the reviewer raised against a counter that was claimed but never incremented.

### 2026-09-20T16:16:39Z · TEST · myan · claude-code/opus-5 · cc0efbd
Check exercised both ways before asking anyone to rely on it: passes on this branch's own diff, and fails with a per-file breakdown when run with --limit 20.

### 2026-09-20T16:16:39Z · COMMIT · myan · claude-code/opus-5 · parent:cc0efbd
docs(agreements): exclude the task log from the line limit, and enforce the limit
5 files changed, 117 insertions(+), 4 deletions(-)

### 2026-09-21T01:35:36Z · DECIDE · myan · claude-code/opus-5 · 3e2e898
Added an explicit base-ref fetch to the workflow. #6 failed with '1 COMMIT entry for 3 commits' on a range that is one commit locally: the runner's copy of the force-pushed base branch was stale, so merge-base landed two commits too early. Fixing the ref rather than loosening the log rule, which was reporting exactly what it saw.

### 2026-09-21T01:35:36Z · COMMIT · myan · claude-code/opus-5 · parent:3e2e898
fix(platform): fetch the base ref before computing the range
2 files changed, 8 insertions(+)

### 2026-09-21T01:44:22Z · EDIT · myan · claude-code/opus-5 · fc018c3
Rebased onto main and force-pushed: branch protection requires branches to be up to date, and main advanced when #7 merged, so GitHub reported the approved pull request as BEHIND and disabled its merge button.

### 2026-09-21T01:44:22Z · COMMIT · myan · claude-code/opus-5 · parent:fc018c3
docs(agreements): record the rebase onto main
1 file changed, 3 insertions(+)

### 2026-09-21T01:54:25Z · EDIT · myan · claude-code/opus-5 · 2827586
Rebased onto main after #5 merged and force-pushed; branch protection requires branches to be up to date.

### 2026-09-21T01:55:36Z · COMMIT · myan · claude-code/opus-5 · parent:2827586
docs(agreements): record the rebase onto main after #5 merged
1 file changed, 3 insertions(+)
