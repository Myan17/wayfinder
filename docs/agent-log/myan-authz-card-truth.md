# Task log — myan-authz-card-truth

| Field | Value |
|---|---|
| Task | Make the authz card describe what actually landed |
| Module | authz |
| Branch | `myan/authz/card-truth` |
| Worktree | `../wayfinder-wt/myan-authz-card-truth` |
| Operator | myan |
| Agent | claude-code/opus-5 |
| Session | 2026-09-20T08:00Z/card-truth |
| Started | 2026-09-21T04:43:51Z |
| Closed when | the last entry says TASK CLOSED (the header is never edited - this file is append-only) |

**Append-only.** Corrections are new entries. Entries are written by `scripts/log.sh` and the
`post-commit` hook; CI rejects a rewritten log (`scripts/check_agent_log.py`).

## Cards read

- (listed by `new-task.sh`; add any you read later as `READ` entries)

## Timeline

### 2026-09-21T04:43:51Z · PLAN · myan · claude-code/opus-5 · 2b75424
Card on main drifted during the stack rebuilds: it still opens with the pre-implementation blockquote, names three test files that do not exist, and points at a fixture yaml that was never created. Rewriting the status, the test table and the fake section against what is actually in the tree. Rejected adding the missing tests to match the card: the card should describe reality, and those tests need the database layer that does not exist yet.

### 2026-09-21T04:44:53Z · EDIT · myan · claude-code/opus-5 · 2b75424
authz card: status rewritten to what is on main, NOT YET IMPLEMENTED markers on the three unbuilt entry points, test table replaced with the 14 real test names (plus the three suites that need the DB layer, listed as not yet written), fake section corrected - FixtureAuthz is built in code, and the YAML fixture from DESIGN 14.4 does not exist.

### 2026-09-21T04:44:53Z · TEST · myan · claude-code/opus-5 · 2b75424
grep of def test_ across apps/api/tests/authz -> 36 tests in 5 files; every name in the card's table now appears in that list.

### 2026-09-21T04:44:53Z · COMMIT · myan · claude-code/opus-5 · parent:2b75424
docs(authz): make the card describe what actually landed
2 files changed, 76 insertions(+), 13 deletions(-)
