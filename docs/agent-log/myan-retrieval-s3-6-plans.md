# Task log — myan-retrieval-s3-6-plans

| Field | Value |
|---|---|
| Task | S3-6 plan harness: cases, checks S3-6a-e and mutation checks (ADR-0007 Amendment 1 step 4, ORIENT item 9c) |
| Module | retrieval |
| Branch | `myan/retrieval/s3-6-plans` |
| Worktree | `../wayfinder-wt/myan-retrieval-s3-6-plans` |
| Operator | myan |
| Agent | claude-code/opus-5.5 |
| Session | 2026-10-22T04:32Z/17251 |
| Started | 2026-10-22T04:32:25Z |
| Closed when | the last entry says TASK CLOSED (the header is never edited - this file is append-only) |

**Append-only.** Corrections are new entries. Entries are written by `scripts/log.sh` and the
`post-commit` hook; CI rejects a rewritten log (`scripts/check_agent_log.py`).

## Cards read

- (listed by `new-task.sh`; add any you read later as `READ` entries)

## Timeline

### 2026-10-22T04:36:51Z · PLAN · myan · claude-code/opus-5.5 · c80845b
S3-6 harness as apps/api/wayfinder/retrieval/s3_6.py (retrieval owns the query; S6's runner precedent: one module that builds the fixture, runs the cases and writes db/evidence/<name>.json, run with python -m). It imports hybrid_sql.build and never edits it: the statement is rewritten from %(name)s to $n only to PREPARE it, and EXECUTE's arguments are literals. Fixture: 100 private repositories, ADR-0005's stand-in vectors (db/s6_identity.stand_in, seeded by row number), 5 TERM matches per repository rotated through body, header and a path segment, ANALYZE last. S3-6d reads the rows: K = 200 and one representation per path, so every leg candidate is a returned row. Rejected: a harness under db/ (the schema module), since S2 must import the query's harness from retrieval.

### 2026-10-22T04:36:51Z · READ · myan · claude-code/opus-5.5 · c80845b
First look at the 7,175 plans (query frozen since #88; nothing tuned). Lexical leg: a ParadeDB Base Scan on representation in all 6 cases. But dense_0_ranked's join to representation (for the path tie key) is a Seq Scan on representation in all 6, so S3-6a's literal 'no node is a Seq Scan on representation' fails, though Amendment 1 also says S3-6 does not judge the plan's other joins. Dense leg: vec768_hnsw only at 100 granted under force_custom_plan; the other 5 cases seq-scan vector_d768 and sort exactly, so S3-6b fails 5 of 6. S3-6d passes in all 6 (lexical 5/50/100, dense 72/100/100). Fixture build 34 s.

### 2026-10-22T04:43:41Z · READ · myan · claude-code/opus-5.5 · c80845b
60,000 plans (fixture build 389 s, mostly COPY into vector_d768 with vec768_hnsw maintained per row). Lexical: ParadeDB Base Scan in all 6, and the dense rank join now uses representation_pkey, so S3-6a holds in all 6. Dense: vec768_hnsw in 5 of 6; at 1 granted repository under force_custom_plan the planner seq-scans vector_d768 (600 rows) and sorts exactly, so S3-6b fails that case. S3-6d holds in all 6. Not tuned; recorded for gupta958's ruling and G0.

### 2026-10-22T04:43:41Z · TEST · myan · claude-code/opus-5.5 · c80845b
make test -> 401 passed. test_s3_6_plans.py against the pinned database -> 10 passed (66 s; 7,175 fixture built once per module). Mutants of s3_6.py, each killed by the named test: provider check dropped, index-name check dropped, Seq Scan clause dropped, outside-repository clause dropped, either leg's count dropped, header/path rotation changed, extra grant not passed to the SQL, parameter numbering collapsed. ruff check clean on both new files (retrieval's existing files are not ruff-formatted, so neither are these).

### 2026-10-22T04:43:42Z · COMMIT · myan · claude-code/opus-5.5 · parent:c80845b
feat(retrieval): the S3-6 plan harness, its checks and mutation checks (ADR-0007 Amendment 1 step 4)
4 files changed, 431 insertions(+)

### 2026-10-22T04:43:55Z · HANDOFF · myan · claude-code/opus-5.5 · dd64312
PR for gupta958, who has to rule on the first plans before step 5. (1) S3-6a reads 'no node is a Seq Scan on representation'; at 7,175 the dense leg's rank join (rep_2, for the path tie key) is one, though the lexical leg is always a ParadeDB scan and Amendment 1 says S3-6 does not judge other joins. Literal or lexical-leg-only? (2) S3-6b fails 5 of 6 at 7,175 and 1 of 6 at 60,000 (1 granted repository, custom plan): the planner sorts exactly. Raised, not tuned. (3) What the CI gate asserts until S3-6 passes. (4) 60,000 stays local (389 s build). Test: make db-test; the harness tests are apps/api/tests/retrieval/test_s3_6_plans.py. Next after merge and the rulings: step 5, the evidence run (python -m wayfinder.retrieval.s3_6 on a clean tree) and its results PR.

### 2026-10-22T04:43:55Z · COMMIT · myan · claude-code/opus-5.5 · parent:dd64312
docs(retrieval): hand the S3-6 plan harness to gupta958
1 file changed, 3 insertions(+)
