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

### 2026-09-21T05:18:14Z · PLAN · myan · claude-code/opus-5 · adb41cd
Reviewer found three false claims on the card; two are code defects, not wording. (1) sql_predicate's now is optional, so omitting it lets an expired scope emit a permissive fragment - fail-open in the authorization path. Defaulting now to the real clock. (2) FixtureAuthz drops anonymous grants silently, so the kernel guard the card credits is never reached through the fake; removing the drop so the fake behaves like a wrong resolver would and the kernel raises. (3) db/views/eligible_repo.sql is listed as an interface file and does not exist. Tests first for both code changes.

### 2026-09-21T05:19:30Z · TEST · myan · claude-code/opus-5 · adb41cd
uv run pytest apps/api/tests -q -> 38 passed. Two of the three findings were code defects and both now have regression tests: sql_predicate with now omitted on a scope expired against the REAL clock returns 'false'; FixtureAuthz passing anonymous grants through raises AnonymousGrantsError. ruff check and format clean on the files this branch touches.

### 2026-09-21T05:19:30Z · DECIDE · myan · claude-code/opus-5 · adb41cd
The first version of the expiry regression test passed a scope expired only against the module's frozen NOW (12:00 UTC) while the real clock read 09:40 UTC, so it did not exercise the default at all. Rewrote it with a lease in the real past - a test for a wall-clock default cannot use a frozen constant.

### 2026-09-21T05:19:30Z · COMMIT · myan · claude-code/opus-5 · parent:adb41cd
fix(authz): close a fail-open default, stop the fake masking the kernel, correct the card
6 files changed, 66 insertions(+), 14 deletions(-)

### 2026-09-21T05:32:05Z · TEST · myan · claude-code/opus-5 · 8d73564
Audited every count the card asserts against the tree: 'pinned by 36 tests' was stale (pytest collects 38 - 37 def test_ lines, one parametrized with two cases), and test_fake_matches_contract.py said 5 where it now has 6. Both corrected; test_metrics.py's 3 was right.

### 2026-09-21T05:32:05Z · COMMIT · myan · claude-code/opus-5 · parent:8d73564
docs(authz): correct two stale test counts on the card
2 files changed, 5 insertions(+), 2 deletions(-)

### 2026-09-21T05:33:07Z · TEST · myan · claude-code/opus-5 · e6e27c3
Second pass on the counts: the first attempt wrote an empty number because the shell parse of pytest's output failed and nothing checked the result. Count now taken from --collect-only and asserted to be a positive integer before it is written.
