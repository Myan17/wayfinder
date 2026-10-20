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
