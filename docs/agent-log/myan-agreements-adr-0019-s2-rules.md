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

### 2026-10-19T23:47:47Z · HANDOFF · myan · claude-code/opus-5.5 · 6daa17b
PR for gupta958: five Reviewer-decides points in ADR-0019. After merge: if gupta958 rules 9c first, that harness next; the S2 harness either way; item 7's A1 run stays blocked on ORIENT 9b (Myan provisions the A1).

### 2026-10-19T23:47:47Z · COMMIT · myan · claude-code/opus-5.5 · parent:6daa17b
docs(agents): hand ADR-0019 to gupta958
1 file changed, 3 insertions(+)

### 2026-10-19T23:57:28Z · READ · myan · claude-code/opus-5.5 · a3c9f77
gupta958 on #85 (relayed by Myan), five rulings: (1) cross-encoder/ms-marco-MiniLM-L6-v2, fix the extra hyphen, pin the ARM64 ONNX artifact, revision, SHA-256 and tokenizer revision, re-measure if E3 picks another artifact; (2) SQL at the real S1 size and at 60k, padding is scale evidence with its fraction reported; (3) API overhead and token relay deferred to L1, no stand-in endpoint; (4) warm for the nominal budget, cold separately, no answer-cache credit; (5) 9c's canonical two-leg query lands before the S2 harness. Blocking: no /proc/<pid>/stat utime+stime per call (tick resolution), high-resolution accounting for Postgres and Ollama with all Ollama threads defined, calibration on that exact path; cold passes separate with the exact reset; explain how the calibration is independent for external processes.

### 2026-10-19T23:57:28Z · EDIT · myan · claude-code/opus-5.5 · a3c9f77
ADR-0019 revised. Reranker pinned from Hugging Face's API and a download: revision 233902d2, onnx/model_qint8_arm64.onnx 23,200,716 bytes sha256 3573b6b9… (matches the LFS oid), four tokenizer files' sha256. Accounting: Ollama by its container's cgroup v2 usage_usec (all threads of serve and runner, including exited ones), Postgres backend by /proc/<host pid>/schedstat ns via NSpid with parallel query off, rerank by thread_time_ns; counter resolution checks. Cold: one query per cold pass, 50 fixed queries, a six-step reset. Calibration: machine idle time from /proc/stat as an independent reference, minus idle baseline and the harness's own CPU, ±5% per path. S2-1 names L1 for the two deferred rows; S2-4 at both sizes; S2-7 uses warm; rulings section; order of work with 9c second.

### 2026-10-19T23:57:28Z · DECIDE · myan · claude-code/opus-5.5 · a3c9f77
Choices the rulings left open, raised to gupta958 in the brief: max_parallel_workers_per_gather = 0 so a call is one backend; the cold sample is 50 dev queries, first 50 by sha256(group_id); Ollama idle CPU reported, not subtracted; machine idle time as the calibration reference.

### 2026-10-19T23:57:28Z · COMMIT · myan · claude-code/opus-5.5 · parent:a3c9f77
docs(agreements): ADR-0019 per gupta958's review — pinned reranker, high-resolution accounting, separate cold passes, independent calibration
2 files changed, 151 insertions(+), 61 deletions(-)

### 2026-10-19T23:57:28Z · HANDOFF · myan · claude-code/opus-5.5 · f7d1f30
Revised for gupta958's re-review of #85. After merge: item 9c's canonical two-leg query harness (ruling 5), then the S2 harness; only the A1 run is blocked (9b).

### 2026-10-19T23:57:28Z · COMMIT · myan · claude-code/opus-5.5 · parent:f7d1f30
docs(agents): hand ADR-0019's revision back to gupta958
1 file changed, 3 insertions(+)

### 2026-10-20T00:06:04Z · READ · myan · claude-code/opus-5.5 · ccd3ecb
gupta958's second review of #85 (relayed by Myan): two blockers. (1) parallel query off does not stop pg_search or another extension creating backend threads; schedstat measures one task; add a preflight that detects thread creation, transient included, and either count all backend threads at high resolution or stop. (2) calibration reference: elapsed x 2 - idle counts iowait and steal; define the exact /proc/stat fields, exclude idle, iowait and steal, avoid double-counting guest; add a noise gate on before/after background. Four open choices accepted. Pinned ONNX and tokenizer sizes and hashes independently verified by gupta958.

### 2026-10-20T00:06:04Z · EDIT · myan · claude-code/opus-5.5 · ccd3ecb
ADR-0019: the backend is charged through its process CPU clock (clock_getcpuclockid on the host pid, then clock_gettime), which sums the scheduler runtime over the whole thread group, live and exited. New backend thread preflight: strace -f on clone/clone3/fork/vfork over 2 sizes x 3 selectivities, warm and cold; none means the process clock must match the main thread's schedstat within 10 us; threads only are recorded and the clock must be >= schedstat; any child process is an error. Calibration: executed = user + nice + system + irq + softirq from /proc/stat's cpu line, excluding idle, iowait and steal, guest not added (already in user/nice); 60 s background before and after each block; noise gate |b_after - b_before| x elapsed <= 1% of the reference, else error; iowait and steal reported. Second-review section, S2-8 provenance and the Error outcome updated.

### 2026-10-20T00:06:04Z · COMMIT · myan · claude-code/opus-5.5 · parent:ccd3ecb
docs(agreements): ADR-0019 per gupta958's second review — every backend thread counted, exact calibration fields, noise gate
2 files changed, 86 insertions(+), 22 deletions(-)

### 2026-10-20T00:06:05Z · HANDOFF · myan · claude-code/opus-5.5 · 32f771b
Second revision for gupta958's re-review of #85. After merge: item 9c's canonical two-leg query harness, then the S2 harness; only the A1 run is blocked (9b).

### 2026-10-20T00:06:05Z · COMMIT · myan · claude-code/opus-5.5 · parent:32f771b
docs(agents): hand ADR-0019's second revision back to gupta958
1 file changed, 3 insertions(+)
