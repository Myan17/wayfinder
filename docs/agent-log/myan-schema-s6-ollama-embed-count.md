# Task log — myan-schema-s6-ollama-embed-count

| Field | Value |
|---|---|
| Task | BCR-2: s6_ollama embed_counted, ContextExceeded, embedder record and truncate_rejected |
| Module | schema |
| Branch | `myan/schema/s6-ollama-embed-count` |
| Worktree | `../wayfinder-wt/myan-schema-s6-ollama-embed-count` |
| Operator | myan |
| Agent | claude-code/opus-5.5 |
| Session | 2026-11-05T05:38Z/30774 |
| Started | 2026-11-05T05:38:33Z |
| Closed when | the last entry says TASK CLOSED (the header is never edited - this file is append-only) |

**Append-only.** Corrections are new entries. Entries are written by `scripts/log.sh` and the
`post-commit` hook; CI rejects a rewritten log (`scripts/check_agent_log.py`).

## Cards read

- (listed by `new-task.sh`; add any you read later as `READ` entries)

## Timeline

### 2026-11-05T05:39:09Z · READ · myan · claude-code/opus-5.5 · 00fef63
BCR-2 (accepted, #110): contract, validation, six tests. db/s6_ollama.py:40-90 (Ollama._call, embed, embedder); db/tests/test_s6_ollama.py:11-41 (FakeOllama; client.calls == 0 pins no embed in the pre-existing-alias case).

### 2026-11-05T05:39:09Z · PLAN · myan · claude-code/opus-5.5 · 00fef63
Implement BCR-2 as written: CONTEXT_EXCEEDED, ContextExceeded, Embedded, Call, Ollama.embed_counted, and embedder's record and truncate_rejected options. embed() is left byte-identical. Test the Ollama class against a real local http.server on 127.0.0.1:0, so the HTTPError path is exercised for real, and the embedder against FakeOllama, which gains embed_counted with a reject set. Schema card: interface block, invariants, test row, change log, hashes. BCR-2 closure checklist ticked. Rejected: monkeypatching urlopen, which would not exercise how a 400's body is read.

### 2026-11-05T05:41:28Z · EDIT · myan · claude-code/opus-5.5 · 00fef63
db/s6_ollama.py: CONTEXT_EXCEEDED, ContextExceeded, Embedded, Call, Ollama.embed_counted, _error, and embedder(record, truncate_rejected) with a digest check before every request; embed() unchanged. db/tests/test_s6_ollama.py: FakeOllama gains requests, reject, reject_truncated, before_retry and embed_counted; six BCR-2 tests (three on a real local http.server). Schema card: interface block, invariants, test row, change log, hashes. BCR-2 closure checklist ticked.

### 2026-11-05T05:41:28Z · TEST · myan · claude-code/opus-5.5 · 00fef63
PYTHONPATH=db:db/tests uv run pytest db/tests/test_s6_ollama.py db/tests/test_s6_identity.py db/tests/test_s2_build_path.py: 10 passed, 45 skipped (no local DSN). The six BCR-2 tests need no database and pass. Mutation check: dropping the recheck before the retry, retrying any exception, loose message matching, hashing the truncated text, and accepting a bool count each fail a test. ruff check and format are clean; freshness OK. S6-5's database tests run in CI's db job.

### 2026-11-05T05:41:28Z · COMMIT · myan · claude-code/opus-5.5 · parent:00fef63
feat(schema): BCR-2 — s6_ollama's embed returns its token count, and may truncate a rejected window
5 files changed, 283 insertions(+), 14 deletions(-)
