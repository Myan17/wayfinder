# Task log — myan-platform-s5-harness-results

| Field | Value |
|---|---|
| Task | S5 part 3 of 3: scenarios, run command, 17x20 results, ADR-0004 Decision (ORIENT item 4) |
| Module | platform |
| Branch | `myan/platform/s5-harness-results` |
| Worktree | `../wayfinder-wt/myan-platform-s5-harness-results` |
| Operator | myan |
| Agent | claude-code/opus-5.5 |
| Session | 2026-09-27T21:44Z/2774 |
| Started | 2026-09-27T21:44:40Z |
| Closed when | the last entry says TASK CLOSED (the header is never edited - this file is append-only) |

**Append-only.** Corrections are new entries. Entries are written by `scripts/log.sh` and the
`post-commit` hook; CI rejects a rewritten log (`scripts/check_agent_log.py`).

## Cards read

- (listed by `new-task.sh`; add any you read later as `READ` entries)

## Timeline

### 2026-09-27T21:44:42Z · COMMIT · myan · claude-code/opus-5.5 · parent:ead65b3
feat(platform): S5 part 3 of 3 — scenarios and the run command
2 files changed, 253 insertions(+), 2 deletions(-)

### 2026-09-27T21:44:52Z · PLAN · myan · claude-code/opus-5.5 · c0e049b
Part 3 of the S5 split (plan in the part 1 log). Stacked on part 2. Adds scenarios.go (ADR-0004's 17 scenarios, the paused takeover, the reconciler and quiescence) and the run command in main.go, so the tree equals the full harness at 0718ea2. Then: the 17x20 run on this exact code, ADR-0004's Decision with the output quoted, the §9.3.3 prose lease_* -> claim_* that ADR-0004 asked for, and ORIENT item 4 done. This PLAN is written after the first commit, which carried only code.

### 2026-09-27T21:55:29Z · TEST · myan · claude-code/opus-5.5 · c0e049b
ADR-0004 full run on this branch's code (c0e049b, built from this tree): 17 scenarios x 20 runs, every scenario 'pass 20 fail 0 error 0'. Median 2.186 s, max 2.995 s over 340 runs. 'S5-1..S5-5: no failure in any run of any scenario', exit 0. This repeats the pre-split run (b09a5f7, 340/340) on the shipped code.

### 2026-09-27T21:55:29Z · EDIT · myan · claude-code/opus-5.5 · c0e049b
ADR-0004: Status Accepted, and the Decision filled in with the run quoted, the fixes found and the mutation results. DESIGN 0.3.2: §9.3.3 prose uses claim_token/claim_expires_at and records the S5 result, §9.3.5 notes that a NULL claim is not live, and the header and revision row are updated. ORIENT item 4: done #45–#47.

### 2026-09-27T21:55:29Z · HANDOFF · myan · claude-code/opus-5.5 · c0e049b
ORIENT item 4 (S5) is complete across #45 (part 1, protocol and worker), #46 (part 2, harness and rules, base #45's branch) and #47 (part 3, scenarios, results, ADR-0004 Decision, DESIGN 0.3.2, ORIENT done; base #46's branch). Merge in order 45, 46, 47. After each merge, the next PR is rebased onto main and retargeted to main. Next ORIENT item: 5, S1 corpus.

### 2026-09-27T21:55:29Z · COMMIT · myan · claude-code/opus-5.5 · parent:c0e049b
docs(platform): S5 results — ADR-0004 accepted, DESIGN 0.3.2, ORIENT item 4 done
4 files changed, 79 insertions(+), 16 deletions(-)

### 2026-09-28T01:23:14Z · TEST · myan · claude-code/opus-5.5 · 0bd230c
After the B3 fix (review of #45), re-run on apps/ingestd tree 9491f5b, the same tree before and after the restack: 17 x 20 all 'pass 20 fail 0 error 0', median 2.243 s, max 10.432 s (a B3-push refusal waits for claim expiry; run time not judged). S5-1..S5-5 no failure, exit 0. B3-push exercises the stale read: generation D=2 'failed', D=3 'active'. Mutations on B3-push/kill/pushkill, 3 runs each: M2 (no head check) survives; M7 (no desired != d in the activation fence) survives, because the re-read after activation recovers. Recorded in ADR-0004 as a limit of the rules, not a rule change.

### 2026-09-28T01:23:14Z · DECIDE · myan · claude-code/opus-5.5 · 0bd230c
Restacked onto part 2's 6215ea0. ADR-0004's Decision now pins the run to the apps/ingestd tree hash, not a commit SHA, so rebases do not stale it, and adds the B3 finding and M7.

### 2026-09-28T01:23:14Z · COMMIT · myan · claude-code/opus-5.5 · parent:0bd230c
docs(platform): S5 evidence re-run with B3 after the read; M7 recorded
2 files changed, 22 insertions(+), 3 deletions(-)

### 2026-09-28T01:45:07Z · DECIDE · myan · claude-code/opus-5.5 · a4f6a46
#45 merged; part 2 rebased onto main as 4d405ed. Restacked part 3 onto it (was on 6215ea0). The apps/ingestd tree is still 9491f5b, the one the 17x20 ran on, so the ADR's pin holds.

### 2026-09-28T01:45:07Z · COMMIT · myan · claude-code/opus-5.5 · parent:a4f6a46
docs(agents): log the restack after #45
1 file changed, 3 insertions(+)

### 2026-09-28T01:53:14Z · DECIDE · myan · claude-code/opus-5.5 · 2f55546
Review of #46/#47 by gupta958: errors added by the final observe() must be checked after checkRules(). oneRun evaluated append(r.failures, r.checkRules(sc)...). Go reads r.failures before checkRules runs, so an S5-3 failure from the final observe() was dropped, and r.errs was checked only before checkRules, so an observation error there became a PASS. Now verdict(r, r.checkRules(sc)) reads both after the call, and any r.errs makes the run an ERROR. Restacked onto #46's fail-closed rules (6e68184); was on 4d405ed.

### 2026-09-28T01:53:14Z · TEST · myan · claude-code/opus-5.5 · 2f55546
go test ./cmd/s5spike: 2 tests pass, TestRulesFailClosedWhenTheDatabaseCannotBeRead (from #46) and TestTheVerdictIsTakenAfterTheFinalObservation. go vet and gofmt are clean. The 17x20 re-run on the new apps/ingestd tree follows.

### 2026-09-28T01:53:14Z · COMMIT · myan · claude-code/opus-5.5 · parent:2f55546
fix(platform): S5 verdict read after checkRules' final observation
3 files changed, 29 insertions(+), 1 deletion(-)
