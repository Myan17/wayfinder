# Task log — myan-agreements-s1-merge-exclusion

| Field | Value |
|---|---|
| Task | ADR-0016 amendment: exclude pairs whose PR history contains a merge commit (merge_commit_in_pr_history), before the runner (gupta958's ruling on #59; ORIENT item 5) |
| Module | agreements |
| Branch | `myan/agreements/s1-merge-exclusion` |
| Worktree | `../wayfinder-wt/myan-agreements-s1-merge-exclusion` |
| Operator | myan |
| Agent | claude-code/opus-5.5 |
| Session | 2026-10-05T03:39Z/9d28c1f |
| Started | 2026-10-05T03:39:15Z |
| Closed when | the last entry says TASK CLOSED (the header is never edited - this file is append-only) |

**Append-only.** Corrections are new entries. Entries are written by `scripts/log.sh` and the
`post-commit` hook; CI rejects a rewritten log (`scripts/check_agent_log.py`).

## Cards read

- (listed by `new-task.sh`; add any you read later as `READ` entries)

## Timeline

### 2026-10-05T03:39:15Z · DECIDE · myan · claude-code/opus-5.5 · 9d28c1f
gupta958's ruling on #59, relayed by myan on 2026-10-04: option (a). Exclude, with an ADR-0016 amendment merged before the runner. The rule is deterministic and conservative: if the PR's own commit history contains any multi-parent merge commit, the pair is excluded with reason merge_commit_in_pr_history. Do not reconstruct the PR's own changes, because merges, conflict resolutions, cherry-picks and rebases make that ambiguous. The pair may still count toward S1-2's pre-filter linkable-pair total. It must not enter the pairs file, gold labels, splits, or strong/weak counts. Its exclusion is recorded under D-6. Tests: a linear PR is accepted and an internal-merge PR is excluded. The amendment merges before the miner is implemented or run.

### 2026-10-05T03:39:15Z · PLAN · myan · claude-code/opus-5.5 · 9d28c1f
Add an 'Amendment 1 (2026-10-04, before S1 runs)' section to ADR-0016 after the per-candidate rules. It defines the PR's commit history as the commits in base..head, with base being D-1's base and head the PR's head commit (refs/pull/N/head); states the rule, the reason string, where it sits in the order (after D-1 resolves, before D-2), and what it does and does not affect (S1-2 and S1-3 still count the pair; pairs file, gold, D-5 splits, strong/weak counts and A-3's 300 do not); and adds a header line saying the ADR was amended before measurement. No change to ADR-0013's rules: this is an S1 acquisition rule recorded under D-6. Rejected: putting the rule in ADR-0013, because it is specific to how S1 resolves changed files.

### 2026-10-05T03:39:35Z · TEST · myan · claude-code/opus-5.5 · 9d28c1f
Docs only, no code. uv run --extra dev pytest: 234 passed in 2.44s. The amendment's terms match the code in #59: repo.has_merges is git rev-list --merges base..head, and repo.base_commit's reasons are what 'S1-3's unresolved reason' refers to.

### 2026-10-05T03:39:36Z · COMMIT · myan · claude-code/opus-5.5 · parent:9d28c1f
docs(agreements): ADR-0016 amendment 1 — exclude PRs with a merge in their history
2 files changed, 56 insertions(+), 1 deletion(-)
