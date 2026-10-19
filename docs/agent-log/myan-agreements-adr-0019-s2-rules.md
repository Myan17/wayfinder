# Task log — myan-agreements-adr-0019-s2-rules

| Field | Value |
|---|---|
| Task | ADR-0019: S2 whole-system CPU measurement protocol and rules, before any harness (ORIENT item 7) |
| Module | agreements |
| Branch | `myan/agreements/adr-0019-s2-rules` |
| Worktree | `../wayfinder-wt/myan-agreements-adr-0019-s2-rules` |
| Operator | myan |
| Agent | claude-code/opus-5.5 |
| Session | 2026-10-19T23:46Z/8428 |
| Started | 2026-10-19T23:46:51Z |
| Closed when | the last entry says TASK CLOSED (the header is never edited - this file is append-only) |

**Append-only.** Corrections are new entries. Entries are written by `scripts/log.sh` and the
`post-commit` hook; CI rejects a rewritten log (`scripts/check_agent_log.py`).

## Cards read

- (listed by `new-task.sh`; add any you read later as `READ` entries)

## Timeline

### 2026-10-19T23:46:51Z · READ · myan · claude-code/opus-5.5 · 1810a79
ORIENT item 7 (S2). DESIGN §10.1–10.6, A-4, §9.5 steps 1–8, §16.4, §19 P0 row (S2: per-stage process CPU across query-length percentiles, cache states, ACL selectivity, concurrent indexing), the 1%/10%/100% visibility levels (§5 NFR row, E7); ADR-0015 (S2 must report every grid arm's per-call CPU); ADR-0013's cost protocol (same host, the A1 once it exists; one thread; 3 warm-up + 5 timed passes; median of per-pass means); ADR-0007 S3-1a/S3-1b (a dev machine is a precondition, never evidence); ADR-0005's pinned nomic-embed-text digest. ORIENT 9b: the A1 is not provisioned.

### 2026-10-19T23:46:51Z · PLAN · myan · claude-code/opus-5.5 · 1810a79
Rules first, as ADR-0004/0005/0007 did: ADR-0019 fixes S2's host, corpus, queries, stages, CPU accounting, control and completeness rules before any harness exists, plus a §12.1 row. The measurement itself needs the A1 (ADR-0013: same host for every cost), so after this merges item 7 is set blocked on the A1 unless gupta958 rules otherwise; the SQL stage needs item 9c's two-leg query, flagged for a ruling. Rejected: measuring on the Mac now and calling it S2 — ADR-0007 already refused approximating the A1 with a development machine.

### 2026-10-19T23:47:47Z · EDIT · myan · claude-code/opus-5.5 · 1810a79
docs/adr/ADR-0019-s2-cpu-measurement.md: setup (A1 only for evidence, S2-dev is a harness check; pinned images and models; S1 corpus plus 60k padding; dev queries; one thread; ADR-0013's timing protocol), process-CPU accounting per stage, rules S2-1 to S2-8, a ±5% calibration control per accounting path, non-rules, order of work (9c dependency; blocked on the A1 for the run), empty Decision. Five Reviewer-decides points: reranker model, 60k padding, api-dependent rows (stand-in or L1), warm numbers for the budget, 9c before S2's harness. DESIGN §12.1: row 0019.

### 2026-10-19T23:47:47Z · TEST · myan · claude-code/opus-5.5 · 1810a79
No code. Section references checked against DESIGN: A-4 in §7.1, §9.4.2 normalization, §9.5 step 1's 2,000-character cap, §10.1–10.5, §14.2 query provenance, the 1/10/100% visibility levels (§3.3, E7), ADR-0013's cost protocol, ADR-0015's grid and consequences, ADR-0005's digest 0a109f42…e59f.

### 2026-10-19T23:47:47Z · COMMIT · myan · claude-code/opus-5.5 · parent:1810a79
docs(agreements): ADR-0019, spike S2's CPU measurement method and rules, before any harness
3 files changed, 153 insertions(+)
