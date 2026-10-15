# Task log — myan-eval-data-s1-no-commits

| Field | Value |
|---|---|
| Task | A merged PR listing no commits (cli/cli#7228) is an unresolved base, not a crash |
| Module | eval-data |
| Branch | `myan/eval-data/s1-no-commits` |
| Worktree | `../wayfinder-wt/myan-eval-data-s1-no-commits` |
| Operator | myan |
| Agent | claude-code/opus-5.5 |
| Session | 2026-10-14T19:58Z/c0c72d9 |
| Started | 2026-10-14T19:58:56Z |
| Closed when | the last entry says TASK CLOSED (the header is never edited - this file is append-only) |

**Append-only.** Corrections are new entries. Entries are written by `scripts/log.sh` and the
`post-commit` hook; CI rejects a rewritten log (`scripts/check_agent_log.py`).

## Cards read

- (listed by `new-task.sh`; add any you read later as `READ` entries)

## Timeline

### 2026-10-14T19:58:56Z · READ · myan · claude-code/opus-5.5 · c0c72d9
Run 2 crashed at cli/cli: RuntimeError 'PR 7228 lists no commits'. gh graphql: merged 2023-03-27, head cubxxw/cli:trunk, commits.totalCount 0, closes #7229. linked_pairs raises by design (#62); repo.base_commit already returns reasons for unresolved bases.

### 2026-10-14T19:58:56Z · PLAN · myan · claude-code/opus-5.5 · c0c72d9
Linked.first_commit becomes str|None; linked_pairs yields the pair with None; repo.base_commit returns (None, 'PR lists no commits'). Pair counts for S1-2, against S1-3, never reaches gold. Rejected: skipping the PR (undercounts S1-2 and hides it from S1-3) and using the merge commit's parent (not D-1's base).

### 2026-10-14T19:59:54Z · TEST · myan · claude-code/opus-5.5 · c0c72d9
cd eval/miners: ruff check/format clean; pytest -> 141 passed. Mutants: restore the raise in linked_pairs -> test_s1_github 1 failed; drop the None branch in base_commit -> test_s1_repo 1 failed. Both restored.

### 2026-10-14T19:59:54Z · HANDOFF · myan · claude-code/opus-5.5 · c0c72d9
Ready for gupta958. After merge Myan re-runs s1.run from the start (no resume; clones are temporary).

### 2026-10-14T19:59:55Z · COMMIT · myan · claude-code/opus-5.5 · parent:c0c72d9
fix(eval-data): a merged PR listing no commits is an unresolved D-1 base, not a crash
6 files changed, 53 insertions(+), 11 deletions(-)
