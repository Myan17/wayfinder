# Task log — myan-schema-v1

| Field | Value |
|---|---|
| Task | Schema v1: authorization facts, three identities, generations, tombstones (ORIENT item 2, DESIGN 9.2) |
| Module | schema |
| Branch | `myan/schema/v1` |
| Worktree | `../wayfinder-wt/myan-schema-v1` |
| Operator | myan |
| Agent | claude-code/opus-5 |
| Session | 2026-09-22T22:55Z/13716 |
| Started | 2026-09-22T22:55:17Z |
| Closed when | the last entry says TASK CLOSED (the header is never edited - this file is append-only) |

**Append-only.** Corrections are new entries. Entries are written by `scripts/log.sh` and the
`post-commit` hook; CI rejects a rewritten log (`scripts/check_agent_log.py`).

## Cards read

- (listed by `new-task.sh`; add any you read later as `READ` entries)

## Timeline

### 2026-09-22T22:55:17Z · READ · myan · claude-code/opus-5 · a45d283
schema card; indexing card (retrieval_rows columns, activation invariants); authz card + apps/api/wayfinder/authz/predicate.py (the row predicate reads row.live); DESIGN 9.2 (DDL, indexes), 9.3.5 (activation), 9.3.6 (GC order); REVIEW-CHECKLIST-SECURITY schema section.

### 2026-09-22T22:55:17Z · PLAN · myan · claude-code/opus-5 · a45d283
One dbmate migration, db/migrations/20260922230000_schema_v1.sql, reproducing DESIGN 9.2's DDL in dependency order, plus db/views/eligible_repo.sql and db/views/retrieval_rows.sql, plus the five tests the schema card names, run against the pinned ParadeDB digest from infra/spikes/s3. db/schema.sql (generated) goes in a separate pull request: AGENTS 2.2 says a large generated file gets its own. Conflicts found in the sources, each resolved one way and flagged for gupta958 rather than silently: (1) DESIGN gives vector_d768 ON DELETE CASCADE but the schema card forbids CASCADE on anything reachable from a generation, and 9.3.6's GC order has no vector step, so DESIGN's cascade is load-bearing; keep the cascade, add a composite (representation_id, repo_id) key so a vector row cannot bind to another repository's representation, and record the exception on the card. (2) DESIGN lists generation before embedding_spec though generation references it; reorder. (3) GC step 2 names code_edge, which is stretch and not created. (4) authz's predicate reads row.live but the indexing card's retrieval_rows column list has no live; the view exposes live (always true) so the predicate applies unchanged, which needs the indexing card's column list updated - declared as Scope: schema, indexing. Rejected: deferring views to a later PR - the predicate cannot be tested without them.

### 2026-09-22T22:59:04Z · EDIT · myan · claude-code/opus-5 · a45d283
db/migrations/20260922230000_schema_v1.sql: DESIGN 9.2 DDL in dependency order (embedding_spec before generation), platform_role folded into principal's CREATE, indexes, autovacuum_vacuum_scale_factor 0.02 on representation (9.3.5), both views, and a down section. Additions beyond 9.2's text, each flagged in the PR: composite (representation_id, repo_id) FK on vector_d768 (DESIGN had a single-column cascade), CHECK tombstone expires_at >= created_at + 90 days, CHECK on embedding_cache.data_class, retrieval_rows exposes live. db/views/*.sql: byte-identical copies. db/tests: conftest (fresh database per test from WAYFINDER_TEST_DSN; skips without it) and 12 tests. Cards: schema (status, cascade exception, tombstone invariant, test table, change log), indexing (retrieval_rows column list gains live); hashes recorded with --fix.

### 2026-09-22T22:59:04Z · TEST · myan · claude-code/opus-5 · a45d283
Against the S3 digest (paradedb 0.25.9, docker compose -p wf-schema -f infra/spikes/s3/compose.yml): uv run pytest db/tests -> 12 passed. First run found two real errors in the tests, not the schema: RESTRICT raises RestrictViolation, not ForeignKeyViolation; and the ParadeDB template database pre-installs postgis, whose tables and views survive the down section, so down is now checked against the relation set taken before up. Mutation checks, each restored after: occurrence RESTRICT removed -> test_gc_order_and_set_null fails; vector key made single-column -> test_cross_repo_vector_rejected fails; visibility lease dropped from eligible_repo -> test_eligible_repo_expiry and test_view_files_match_migration fail. uv run pytest (default testpaths) -> 81 passed; ruff clean on db/tests; context-freshness OK (6 interface files). Note: db/tests is not in pyproject testpaths and CI runs no database yet; wiring it is the pinned-extension integration harness in DESIGN 19.3, not this task.

### 2026-09-22T22:59:04Z · COMMIT · myan · claude-code/opus-5 · parent:a45d283
feat(schema): v1 — authorization facts, three identities, generations, tombstones
11 files changed, 676 insertions(+), 6 deletions(-)

### 2026-09-22T23:01:23Z · DECIDE · myan · claude-code/opus-5 · a45d283
The single commit above (never pushed) measured 648 changed lines against the 400 limit. Following gupta958's ruling on #20 (functional split, no exception), v1 is three migrations and three pull requests, each standing alone with its own tests: this one is part 1, 20260922230000_schema_v1_index (sources, embedding_spec, generations, content/representation/vector/occurrence, embedding_cache, tombstone, and the indexes); part 2, _principals (principal, session, grants, access state, connection_admin, answer and serving tables, webhook_delivery) with test_cached_from_set_null; part 3, _views (eligible_repo, retrieval_rows, db/views/*.sql, test_views, the indexing card's live column). Parts 2 and 3 each depend only on part 1. The earlier EDIT and TEST entries describe the combined work; they stay as written (append-only), and this entry supersedes them for what this branch contains. test_migrations now applies every migration up, all down in reverse, and up again.

### 2026-09-22T23:01:23Z · TEST · myan · claude-code/opus-5 · a45d283
Part 1 alone against the S3 digest: uv run pytest db/tests -> 8 passed (test_migrations x2, test_constraints x5, test_delete_modes x1). ruff clean on db/tests. The mutation results logged above for RESTRICT and the vector composite key apply to tests in this part, unchanged.

### 2026-09-22T23:01:23Z · COMMIT · myan · claude-code/opus-5 · parent:a45d283
feat(schema): v1 part 1 — sources, generations, three identities, tombstones
7 files changed, 440 insertions(+), 1 deletion(-)

### 2026-09-22T23:04:19Z · HANDOFF · myan · claude-code/opus-5 · eba70f4
#25 open (part 1). Parts 2 (#26) and 3 (#27) are stacked on this branch. When #25 squash-merges, rebuild each onto main with git rebase --onto origin/main <this branch's head> and force-push, as #21 was. Joint module: gupta958 rules on the five deviations in the PR body.

### 2026-09-22T23:04:19Z · COMMIT · myan · claude-code/opus-5 · parent:eba70f4
docs(schema): hand off #25
1 file changed, 3 insertions(+)

### 2026-09-23T02:33:56Z · DECIDE · myan · claude-code/opus-5 · 7ac0795
gupta958 requested changes (relayed by Myan, recorded on #25): make vector_d768.spec_id match its representation through a three-column composite FK, with a regression test; resolve the missing db/schema.sql snapshot commitment. Accepted as declared: the five DESIGN departures. With the fix the diff measured 429 lines. CI has no exception path and the #20 ruling was to split functionally, so embedding_cache and tombstone (GC steps 6 and 9, the deletion-support tables) and their test move to a new part 4 (_deletion), stacked on this branch like #26 and #27.

### 2026-09-23T02:33:56Z · EDIT · myan · claude-code/opus-5 · 7ac0795
Migration: representation gains UNIQUE (id, repo_id, spec_id); vector_d768's FK becomes (representation_id, repo_id, spec_id) -> representation (id, repo_id, spec_id) ON DELETE CASCADE; embedding_cache and tombstone removed (to part 4), down section adjusted; header says part 1 of 4. conftest: seed_spec takes a digest so a test can make two specs. test_constraints: test_vector_spec_must_match_representation added; the tombstone test moves to part 4. Schema card: db/schema.sql commitment rewritten - a pg_dump --schema-only snapshot from the pinned image, landing in its own pull request as soon as each migration pull request merges, with ORIENT item 3's CI adding a drift check; change protocol step 3 and the open question updated to match (the question is resolved: generated, diffed); status names four migrations; vector exception names the three-column key. Removed one trailing blank line and shortened my own new card prose to fit; no correctness comment was cut.

### 2026-09-23T02:33:56Z · TEST · myan · claude-code/opus-5 · 7ac0795
Against the S3 digest: uv run pytest db/tests -> 8 passed. Mutation: vector FK back to two columns -> test_vector_spec_must_match_representation fails; restored. ruff clean.

### 2026-09-23T02:33:56Z · COMMIT · myan · claude-code/opus-5 · parent:7ac0795
fix(schema): vector spec_id bound to its representation; schema.sql commitment; deletion tables to part 4
5 files changed, 47 insertions(+), 45 deletions(-)

### 2026-09-23T02:33:56Z · COMMIT · myan · claude-code/opus-5 · parent:7ac0795
fix(schema): vector spec_id bound to its representation; schema.sql commitment; deletion tables to part 4
5 files changed, 51 insertions(+), 45 deletions(-)

### 2026-09-23T02:36:00Z · HANDOFF · myan · claude-code/opus-5 · 208f710
#25 revised per review (400 lines); deletion tables moved to #28. Re-review requested. After merge, rebuild #26, #27, #28 onto main.

### 2026-09-23T02:36:00Z · COMMIT · myan · claude-code/opus-5 · parent:208f710
docs(schema): hand off after review
1 file changed, 3 insertions(+)

### 2026-09-23T03:05:04Z · DECIDE · myan · claude-code/opus-5 · 1a81e3d
#24 merged as 14c635f. Per gupta958: rebased onto origin/main, no conflicts; force-push over 0f657b4 required (AGENTS.md 2.2). ORIENT item 2 stays 'in review #25-#28': it is done only when the last of the four parts merges, and that pull request marks it.

### 2026-09-23T03:05:04Z · TEST · myan · claude-code/opus-5 · 1a81e3d
After the rebase, against the S3 digest: uv run pytest db/tests -> 8 passed; uv run pytest (default testpaths) -> 81 passed; ruff clean; identity, ownership, size (400), agent-log, CODEOWNERS and context-freshness all OK.

### 2026-09-23T03:05:04Z · COMMIT · myan · claude-code/opus-5 · parent:1a81e3d
docs(schema): record the rebase onto #24
1 file changed, 6 insertions(+)
