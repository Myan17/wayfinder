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

### 2026-09-26T16:29:57Z · TEST · myan · claude-code/opus-5.5 · 6d11737
Remaining six at 1 run each on 6d11737: B4-pushkill PASS (async-push fix confirmed), B5-push PASS, B5-kill PASS, B5-pushkill PASS. B2-pause FAIL S5-4: events [claim 464aeaa9 d=2, claim 3a69677a d=2, activated gen=4 d=2 token=3a69677a]; the harness attributes the activation to the resumed worker - not yet known whether 3a69677a is the resumed worker or the takeover (harness attribution bug vs protocol finding). B4'-pause ERROR: w1: no "EVENT " within 30s. Now 15/17 at 1 run.

### 2026-09-27T20:38:08Z · TEST · myan · claude-code/opus-5.5 · 6d11737
Root cause of B2-pause and B4'-pause (found with temporary stderr diagnostics, since removed). The fence in activate() scanned 'claim_expires_at > now()' into a Go bool. After the takeover released its claim (claim_expires_at NULL), the comparison was NULL, pgx failed with 'cannot scan NULL into *bool', and Work returned that error instead of refusing. River then retried the job, which explains both earlier symptoms: the retry claimed and activated a redundant rebuild, or nothing came within 30 s. Fix: coalesce(claim_expires_at > now(), false), as reconcileOnce already does; a released claim is not live. Second bug, in the harness only: pausedTakeover stopped on any EVENT line containing 'refused', so the 'failed ... reason="activation refused"' line ended the read before the 'refused' event that S5-4 checks for. It now matches the event prefix, as rules.go does. Result: B2-pause 3/3 and B4'-pause 3/3 pass, and all 17 scenarios pass at 1 run each on this commit's code.

### 2026-09-27T20:38:08Z · COMMIT · myan · claude-code/opus-5.5 · parent:6d11737
fix(platform): S5 fence treats a released claim as not live; pause read stops on the event
3 files changed, 18 insertions(+), 5 deletions(-)

### 2026-09-27T21:32:07Z · TEST · myan · claude-code/opus-5.5 · b09a5f7
Mutation checks on b09a5f7, all 17 scenarios. Each mutant was built from a patched copy and the source restored (git status clean).
M1, no claim-liveness fence: SURVIVES. The pause scenarios are refused by the CAS on active_generation_id, since w2 has already moved it. ADR-0004 S5-4 counts either fence ('touches 0 rows, or its claim check fails'), so the handoff's expectation that M1 fails S5-4 was wrong.
M2, no final head check: SURVIVES. The activation fence's desired != d and the post-activation re-read backstop it; the head check is an early exit.
M3, no reconciler: KILLED. S5-1 fails in B1-kill, B2-kill, B2-pushkill, B3-push, B3-kill, B3-pushkill, B4-kill, B4-pushkill and B5-kill; the pause scenarios error because nobody re-enqueues.
M4, no CAS (claim fence kept): SURVIVES. The claim fence refuses.
M5, both fences removed: caught as ERROR in both pause scenarios. The river_job error was 'duplicate key value violates unique constraint "one_active_per_repo" (SQLSTATE 23505)', so the schema's partial unique index is a third layer.
M6, naive activation (no fences, retire whatever is active): KILLED, S5-4 FAIL in B2-pause and B4'-pause, 2/2 runs each, on all three S5-4 checks (activated, not refused, 1 row not failed or live).
Conclusion: S5-4 is enforced in depth (claim fence, CAS, one_active_per_repo), and the harness detects a stale activation when all three are gone.

### 2026-09-27T21:42:29Z · TEST · myan · claude-code/opus-5.5 · b09a5f7
ADR-0004 full run, 17 scenarios x 20 runs, binary built from b09a5f7, River v0.47.0, ParadeDB at localhost:55432 via make db-up: every scenario 'pass 20 fail 0 error 0'. Run time (not judged): median 2.193s, max 2.849s over 340 runs. Harness verdict: 'S5-1..S5-5: no failure in any run of any scenario'. Exit 0.

### 2026-09-27T21:42:30Z · COMMIT · myan · claude-code/opus-5.5 · parent:b09a5f7
test(platform): S5 mutation checks and the 17x20 run, logged
1 file changed, 13 insertions(+)

### 2026-09-27T21:44:03Z · EDIT · myan · claude-code/opus-5.5 · 207e521
Moved type scenario and observe() (the S5-3 check) from scenarios.go into rules.go, where the rules live, so the harness can be split into parts that compile on their own. Code moved, not changed; 17/17 scenarios pass at 1 run on the refactored binary.

### 2026-09-27T21:44:03Z · COMMIT · myan · claude-code/opus-5.5 · parent:207e521
refactor(platform): S5 scenario type and S5-3 observer live with the rules
3 files changed, 23 insertions(+), 20 deletions(-)

### 2026-09-27T21:44:17Z · DECIDE · myan · claude-code/opus-5.5 · 0718ea2
The S5 harness is 1,000+ lines against the 400-line limit, so it ships as three stacked PRs, split by function as the reviewer prefers. Part 1 (this branch): go.mod/go.sum with River v0.47.0 pinned, protocol.go (the §9.3.3-9.3.5 IndexRepo protocol, including the claim-liveness fix), worker.go, and a main.go with only the worker command. Part 2, myan/platform/s5-harness-rules: harness.go (databases, seeding, worker processes) and rules.go (S5-1 to S5-5). Part 3, myan/platform/s5-harness-results: scenarios.go, the run command, the 17x20 output, ADR-0004's Decision, the DESIGN §9.3.3 lease_* -> claim_* prose, and ORIENT item 4 done. Each part compiles and vets on its own (checked in a scratch module). The full code is at 0718ea2 on this branch's history.

### 2026-09-27T21:44:17Z · COMMIT · myan · claude-code/opus-5.5 · parent:0718ea2
feat(platform): S5 part 1 of 3 — IndexRepo protocol and worker under River v0.47.0
5 files changed, 5 insertions(+), 602 deletions(-)

### 2026-09-28T01:09:49Z · DECIDE · myan · claude-code/opus-5.5 · 6026ec1
Review of #45 by gupta958: B3 fired before the final 'SELECT desired_generation', but ADR-0004 defines B3 as 'between reading D and deciding to activate'. A push at B3 was visible to the read, so the worker just rebuilt, and the stale-read case, where the activation fence must refuse, was never exercised. The barrier now fires after Scan(&now) succeeds and before 'if now != d'. Every B3 result so far (both 340/340 runs and the mutation checks) was taken with the wrong order and is re-run in part 3.

### 2026-09-28T01:09:50Z · COMMIT · myan · claude-code/opus-5.5 · parent:6026ec1
fix(platform): S5 barrier B3 after the final read of D, as ADR-0004 defines it
2 files changed, 6 insertions(+), 1 deletion(-)
