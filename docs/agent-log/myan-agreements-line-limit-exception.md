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
