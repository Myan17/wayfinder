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

### 2026-09-23T04:31:18Z · TEST · myan · claude-code/opus-5 · 6337246
CI guardrails failed on 6337246: 'ORIENT.md - module agreements, not this task's scope (schema)'. The push ran before the 'Scope: schema, agreements' line was added to the PR body; guardrails runs on opened/synchronize/reopened only, and a rerun reuses the original event's body, so the rerun failed identically. This commit is the new synchronize event that makes CI read the current body. Locally, check_ownership with the current body: OK, 5 files.

### 2026-09-23T04:31:18Z · COMMIT · myan · claude-code/opus-5 · parent:6337246
docs(schema): record why guardrails needed a fresh run
1 file changed, 3 insertions(+)

### 2026-09-23T05:07:26Z · DECIDE · myan · claude-code/opus-5 · fbcfa02
#27 merged as a6cae0e, putting this branch BEHIND. Rebased onto origin/main; one conflict in the schema card's change log (parts 2 and 3 rows on main, this part's row), resolved by keeping all three. Force-push over 7e144a7 required (AGENTS.md 2.2).

### 2026-09-23T05:07:26Z · EDIT · myan · claude-code/opus-5 · fbcfa02
db/tests/test_views.py::test_view_files_match_migration, merged in #27, compared db/views/*.sql against MIGRATIONS[-1] - the newest migration - which was the views migration only until this part added a later one; with all four parts it failed with IndexError. It now locates the one migration that defines each view (and asserts there is exactly one), so a later migration cannot break it without touching a view. Same module (schema), so no scope widening.

### 2026-09-23T05:07:26Z · TEST · myan · claude-code/opus-5 · fbcfa02
Against main with parts 1-3 merged, S3 digest: before the fix db/tests 14 passed, 1 failed (test_view_files_match_migration, IndexError); after the fix 15 passed (8 + 2 + 3 + this part's 2). Mutation: eligible_repo.sql edited to drift from its migration -> test_view_files_match_migration fails; restored. Full suite 81; ruff clean; identity, ownership (Scope: schema, agreements), size, agent-log, context-freshness, CODEOWNERS OK.

### 2026-09-23T05:07:26Z · COMMIT · myan · claude-code/opus-5 · parent:fbcfa02
fix(schema): the view-file test finds its defining migration, not the newest
2 files changed, 14 insertions(+), 1 deletion(-)

### 2026-09-23T05:15:37Z · DECIDE · myan · claude-code/opus-5 · e3cb56a
gupta958 (relayed by Myan, recorded on #28): item 2 is not done until the db/schema.sql snapshot the schema card commits to exists. ORIENT item 2 now reads 'in review #25-#28; db/schema.sql pending'; this pull request no longer claims to complete the item. After #28 merges, the generated snapshot pull request opens immediately and marks item 2 done #25-#29.

### 2026-09-23T05:15:37Z · EDIT · myan · claude-code/opus-5 · e3cb56a
ORIENT.md item 2 status: done #25-#28 -> in review #25-#28; db/schema.sql pending. Scope: schema, agreements still applies to this one line.

### 2026-09-23T05:15:37Z · COMMIT · myan · claude-code/opus-5 · parent:e3cb56a
docs(schema): item 2 stays open until db/schema.sql lands, per review
2 files changed, 7 insertions(+), 1 deletion(-)
