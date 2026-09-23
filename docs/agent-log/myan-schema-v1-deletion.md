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

### 2026-09-23T02:36:02Z · HANDOFF · myan · claude-code/opus-5 · c9740da
#28 open, stacked on #25, independent of #26/#27. Rebuild onto main after #25 merges.

### 2026-09-23T02:36:02Z · COMMIT · myan · claude-code/opus-5 · parent:c9740da
docs(schema): hand off after review
1 file changed, 3 insertions(+)

### 2026-09-23T04:29:56Z · DECIDE · myan · claude-code/opus-5 · b4ca447
#25 merged as 1b33b29 and GitHub retargeted #28 to main. Rebuilt with git rebase --onto origin/main 208f710, which drops part 1's pre-merge commits and replays only this part's. Force-push over c1b6b99 required (AGENTS.md 2.2).

### 2026-09-23T04:29:56Z · EDIT · myan · claude-code/opus-5 · b4ca447
ORIENT.md item 2: done #25-#28. This is the last of the four parts in the merge order given to gupta958 (#26, #27, #28), so it marks the item (ORIENT rule 3). If the order changes, the mark moves to whichever merges last.

### 2026-09-23T04:29:56Z · TEST · myan · claude-code/opus-5 · b4ca447
Rebuilt branch alone against main, S3 digest: db/tests 10 passed; full suite 81 passed; ruff clean; identity, ownership, size, agent-log, context-freshness and CODEOWNERS OK.

### 2026-09-23T04:29:56Z · COMMIT · myan · claude-code/opus-5 · parent:b4ca447
docs(schema): record the rebuild onto main
2 files changed, 10 insertions(+), 1 deletion(-)
