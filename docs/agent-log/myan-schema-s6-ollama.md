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
