# Task log — myan-platform-s5-harness-rules

| Field | Value |
|---|---|
| Task | S5 part 2 of 3: harness (databases, seeding, worker processes) and ADR-0004 rules S5-1 to S5-5 (ORIENT item 4) |
| Module | platform |
| Branch | `myan/platform/s5-harness-rules` |
| Worktree | `../wayfinder-wt/myan-platform-s5-harness-rules` |
| Operator | myan |
| Agent | claude-code/opus-5.5 |
| Session | 2026-09-27T21:44Z/22484 |
| Started | 2026-09-27T21:44:29Z |
| Closed when | the last entry says TASK CLOSED (the header is never edited - this file is append-only) |

**Append-only.** Corrections are new entries. Entries are written by `scripts/log.sh` and the
`post-commit` hook; CI rejects a rewritten log (`scripts/check_agent_log.py`).

## Cards read

- (listed by `new-task.sh`; add any you read later as `READ` entries)

## Timeline

### 2026-09-27T21:44:30Z · PLAN · myan · claude-code/opus-5.5 · 6026ec1
Part 2 of the S5 split (plan in the part 1 log, myan/platform/s5-harness). Stacked on part 1. Adds harness.go (a fresh template0 database per run with every migration plus rivermigrate, ADR-0004's baseline seed, the five preconditions, pushes, and worker processes driven through stdin barriers and signals) and rules.go (S5-1 to S5-5 after quiescence, plus the S5-3 observer). The scenarios and the run command come in part 3, so nothing calls this code yet.

### 2026-09-27T21:44:30Z · TEST · myan · claude-code/opus-5.5 · 6026ec1
go vet ./... clean with parts 1+2. Behaviour is tested in part 3, where the scenarios drive this code. The same code passed 17x20 before the split (log of part 1).

### 2026-09-27T21:44:30Z · COMMIT · myan · claude-code/opus-5.5 · parent:6026ec1
feat(platform): S5 part 2 of 3 — the harness and ADR-0004's rules
3 files changed, 377 insertions(+)

### 2026-09-28T01:10:32Z · DECIDE · myan · claude-code/opus-5.5 · 387dfe8
Restacked onto part 1's head 4528713 (the B3 fix from review of #45); was on 6026ec1. No conflicts; part 2's content is unchanged.

### 2026-09-28T01:10:32Z · COMMIT · myan · claude-code/opus-5.5 · parent:387dfe8
docs(agents): log the restack onto part 1's B3 fix
1 file changed, 3 insertions(+)

### 2026-09-28T01:44:49Z · DECIDE · myan · claude-code/opus-5.5 · 9f9af68
#45 merged as 466c475. Rebased part 2 onto main (was stacked on 4528713, part 1's head) and retargeted #46 to main. Part 2's content is unchanged.

### 2026-09-28T01:44:49Z · COMMIT · myan · claude-code/opus-5.5 · parent:9f9af68
docs(agents): log the rebase onto main after #45
1 file changed, 3 insertions(+)

### 2026-09-28T01:52:15Z · DECIDE · myan · claude-code/opus-5.5 · 4d405ed
Review of #46 by gupta958: every S5 rule must fail closed on database observation errors, and no query error may become a PASS. Before this, S5-2 dropped rows.Scan errors and never checked rows.Err, S5-4 and S5-5 discarded their Scan errors with '_ =' (so an error read as 0 bad rows and passed), and S5-1 reported its error as a rule failure. Now every query or scan error goes to r.errs via unobserved(), which makes the run an ERROR, and that rule is not judged. S5-2 reads through activations(), which returns an error rather than a shorter sequence.

### 2026-09-28T01:52:16Z · TEST · myan · claude-code/opus-5.5 · 4d405ed
go test ./cmd/s5spike: TestRulesFailClosedWhenTheDatabaseCannotBeRead points the rules at an unreachable database and asserts S5-1, S5-2, S5-4 and S5-5 errors are all in r.errs, plus the final S5-3 observe() (5 in all), and that no rule was judged on a DB read. Mutation: restoring '_ =' on S5-5 makes the test fail ('S5-5: query error was not recorded'); restored, it passes. go vet and gofmt are clean.

### 2026-09-28T01:52:16Z · COMMIT · myan · claude-code/opus-5.5 · parent:4d405ed
fix(platform): S5 rules fail closed on database observation errors
3 files changed, 81 insertions(+), 14 deletions(-)
