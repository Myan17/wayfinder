# Task log — myan-eval-harness-s2-inputs

| Field | Value |
|---|---|
| Task | S2 harness inputs: 60-line windows, pseudo-repositories, strong-dev query set and issue fetch (ORIENT item 7) |
| Module | eval-harness |
| Branch | `myan/eval-harness/s2-inputs` |
| Worktree | `../wayfinder-wt/myan-eval-harness-s2-inputs` |
| Operator | myan |
| Agent | claude-code/opus-5 |
| Session | 2026-11-03T02:35Z/26882 |
| Started | 2026-11-03T02:48:30Z |
| Closed when | the last entry says TASK CLOSED (the header is never edited - this file is append-only) |

**Append-only.** Corrections are new entries. Entries are written by `scripts/log.sh` and the
`post-commit` hook; CI rejects a rewritten log (`scripts/check_agent_log.py`).

## Cards read

- (listed by `new-task.sh`; add any you read later as `READ` entries)

## Timeline

### 2026-11-03T02:49:15Z · READ · myan · claude-code/opus-5 · 89e57be
ADR-0019 in full with Amendment 1 (merged #94, 89e57be); cards eval-harness (placeholder), eval-data, retrieval; DESIGN §9.4.2. Read eval/miners/s1/universe.py and repo.measure (same operator, AGENTS.md §3.2).

### 2026-11-03T02:49:16Z · PLAN · myan · claude-code/opus-5 · 89e57be
First harness PR = Amendment 1's 'inputs': eval/harness/s2/inputs.py with pure functions: 60-line windows that import universe.excluded/lines/CHUNK_LINES; a snapshot reader over git ls-tree/cat-file (repo._tree/_blobs are private, so not imported); the per-repository count check against the manifest's chunk_estimate, refusing on any difference; pseudo_repo() with Amendment 1 §3's exact hash; the three grant levels; the strong-dev query set (distinct issues, expected 874) and §4's cold sample; §9.4.2 query normalization (NFC + per-line trailing-whitespace strip) with the 2,000-character rejection. The issue-fetch script goes in a second PR to stay under 400 lines. Card written in this PR (its first interface file). Rejected: re-implementing the universe steps, which Amendment 1 forbids.

### 2026-11-03T02:52:35Z · EDIT · myan · claude-code/opus-5 · 89e57be
eval/harness/s2/{__init__,inputs}.py (new), eval/harness/tests/test_s2_inputs.py (new), docs/context/modules/eval-harness.md (first contract), docs/context/modules/platform.md and pyproject.toml (eval/harness on the pythonpath and collected), docs/context/INDEX.md (eval-harness row: written, s2/inputs.py).

### 2026-11-03T02:52:36Z · TEST · myan · claude-code/opus-5 · 89e57be
uv run pytest eval/harness/tests → 13 passed; uv run pytest → 401 passed, 25 skipped; ruff check and ruff format --check on eval/harness clean (repo-wide ruff has pre-existing findings in scripts/ only, untouched); check_context_freshness → OK, 9 interface files across 16 cards.

### 2026-11-03T02:52:36Z · COMMIT · myan · claude-code/opus-5 · parent:89e57be
feat(eval-harness): S2's inputs — 60-line windows, pseudo-repositories, the strong-dev query set (ADR-0019 Amendment 1)
8 files changed, 436 insertions(+), 32 deletions(-)
