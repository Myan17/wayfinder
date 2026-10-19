# Task log — myan-schema-s6-serving

| Field | Value |
|---|---|
| Task | S6 serving half: §9.3.5 activation, serving queries, S6-4 and refusal cases, stacked on #81 (ORIENT item 6) |
| Module | schema |
| Branch | `myan/schema/s6-serving` |
| Worktree | `../wayfinder-wt/myan-schema-s6-serving` |
| Operator | myan |
| Agent | claude-code/opus-5.5 |
| Session | 2026-10-19T19:47Z/2357 |
| Started | 2026-10-19T19:47:12Z |
| Closed when | the last entry says TASK CLOSED (the header is never edited - this file is append-only) |

**Append-only.** Corrections are new entries. Entries are written by `scripts/log.sh` and the
`post-commit` hook; CI rejects a rewritten log (`scripts/check_agent_log.py`).

## Cards read

- (listed by `new-task.sh`; add any you read later as `READ` entries)

## Timeline

### 2026-10-19T19:50:00Z · READ · myan · claude-code/opus-5.5 · e66f6ae
Stacked on myan/schema/s6-identity-prototype (#81, open) because activation and serving use its index_chunk and fixture. Read ADR-0005's S6-4 as amended by gupta958's ruling 4, DESIGN §9.3.5's activation SQL and status machine, db/views/retrieval_rows.sql.

### 2026-10-19T19:50:00Z · PLAN · myan · claude-code/opus-5.5 · e66f6ae
Add push_and_claim (accept a push and claim, no scheduling), finish_build (ready + chunk_count), activate (§9.3.5 in one transaction: row lock, claim and expiry, desired, base, ready, chunk count; flip live on added and removed for representation and vector_d768; retire base; activate new; move the pointer only from base), serving_rows (retrieval_rows bound to one spec) and nearest (live vectors, spec_id bound, cosine). The fixture activates A, then builds B. S6-4 per ruling 4, and one refusal test per precondition. Rejected: putting activation in the test file (the Ollama path must activate through the same code, ruling 1).

### 2026-10-19T19:50:01Z · TEST · myan · claude-code/opus-5.5 · e66f6ae
pytest db/tests against the pinned ParadeDB -> 41 passed (test_s6_identity: 26). ruff clean. Mutants on the serving half, all killed: removed rows stay live (2 failed), added never live (8), nearest ignores live (2) or spec (2), serving ignores spec (2), base not retired (2), and each precondition dropped: claim (2), expiry (2), ready (2), chunk count (2), desired (2), base (2). 'ready', desired, expiry and base each survived once and gained a refusal case (failed, a newer push, claim expired, stale base). One equivalent survivor: skipping the pointer's rowcount check, since the row lock and the base check already guarantee one row.

### 2026-10-19T19:50:01Z · COMMIT · myan · claude-code/opus-5.5 · parent:e66f6ae
feat(schema): S6 serving half — §9.3.5 activation, serving queries, S6-4 and the refusal cases
4 files changed, 217 insertions(+), 7 deletions(-)
