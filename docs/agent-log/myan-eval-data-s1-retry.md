# Task log — myan-eval-data-s1-retry

| Field | Value |
|---|---|
| Task | Retry transient GitHub GraphQL failures a bounded number of times; fail closed after |
| Module | eval-data |
| Branch | `myan/eval-data/s1-retry` |
| Worktree | `../wayfinder-wt/myan-eval-data-s1-retry` |
| Operator | myan |
| Agent | claude-code/opus-5.5 |
| Session | 2026-10-15T18:20Z/5330f34 |
| Started | 2026-10-15T18:20:42Z |
| Closed when | the last entry says TASK CLOSED (the header is never edited - this file is append-only) |

**Append-only.** Corrections are new entries. Entries are written by `scripts/log.sh` and the
`post-commit` hook; CI rejects a rewritten log (`scripts/check_agent_log.py`).

## Cards read

- (listed by `new-task.sh`; add any you read later as `READ` entries)

## Timeline

### 2026-10-15T18:21:11Z · READ · myan · claude-code/opus-5.5 · 5330f34
Run 2 (main 5330f34) passed cli/cli, then stopped in linked_pairs for stretchr/testify: 'GraphQL failed (200): Something went wrong while executing your query ... D013:1F5892:2FAD544:9C40E22:6AD0461F'. Probe re-paging testify with PRS_QUERY: 11 pages, 0 errors, so the failure is transient on GitHub's side.

### 2026-10-15T18:21:11Z · PLAN · myan · claude-code/opus-5.5 · 5330f34
Client.query retries transient failures only: HTTP 502/503/504, a 200 whose errors are GitHub's 'Something went wrong while executing your query', and a timeout or connection error. 4 attempts, waits 2, 4, 8 s (injectable sleep). Every attempt is tallied; S1-5 is checked on every non-transient response as before. urllib_transport returns HTTP errors as a status instead of raising. Anything else, and a 4th transient failure, still fails closed. Rejected: resuming the run from a checkpoint (more code, and the manifest's call tally would span two processes).

### 2026-10-15T18:22:08Z · TEST · myan · claude-code/opus-5.5 · 5330f34
cd eval/miners: ruff clean; pytest -> 144 passed. Mutants on s1/github.py, all killed: ATTEMPTS=1 (2 failed), all->any on transient errors (1), no scope check on a retried response (1), fixed 2 s wait (1), timeouts not retried (1), every non-200 transient (2).

### 2026-10-15T18:22:08Z · HANDOFF · myan · claude-code/opus-5.5 · 5330f34
Ready for gupta958. After merge Myan re-runs s1.run from the start.

### 2026-10-15T18:22:09Z · COMMIT · myan · claude-code/opus-5.5 · parent:5330f34
fix(eval-data): retry GitHub's transient GraphQL failures, at most 4 attempts, then fail closed
4 files changed, 128 insertions(+), 8 deletions(-)
