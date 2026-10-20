# Task log — myan-retrieval-hybrid-sql-order

| Field | Value |
|---|---|
| Task | ADR-0007 Amendment 1 step 3b: the canonical query's ordering tests, stacked on hybrid_sql.py (ORIENT item 9c) |
| Module | retrieval |
| Branch | `myan/retrieval/hybrid-sql-order` |
| Worktree | `../wayfinder-wt/myan-retrieval-hybrid-sql-order` |
| Operator | myan |
| Agent | claude-code/opus-5.5 |
| Session | 2026-10-20T01:29Z/22749 |
| Started | 2026-10-20T01:29:06Z |
| Closed when | the last entry says TASK CLOSED (the header is never edited - this file is append-only) |

**Append-only.** Corrections are new entries. Entries are written by `scripts/log.sh` and the
`post-commit` hook; CI rejects a rewritten log (`scripts/check_agent_log.py`).

## Cards read

- (listed by `new-task.sh`; add any you read later as `READ` entries)

## Timeline

### 2026-10-20T01:30:09Z · PLAN · myan · claude-code/opus-5.5 · 6c140c1
Step 3b, stacked on myan/retrieval/hybrid-sql (3a): the four ordering tests split from 3a for size, in test_hybrid_sql_order.py using 3a's conftest helpers. No change to hybrid_sql.py and no plan harness.

### 2026-10-20T01:30:09Z · TEST · myan · claude-code/opus-5.5 · 6c140c1
pytest apps/api/tests/retrieval on the pinned database -> 16 passed (order file 5). Mutants on hybrid_sql.py against the order file alone, each killed: lexical rank tie key (2 failed), lexical cut tie key (1), dense tie key (1), file cap off (1), final order by id desc (1) and by id asc (1). ruff clean.

### 2026-10-20T01:30:09Z · COMMIT · myan · claude-code/opus-5.5 · parent:6c140c1
test(retrieval): the canonical query's ordering — tie keys, the lexical cut, equal fused scores, the per-file cap (ADR-0007 Amendment 1 step 3b)
3 files changed, 109 insertions(+), 1 deletion(-)

### 2026-10-20T01:30:09Z · HANDOFF · myan · claude-code/opus-5.5 · a9d6eaa
Stacked PR for gupta958, after 3a. Then step 4 (plan harness) once both are merged.

### 2026-10-20T01:30:09Z · COMMIT · myan · claude-code/opus-5.5 · parent:a9d6eaa
docs(agents): hand the ordering tests to gupta958
1 file changed, 3 insertions(+)

### 2026-10-20T02:01:29Z · READ · myan · claude-code/opus-5.5 · 8ce71cf
gupta958 on #89 (relayed by Myan): ordering coverage incomplete. Per-leg tests exercise repo_id and path but not the final representation_id tie-break; equal-fusion testing exercises path but not repo_id, start_line or representation_id; the per-file-cap test checks only that three rows survive, not which three. Add tests that fail if any component of the pinned keys is removed or reordered.

### 2026-10-20T02:01:29Z · EDIT · myan · claude-code/opus-5.5 · 8ce71cf
Rebased onto #88's revision (c6e1503); the retrieval card conflict resolved by keeping #88's row and adding this file's. test_hybrid_sql_order.py rewritten: equal-length texts with different term counts for deliberate BM25 order; explicit representation ids inserted in reverse; equal fused scores from rank-swapped pairs. Tests: each leg's ranks (one fixture where every key component disagrees with the next); the lexical cut (103 matches, the best row last by repo and path, a tied pair at the boundary); equal fused scores decided by repo_id, path, start_line and representation_id in turn; the per-file cap deciding by start_line and by representation_id, with an uncapped passage in another path and another repository; and every ORDER BY key list pinned on the statement.

### 2026-10-20T02:01:29Z · TEST · myan · claude-code/opus-5.5 · 8ce71cf
A mutant script tried every drop, adjacent swap and direction flip of each of the five pinned keys (55 mutants). Before the rewrite, 35 survived the order tests. After it, 3 survived, all trailing-id drops masked by an earlier sort over the same id (the cut under the lexical ranks, the per-file window under the final order, pg_search's tie order under the cut). With the statement-key test, 0 of 55 survive. The cap's PARTITION BY reduced to path only or to repo only: 2 failed each. make db-test -> 97 passed; make test -> 391 passed; ruff clean.

### 2026-10-20T02:01:29Z · COMMIT · myan · claude-code/opus-5.5 · parent:8ce71cf
test(retrieval): pin every component of every ordering key (gupta958's review of #89)
3 files changed, 156 insertions(+), 61 deletions(-)

### 2026-10-20T02:01:29Z · HANDOFF · myan · claude-code/opus-5.5 · ba86479
Revised for gupta958's re-review of #89, rebased onto #88's revision.

### 2026-10-20T02:01:29Z · COMMIT · myan · claude-code/opus-5.5 · parent:ba86479
docs(agents): hand #89's revision back to gupta958
1 file changed, 3 insertions(+)

### 2026-10-20T02:01:42Z · TEST · myan · claude-code/opus-5.5 · e61eed2
Correction to the previous TEST entry, whose counts were written before the run finished: make db-test -> 101 passed (db 79, retrieval 22: test_hybrid_sql 13, test_hybrid_sql_order 9); make test -> 400 passed. The mutant results in that entry stand as measured.

### 2026-10-20T02:01:42Z · COMMIT · myan · claude-code/opus-5.5 · parent:e61eed2
docs(agents): correct #89's test counts in the task log
1 file changed, 3 insertions(+)
