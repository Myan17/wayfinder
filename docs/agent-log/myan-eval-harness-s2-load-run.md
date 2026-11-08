# Task log — myan-eval-harness-s2-load-run

| Field | Value |
|---|---|
| Task | S2 load command and report: load the corpus into a new database and write the load report (ORIENT item 7) |
| Module | eval-harness |
| Branch | `myan/eval-harness/s2-load-run` |
| Worktree | `../wayfinder-wt/myan-eval-harness-s2-load-run` |
| Operator | myan |
| Agent | claude-code/opus-5.5 |
| Session | 2026-11-08T18:10Z/18569 |
| Started | 2026-11-08T17:55:56Z |
| Closed when | the last entry says TASK CLOSED (the header is never edited - this file is append-only) |

**Append-only.** Corrections are new entries. Entries are written by `scripts/log.sh` and the
`post-commit` hook; CI rejects a rewritten log (`scripts/check_agent_log.py`).

## Cards read

- (listed by `new-task.sh`; add any you read later as `READ` entries)

## Timeline

### 2026-11-08T17:56:13Z · PLAN · myan · claude-code/opus-5.5 · f1f6d29
New s2.load_run: an argparse command that reads the four mirrors (<owner>__<name>.git, eval/miners/s1/run.py's naming) at the manifest as_of_commit, refuses on count_problems, refuses unless the ingestion Ollama reports version 0.34.2 and nomic-embed-text's pinned digest, creates a new database on the S2 Postgres (refusing an existing one), applies the migrations, runs s2.load.load with s6_ollama.embedder(record=calls, truncate_rejected=True), and writes the JSON report: lease, per-pseudo-repository durations, windows and distinct representations, real and padded counts, padding fraction, every truncated window with count and fraction, the accepted windows' token distribution (nearest-rank p50/p95/max), digests, version, commit, host. --size real|60k; 60k pads to 60,000 and is labelled scale evidence. s6_ollama is imported lazily so the pure parts and their unit tests do not load the schema tests' setup. Rejected: one database holding both sizes; load() seeds 100 pseudo-repositories per call and the passes need each size alone.

### 2026-11-08T18:00:03Z · TEST · myan · claude-code/opus-5.5 · f1f6d29
eval/harness tests: 112 passed, 18 skipped (the two new run() database tests and the existing load tests skip here: Docker does not answer on this Mac, so CI's db job runs them). New test_s2_load_run.py: 7 passed (mirror path and as-of commit, count refusal, version and digest refusal, nearest-rank distribution, report fields for 60k and real, a refusal exits 1 before any load). make test: 501 passed, 43 skipped. ruff check and format clean.

### 2026-11-08T18:00:04Z · COMMIT · myan · claude-code/opus-5.5 · parent:f1f6d29
feat(eval-harness): S2 load command — load the corpus into a new database and write the load report
5 files changed, 381 insertions(+), 1 deletion(-)
