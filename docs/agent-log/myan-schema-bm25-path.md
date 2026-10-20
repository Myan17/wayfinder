# Task log — myan-schema-bm25-path

| Field | Value |
|---|---|
| Task | representation.path and the code-aware rep_bm25, ADR-0007 Amendment 1 step 2 (ORIENT item 9c) |
| Module | schema |
| Branch | `myan/schema/bm25-path` |
| Worktree | `../wayfinder-wt/myan-schema-bm25-path` |
| Operator | myan |
| Agent | claude-code/opus-5.5 |
| Session | 2026-10-20T00:50Z/13067 |
| Started | 2026-10-20T00:50:03Z |
| Closed when | the last entry says TASK CLOSED (the header is never edited - this file is append-only) |

**Append-only.** Corrections are new entries. Entries are written by `scripts/log.sh` and the
`post-commit` hook; CI rejects a rewritten log (`scripts/check_agent_log.py`).

## Cards read

- (listed by `new-task.sh`; add any you read later as `READ` entries)

## Timeline

### 2026-10-20T00:50:03Z · READ · myan · claude-code/opus-5.5 · 279c9b7
ADR-0007 Amendment 1 (merged #86) step 2: representation.path NOT NULL, UNIQUE (id, repo_id, path), occurrence FK on path, refuse a non-empty table, rep_bm25 rebuilt with six fields (header/body_text source_code, header_ident/body_ident dotted-identifier regex, path segments, path_code source_code), §9.2 DDL edited. Schema card change protocol: one migration, cards in the same PR; CI's schema-check needs db/schema.sql regenerated in the same PR. Insert sites: db/s6_identity.py index_chunk, db/tests/conftest.py seed_representation, apps/ingestd/cmd/s5spike/protocol.go; db/tests/test_views.py inserts a live representation's occurrence at another path.

### 2026-10-20T00:50:03Z · PLAN · myan · claude-code/opus-5.5 · 279c9b7
One migration (up: emptiness guard, ADD COLUMN path NOT NULL, UNIQUE, occurrence FK, DROP and CREATE rep_bm25; down: reverse to v1's DDL). Callers pass path: s6_identity, conftest, s5spike. test_views keeps its intent (only the active-generation join hides a live representation's old occurrence) with the same path at another start_line, since two paths now mean two representations. New tests: each field's example, the emptiness guard, the occurrence path FK. Regenerate db/schema.sql. Scope: schema, platform (s5spike). Rejected: a nullable path with a backfill from header, because header's format is not pinned and a parsed path would be a guess.

### 2026-10-20T00:53:44Z · EDIT · myan · claude-code/opus-5.5 · 279c9b7
Migration 20261019230000_representation_path_bm25.sql (emptiness guard, path NOT NULL, UNIQUE (id, repo_id, path), occurrence FK on path, rep_bm25 with six fields; down restores v1). Callers pass path: db/s6_identity.py index_chunk, conftest seed_representation/seed_occurrence (path, start_line), apps/ingestd/cmd/s5spike/protocol.go ('f.go'). test_views: the retired-generation occurrence of a live representation now differs by line, not path. test_s6_identity's 'chunk added after ready' case gives its late.py chunk a header naming late.py, since the old call reused ranges.py's representation at another path. New db/tests/test_bm25_path.py. db/schema.sql regenerated. DESIGN §9.2: representation.path, the unique key, occurrence's FK, the new rep_bm25 DDL. Schema and indexing cards: status, tests row, change-log.

### 2026-10-20T00:53:44Z · TEST · myan · claude-code/opus-5.5 · 279c9b7
pytest db/tests on the pinned ParadeDB -> 70 passed (test_bm25_path: 12). ruff clean. go build ./... and go vet ./cmd/s5spike clean; s5spike run -runs 1 against the new schema: all 17 scenarios pass. db/dump-schema.sh --check -> current. Mutants on the migration, each killed: emptiness guard off (1 failed), occurrence FK removed (2), body_text default tokenizer (1), body_ident split (1), path split (1), path nullable (1). No scratch databases left.

### 2026-10-20T00:53:44Z · DECIDE · myan · claude-code/opus-5.5 · 279c9b7
Two existing tests changed, both because they encoded a representation at two paths, which ADR-0007 Amendment 1 makes impossible: test_views keeps its point (only the active-generation join hides a live representation's retired occurrence) with a different start_line; test_s6_identity's late chunk now has a header naming its own path. Scope widened to platform for one SQL line in the S5 spike, which would otherwise fail on NOT NULL; DESIGN §9.2 is agreements.

### 2026-10-20T00:53:51Z · COMMIT · myan · claude-code/opus-5.5 · parent:279c9b7
feat(schema): representation.path and the code-aware rep_bm25 (ADR-0007 Amendment 1 step 2)
12 files changed, 246 insertions(+), 23 deletions(-)

### 2026-10-20T00:53:51Z · HANDOFF · myan · claude-code/opus-5.5 · 44e7096
PR for gupta958. After merge: hybrid_sql.py alone with result, authorization and determinism tests, no plan harness (Amendment 1 step 3).

### 2026-10-20T00:53:51Z · COMMIT · myan · claude-code/opus-5.5 · parent:44e7096
docs(agents): hand the BM25 path migration to gupta958
1 file changed, 3 insertions(+)
