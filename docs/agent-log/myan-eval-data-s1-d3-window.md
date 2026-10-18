# Task log — myan-eval-data-s1-d3-window

| Field | Value |
|---|---|
| Task | pairs.weak allows ADR-0013 Amendment 1's 60 s window (ORIENT item 5) |
| Module | eval-data |
| Branch | `myan/eval-data/s1-d3-window` |
| Worktree | `../wayfinder-wt/myan-eval-data-s1-d3-window` |
| Operator | myan |
| Agent | claude-code/opus-5.5 |
| Session | 2026-10-18T20:44Z/25385 |
| Started | 2026-10-18T20:44:48Z |
| Closed when | the last entry says TASK CLOSED (the header is never edited - this file is append-only) |

**Append-only.** Corrections are new entries. Entries are written by `scripts/log.sh` and the
`post-commit` hook; CI rejects a rewritten log (`scripts/check_agent_log.py`).

## Cards read

- (listed by `new-task.sh`; add any you read later as `READ` entries)

## Timeline

### 2026-10-18T20:44:48Z · READ · myan · claude-code/opus-5.5 · 1f6af86
ADR-0013 Amendment 1 (#77, merged 1f6af86): a pair is weak when the issue's updatedAt is more than W = 60 s after the PR's mergedAt (W is gupta958's decision); its Order paragraph: this miner PR next, with tests at 60 s and 61 s, then the S1 re-run. Read eval/miners/s1/pairs.py weak(), its one caller run.py:94, tests/test_s1_pairs.py, and the eval-data card's D-3 invariant (line 73) and test row.

### 2026-10-18T20:44:49Z · PLAN · myan · claude-code/opus-5.5 · 1f6af86
pairs.WEAK_WINDOW = dt.timedelta(seconds=60); weak() returns issue_updated_at > pr_merged_at + WEAK_WINDOW. Replace the D-3 test with boundaries: 0 s, 60 s and a negative delta strong; 61 s and 60 s + 1 µs weak; and pin WEAK_WINDOW to 60 s. Card: the D-3 invariant states the window, the test row is renamed, a change-log line. Rejected: recording W in the manifest's rules (a schema change the amendment did not ask for; ADR-0013 records W), and a configurable window (W is a ruling, not a parameter).

### 2026-10-18T20:45:57Z · EDIT · myan · claude-code/opus-5.5 · 1f6af86
pairs.WEAK_WINDOW = 60 s; weak() is issue_updated_at > pr_merged_at + WEAK_WINDOW, docstring citing Amendment 1 and #77. test_s1_pairs: the D-3 test becomes six boundary cases (-5 s, 0, 2 s, 60 s strong; 60 s + 1 us, 61 s weak) and a pin of WEAK_WINDOW at 60 s. Card: the D-3 invariant states the window, the test row is renamed, a change-log line. run.py, the only caller, is unchanged; test_s1_run's D-3 fixtures (a day before, 22 days after) still give one strong and one weak.

### 2026-10-18T20:45:57Z · TEST · myan · claude-code/opus-5.5 · 1f6af86
pytest eval/miners/tests -> 197 passed; ruff check and format clean. Mutants on pairs.py, all killed: window 59 s (2 failed), window 61 s (3), >= for > (1), window dropped (2).

### 2026-10-18T20:45:57Z · COMMIT · myan · claude-code/opus-5.5 · parent:1f6af86
feat(eval-data): pairs.weak allows ADR-0013 Amendment 1's 60 s window for merge-adjacent updates
4 files changed, 63 insertions(+), 8 deletions(-)
