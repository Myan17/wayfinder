# Task log — myan-agreements-g0-extend-p1-list

| Field | Value |
|---|---|
| Task | G0 extension under rule 5 and DESIGN 19.8 step 4, P1 ordered list under rule 6, phase-independent orient brief test (gupta958's ruling on #56/#57; ORIENT item 5) |
| Module | agreements |
| Branch | `myan/agreements/g0-extend-p1-list` |
| Worktree | `../wayfinder-wt/myan-agreements-g0-extend-p1-list` |
| Operator | myan |
| Agent | claude-code/opus-5.5 |
| Session | 2026-10-05T02:47Z/93efd94 |
| Started | 2026-10-05T02:47:46Z |
| Closed when | the last entry says TASK CLOSED (the header is never edited - this file is append-only) |

**Append-only.** Corrections are new entries. Entries are written by `scripts/log.sh` and the
`post-commit` hook; CI rejects a rewritten log (`scripts/check_agent_log.py`).

## Cards read

- (listed by `new-task.sh`; add any you read later as `READ` entries)

## Timeline

### 2026-10-05T02:47:46Z · DECIDE · myan · claude-code/opus-5.5 · 93efd94
gupta958's ruling of 2026-10-04, relayed by myan: authorized a separate planning/CI repair PR that (1) applies ORIENT rule 5 and DESIGN 19.8 by extending the schedule, including all dependent phase and launch-review dates; (2) keeps P0 current until G0 actually closes rather than relabelling the project P1 because the calendar passed; (3) adds the ordered P1 list required by rule 6; (4) makes test_the_brief_renders_from_a_subdirectory phase-independent, still checking that a phase and CARDS render and that 'no phase table found' is absent, without another hard-coded phase; (5) stays separate from #57 and #56. #56 and #57 are accepted on their merits but wait for green unit and dispatcher.

### 2026-10-05T02:47:46Z · PLAN · myan · claude-code/opus-5.5 · 93efd94
Move every phase 11 days: P0 Sep 21 - Oct 11, P1 Oct 12 - 25, P2 Oct 26 - Nov 8, P3 Nov 9 - 15, P4 Nov 16 - 22, P5 Nov 23 - 29, launch review Mon Nov 30. P0 has 16 h sized open (items 5 remainder, 6, 7, 8) plus 9c unsized, and its 3 h contingency is spent; 7 days at DESIGN's 35 h/week is 35 h. The 11 days also put every phase back on week boundaries from Mon Sep 21, so the Weeks column becomes exact (P0 1-3 ... P5 10). DESIGN 0.3.3: header window, 19.1 table and a revision row; ORIENT: P0 header, the P1 table in Next phase (rule 6). Test: assert a rendered phase line by pattern (P<n> theme, ISO start to end) and the gate line, not a literal. Rejected: a 7-day move to Oct 7, which leaves under 1 day of slack against 16 h plus an unsized item and review latency; and making orient.py treat a phase as current until its gate report exists, which is new tooling the ruling did not ask for.

### 2026-10-05T02:49:14Z · EDIT · myan · claude-code/opus-5.5 · 93efd94
DESIGN 0.3.3: header window Mon 2026-09-21 to Sun 2026-11-29, launch review Mon 2026-11-30; 19.1 rows moved 11 days with Weeks 1-3, 4-5, 6-7, 8, 9, 10; a 19.1 note that P0 took step 4 twice; revision row 0.3.3 saying the move came four days late. ORIENT: P0 header Sep 21 - Oct 11 with both moves; Next phase holds the 9-item P1 list in dependency order (harness, authz predicate, grant refresh, ingestion, chunking, generation, webhooks, deletion, oracle suite), with early work (#4-#7, #10) and ADR-0004's obligations on their rows. The stale-date grep finds only the 0.3.1 history row.

### 2026-10-05T02:49:14Z · COMMIT · myan · claude-code/opus-5.5 · parent:93efd94
docs(agreements): extend G0 to Oct 11 under rule 5; P1's ordered list
3 files changed, 63 insertions(+), 14 deletions(-)
