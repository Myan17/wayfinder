# Task log — myan-eval-data-s1-miner-core

| Field | Value |
|---|---|
| Task | S1 miner core: manifest schema, file universe and chunk estimate, D-2/D-3 filters, D-5 split, ADR-0016 selection (ORIENT item 5) |
| Module | eval-data |
| Branch | `myan/eval-data/s1-miner-core` |
| Worktree | `../wayfinder-wt/myan-eval-data-s1-miner-core` |
| Operator | myan |
| Agent | claude-code/opus-5.5 |
| Session | 2026-09-28T22:27Z/25276 |
| Started | 2026-09-28T22:27:51Z |
| Closed when | the last entry says TASK CLOSED (the header is never edited - this file is append-only) |

**Append-only.** Corrections are new entries. Entries are written by `scripts/log.sh` and the
`post-commit` hook; CI rejects a rewritten log (`scripts/check_agent_log.py`).

## Cards read

- (listed by `new-task.sh`; add any you read later as `READ` entries)

## Timeline

### 2026-09-28T22:27:51Z · PLAN · myan · claude-code/opus-5.5 · ccc79cc
S1 step 2a: the pure core of the miner, test-first, with no network. eval/miners/s1/universe.py implements ADR-0016's seven-step file universe, the line count and ceil(lines/60). pairs.py implements D-2's gold files: modified files in the universe restricted to .py/.pyi/.go, with 0 or more than max_files dropped (10, or 15 under R-03 step 2), and D-3's weak rule. split.py implements D-5's group-then-temporal split, with the per-repository placement, order and assignment exactly as ADR-0013 writes them, and the worked example as a test. select.py implements ADR-0016's feasibility and total order. eval/datasets/manifest.schema.json is the interface file, and the eval-data card is written in this PR. pyproject testpaths gains eval/miners/tests (Scope: platform). Acquisition (clone, GraphQL) and the run come in later PRs. Rejected: one PR for the whole miner, which would be well over 400 lines.

### 2026-09-28T22:32:16Z · TEST · myan · claude-code/opus-5.5 · ccc79cc
PYTHONDONTWRITEBYTECODE=1 uv run --extra dev pytest: 190 passed, including 33 new in eval/miners/tests/test_s1_core.py. Mutations, each caught by its named test: group time min instead of max (the latest-merge test), a sum of ids instead of the sorted tuple (the tuple test, rebuilt so the two orders disagree), and 'testdata' dropped from the test directories (the universe test). A stale __pycache__ first hid a restored file (min and max have the same length and mtime second), so these checks were re-run with bytecode disabled. The schema is valid JSON. context-freshness OK after --fix eval-data and --fix platform.

### 2026-09-28T22:32:26Z · COMMIT · myan · claude-code/opus-5.5 · parent:ccc79cc
feat(eval-data): S1 miner core — file universe, D-2/D-3, D-5 split, ADR-0016 selection
12 files changed, 484 insertions(+), 36 deletions(-)

### 2026-09-28T22:33:03Z · DECIDE · myan · claude-code/opus-5.5 · 6579aad
The size guard blocked the push at 492/400. Split by function: this PR keeps the manifest schema, the card, universe.py and pairs.py with their tests, and the pyproject and platform-card change. split.py and select.py with their tests (the D-5 worked example, latest merge, per-repository issues, total order, sorted-tuple tie-break, no feasible corpus) move to myan/eval-data/s1-miner-select, stacked on this one.

### 2026-09-28T22:33:03Z · COMMIT · myan · claude-code/opus-5.5 · parent:6579aad
refactor(eval-data): move the D-5 split and selection to the next PR
6 files changed, 69 insertions(+), 223 deletions(-)
