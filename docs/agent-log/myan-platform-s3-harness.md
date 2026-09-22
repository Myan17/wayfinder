# Task log — myan-platform-s3-harness

| Field | Value |
|---|---|
| Task | Build the S3 spike harness and measure S3-1a and S3-2..S3-6 locally |
| Module | platform |
| Branch | `myan/platform/s3-harness` |
| Worktree | `../wayfinder-wt/myan-platform-s3-harness` |
| Operator | myan |
| Agent | human |
| Session | 2026-09-22T01:12Z/d4a5535 |
| Started | 2026-09-22T01:12:06Z |
| Closed when | the last entry says TASK CLOSED (the header is never edited - this file is append-only) |

**Append-only.** Corrections are new entries. Entries are written by `scripts/log.sh` and the
`post-commit` hook; CI rejects a rewritten log (`scripts/check_agent_log.py`).

## Cards read

- (listed by `new-task.sh`; add any you read later as `READ` entries)

## Timeline

### 2026-09-22T01:18:58Z · PLAN · myan · claude-code/opus-5 · d4a5535
Building the S3 harness against rules already merged on main, which is the point of having split them. infra/spikes/s3/ holds a compose file pinned to the arm64 digest and a runner that measures S3-1a and S3-2..S3-6 and reports S3-1b as OUTSTANDING rather than skipping it, so a partial run cannot read as acceptance. psycopg added to the dev extra: two concurrent sessions with a transaction held open across another session's commit is the whole of S3-3, S3-4 and S3-5, and one-shot docker exec psql calls cannot express it. DESIGN 12 already names psycopg 3 as the driver, so this is not a spike-only choice. tmpfs rather than a volume, so no run can inherit state from the last one. Port 55432 so the spike cannot collide with a real local Postgres. Rejected writing results into the ADR's Decision as an acceptance: S3-1b is unmeasurable here and the ADR says a partial result is recorded as outstanding.

### 2026-09-22T01:18:59Z · TEST · myan · claude-code/opus-5 · d4a5535
Compose first failed: the Postgres 18 image aborts when the mount is at /var/lib/postgresql/data, wanting /var/lib/postgresql instead ('appears to be PostgreSQL data in /var/lib/postgresql/data (unused mount/volume)'). Moved the tmpfs up one level. Container then healthy, uname -m aarch64, PostgreSQL 18.6 on aarch64-unknown-linux-gnu. Full run, all against digest sha256:c17153b8: S3-1a PASS (host=arm64 daemon=arm64 image=arm64 variant absent); S3-1b OUTSTANDING; S3-2 PASS, pg_search 0.25.9, is_superuser=on, DESIGN 9.2's BM25 DDL accepted verbatim with no adaptation; S3-3 PASS; S3-4 PASS with reader seeing gen [1], writer activating gen 2 and retiring gen 1, the same transaction still seeing [1], a new transaction seeing [2]; S3-5 PASS, old snapshot kept 4 rows and a new transaction saw 0; S3-6 PASS with 'Parallel Custom Scan (ParadeDB Base Scan)', 'Index: rep_bm25', TopKScanExecState and a Tantivy query, no Seq Scan. Mutation-checked S3-4 because it is the load-bearing rule and passed first try: weakening the reader to READ COMMITTED makes step 4 return gen [2] and the rule fail, so the PASS reflects pg_search honouring the snapshot rather than a test that cannot fail. That mutation also exposed a harness bug - S3-4 recorded itself twice on failure, double-counting in the failure list - now one row. Suite still 67 passed; ruff clean after removing an unused sys import and wrapping two long lines.

### 2026-09-22T01:19:19Z · HANDOFF · myan · claude-code/opus-5 · d4a5535
Ready for review. S3 measured locally: every rule passes except S3-1b, which is OUTSTANDING because it needs the Oracle A1. ADR-0007 stays Proposed and the Decision section says so explicitly - nothing here should be cited as A-5 settled. The result a reviewer should weigh is S3-4, and the evidence that it means anything is the mutation check, not the PASS. Also in the diff: the platform card no longer states a test count. It had drifted to 17 against an actual 29 because #15 added tests without touching an interface file, so the freshness check never forced an update; that is the third time the number has been wrong, and 'uv run pytest -q' cannot go stale. The remaining blocker for a decision is the A1, which is Myan's to provision, not the reviewer's.

### 2026-09-22T01:19:19Z · COMMIT · myan · claude-code/opus-5 · parent:d4a5535
feat(platform): S3 harness, and every rule but S3-1b measured
7 files changed, 444 insertions(+), 8 deletions(-)

### 2026-09-22T19:12:19Z · READ · myan · claude-code/opus-5 · 15b7408
gupta958's review of #19, relayed off-platform: rebase after #18; S3-1a cannot record PASS until Postgres accepts the connection; S3-2 must fail unless is_superuser is on; S3-6 runs the BM25 query, not ADR-0007's required two-leg hybrid of DESIGN 9.5, so implement it or mark OUTSTANDING and split; Custom Scan alone is insufficient evidence the BM25 index was used; rerun and update the ADR. All five verified in the code before changing anything. S3-1a recorded PASS from main() before the connection was attempted. s3_2 read is_superuser into the detail string and recorded PASS unconditionally. s3_6 queried body_text @@@ 'widget' only, with used_index = 'bm25' in plan.lower() or 'Custom Scan' in plan - the or means a plan naming no bm25 index still passed.

### 2026-09-22T19:12:19Z · DECIDE · myan · claude-code/opus-5 · 15b7408
Taking the OUTSTANDING-and-split option on S3-6 rather than implementing the two-leg query here. DESIGN 9.5's hybrid is a BM25 leg fused with one HNSW dense leg per embedding specification under RRF; this spike's table has no vector column, no pgvector index and no embeddings, so the honest version is a vector column, an HNSW index, stand-in embeddings and the RRF fusion - well over the 53 lines this branch has left under the 400 limit, and it would bury the MVCC rules that are the load-bearing half of S3. The lexical plan is still captured and printed, labelled as not being S3-6, because the follow-up builds on it. ADR-0007 already says S3-6 is not an automatic fallback, so holding it open does not hold the engine decision hostage - S3-1b does that on its own.

### 2026-09-22T19:12:19Z · TEST · myan · claude-code/opus-5 · 15b7408
Rebased onto origin/main (320fd85, #18 merged). Resolved one conflict in the platform card - took main's version and re-applied only this branch's test-count note - and skipped the now-meaningless commit that had reverted psycopg, since main carries it. Verified the branch diff touches neither pyproject.toml nor uv.lock. Reran the harness against the same digest: S3-1a PASS with connection=accepted, S3-1b OUTSTANDING, S3-2 PASS is_superuser=on, S3-3 PASS, S3-4 PASS with reader on [1] across the activation and a new transaction on [2], S3-5 PASS, S3-6 OUTSTANDING with rep_bm25_named=True seq_scan=False. Mutation-checked both new gates rather than trusting the happy path: connecting as a NOSUPERUSER role gives 'S3-2 FAIL is_superuser=off' with the DDL not attempted, and stopping the container gives 'S3-1a FAIL ... failed: [postgres accepts a connection]'. uv run pytest -q -> 67 passed; ruff clean on run.py.

### 2026-09-22T19:12:38Z · HANDOFF · myan · claude-code/opus-5 · 15b7408
Review fixes in, harness rerun, ADR evidence updated. S3-6 is now OUTSTANDING alongside S3-1b, so the Decision section says two rules are open rather than one, and the closing paragraph's partial-result wording matches. The two-leg hybrid harness is the follow-up pull request; it needs a vector column, an HNSW index and stand-in embeddings before it can run 9.5's query at all. Nothing here should still read as an acceptance: the run prints 'OUTSTANDING: S3-1b, S3-6 -- this is NOT an acceptance'. The A1 remains Myan's to provision.

### 2026-09-22T19:12:38Z · COMMIT · myan · claude-code/opus-5 · parent:15b7408
fix(platform): S3-1a and S3-2 could pass without measuring their rule, and S3-6 was not S3-6
3 files changed, 95 insertions(+), 32 deletions(-)
