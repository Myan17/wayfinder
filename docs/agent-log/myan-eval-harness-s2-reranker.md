# Task log — myan-eval-harness-s2-reranker

| Field | Value |
|---|---|
| Task | S2 harness part 6: the pinned reference reranker and its locked dependencies (ORIENT item 7) |
| Module | eval-harness |
| Branch | `myan/eval-harness/s2-reranker` |
| Worktree | `../wayfinder-wt/myan-eval-harness-s2-reranker` |
| Operator | myan |
| Agent | claude-code/opus-5.5 |
| Session | 2026-11-04T00:15Z/2859 |
| Started | 2026-11-04T00:15:26Z |
| Closed when | the last entry says TASK CLOSED (the header is never edited - this file is append-only) |

**Append-only.** Corrections are new entries. Entries are written by `scripts/log.sh` and the
`post-commit` hook; CI rejects a rewritten log (`scripts/check_agent_log.py`).

## Cards read

- (listed by `new-task.sh`; add any you read later as `READ` entries)

## Timeline

### 2026-11-04T00:16:59Z · PLAN · myan · claude-code/opus-5.5 · 0a95de8
Pin onnxruntime and tokenizers exactly, as Amendment 1 requires before any measurement, in a new optional extra 's2' so the API and CI's dev sync do not install them. The lock adds 351 lines, so the pin is its own pull request and the reranker module (pinned-hash loading, L-token truncation, one intra-op thread) follows. Versions are the newest released before 2026-10-20, two weeks before pinning: uv lock --exclude-newer chose them, then the option was removed from the lock and the lock re-resolved unchanged so the cutoff does not bind later relocks. Rejected: the newest versions (onnxruntime 1.31.1 and huggingface-hub 2.4.0, 8 and 5 days old).

### 2026-11-04T00:16:59Z · TEST · myan · claude-code/opus-5.5 · 0a95de8
uv lock --check OK (51 packages). onnxruntime 1.31.0 and tokenizers 0.23.3 import; SessionOptions.intra_op_num_threads = 1 accepted. The lock has cp313 manylinux_2_28 aarch64 wheels for onnxruntime and abi3 aarch64 wheels for tokenizers, so the A1 installs from wheels. uv sync --extra dev --locked (CI's sync) still OK. uv run pytest: 441 passed, 28 skipped.

### 2026-11-04T00:16:59Z · COMMIT · myan · claude-code/opus-5.5 · parent:0a95de8
build(platform): pin onnxruntime and tokenizers for S2's reference reranker
3 files changed, 382 insertions(+), 1 deletion(-)

### 2026-11-04T00:16:59Z · HANDOFF · myan · claude-code/opus-5.5 · ee01ca2
S2 part 6a: onnxruntime 1.31.0 and tokenizers 0.23.3 pinned in the s2 extra. Next: the reranker module (pinned-hash loading of the ARM64 ONNX artifact and tokenizer files, L-token truncation, intra_op_num_threads = 1), then the services wiring and passes.

### 2026-11-04T00:17:00Z · COMMIT · myan · claude-code/opus-5.5 · parent:ee01ca2
docs(agents): hand off the S2 dependency pin
1 file changed, 3 insertions(+)

### 2026-11-04T00:17:00Z · HANDOFF · myan · claude-code/opus-5.5 · a8a0225
TASK CLOSED. Pull request open for review.

### 2026-11-04T00:17:00Z · COMMIT · myan · claude-code/opus-5.5 · parent:a8a0225
docs(agents): close task log for myan-eval-harness-s2-reranker
1 file changed, 3 insertions(+)

### 2026-11-04T00:17:25Z · COMMIT · myan · claude-code/opus-5.5 · parent:26c3e45
docs(platform): record the s2 extra on the platform card
1 file changed, 6 insertions(+), 2 deletions(-)

### 2026-11-04T00:17:25Z · HANDOFF · myan · claude-code/opus-5.5 · 1e2dfd5
Platform card updated for the s2 extra after check_context_freshness flagged it. TASK CLOSED. Pull request open for review.

### 2026-11-04T00:17:26Z · COMMIT · myan · claude-code/opus-5.5 · parent:1e2dfd5
docs(agents): log the platform card update
1 file changed, 3 insertions(+)

### 2026-11-04T00:46:02Z · DECIDE · myan · claude-code/opus-5.5 · 48f32ca
gupta958's review of #103: the documented S2 sync is uv sync --extra dev --extra s2 --locked. uv sync --extra s2 alone removes the dev extra, including psycopg, which S2's SQL stage needs.

### 2026-11-04T00:46:02Z · TEST · myan · claude-code/opus-5.5 · 48f32ca
uv sync --extra s2 --locked, then import psycopg: ModuleNotFoundError (the defect confirmed). uv sync --extra dev --extra s2 --locked: psycopg 3.3.6, onnxruntime 1.31.0 and tokenizers 0.23.3 import together; uv run --no-sync pytest 441 passed, 28 skipped in that environment. context-freshness --fix platform.

### 2026-11-04T00:46:03Z · COMMIT · myan · claude-code/opus-5.5 · parent:48f32ca
docs(platform): document S2's sync as the dev and s2 extras together
2 files changed, 9 insertions(+), 2 deletions(-)
