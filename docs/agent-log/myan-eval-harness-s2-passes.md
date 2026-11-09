# Task log — myan-eval-harness-s2-passes

| Field | Value |
|---|---|
| Task | S2 passes: the warm and cold pass protocol and its statistics (ORIENT item 7) |
| Module | eval-harness |
| Branch | `myan/eval-harness/s2-passes` |
| Worktree | `../wayfinder-wt/myan-eval-harness-s2-passes` |
| Operator | myan |
| Agent | claude-code/opus-5.5 |
| Session | 2026-11-09T00:40Z/12693 |
| Started | 2026-11-09T00:27:30Z |
| Closed when | the last entry says TASK CLOSED (the header is never edited - this file is append-only) |

**Append-only.** Corrections are new entries. Entries are written by `scripts/log.sh` and the
`post-commit` hook; CI rejects a rewritten log (`scripts/check_agent_log.py`).

## Cards read

- (listed by `new-task.sh`; add any you read later as `READ` entries)

## Timeline

### 2026-11-09T00:27:30Z · PLAN · myan · claude-code/opus-5.5 · 3e41c5c
New s2.passes, the protocol of ADR-0019's 'Warm and cold measurements are separate passes', with each stage's call injected (the stage wiring follows in the next PR): warm(queries, measure) runs 3 warm-up passes over the full set and 5 timed passes, keeps only the timed calls, and gives the stage cost as the median of the five per-pass means with per-call p50 and p95 over all timed calls; cold(sample, reset, load, measure) requires the 50-query cold sample and, per query, runs reset, then the model load (reported separately), then one call through each stage, with p50 and p95 per stage over the 50. Measured holds CPU ns, wall ns (recorded, never judged) and the embedder's token count for S2-3. Percentiles are nearest-rank, as #118's report uses. Rejected: one runner that also builds the stages' inputs; it would mix Linux counters into code that can be tested anywhere.

### 2026-11-09T00:28:24Z · TEST · myan · claude-code/opus-5.5 · 3e41c5c
pytest eval/harness/tests: 119 passed, 18 skipped. New test_s2_passes.py: 7 passed (warm-up and timed order, median of per-pass means against a skewed pass, nearest-rank p50/p95 over 100 timed calls, empty set refused, cold order reset/load/call for all 50, 49 refused, mixed stages refused). ruff check and format clean. Card: s2.passes in the interface, test row, change log; hashes refreshed.

### 2026-11-09T00:28:24Z · COMMIT · myan · claude-code/opus-5.5 · parent:3e41c5c
feat(eval-harness): S2 passes — the warm and cold pass protocol and its statistics
4 files changed, 238 insertions(+)

### 2026-11-09T00:30:45Z · HANDOFF · myan · claude-code/opus-5.5 · 242c3d3
make test: 508 passed, 43 skipped. PR open for gupta958. Next, after the merge: the stage calls for s2.passes. Embedding: the query Ollama container's cgroup usage_usec around one /api/embed call with num_thread 1 and the search_query template, returning prompt_eval_count. SQL: the backend's process clock around hybrid_sql.execute at each size and level. Rerank: thread_cpu_ns around Reranker.score per (N, L) arm over the two-leg query's top N. Open question in the brief: the SQL k (proposed 50, the largest rerank N).

### 2026-11-09T00:30:45Z · COMMIT · myan · claude-code/opus-5.5 · parent:242c3d3
docs(agents): hand off the S2 passes task
1 file changed, 3 insertions(+)
