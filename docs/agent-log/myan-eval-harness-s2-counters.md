# Task log — myan-eval-harness-s2-counters

| Field | Value |
|---|---|
| Task | S2 harness part 3: ADR-0019's per-stage CPU counters, counter checks and the backend thread preflight (ORIENT item 7) |
| Module | eval-harness |
| Branch | `myan/eval-harness/s2-counters` |
| Worktree | `../wayfinder-wt/myan-eval-harness-s2-counters` |
| Operator | myan |
| Agent | claude-code/opus-5.5 |
| Session | 2026-11-03T19:56Z/9225 |
| Started | 2026-11-03T19:57:05Z |
| Closed when | the last entry says TASK CLOSED (the header is never edited - this file is append-only) |

**Append-only.** Corrections are new entries. Entries are written by `scripts/log.sh` and the
`post-commit` hook; CI rejects a rewritten log (`scripts/check_agent_log.py`).

## Cards read

- (listed by `new-task.sh`; add any you read later as `READ` entries)

## Timeline

### 2026-11-03T19:57:06Z · DECIDE · myan · claude-code/opus-5.5 · 416a167
Direction from myan (2026-11-03): 'start S2 harness part 2'. Part 2 merged as #99, so this is read as the next part, part 3 (counters and preflight), which ORIENT item 7 needs next anyway.

### 2026-11-03T19:57:06Z · READ · myan · claude-code/opus-5.5 · 416a167
ADR-0019 setup, 'How CPU is accounted', 'The backend thread preflight', 'Counter checks' and the rulings; eval-harness card. onnxruntime and tokenizers are not in uv.lock yet; Amendment 1 leaves that to the harness, and it belongs with the rerank pass, not this part.

### 2026-11-03T19:57:06Z · PLAN · myan · claude-code/opus-5.5 · 416a167
Two new modules. s2/counters.py: cgroup v2 cpu.stat usage_usec (a container's cgroup found from a host pid's /proc/<pid>/cgroup); the backend's host pid from NSpid, restricted to the Postgres container's cgroup.procs so a pid in another namespace cannot match; the backend's process CPU clock via ctypes clock_getcpuclockid + time.clock_gettime_ns; the rerank thread clock (time.thread_time_ns); main-thread schedstat; /proc/stat executed = user+nice+system+irq+softirq with iowait and steal reported; and the counter checks (cgroup v2, process clock readable, two reads across a busy target with 0 < diff < 10 µs). s2/preflight.py: the strace command, a parser that classifies every clone/clone3/fork/vfork into none, threads only, or a child process, the clock agreement rules (none: |process − schedstat| ≤ 10 µs per call; threads: process ≥ schedstat; child: error), and the six-case warm/cold case list with injected attach/query/reset callables, so the docker/Postgres wiring arrives with the passes part. Pure parsing is tested everywhere with fixtures; the real Linux counters are tested on CI's Ubuntu runner against this test process, and skipped on macOS. Rejected: wiring docker and strace for real now, because without the passes there is nothing to run them against, and it would push this part over 400 lines.

### 2026-11-03T20:06:58Z · EDIT · myan · claude-code/opus-5.5 · 416a167
eval/harness/s2/counters.py, eval/harness/s2/preflight.py (new); eval/harness/tests/test_s2_counters.py, test_s2_preflight.py (new); docs/context/modules/eval-harness.md (interface, invariants, failure modes, tests, change log; two interface files added, hashes via --fix); docs/context/INDEX.md (the eval-harness row's interface files).

### 2026-11-03T20:06:58Z · DECIDE · myan · claude-code/opus-5.5 · 416a167
check_resolution reads the counter twice back to back while the caller keeps the target busy, as ADR-0019's 'Counter checks' says. The first draft put a busy() call between the two reads, which would measure the busy work and fail any counter; it was corrected before commit.

### 2026-11-03T20:06:58Z · TEST · myan · claude-code/opus-5.5 · 416a167
On macOS: uv run pytest eval/harness/tests → 41 passed, 3 skipped (the three Linux-only counter tests); uv run pytest → 430 passed, 28 skipped; ruff check and format clean; check_context_freshness OK, 11 interface files. A local Linux run in Docker was not possible (the Docker daemon did not answer), so the three Linux tests first run on CI's ubuntu-24.04 unit job.

### 2026-11-03T20:06:58Z · COMMIT · myan · claude-code/opus-5.5 · parent:416a167
feat(eval-harness): S2 harness part 3 — ADR-0019's CPU counters, counter checks and the backend thread preflight
7 files changed, 568 insertions(+), 1 deletion(-)
