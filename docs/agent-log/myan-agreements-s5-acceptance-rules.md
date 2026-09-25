# Task log — myan-agreements-s5-acceptance-rules

| Field | Value |
|---|---|
| Task | ADR-0004: S5's acceptance rules, written before the harness (ORIENT item 4, following #16 for S3) |
| Module | agreements |
| Branch | `myan/agreements/s5-acceptance-rules` |
| Worktree | `../wayfinder-wt/myan-agreements-s5-acceptance-rules` |
| Operator | myan |
| Agent | claude-code/opus-5 |
| Session | 2026-09-25T00:40Z/25587 |
| Started | 2026-09-25T00:40:38Z |
| Closed when | the last entry says TASK CLOSED (the header is never edited - this file is append-only) |

**Append-only.** Corrections are new entries. Entries are written by `scripts/log.sh` and the
`post-commit` hook; CI rejects a rewritten log (`scripts/check_agent_log.py`).

## Cards read

- (listed by `new-task.sh`; add any you read later as `READ` entries)

## Timeline

### 2026-09-25T00:40:38Z · READ · myan · claude-code/opus-5 · cc77be3
DESIGN 9.3.3 (desired generations; S5's five push boundaries and kill at each), 9.3.4 (jobs), 9.3.5 (fenced activation), 9.1.3 (River job in the receiving transaction), A-6, R-11, WF-07, Appendix B River row; ADR-0007 (the rules-before-measurement form); schema v1 (repository.claim_token/claim_expires_at, generation.status/lease_token).

### 2026-09-25T00:40:38Z · PLAN · myan · claude-code/opus-5 · cc77be3
ORIENT item 4 starts, as S3 did in #16, with the acceptance rules in their own pull request before any harness: ADR-0004 (DESIGN 12.1: desired-generation counter is the source of truth, queue is a wake-up), Status Proposed, decision empty. Rules: S5-1 no lost push, S5-2 no regression, S5-3 one active generation, S5-4 an expired claim never activates, S5-5 all of it with River's unique-job options off. Scenarios: DESIGN's five boundaries x {push, kill, push-then-kill}, plus a paused-past-expiry worker at mid-build and at activation: 17 scenarios, each repeated 20 times, any single failure fails the rule. River pinned at v0.47.0 (latest release, 2026-08-31). Records the DESIGN 9.3.3 vs schema column-name mismatch (lease_* vs claim_*) for a DESIGN edit in the harness pull request. No thresholds DESIGN does not give (convergence time is recorded, not judged).

### 2026-09-25T00:41:10Z · EDIT · myan · claude-code/opus-5 · cc77be3
docs/adr/ADR-0004-desired-generation-acceptance.md (new): Status Proposed, decision empty. Pins River v0.47.0 and the S3 image digest. Claim under test (9.3.3); column-name mismatch recorded (schema's claim_* used; 9.3.3 prose corrected in the harness pull request). Scenarios: B1-B5 x {push, kill, push then kill} + SIGSTOP past claim expiry at B2 and B4 = 17, each run 20 times, deterministic barriers not timers. Rules S5-1 no lost push, S5-2 no regression, S5-3 one active generation, S5-4 an expired claim never activates, S5-5 all without River unique options. Any single failure fails; a FAIL is a defect in our protocol (R-11), fixed with the 9.3 text before P1. No convergence-time threshold (DESIGN gives none; recorded, not judged). ORIENT item 4 status unchanged: this pull request does not complete the item.

### 2026-09-25T00:41:10Z · TEST · myan · claude-code/opus-5 · cc77be3
Documentation only; no measurement exists and none is quoted. River v0.47.0 confirmed as the latest release via the GitHub API (published 2026-08-31).

### 2026-09-25T00:41:10Z · COMMIT · myan · claude-code/opus-5 · parent:cc77be3
docs(agreements): ADR-0004, S5's acceptance rules before the harness
2 files changed, 120 insertions(+)

### 2026-09-25T00:42:36Z · HANDOFF · myan · claude-code/opus-5 · cb0df5c
#34 open, CI all green. Once merged, the S5 harness (platform/indexing) runs against these rules; ORIENT item 4 closes with it.

### 2026-09-25T00:42:36Z · COMMIT · myan · claude-code/opus-5 · parent:cb0df5c
docs(agreements): hand off #34
1 file changed, 3 insertions(+)
