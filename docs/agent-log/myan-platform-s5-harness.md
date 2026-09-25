# Task log — myan-platform-s5-harness

| Field | Value |
|---|---|
| Task | S5 harness: River v0.47.0 scheduling proof against ADR-0004's rules (ORIENT item 4) |
| Module | platform |
| Branch | `myan/platform/s5-harness` |
| Worktree | `../wayfinder-wt/myan-platform-s5-harness` |
| Operator | myan |
| Agent | claude-code/opus-5 |
| Session | 2026-09-25T02:50Z/19159 |
| Started | 2026-09-25T02:50:01Z |
| Closed when | the last entry says TASK CLOSED (the header is never edited - this file is append-only) |

**Append-only.** Corrections are new entries. Entries are written by `scripts/log.sh` and the
`post-commit` hook; CI rejects a rewritten log (`scripts/check_agent_log.py`).

## Cards read

- (listed by `new-task.sh`; add any you read later as `READ` entries)

## Timeline

### 2026-09-25T15:59:41Z · PLAN · myan · claude-code/opus-5 · 2bddc30
S5 harness for ADR-0004 (merged in #34). apps/ingestd/cmd/s5spike (platform-owned cmd/**), River v0.47.0 pinned in apps/ingestd/go.mod as the ADR says. Worker: the 9.3.3-9.3.5 protocol with a stand-in build (one generation, representation, occurrence) and barriers B1, B2, B3, B4', B4, B5, which print BARRIER and park on stdin. Orchestrator 'run': per run a fresh template0 database with every migration's up section plus rivermigrate; seed ADR-0004's baseline; assert the five preconditions (a failure is an error); initial push (desired 1 -> 2 plus InsertTx, no unique opts); start worker w1 at the scenario's barrier; inject push / kill / push-then-kill / pause-and-takeover; start a replacement w2 after a kill; quiesce (no job outstanding on a live worker, no live claim, a reconciler pass enqueues nothing) without relying on River's stuck-job rescue; check S5-1..S5-5 (S5-3 also at every poll). Claim TTL 1.5 s.

### 2026-09-25T15:59:41Z · EDIT · myan · claude-code/opus-5 · 2bddc30
WIP: cmd/s5spike/{protocol,worker,harness,scenarios,rules,main}.go; go.mod/go.sum add River v0.47.0, riverpgxv5, pgx v5.11.0, google/uuid v1.6.0.

### 2026-09-25T15:59:41Z · TEST · myan · claude-code/opus-5 · 2bddc30
Harness bugs found and fixed, none in the protocol: (1) build SQL used $2 as both bigint and text -> 'inconsistent types deduced'; (2) activation steps passed two args to one-parameter statements -> 'mismatched param and argument count' - while broken, the reconciler kept re-enqueueing every ~1.5 s exactly as designed; (3) push-then-kill at B4 deadlocked the harness: a synchronous push waited on the row lock the parked worker held - now asynchronous, kill releases the lock. Results so far, 1 run each: B1-push, B1-kill, B1-pushkill, B2-push, B2-kill, B2-pushkill, B3-push, B3-kill, B3-pushkill, B4-push, B4-kill all PASS. Not yet run with the fix: B4-pushkill, B5-push, B5-kill, B5-pushkill, B2-pause, B4'-pause.

### 2026-09-25T15:59:41Z · HANDOFF · myan · claude-code/opus-5 · 2bddc30
State: harness builds (go vet clean), 11/17 scenarios pass at 1 run; B4-pushkill fix untested. Next, in order: (1) rerun the six remaining scenarios at 1 run: build with 'cd apps/ingestd && go build -o /tmp/s5spike ./cmd/s5spike', DB via 'make db-up', then '/tmp/s5spike run -admin postgresql://wayfinder:spike_local_only_not_a_secret@localhost:55432/s3spike -root . -runs 1 [-scenario NAME]' from the repo root; (2) mutation checks proving the harness can fail - e.g. drop the claim-liveness fence in activate() (pause scenarios must fail S5-4), drop the final head check; (3) the full 17 x 20 run (ADR-0004), quote the output; (4) split for the 400-line limit (go.sum counts) - likely protocol+worker+go.mod first, orchestrator+rules second, results+ADR decision+DESIGN 9.3.3 lease_* -> claim_* prose third; (5) fill ADR-0004's Decision; ORIENT item 4 done in the last PR. Brief gupta958 on each PR with review_handoff brief (or gh pr comment with @Gupta958 until #35 merges).

### 2026-09-25T15:59:49Z · COMMIT · myan · claude-code/opus-5 · parent:2bddc30
feat(platform): S5 harness in progress — protocol, worker, orchestrator, rules
9 files changed, 1001 insertions(+), 1 deletion(-)
