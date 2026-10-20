# Task log — myan-agreements-adr-0007-s3-6-pin

| Field | Value |
|---|---|
| Task | ADR-0007 Amendment 1: pin S3-6's canonical two-leg query and its plan checks, before the harness (ORIENT item 9c) |
| Module | agreements |
| Branch | `myan/agreements/adr-0007-s3-6-pin` |
| Worktree | `../wayfinder-wt/myan-agreements-adr-0007-s3-6-pin` |
| Operator | myan |
| Agent | claude-code/opus-5.5 |
| Session | 2026-10-20T00:24Z/18529 |
| Started | 2026-10-20T00:24:39Z |
| Closed when | the last entry says TASK CLOSED (the header is never edited - this file is append-only) |

**Append-only.** Corrections are new entries. Entries are written by `scripts/log.sh` and the
`post-commit` hook; CI rejects a rewritten log (`scripts/check_agent_log.py`).

## Cards read

- (listed by `new-task.sh`; add any you read later as `READ` entries)

## Timeline

### 2026-10-20T00:24:39Z · DECIDE · myan · claude-code/opus-5.5 · ed8273f
Out of ORIENT order under rule 2, by gupta958's direction on #85 (ruling 5, relayed by Myan): "Land item 9c's canonical two-leg query before the S2 measuring harness so S2 times the exact query whose plan 9c validates." Item 7's harness waits on 9c.

### 2026-10-20T00:24:39Z · READ · myan · claude-code/opus-5.5 · ed8273f
ADR-0007 S3-6 (BM25 scan in use, not a seq scan with a filter; plan capturable as text; not an automatic fallback) and its Decision (S3-6 OUTSTANDING: no dense leg). DESIGN §9.5 steps 1-8 and the plan-capture paragraph, §9.2's partial-index note (EXPLAIN proving the partial index with a parameterized spec_id), §9.1.5 (one predicate helper on scanned relations), authz sql_predicate, retrieval card, schema migrations (vec768_hnsw WHERE live, rep_bm25, retrieval_rows, eligible_repo). ADR-0019 (S2 times 9c's query; parallel query off; 1/10/100% selectivity; 7,175 and 60k sizes).

### 2026-10-20T00:24:39Z · TEST · myan · claude-code/opus-5.5 · ed8273f
Exploration only, not evidence: a scratch probe on the local pinned image (pg_search 0.25.9, pgvector 0.8.4), 20k synthetic rows over 100 private repos, granted 1/10/100. The candidate query ran; lexical leg used 'Parallel Custom Scan (ParadeDB Base Scan)' with default parallel settings; dense leg used 'Index Scan using vec768_hnsw'; the retrieval_rows join read occurrence by Seq Scan. ~50 ms execution.

### 2026-10-20T00:24:39Z · PLAN · myan · claude-code/opus-5.5 · ed8273f
ADR-0007 Amendment 1 pins S3-6 before the harness: where the canonical query lives (retrieval module, built with authz's sql_predicate), its shape, the fixture (synthetic, 100 private repos, 7,175 and 60k rows, granted 1/10/100), session settings (parallel query off per ADR-0019, relaxed iterative scan), the plan checks S3-6a-d on custom and generic plans, mutation checks, and what CI runs. Rejected: going straight to the harness — the rule's 'two-leg hybrid query' is not pinned text, and choosing it after seeing plans is the goalpost problem ADR-0007 warns about.

### 2026-10-20T00:25:16Z · EDIT · myan · claude-code/opus-5.5 · ed8273f
ADR-0007: Amendment 1 under the acceptance rules (query location in the retrieval module via authz's sql_predicate; shape table; synthetic fixture at 7,175 and 60,000 over 100 private repos; parallel query off; 2 sizes x 3 selectivities x custom/generic = 12 plans; checks S3-6a-d; mutation checks; what S3-6 does not judge; where it runs). S3-6's rule row points to the amendment.

### 2026-10-20T00:25:16Z · COMMIT · myan · claude-code/opus-5.5 · parent:ed8273f
docs(agreements): ADR-0007 Amendment 1 — S3-6's canonical two-leg query and plan checks, pinned before the harness
2 files changed, 101 insertions(+), 1 deletion(-)

### 2026-10-20T00:25:16Z · HANDOFF · myan · claude-code/opus-5.5 · 72021de
PR for gupta958. After merge: the canonical query (apps/api/wayfinder/retrieval/hybrid_sql.py) and the S3-6 harness with its tests, then the evidence run and results; then item 7's S2 harness.

### 2026-10-20T00:25:17Z · COMMIT · myan · claude-code/opus-5.5 · parent:72021de
docs(agents): hand ADR-0007 Amendment 1 to gupta958
1 file changed, 3 insertions(+)
