# Task log — myan-schema-v1-views

| Field | Value |
|---|---|
| Task | Schema v1 part 3: eligible_repo and retrieval_rows views (ORIENT item 2) |
| Module | schema |
| Branch | `myan/schema/v1-views` |
| Worktree | `../wayfinder-wt/myan-schema-v1-views` |
| Operator | myan |
| Agent | claude-code/opus-5 |
| Session | 2026-09-22T23:01Z/14893 |
| Started | 2026-09-22T23:02:00Z |
| Closed when | the last entry says TASK CLOSED (the header is never edited - this file is append-only) |

**Append-only.** Corrections are new entries. Entries are written by `scripts/log.sh` and the
`post-commit` hook; CI rejects a rewritten log (`scripts/check_agent_log.py`).

## Cards read

- (listed by `new-task.sh`; add any you read later as `READ` entries)

## Timeline

### 2026-09-22T23:03:03Z · PLAN · myan · claude-code/opus-5 · eba70f4
Part 3 of schema v1, stacked on myan/schema/v1 (#25), independent of part 2. Migration 20260922230200_schema_v1_views creates eligible_repo (DESIGN 9.2 verbatim) and retrieval_rows (the indexing card's column list, plus live so authz's row predicate applies unchanged). db/views/*.sql are byte-identical copies, checked by a test. Cross-module: the indexing card's retrieval_rows column list gains live; declared as Scope: schema, indexing in the pull request.

### 2026-09-22T23:03:50Z · TEST · myan · claude-code/opus-5 · eba70f4
Against the S3 digest with part 1 applied: uv run pytest db/tests -> 11 passed. Mutations, restored after each: visibility lease removed from eligible_repo (migration and file) -> test_eligible_repo_expiry fails. Active-generation join removed from retrieval_rows -> first version of the test still PASSED, because its stale row was also live=false and the WHERE hid it. Strengthened the test: the live representation now also occurs in the retired generation at another path, which only the join excludes; the mutation now fails the test. ruff clean; context-freshness OK after recording the view hashes on the schema and indexing cards.

### 2026-09-22T23:03:50Z · COMMIT · myan · claude-code/opus-5 · parent:eba70f4
feat(schema): v1 part 3 — eligible_repo and retrieval_rows views
7 files changed, 160 insertions(+), 5 deletions(-)
