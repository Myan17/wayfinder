# Task log — myan-retrieval-hybrid-sql

| Field | Value |
|---|---|
| Task | ADR-0007 Amendment 1 step 3: the canonical two-leg query, hybrid_sql.py, with result, authorization and determinism tests and no plan harness (ORIENT item 9c) |
| Module | retrieval |
| Branch | `myan/retrieval/hybrid-sql` |
| Worktree | `../wayfinder-wt/myan-retrieval-hybrid-sql` |
| Operator | myan |
| Agent | claude-code/opus-5.5 |
| Session | 2026-10-20T01:17Z/11449 |
| Started | 2026-10-20T01:17:44Z |
| Closed when | the last entry says TASK CLOSED (the header is never edited - this file is append-only) |

**Append-only.** Corrections are new entries. Entries are written by `scripts/log.sh` and the
`post-commit` hook; CI rejects a rewritten log (`scripts/check_agent_log.py`).

## Cards read

- (listed by `new-task.sh`; add any you read later as `READ` entries)

## Timeline

### 2026-10-20T01:17:45Z · READ · myan · claude-code/opus-5.5 · b4835f2
ADR-0007 Amendment 1 (merged #86, schema #87): query location and shape (six-field paradedb.match in paradedb.boolean should; one dense leg per spec with parameterized spec_id, SET LOCAL hnsw.iterative_scan = relaxed_order; sql_predicate on each scanned alias joined to eligible_repo; RRF k = 60; retrieval_rows for location; per-file cap 3), tie keys (lexical score desc, repo_id, path, id; dense exact distance asc, repo_id, path, id; final fused desc, repo_id, path, start_line, representation_id), and step 3: this PR has no plan harness, no EXPLAIN and no plan evidence. Indexing card's documented query shape; retrieval card invariants; authz sql_predicate and assert_rows_authorized.

### 2026-10-20T01:17:45Z · PLAN · myan · claude-code/opus-5.5 · b4835f2
apps/api/wayfinder/retrieval/hybrid_sql.py: build(query_text, query_vectors by spec_id, scope, k) returns SQL and parameters built with sql_predicate per leg; execute(conn, query, scope) runs it in a transaction after SET LOCAL hnsw.iterative_scan = relaxed_order and asserts every row with assert_rows_authorized. Tests in apps/api/tests/retrieval against the pinned database, reusing db/tests' fixtures: authorization (ungranted private, verified public, expired scope, not live, retired generation), results (RRF arithmetic, both legs present, multi-spec), determinism (tied scores and tied vectors, insertion order shuffled), per-file cap, query text with query-grammar characters, no user value in the SQL text. Run by make db-test so CI's pinned job executes them. No EXPLAIN anywhere: plans are step 4. Rejected: a stored SQL function, since behaviour stays in code tests can reach (schema card).

### 2026-10-20T01:26:52Z · EDIT · myan · claude-code/opus-5.5 · b4835f2
apps/api/wayfinder/retrieval/hybrid_sql.py: build() returns the one statement (lexical leg over the six rep_bm25 fields with paradedb.match in paradedb.boolean should, cut and ranked by (score desc, repo_id, path, id); one dense leg per spec_id in sorted order, index-order cut, ranked by (exact distance, repo_id, path, id); sql_predicate on each scanned alias joined to its own eligible_repo; RRF k=60 with lexical and dense ranks; retrieval_rows for location; per-file cap 3; final (fused desc, repo_id, path, start_line, representation_id)); every caller value bound. execute() runs it in a transaction after SET LOCAL hnsw.iterative_scan = relaxed_order and asserts rows with assert_rows_authorized. Tests in apps/api/tests/retrieval (16) on the schema module's db fixture, with a reachability skip for CI's unit job; make db-test now runs them. Retrieval card: tests row and change-log.

### 2026-10-20T01:26:52Z · TEST · myan · claude-code/opus-5.5 · b4835f2
make db-test -> 95 passed (db 79, retrieval 16); make test -> 394 passed; with an unreachable DSN (CI unit job's situation) -> 380 passed, 14 skipped; ruff clean. No EXPLAIN anywhere (Amendment 1 step 3). Mutants on hybrid_sql.py, each killed: lexical predicate off (2 failed), dense predicate off (2), lexical rank tie key (1), lexical cut tie key (1, after adding the 102-row cut test), dense tie key (1), file cap off (1), RRF constant (1), no active-generation join (1), final order by id desc and by id asc (1 each, after parametrizing insertion order), assertion removed (1), SET LOCAL removed (1, spy test), path fields dropped (1, path-only test). Test fixes on the way: generation commit_sha collided on the unique key; the no-caller-value test matched RRF's 1.0 literal; 'widget_parser.py' legitimately matched other.py through path_code's 'py'.

### 2026-10-20T01:26:52Z · COMMIT · myan · claude-code/opus-5.5 · parent:b4835f2
feat(retrieval): the canonical two-leg query, hybrid_sql.py, with result, authorization and determinism tests (ADR-0007 Amendment 1 step 3)
7 files changed, 474 insertions(+), 2 deletions(-)

### 2026-10-20T01:26:52Z · HANDOFF · myan · claude-code/opus-5.5 · 3e4ffe5
PR for gupta958. After merge the query is frozen for S3-6: next is the plan harness and its mutation tests in a separate PR that may not touch hybrid_sql.py (step 4), then the evidence run (step 5).

### 2026-10-20T01:26:52Z · COMMIT · myan · claude-code/opus-5.5 · parent:3e4ffe5
docs(agents): hand hybrid_sql.py to gupta958
1 file changed, 3 insertions(+)

### 2026-10-20T01:28:50Z · DECIDE · myan · claude-code/opus-5.5 · 3e84702
check_pr_size failed at 442 counted lines, so step 3 splits by function before any push: this PR (3a) keeps hybrid_sql.py, the authorization and result tests, the shared test helpers (moved into the retrieval tests' conftest) and make db-test; a stacked PR (3b) adds the four ordering tests (tie keys, the lexical cut, equal fused scores, the per-file cap). Neither has a plan harness. The query is frozen when 3a merges; a bug 3b found before step 4 would still be fixed before any plan is seen. Scope widened to platform for the Makefile line and its card.

### 2026-10-20T01:28:50Z · TEST · myan · claude-code/opus-5.5 · 3e84702
After the split: make db-test -> 90 passed (retrieval 11); make test -> 389 passed; unreachable DSN -> 380 passed, 9 skipped; ruff clean. The four moved tests pass unchanged in the stacked branch.

### 2026-10-20T01:28:50Z · COMMIT · myan · claude-code/opus-5.5 · parent:3e84702
refactor(retrieval): split the ordering tests into their own pull request; shared helpers in conftest
5 files changed, 100 insertions(+), 152 deletions(-)
