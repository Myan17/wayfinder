# Task log — myan-authz-row-predicate

| Field | Value |
|---|---|
| Task | Row predicate matching the documented contract, plus the violation counter |
| Module | authz |
| Branch | `myan/authz/row-predicate` |
| Worktree | `../wayfinder-wt/myan-authz-row-predicate` |
| Operator | myan |
| Agent | claude-code/opus-5 |
| Session | 2026-09-19T01:20Z/split-3 |
| Started | 2026-09-19T23:41:16Z |
| Status | open |

**Append-only.** Corrections are new entries. Entries are written by `scripts/log.sh` and the
`post-commit` hook; CI rejects a rewritten log (`scripts/check_agent_log.py`).

## Cards read

- (listed by `new-task.sh`; add any you read later as `READ` entries)

## Timeline

### 2026-09-19T23:41:16Z · PLAN · myan · claude-code/opus-5 · 1aa0743
Rewrite sql_predicate to the shape the card documents: the database decides public-ness through eligible_repo, and we bind only the granted ids. Rejected keeping the visible-set form: besides contradicting the card, it needs every visible repo id as a query parameter, which is a 10k-element array for a large public org.

### 2026-09-19T23:42:12Z · TEST · myan · claude-code/opus-5 · 1aa0743
uv run pytest apps/api/tests -q -> 22 passed (13 scope + 9 predicate incl. counter tests and the Hypothesis property). ruff clean.

### 2026-09-19T23:42:12Z · EDIT · myan · claude-code/opus-5 · 1aa0743
predicate.py rewritten to the card's contract; metrics.py adds authorization_violation_total; card updated to say what is landed and that metric export is not wired yet.

### 2026-09-19T23:42:13Z · COMMIT · myan · claude-code/opus-5 · parent:1aa0743
feat(authz): row predicate matching the card, plus a violation counter
6 files changed, 269 insertions(+), 8 deletions(-)

### 2026-09-21T01:26:50Z · EDIT · myan · claude-code/opus-5 · 8f9f972
Rebuilt on main after #7 merged, and force-pushed. The branch had been carrying scope, counters, interface and three other tasks' logs, all of which landed with #7; keeping them would have made the pull request claim credit for work already upstream and conflict on another task's log. This branch is now the predicate, its tests and the card edits that describe them.

### 2026-09-21T01:27:13Z · TEST · myan · claude-code/opus-5 · 1861a10
Caught an incomplete push: the rebuild's git show calls failed on shell expansion, so predicate.py and test_predicate.py were missing and the branch was only +51 lines. Recovered both from the previous tip; suite back to 26 tests.
