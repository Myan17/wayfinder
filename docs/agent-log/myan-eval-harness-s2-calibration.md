# Task log — myan-eval-harness-s2-calibration

| Field | Value |
|---|---|
| Task | S2 harness part 5: ADR-0019's calibration cross-check (ORIENT item 7) |
| Module | eval-harness |
| Branch | `myan/eval-harness/s2-calibration` |
| Worktree | `../wayfinder-wt/myan-eval-harness-s2-calibration` |
| Operator | myan |
| Agent | claude-code/opus-5.5 |
| Session | 2026-11-03T23:15Z/6667 |
| Started | 2026-11-03T23:15:17Z |
| Closed when | the last entry says TASK CLOSED (the header is never edited - this file is append-only) |

**Append-only.** Corrections are new entries. Entries are written by `scripts/log.sh` and the
`post-commit` hook; CI rejects a rewritten log (`scripts/check_agent_log.py`).

## Cards read

- (listed by `new-task.sh`; add any you read later as `READ` entries)

## Timeline

### 2026-11-03T23:15:23Z · PLAN · myan · claude-code/opus-5.5 · 0f8845d
Add s2/calibration.py as pure logic with injected callables, like the preflight: background rate, the block runner (until the path's summed per-call CPU reaches 30 s), the noise gate (1%), the reference (minus mean background and harness CPU, harness CPU kept for rerank), the +/-5% check, and the kernel CPU-time accounting parser for S2-8. Rejected: reading /proc/stat and sleeping inside the module, which would make every rule untestable off Linux and slow; the Docker wiring comes with the passes.

### 2026-11-03T23:17:05Z · TEST · myan · claude-code/opus-5.5 · 0f8845d
uv run pytest: 440 passed, 28 skipped on macOS (431 before; 9 new in test_s2_calibration.py, all platform-independent through Machine's callables). ruff check and format clean. check_context_freshness OK after --fix eval-harness.

### 2026-11-03T23:17:05Z · COMMIT · myan · claude-code/opus-5.5 · parent:0f8845d
feat(eval-harness): add ADR-0019's calibration cross-check
5 files changed, 366 insertions(+), 2 deletions(-)

### 2026-11-03T23:17:29Z · HANDOFF · myan · claude-code/opus-5.5 · a444b06
S2 part 5: s2.calibration, ADR-0019's calibration cross-check as pure logic behind Machine's callables (background 60 s, block to 30 s of summed per-call CPU, background 60 s, 1% noise gate, reference minus mean background and harness CPU except on rerank, 5% band), plus the kernel accounting option for S2-8. Nothing measures yet. Next: the passes and report, which wire Docker, Postgres, Ollama, the reranker and strace into the preflight's and calibration's callables, and pin onnxruntime and tokenizers in uv.lock.

### 2026-11-03T23:17:29Z · COMMIT · myan · claude-code/opus-5.5 · parent:a444b06
docs(agents): hand off the calibration task
1 file changed, 3 insertions(+)

### 2026-11-03T23:17:29Z · HANDOFF · myan · claude-code/opus-5.5 · 3f449b7
TASK CLOSED. Pull request open for review.

### 2026-11-03T23:17:30Z · COMMIT · myan · claude-code/opus-5.5 · parent:3f449b7
docs(agents): close task log for myan-eval-harness-s2-calibration
1 file changed, 3 insertions(+)
