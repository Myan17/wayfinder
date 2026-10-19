# Task log — myan-agreements-adr-0005-s6-rules

| Field | Value |
|---|---|
| Task | ADR-0005 S6 acceptance rules: two embedding specifications over identical text, written before the prototype (ORIENT item 6) |
| Module | agreements |
| Branch | `myan/agreements/adr-0005-s6-rules` |
| Worktree | `../wayfinder-wt/myan-agreements-adr-0005-s6-rules` |
| Operator | myan |
| Agent | claude-code/opus-5.5 |
| Session | 2026-10-19T19:08Z/26648 |
| Started | 2026-10-19T19:08:48Z |
| Closed when | the last entry says TASK CLOSED (the header is never edited - this file is append-only) |

**Append-only.** Corrections are new entries. Entries are written by `scripts/log.sh` and the
`post-commit` hook; CI rejects a rewritten log (`scripts/check_agent_log.py`).

## Cards read

- (listed by `new-task.sh`; add any you read later as `READ` entries)

## Timeline

### 2026-10-19T19:10:30Z · READ · myan · claude-code/opus-5.5 · 5f17fb8
ORIENT item 6 (S6, 3 h): DESIGN §12.1 ADR 0005 (three identities), §9.2 embedding_spec/content/representation/vector_d768/occurrence and 'Why three identities (WF-05)', 'Model transitions', §8.5 reuse step, §9.3.5 activation, §16.3.1 INDEX-01, §2 principle 2. Schema v1 migrations (index, views, deletion) and db/tests/test_constraints.py (vector spec must match representation already pinned). ADR-0004 for the rules-first shape (#45-#48).

### 2026-10-19T19:10:30Z · PLAN · myan · claude-code/opus-5.5 · 5f17fb8
Rules first, as S5 did: ADR-0005 Proposed with S6-1 to S6-5 and an empty Decision; prototype and results in later PRs. Rules: new rows per spec (digest pair and template pair), A's vector byte-identical after B, reuse never crosses specs (embedder call counts), old spec keeps serving while B builds even when B's vector equals the query, spec identified by runtime digest not alias (real Ollama, alias re-pointed with ollama cp). A v0.2-shaped negative control must fail, else S6 is an error. Determinism, a second dimension, RRF, the HNSW plan and GC are named as not rules. Rejected: real Ollama for every rule (identity is a storage claim; a stand-in keeps S6-1..4 in CI) and testing a 384-d spec (needs a migration S6 does not own).

### 2026-10-19T19:10:30Z · COMMIT · myan · claude-code/opus-5.5 · parent:5f17fb8
docs(agreements): ADR-0005 — S6's acceptance rules for the three identities, written before the prototype
2 files changed, 133 insertions(+)

### 2026-10-19T19:10:30Z · HANDOFF · myan · claude-code/opus-5.5 · 22a463f
PR for gupta958: ADR-0005 rules only, no code. Decisions for B: stand-in embedder for S6-1..4 with real Ollama only in S6-5; determinism as a measurement, not a rule; prototype in db/tests plus a local db/s6_ollama.py (schema module). After merge, in order: new task schema/s6-identity-prototype (ORIENT item 6), db/tests/test_s6_identity.py with the v0.2 control, then db/s6_ollama.py pinned to an Ollama version and nomic-embed-text digest, Myan runs it, then the results PR (report committed unchanged, Decision, ORIENT item 6 done). Test for the prototype: make test / pytest db/tests against the pinned image.

### 2026-10-19T19:10:30Z · HANDOFF · myan · claude-code/opus-5.5 · 22a463f
TASK CLOSED. Pull request open for review.

### 2026-10-19T19:10:30Z · COMMIT · myan · claude-code/opus-5.5 · parent:22a463f
docs(agents): close task log for myan-agreements-adr-0005-s6-rules
1 file changed, 6 insertions(+)
