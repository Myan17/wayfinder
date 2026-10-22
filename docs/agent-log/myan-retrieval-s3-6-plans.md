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

### 2026-10-22T04:59:37Z · READ · myan · claude-code/opus-5.5 · 95bb67d
gupta958's rulings on #90 (relayed by Myan): S3-6a on the lexical leg only, by ADR-0007 Amendment 2 first (#91); S3-6b exactly as written, failures raised at G0; CI pins the complete observed scan outcome of the six 7,175 cases (the last test asserted only S3-6d/e); 60,000 stays local; location, stand-in reuse and the parameter rewrite accepted. Do not merge until revised.

### 2026-10-22T04:59:37Z · EDIT · myan · claude-code/opus-5.5 · 95bb67d
Rebased onto main 6bf7cc5 (#89); the card's test table conflict resolved by keeping #89's rows and adding this one. check_lexical now reads lexical_leg(plan): the subtree under the Subquery Scan aliased lexical or the CTE lexical subplan, empty (so failing) when neither exists, as Amendment 2 defines it. check_dense is unchanged in meaning. The last test is replaced by a pin of (S3-6a, S3-6b) for every (granted, mode) at 7,175, plus S3-6d, the text capture and the overall checks {a: true, b: false, c: false, d: true, e: true}. The mutation tests' baseline asserts were removed, because the pin covers them.

### 2026-10-22T04:59:37Z · TEST · myan · claude-code/opus-5.5 · 95bb67d
test_s3_6_plans.py against the pinned database -> 10 passed (58 s). Mutants on the scoped check, each killed: the Alias branch dropped, the CTE subplan branch dropped, the whole plan used instead of the subtree, and S3-6b scoped to the lexical leg. ruff check clean.

### 2026-10-22T04:59:37Z · COMMIT · myan · claude-code/opus-5.5 · parent:95bb67d
feat(retrieval): S3-6a reads only the lexical leg, and CI pins every 7,175 case's scans (ADR-0007 Amendment 2)
4 files changed, 52 insertions(+), 17 deletions(-)

### 2026-10-22T05:02:19Z · DECIDE · myan · claude-code/opus-5.5 · cffd617
check_pr_size failed at 423 counted lines after the revision. Split by function, as S6's runner was (#83, then #84): this PR keeps the fixture, cases, checks and tests; the evidence runner (cases_at, on_temporary_database, main, the report path and image pin) moves to a stacked PR, which step 5 runs. Nothing in this PR's tests used the runner.

### 2026-10-22T05:02:19Z · TEST · myan · claude-code/opus-5.5 · cffd617
After the split: test_s3_6_plans.py -> 10 passed (56 s); ruff clean.

### 2026-10-22T05:02:19Z · COMMIT · myan · claude-code/opus-5.5 · parent:cffd617
refactor(retrieval): move the S3-6 evidence runner to its own pull request
3 files changed, 8 insertions(+), 58 deletions(-)

### 2026-10-22T05:02:19Z · HANDOFF · myan · claude-code/opus-5.5 · fd1c179
Revised for gupta958's re-review of #90: rebased onto 6bf7cc5, S3-6a scoped by Amendment 2 (#91, which merges first), the 7,175 scan matrix pinned, the runner split to a stacked PR. Next: #91 merges, then #90, then the runner PR rebased onto main, then step 5.

### 2026-10-22T05:02:19Z · COMMIT · myan · claude-code/opus-5.5 · parent:fd1c179
docs(retrieval): hand #90's revision back to gupta958
1 file changed, 3 insertions(+)
