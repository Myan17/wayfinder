# Task log — myan-eval-data-s1-miner-select

| Field | Value |
|---|---|
| Task | S1 miner: ADR-0013 D-5 split and ADR-0016 corpus selection, stacked on s1-miner-core (ORIENT item 5) |
| Module | eval-data |
| Branch | `myan/eval-data/s1-miner-select` |
| Worktree | `../wayfinder-wt/myan-eval-data-s1-miner-select` |
| Operator | myan |
| Agent | claude-code/opus-5.5 |
| Session | 2026-09-28T22:33Z/18985 |
| Started | 2026-09-28T22:33:24Z |
| Closed when | the last entry says TASK CLOSED (the header is never edited - this file is append-only) |

**Append-only.** Corrections are new entries. Entries are written by `scripts/log.sh` and the
`post-commit` hook; CI rejects a rewritten log (`scripts/check_agent_log.py`).

## Cards read

- (listed by `new-task.sh`; add any you read later as `READ` entries)

## Timeline

### 2026-09-28T22:33:27Z · PLAN · myan · claude-code/opus-5.5 · dea5487
Stacked on myan/eval-data/s1-miner-core (split for size; the plan is in that log). It adds eval/miners/s1/split.py (ADR-0013 D-5) and select.py (ADR-0016's feasibility and total order) with their tests, and the card rows that pin them.

### 2026-09-28T22:33:27Z · TEST · myan · claude-code/opus-5.5 · dea5487
uv run --extra dev pytest: 190 passed (8 new here). These were written test-first in the core task, and their mutations are logged there: the latest-merge test and the sorted-tuple test each fail under their mutation (min group time; a sum of ids). context-freshness OK.

### 2026-09-28T22:33:27Z · COMMIT · myan · claude-code/opus-5.5 · parent:dea5487
feat(eval-data): S1 D-5 group-then-temporal split and ADR-0016 corpus selection
5 files changed, 195 insertions(+), 3 deletions(-)
