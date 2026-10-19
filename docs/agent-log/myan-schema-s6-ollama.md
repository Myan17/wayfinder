# Task log — myan-schema-s6-ollama

| Field | Value |
|---|---|
| Task | S6-5 and repeatability: db/s6_ollama.py against a real Ollama through db/s6_identity.py (ORIENT item 6) |
| Module | schema |
| Branch | `myan/schema/s6-ollama` |
| Worktree | `../wayfinder-wt/myan-schema-s6-ollama` |
| Operator | myan |
| Agent | claude-code/opus-5.5 |
| Session | 2026-10-19T20:19Z/4731 |
| Started | 2026-10-19T20:19:34Z |
| Closed when | the last entry says TASK CLOSED (the header is never edited - this file is append-only) |

**Append-only.** Corrections are new entries. Entries are written by `scripts/log.sh` and the
`post-commit` hook; CI rejects a rewritten log (`scripts/check_agent_log.py`).

## Cards read

- (listed by `new-task.sh`; add any you read later as `READ` entries)

## Timeline

### 2026-10-19T20:22:08Z · READ · myan · claude-code/opus-5.5 · a8bfbb3
#82 merged as a8bfbb3 (gh state MERGED checked before closing its task). ADR-0005's S6-5, rulings 1 and 2, and 'Where the prototype lives'; db/s6_identity.py as merged; db/tests/conftest.py's database setup. Ollama API used: /api/version, /api/tags (name and digest), /api/copy, /api/delete, /api/embed (model, input, options, truncate).

### 2026-10-19T20:22:08Z · PLAN · myan · claude-code/opus-5.5 · a8bfbb3
db/s6_ollama.py: an Ollama client class (five calls), an embedder for s6.index_chunk that refuses unless the alias still names the captured digest, and run(client, conn): copy nomic-embed-text to the alias, capture A from the runtime's digest, recapture (same row), build and activate A, re-point the alias to snowflake-arctic-embed:110m (also 768-d), capture B (new row), build B (new representation, one call), activate, serving follows; then repeatability: two direct /api/embed calls on nomic-embed-text with identical digest, input and options, reporting byte equality, max abs difference and cosine distance. main() uses the same fresh-database setup as conftest, refuses a dirty db/, writes db/evidence/s6-ollama.json, deletes the alias, exits 1 unless every check passed. Tests run run() against a fake Ollama in CI. Rejected: a second 768-d model chosen at run time (the pair is fixed before the run) and storing vectors in the report (size; the three numbers are what NFR-12 needs).

### 2026-10-19T20:22:08Z · TEST · myan · claude-code/opus-5.5 · a8bfbb3
pytest db/tests against the pinned ParadeDB -> 54 passed (test_s6_ollama: 5). ruff clean. Mutants on s6_ollama.py, all killed (1 failed each): embedder digest guard off, alias move unchecked, byte equality forced, one embed call reused for both, cosine forced 0, passed forced; 'new spec unchecked' survived until test_s6_5_fails_when_capture_ignores_the_digest. Not run against a real Ollama here: that run is Myan's (ADR-0005).

### 2026-10-19T20:22:09Z · COMMIT · myan · claude-code/opus-5.5 · parent:a8bfbb3
feat(schema): S6-5 runner — db/s6_ollama.py against a real Ollama, tested on a fake in CI
4 files changed, 316 insertions(+)

### 2026-10-19T20:22:09Z · HANDOFF · myan · claude-code/opus-5.5 · c8c6df4
PR for gupta958. After merge, Myan runs on a clean main: make db-up; ollama serve (separate terminal); ollama pull nomic-embed-text; ollama pull snowflake-arctic-embed:110m; WAYFINDER_TEST_DSN=postgresql://wayfinder:spike_local_only_not_a_secret@localhost:55432/s3spike uv run --extra dev python db/s6_ollama.py. It prints the checks and repeatability and writes db/evidence/s6-ollama.json. Then the results PR: the report unchanged, ADR-0005 Decision (each rule for both pairs from CI, the control, the report's hash and repeatability numbers for NFR-12), ORIENT item 6 done.

### 2026-10-19T20:22:09Z · HANDOFF · myan · claude-code/opus-5.5 · c8c6df4
TASK CLOSED. Pull request open for review.

### 2026-10-19T20:22:09Z · COMMIT · myan · claude-code/opus-5.5 · parent:c8c6df4
docs(agents): close task log for myan-schema-s6-ollama
1 file changed, 6 insertions(+)

### 2026-10-19T21:22:20Z · READ · myan · claude-code/opus-5.5 · 2934edf
gupta958 on #83 (relayed by Myan): refuse to start if the alias already exists or use a unique per-run alias; delete the alias only if this run created it; nest cleanup so the temporary database is dropped even if alias cleanup fails; add regressions for a pre-existing alias and an initial copy failure.

### 2026-10-19T21:22:20Z · PLAN · myan · claude-code/opus-5.5 · 2934edf
Both: a per-run alias wayfinder-s6-<8 hex>, and run() refuses if that name already exists (Ollama.exists via /api/tags). run() owns the alias: copy, then try/finally delete, so a failed copy deletes nothing and a pre-existing alias is never touched. main's database drop stays in its own outer finally, so a failing alias delete inside run() cannot skip it. Tests: pre-existing alias untouched and no copy; failed initial copy deletes nothing; alias deleted after a mid-run failure; main drops the database when alias delete raises.

### 2026-10-19T21:24:09Z · EDIT · myan · claude-code/opus-5.5 · 2934edf
db/s6_ollama.py: ALIAS replaced by ALIAS_PREFIX and a per-run alias; Ollama.exists; run() refuses an existing alias, copies, then deletes in its own finally; the rest moved to sequence(); main's database lifecycle moved to on_temporary_database(), whose finally drops the database outside run(). Tests: FakeOllama records deletes and has exists; four regressions.

### 2026-10-19T21:24:09Z · TEST · myan · claude-code/opus-5.5 · 2934edf
pytest db/tests against the pinned ParadeDB -> 58 passed (test_s6_ollama: 9). ruff clean. Mutants, each killed (1+ failed): refusal removed; initial copy moved inside try; alias delete removed (3 failed); database drop moved out of finally (the mutant leaked wf_s6_6fc44349d8a7, dropped by hand afterwards).

### 2026-10-19T21:24:19Z · COMMIT · myan · claude-code/opus-5.5 · parent:2934edf
fix(schema): S6-5 runner owns its Ollama alias and always drops its database
3 files changed, 112 insertions(+), 24 deletions(-)
