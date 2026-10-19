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

### 2026-10-19T19:50:08Z · HANDOFF · myan · claude-code/opus-5.5 · 682de9f
Stacked PR for gupta958 on #81. Next, in order: (1) #81 merges; rebase this branch onto main with rebase -X theirs, force-push with a lease, retarget to main, close and reopen to re-run guardrails, refresh the body; (2) this PR merges; (3) new task for db/s6_ollama.py (S6-5 and repeatability through this helper's index_chunk and activate), Myan runs it; (4) results PR: report unchanged, ADR-0005 Decision, ORIENT item 6 done. Test: make db-up; WAYFINDER_TEST_DSN=postgresql://wayfinder:spike_local_only_not_a_secret@localhost:55432/s3spike uv run --extra dev pytest db/tests (41). Guardrails while stacked: B=$(git merge-base origin/myan/schema/s6-identity-prototype HEAD).

### 2026-10-19T19:50:08Z · HANDOFF · myan · claude-code/opus-5.5 · 682de9f
TASK CLOSED. Pull request open for review.

### 2026-10-19T19:50:09Z · COMMIT · myan · claude-code/opus-5.5 · parent:682de9f
docs(agents): close task log for myan-schema-s6-serving
1 file changed, 6 insertions(+)

### 2026-10-19T20:02:15Z · READ · myan · claude-code/opus-5.5 · 2d82408
#81 merged as bc77193 (gh state MERGED checked first); its task closed and worktree removed. GitHub retargeted #82 to main. Rebased with --onto origin/main past #81's pre-squash commits, so the branch holds only #82's two commits. gupta958's review of #82 (relayed by myan, 2026-10-19): activate() trusts caller-supplied base and desired and never ties them to the generation; read the generation's repo_id, base_generation_id and desired_generation in the locked path and require them to match (or derive them); add regression tests for a stale stored base with the caller passing the current base, and an old stored desired with the caller passing the new desired; keep the refusal cases in #82 (P1 item 6 later carries equivalents for production).

### 2026-10-19T20:02:15Z · EDIT · myan · claude-code/opus-5.5 · 2d82408
activate() reads repo_id, base_generation_id and desired_generation from the generation row inside the transaction that holds the repository lock, and refuses unless they equal repo_id, base and desired, alongside the existing checks. Chose matching over deriving: the caller still states its intent, and a mismatch is refused rather than silently corrected. Refusal cases added: stored base stale (base_generation_id NULL, caller passes gen_a), stored desired old (newer push, caller passes the new desired), another repository's generation (same base and target), another generation activated underneath. Each refusal case also asserts B did not become active. Card row updated.

### 2026-10-19T20:02:15Z · TEST · myan · claude-code/opus-5.5 · 2d82408
pytest db/tests against the pinned ParadeDB -> 49 passed (test_s6_identity: 34). ruff clean. New fences, each killed alone: stored repo unchecked (2 failed; survived until the cross-repository case), stored base (2), stored desired (2). current base unchecked (2, after the underneath case; before it the pointer guard made it equivalent), both base guards removed together (2). Earlier set re-run, all killed: claim, expiry, ready, chunk count, removed stay live, added never live (22), nearest ignores live, base not retired. One equivalent survivor as before: the pointer's rowcount check alone.

### 2026-10-19T20:02:15Z · COMMIT · myan · claude-code/opus-5.5 · parent:2d82408
fix(schema): activate() ties base and desired to the generation's own row, refusing caller substitution
4 files changed, 49 insertions(+), 9 deletions(-)

### 2026-10-19T20:02:15Z · HANDOFF · myan · claude-code/opus-5.5 · 4600b12
TASK CLOSED. Pull request open for review.

### 2026-10-19T20:02:15Z · COMMIT · myan · claude-code/opus-5.5 · parent:4600b12
docs(agents): close task log for myan-schema-s6-serving
1 file changed, 3 insertions(+)
