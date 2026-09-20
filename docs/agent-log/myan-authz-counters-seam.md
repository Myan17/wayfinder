# Task log — myan-authz-counters-seam

| Field | Value |
|---|---|
| Task | Unsampled counters for authorization denials and defects |
| Module | authz |
| Branch | `myan/authz/counters-seam` |
| Worktree | `../wayfinder-wt/myan-authz-counters-seam` |
| Operator | myan |
| Agent | claude-code/opus-5 |
| Session | 2026-09-19T02:50Z/counters |
| Started | 2026-09-20T00:10:39Z |
| Status | open |

**Append-only.** Corrections are new entries. Entries are written by `scripts/log.sh` and the
`post-commit` hook; CI rejects a rewritten log (`scripts/check_agent_log.py`).

## Cards read

- (listed by `new-task.sh`; add any you read later as `READ` entries)

## Timeline

### 2026-09-20T00:10:39Z · PLAN · myan · claude-code/opus-5 · af0f734
Counters get their own pull request so neither the scope nor the predicate PR crosses the 400-line limit, and because both need them. Reviewer asked for a counter on the anonymous-grant defect without replacing the exception.

### 2026-09-20T00:10:41Z · TEST · myan · claude-code/opus-5 · af0f734
uv run pytest apps/api/tests -q -> 3 passed (counter semantics). ruff clean.

### 2026-09-20T00:10:41Z · COMMIT · myan · claude-code/opus-5 · parent:af0f734
feat(authz): counters that survive sampling
3 files changed, 114 insertions(+)
