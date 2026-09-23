# Task log — myan-schema-v1-deletion

| Field | Value |
|---|---|
| Task | Schema v1 part 4: embedding_cache and tombstone, the deletion-support tables (ORIENT item 2) |
| Module | schema |
| Branch | `myan/schema/v1-deletion` |
| Worktree | `../wayfinder-wt/myan-schema-v1-deletion` |
| Operator | myan |
| Agent | claude-code/opus-5 |
| Session | 2026-09-23T02:34Z/19584 |
| Started | 2026-09-23T02:34:07Z |
| Closed when | the last entry says TASK CLOSED (the header is never edited - this file is append-only) |

**Append-only.** Corrections are new entries. Entries are written by `scripts/log.sh` and the
`post-commit` hook; CI rejects a rewritten log (`scripts/check_agent_log.py`).

## Cards read

- (listed by `new-task.sh`; add any you read later as `READ` entries)

## Timeline

### 2026-09-23T02:34:22Z · PLAN · myan · claude-code/opus-5 · 208f710
Part 4 of schema v1, stacked on myan/schema/v1 (#25), independent of #26 and #27. Split out of #25 when gupta958's requested fix took it to 429 lines. Migration 20260922230300_schema_v1_deletion: embedding_cache (CHECK on data_class, which GC step 6 branches on) and tombstone (CHECK retention >= 90 days, GC step 9), exactly as they were in #25 and already accepted there as departures 3 and 4. Test: test_deletion.py::test_tombstone_retained_at_least_90_days, plus one for the data_class check.

### 2026-09-23T02:34:35Z · TEST · myan · claude-code/opus-5 · 208f710
Against the S3 digest with part 1 applied: uv run pytest db/tests -> 10 passed (part 1's 8 + 2). Mutation: retention CHECK weakened to expires_at >= created_at -> test_tombstone_retained_at_least_90_days fails; restored. ruff clean.

### 2026-09-23T02:34:35Z · COMMIT · myan · claude-code/opus-5 · parent:208f710
feat(schema): v1 part 4 — embedding_cache and tombstone
4 files changed, 78 insertions(+)
