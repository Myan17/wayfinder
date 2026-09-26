# Task log — myan-agreements-g0-extend

| Field | Value |
|---|---|
| Task | ORIENT rule 5: extend the schedule 3 days under DESIGN §19.8 step 4 (approved by myan) |
| Module | agreements |
| Branch | `myan/agreements/g0-extend` |
| Worktree | `../wayfinder-wt/myan-agreements-g0-extend` |
| Operator | myan |
| Agent | claude-code/opus-5.5 |
| Session | 2026-09-26T16:40Z/89 |
| Started | 2026-09-26T19:03:18Z |
| Closed when | the last entry says TASK CLOSED (the header is never edited - this file is append-only) |

**Append-only.** Corrections are new entries. Entries are written by `scripts/log.sh` and the
`post-commit` hook; CI rejects a rewritten log (`scripts/check_agent_log.py`).

## Cards read

- (listed by `new-task.sh`; add any you read later as `READ` entries)

## Timeline

### 2026-09-26T19:03:18Z · DECIDE · myan · claude-code/opus-5.5 · 8435c4f
ORIENT rule 5, approved by myan on 2026-09-26. The question: 'does that approve applying ORIENT rule 5, moving P0's G0 date per DESIGN §19.8?' The answer: 'Yes, move G0'. Shortfall: 21 h of open P0 items (4 5 6 7 8; 9c unsized) on Sep 26, with G0 on Sep 27. At DESIGN §19.1's capacity (~35 h/week, 5 h/day), 21 h needs 4.2 days, so G0 moves to Wed Sep 30 and every later phase moves +3 days. §19.8's steps 1-3 cut stretch features, experiment arms and generated answers, and none of those is P0 work, so step 4 (extend) is the one that applies. No evidence is cut.

### 2026-09-26T19:03:46Z · TEST · myan · claude-code/opus-5.5 · 8435c4f
DESIGN §19.1: every phase moved +3 days and the build window updated, plus a 0.3.1 revision row. ORIENT: the P0 line and the next-phase line. No other file names the old dates (grep over DESIGN, ORIENT, AGENTS, docs/team and docs/adr). orient.py --no-network shows P0 2026-09-21 to 2026-09-30. Scripts tests pass.

### 2026-09-26T19:03:47Z · COMMIT · myan · claude-code/opus-5.5 · parent:8435c4f
docs(agreements): extend the schedule 3 days at G0 (DESIGN §19.8 step 4)
3 files changed, 39 insertions(+), 10 deletions(-)

### 2026-09-26T19:04:05Z · PLAN · myan · claude-code/opus-5.5 · 77a0731
Take DESIGN §19.8 step 4: shift every §19.1 phase and the build window by the shortfall (3 days) and add a revision row. Update ORIENT's P0 and next-phase lines. Rejected: extending only P0 and compressing P1, which cuts P1's time and so its evidence (rule 5: the date moves, evidence is never cut). This PLAN is recorded after the edit; the guardrail caught that it was missing.

### 2026-09-26T19:04:05Z · COMMIT · myan · claude-code/opus-5.5 · parent:77a0731
docs(agreements): record the g0-extend PLAN the guardrail found missing
1 file changed, 3 insertions(+)
