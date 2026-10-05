# Task log — myan-eval-data-s1-dataset-checks

| Field | Value |
|---|---|
| Task | S1 dataset checks: canonical order, per-line schema, SHA-256 and counts against the manifest, before the pairs file lands (ORIENT item 5) |
| Module | eval-data |
| Branch | `myan/eval-data/s1-dataset-checks` |
| Worktree | `../wayfinder-wt/myan-eval-data-s1-dataset-checks` |
| Operator | myan |
| Agent | claude-code/opus-5.5 |
| Session | 2026-10-05T01:53Z/93efd94 |
| Started | 2026-10-05T01:53:37Z |
| Closed when | the last entry says TASK CLOSED (the header is never edited - this file is append-only) |

**Append-only.** Corrections are new entries. Entries are written by `scripts/log.sh` and the
`post-commit` hook; CI rejects a rewritten log (`scripts/check_agent_log.py`).

## Cards read

- (listed by `new-task.sh`; add any you read later as `READ` entries)

## Timeline

### 2026-10-05T01:53:43Z · PLAN · myan · claude-code/opus-5.5 · 93efd94
Add eval/miners/s1/dataset.py with problems(pairs_bytes, manifest) returning every failure of the four checks gupta958 required on #50: canonical order by (github_repo_id, pr, issue), strictly increasing so duplicates fail; each line valid JSON and valid against $defs/pair; SHA-256 of the file equal to pairs_file.sha256; total, strong and weak counts equal to the manifest's, which must itself pass count_problem. Pair validation is stdlib code checked against the schema's required list and property types by a test, so the two cannot drift. Rejected: adding jsonschema as a dependency, which changes the lock for one nine-field object. A CLI entry point (python -m eval.miners.s1.dataset) lets CI refuse the dataset; wiring it into ci.yml waits for the PR that commits the file.

### 2026-10-05T01:55:11Z · TEST · myan · claude-code/opus-5.5 · 93efd94
uv run --extra dev pytest eval/miners/tests: 60 passed (20 new in test_s1_dataset.py). Mutation check, 8 mutants in dataset.py, each killed by exactly one test: order compare < instead of <=, bool accepted as integer, naive t_g accepted, split enum skipped, final-newline check removed, SHA-256 check inverted, empty gold accepted, manifest count_problem dropped. ruff check and ruff format --check clean on both new files. CLI smoke: python -m s1.dataset from eval/miners on an empty file with weak_count 1 printed both problems and exited 1.

### 2026-10-05T01:55:11Z · COMMIT · myan · claude-code/opus-5.5 · parent:93efd94
feat(eval-data): S1 pairs file landing checks — order, schema, SHA-256, counts
4 files changed, 278 insertions(+), 1 deletion(-)
