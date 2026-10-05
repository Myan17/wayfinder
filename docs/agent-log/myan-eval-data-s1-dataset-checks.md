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

### 2026-10-05T02:20:44Z · DECIDE · myan · claude-code/opus-5.5 · 8d55133
gupta958's review of #56, relayed by myan on 2026-10-04: (1) jsonschema[format-nongpl] in a prerequisite dependency PR with the lock, which is #57; (2) validate $defs/pair with Draft202012Validator and an explicit FormatChecker, since format validation is off by default and date-time needs its optional validator; (3) reject NaN/Infinity in json.loads with a parse_constant that raises; (4) regression tests for invalid timestamps and non-standard numeric constants; (5) keep the final-newline requirement as part of canonical JSONL. This branch is now stacked on #57.

### 2026-10-05T02:20:44Z · EDIT · myan · claude-code/opus-5.5 · 8d55133
dataset.py: the stdlib pair validator (PAIR type map, SHA1, SPLITS, fromisoformat) is replaced by Draft202012Validator over the schema file's $defs/pair with FORMAT_CHECKER; problems name the field path and jsonschema's message; parse() uses parse_constant to refuse NaN, Infinity and -Infinity. Tests: the drift test is replaced by one asserting the validator holds the committed $defs/pair and a format checker; 8 invalid t_g values and 3 constants added. The old fromisoformat check accepted three of those t_g values: '2026-01-02 03:04:05Z', '20260102T030405Z' and '2026-01-02T03:04:05+05'. Card's invariant and test row updated.

### 2026-10-05T02:20:44Z · TEST · myan · claude-code/opus-5.5 · 8d55133
uv run --extra dev pytest eval/miners/tests: 69 passed. Mutation check on dataset.py, all killed: no format_checker (9 tests fail), plain json.loads (3 fail), order compare < instead of <=, SHA-256 check inverted, final-newline check removed, manifest count_problem dropped (1 fail each). ruff check and ruff format --check clean on both files.

### 2026-10-05T02:20:44Z · COMMIT · myan · claude-code/opus-5.5 · parent:8d55133
feat(eval-data): validate pairs with jsonschema; RFC 3339 t_g; refuse NaN
4 files changed, 75 insertions(+), 66 deletions(-)
