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

### 2026-11-03T02:53:25Z · COMMIT · myan · claude-code/opus-5 · be44316
be44316 (parent:417c796) docs(agents): close task log for myan-agreements-adr-0019-s2-inputs — cherry-picked from e37f54c on the merged #94 branch, which squash-merged without its TASK CLOSED entry; the cherry-pick does not run the post-commit hook, so this entry is written by hand.

### 2026-11-03T02:53:25Z · DECIDE · myan · claude-code/opus-5 · be44316
Split by function after check_pr_size reported 441 lines: this PR keeps Amendment 1 §1 (windows, the count refusal) and §3 (pseudo-repositories, grant levels). §4 (strong-dev issues, normalization, the 2,000-character rejection, the cold sample) moves unchanged into the next PR with the issue-fetch script.

### 2026-11-03T02:53:25Z · EDIT · myan · claude-code/opus-5 · be44316
eval/harness/s2/inputs.py, eval/harness/tests/test_s2_inputs.py, docs/context/modules/eval-harness.md: §4's functions, tests and card lines removed (kept for the next PR).

### 2026-11-03T02:53:26Z · COMMIT · myan · claude-code/opus-5 · parent:be44316
refactor(eval-harness): move the S2 query set to the next part, to keep this one under 400 lines
4 files changed, 15 insertions(+), 114 deletions(-)

### 2026-11-03T02:53:56Z · TEST · myan · claude-code/opus-5 · 24898da
On the split head: uv run pytest eval/harness/tests → 8 passed; uv run pytest → 396 passed, 25 skipped; ruff on eval/harness clean; check_pr_size → 333 counted lines; check_ownership with PR_BODY 'Scope: eval-harness, platform' → OK; identity, agent-log, context-freshness, codeowners, gh-account → OK.

### 2026-11-03T02:53:56Z · HANDOFF · myan · claude-code/opus-5 · 24898da
Part 1 of the S2 harness: Amendment 1 §1 and §3 in eval/harness/s2/inputs.py, the eval-harness card's first contract, and #94's missing TASK CLOSED entry. Next part (own branch after this merges, or stacked): §4's query set, kept in the scratchpad copies of inputs.py and its tests, plus the REST issue-fetch script. Open question for gupta958 then: how title and body are joined (DESIGN §14.2 step 4 does not say).

### 2026-11-03T02:53:56Z · COMMIT · myan · claude-code/opus-5 · parent:24898da
docs(eval-harness): S2 inputs part 1 test record and handoff
1 file changed, 6 insertions(+)

### 2026-11-03T02:53:56Z · HANDOFF · myan · claude-code/opus-5 · d95a9e0
TASK CLOSED. Pull request open for review.

### 2026-11-03T02:53:56Z · COMMIT · myan · claude-code/opus-5 · parent:d95a9e0
docs(agents): close task log for myan-eval-harness-s2-inputs
1 file changed, 3 insertions(+)
