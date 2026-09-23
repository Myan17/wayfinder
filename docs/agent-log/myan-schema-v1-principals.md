# Task log — myan-schema-v1-principals

| Field | Value |
|---|---|
| Task | Schema v1 part 2: principals, authorization facts, serving artifacts (ORIENT item 2) |
| Module | schema |
| Branch | `myan/schema/v1-principals` |
| Worktree | `../wayfinder-wt/myan-schema-v1-principals` |
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

### 2026-09-22T23:02:15Z · PLAN · myan · claude-code/opus-5 · eba70f4
Part 2 of schema v1, stacked on myan/schema/v1 (#25); the pull request targets that branch so the guardrails measure only this part. Migration 20260922230100_schema_v1_principals: DESIGN 9.2's principals and authorization section (principal with platform_role folded into its CREATE, session, user_repo_access, user_access_state, connection_admin) and serving artifacts (answer, answer_trace, answer_cache, feedback, audit_event, webhook_delivery), exactly as 9.2 gives them, with a tested down. Test: test_serving.py::test_cached_from_set_null (9.3.6 step 3). The DESIGN cascades from answer to answer_trace and feedback are kept as written and named on the card.

### 2026-09-22T23:02:36Z · TEST · myan · claude-code/opus-5 · eba70f4
Against the S3 digest with part 1 applied first: uv run pytest db/tests -> 10 passed (part 1's 8, plus test_cached_from_set_null and test_answer_needs_a_principal); test_migrations now also cycles this migration's down. Mutation: cached_from made NO ACTION -> test_cached_from_set_null fails; restored. ruff clean.

### 2026-09-22T23:02:36Z · COMMIT · myan · claude-code/opus-5 · parent:eba70f4
feat(schema): v1 part 2 — principals, authorization facts, serving artifacts
4 files changed, 150 insertions(+)

### 2026-09-22T23:04:23Z · HANDOFF · myan · claude-code/opus-5 · def41f1
#26 open, based on myan/schema/v1 (#25). Needs a rebuild onto main after #25 merges.

### 2026-09-22T23:04:24Z · COMMIT · myan · claude-code/opus-5 · parent:def41f1
docs(schema): hand off #26
1 file changed, 3 insertions(+)

### 2026-09-23T04:29:52Z · DECIDE · myan · claude-code/opus-5 · d1e570a
#25 merged as 1b33b29 and GitHub retargeted #26 to main. Rebuilt with git rebase --onto origin/main eba70f4, which drops part 1's pre-merge commits and replays only this part's. Resolved one conflict in the schema card: main's part-1 lines (three-column vector key, its change-log row) were kept, and only this part's own lines were re-added; the stale two-column sentence and the moved tombstone change-log row were dropped. Force-push over 064ff7d required (AGENTS.md 2.2).

### 2026-09-23T04:29:52Z · TEST · myan · claude-code/opus-5 · d1e570a
Rebuilt branch alone against main, S3 digest: db/tests 10 passed; full suite 81 passed; ruff clean; identity, ownership, size, agent-log, context-freshness and CODEOWNERS OK.

### 2026-09-23T04:29:52Z · COMMIT · myan · claude-code/opus-5 · parent:d1e570a
docs(schema): record the rebuild onto main
1 file changed, 6 insertions(+)

### 2026-09-23T04:44:34Z · DECIDE · myan · claude-code/opus-5 · 0ab788f
gupta958 (relayed by Myan, recorded on #26): implementation passes and the answer_trace/feedback cascade exception is accepted; fix two stale references - migration line 1 'part 2 of 3', and the PR description's 'part 2 of 3' and 'Closes ... with #25 and part 3'.

### 2026-09-23T04:44:34Z · EDIT · myan · claude-code/opus-5 · 0ab788f
Migration header: part 2 of 4. The migration is unmerged, so editing it does not break immutability (DESIGN 18.3 applies once merged). PR title and description updated to four parts, closing with #25, #27 and #28.

### 2026-09-23T04:44:36Z · COMMIT · myan · claude-code/opus-5 · parent:0ab788f
docs(schema): part 2 of 4, per review
2 files changed, 7 insertions(+), 1 deletion(-)
