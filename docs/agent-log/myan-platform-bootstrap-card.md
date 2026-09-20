# Task log — myan-platform-bootstrap-card

| Field | Value |
|---|---|
| Task | Write the platform card and map tests/root files to modules so CI can pass |
| Module | platform |
| Branch | `myan/platform/bootstrap-card` |
| Worktree | `../wayfinder-wt/myan-platform-bootstrap-card` |
| Operator | myan |
| Agent | claude-code/opus-5 |
| Session | 2026-09-18T19:35Z/platform-1 |
| Started | 2026-09-19T00:18:58Z |
| Closed when | the last entry says TASK CLOSED (the header is never edited - this file is append-only) |

**Append-only.** Corrections are new entries. Entries are written by `scripts/log.sh` and the
`post-commit` hook; CI rejects a rewritten log (`scripts/check_agent_log.py`).

## Cards read

- (listed by `new-task.sh`; add any you read later as `READ` entries)

## Timeline

### 2026-09-19T00:18:58Z · PLAN · myan · claude-code/opus-5 · 91b31fd
Write the real platform card (its interface today is the Makefile + compose + CI, which already exist from bootstrap), and extend the ownership globs so apps/api/tests/**, uv.lock and project root files map to a module instead of warning. Rejected deleting Makefile from platform's interface_files: the Makefile IS the developer-facing contract of that module, so the card should describe it rather than the check being weakened.

### 2026-09-19T00:19:35Z · COMMIT · myan · claude-code/opus-5 · parent:91b31fd
docs(platform): write the platform card and map tests and root files to modules
4 files changed, 108 insertions(+), 36 deletions(-)

### 2026-09-19T00:19:45Z · TEST · myan · claude-code/opus-5 · 50f6fd6
python3 scripts/check_context_freshness.py -> context-freshness OK: 2 interface files checked across 16 cards. gen_codeowners.py --check -> CODEOWNERS OK. check_ownership.py with declared Scope -> OK, 4 files.

### 2026-09-19T00:19:45Z · HANDOFF · myan · claude-code/opus-5 · 50f6fd6
Platform card written (command surface + python project definition, with what has NOT landed stated); ownership globs now cover per-module tests and project root files. CI-blocking placeholder cleared. Reviewer: the judgement call is keeping Makefile as an interface file rather than dropping it to silence the check.

### 2026-09-19T00:19:45Z · COMMIT · myan · claude-code/opus-5 · parent:50f6fd6
docs(platform): record card verification and task log
1 file changed, 6 insertions(+)

### 2026-09-19T00:19:46Z · HANDOFF · myan · claude-code/opus-5 · f4e6b2e
TASK CLOSED. Pull request open for review.

### 2026-09-19T00:19:46Z · COMMIT · myan · claude-code/opus-5 · parent:f4e6b2e
docs(agents): close task log for myan-platform-bootstrap-card
1 file changed, 4 insertions(+), 1 deletion(-)

### 2026-09-19T00:30:27Z · DECIDE · myan · claude-code/opus-5 · 10461b5
CI checked out GitHub's synthetic merge commit, so the identity guardrail rejected it as a merge commit on a task branch. Fixed by checking out pull_request.head.sha rather than relaxing the no-merge-commits rule: the rule is right, the checkout was wrong.

### 2026-09-19T00:30:27Z · TEST · myan · claude-code/opus-5 · 10461b5
gh run view 35409512319 --log-failed -> '6ce07c3: merge commit on a task branch - rebase instead (AGENTS.md 2.2)'; root cause is actions/checkout defaulting to refs/pull/N/merge.

### 2026-09-19T00:30:27Z · COMMIT · myan · claude-code/opus-5 · parent:10461b5
fix(platform): check out the pull request head, not the synthetic merge commit
2 files changed, 10 insertions(+)

### 2026-09-19T00:31:55Z · COMMIT · myan · claude-code/opus-5 · parent:34695d5
fix(platform): resolve the branch name in CI, where the checkout is detached
3 files changed, 18 insertions(+), 4 deletions(-)

### 2026-09-19T00:33:13Z · COMMIT · myan · claude-code/opus-5 · parent:9fbedff
docs(platform): platform card, module globs and CI branch resolution
11 files changed, 175 insertions(+), 56 deletions(-)

### 2026-09-20T00:09:41Z · DECIDE · myan · claude-code/opus-5 · ecdfaa7
Reviewer was right that #2 reverts the privacy fix: merge-base is the scrub commit and the branch carried an older ROSTER.md, so the diff restores the address. My earlier reasoning - that a branch which never edited the file cannot revert it - was wrong, because this branch was rebuilt from a pre-scrub worktree snapshot. Taking main's copy of the file.

### 2026-09-20T00:09:41Z · EDIT · myan · claude-code/opus-5 · ecdfaa7
docs/team/ROSTER.md restored from origin/main; guardrails workflow now triggers on all pull requests so stacked ones get checks.

### 2026-09-20T00:09:42Z · COMMIT · myan · claude-code/opus-5 · parent:ecdfaa7
fix(platform): stop reverting the roster privacy fix, and check stacked pull requests
3 files changed, 14 insertions(+), 3 deletions(-)

### 2026-09-20T00:17:42Z · DECIDE · myan · claude-code/opus-5 · 3ae763e
Removed the required-suites placeholder rather than making it conditional: a job that echoes and exits zero appears as a passing check while testing nothing, which is worse than an absent job. The real lint/test job lands with the first suite (#4).

### 2026-09-20T00:17:42Z · TEST · myan · claude-code/opus-5 · 3ae763e
python3 -c yaml-shape check -> merge_group removed from triggers; jobs = ['guardrails']. python3 scripts/check_context_freshness.py -> OK.

### 2026-09-20T00:17:42Z · COMMIT · myan · claude-code/opus-5 · parent:3ae763e
fix(platform): drop the placeholder CI job and the unsupported merge_group trigger
3 files changed, 17 insertions(+), 11 deletions(-)
