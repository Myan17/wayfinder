# Task log — myan-platform-release-manifest

| Field | Value |
|---|---|
| Task | Release-manifest format, validator and manifest-derived cache keys (ORIENT item 3, part b; DESIGN 16.9) |
| Module | platform |
| Branch | `myan/platform/release-manifest` |
| Worktree | `../wayfinder-wt/myan-platform-release-manifest` |
| Operator | myan |
| Agent | claude-code/opus-5 |
| Session | 2026-09-24T17:36Z/12222 |
| Started | 2026-09-24T17:36:01Z |
| Closed when | the last entry says TASK CLOSED (the header is never edited - this file is append-only) |

**Append-only.** Corrections are new entries. Entries are written by `scripts/log.sh` and the
`post-commit` hook; CI rejects a rewritten log (`scripts/check_agent_log.py`).

## Cards read

- (listed by `new-task.sh`; add any you read later as `READ` entries)

## Timeline

### 2026-09-24T17:36:01Z · READ · myan · claude-code/opus-5 · 3926ec7
DESIGN 16.9 (what the manifest pins), 15.5 (index cache key: chunker, specification, templates, schema), NFR-12, 14.5 (dataset manifests are part of the release manifest), 9.2 embedding_spec columns; platform card.

### 2026-09-24T17:36:01Z · PLAN · myan · claude-code/opus-5 · 3926ec7
infra/manifest/release_manifest.py (stdlib only, so it runs before any dependency is installed): FIELDS describing every 16.9 item; validate() returns every error rather than the first, and rejects unknown keys so a misspelt field cannot silently fall out of a cache key; check_schema_version() ties schema_version to the newest db/migrations file; cache_key(manifest, scope) = sha256 over the canonical JSON of the fields that scope depends on. Two scopes: 'index' (schema, postgres image and extensions, grammars, chunker, full embedding spec - 15.5's list plus what else changes an index) and 'eval' (index plus retrieval parameters, answerability version, prompts, providers, datasets). code_commit and platform are excluded from both: a commit that changes none of those inputs must reuse the cache. CLI: validate FILE, cache-key FILE --scope. infra/manifest/example.json with the real pinned digest. Tests under infra/manifest/tests, added to pyproject testpaths. make manifest-check. Rejected: a jsonschema dependency - it would add a lockfile diff for what forty lines of stdlib do, and the guardrails convention is stdlib-only.

### 2026-09-24T17:37:57Z · EDIT · myan · claude-code/opus-5 · 3926ec7
infra/manifest/release_manifest.py (new, stdlib only): FIELDS for every 16.9 item with a checker and the scopes that key on it; validate (all errors, unknown keys rejected, images by digest only, lowercase-hex hashes, 40-char commits, 14-digit schema stamps, dimension a positive int not a bool); check_schema_version against db/migrations; cache_key over the canonical JSON of a scope's fields; CLI validate and cache-key. infra/manifest/example.json (real pinned digest, pg_search 0.25.9, vector 0.8.4 from the running image, DESIGN 9.5's retrieval defaults; values not chosen yet say unpinned-until-P1-chunker / unpinned-until-E5). pyproject testpaths += infra/manifest/tests. Makefile manifest-check. Platform card: interface, invariants, test row, change log; hashes re-recorded. Both new files ruff-formatted, so the format debt does not grow.

### 2026-09-24T17:37:57Z · TEST · myan · claude-code/opus-5 · 3926ec7
make test -> 130 passed (98 + 32). make manifest-check -> valid; wf-index-v1-e61118982f358fb8, wf-eval-v1-ac45d5460c665201. ruff check and format --check clean on infra/manifest. Mutations, each restored: grammars dropped from the index scope -> test_index_inputs_change_both_keys[grammars] fails; unknown-key rejection removed -> test_unknown_fields_are_rejected fails; code_commit keyed -> test_every_field_is_either_keyed_or_deliberately_unkeyed fails. Moved the schema_version-vs-tree test onto a temporary migrations directory, so a future migration never forces an edit to this platform-owned example.

### 2026-09-24T17:37:57Z · COMMIT · myan · claude-code/opus-5 · parent:3926ec7
feat(platform): release-manifest format, validator and manifest-derived cache keys
7 files changed, 411 insertions(+), 6 deletions(-)

### 2026-09-24T17:41:16Z · HANDOFF · myan · claude-code/opus-5 · afad8fa
#32 open; CI unit, guardrails, pinned-extension integration and dispatcher all success. Next: item 3 part c, the Go ingestd scaffold (Appendix C).

### 2026-09-24T17:41:16Z · COMMIT · myan · claude-code/opus-5 · parent:afad8fa
docs(platform): hand off #32
1 file changed, 3 insertions(+)
