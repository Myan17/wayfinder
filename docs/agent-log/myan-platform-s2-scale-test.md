# Task log — myan-platform-s2-scale-test

| Field | Value |
|---|---|
| Task | Move the exact 60,000-row test from the db job to the conditional s2 job (gupta958's #108 ruling) |
| Module | platform |
| Branch | `myan/platform/s2-scale-test` |
| Worktree | `../wayfinder-wt/myan-platform-s2-scale-test` |
| Operator | myan |
| Agent | claude-code/opus-5.5 |
| Session | 2026-11-05T03:34Z/10711 |
| Started | 2026-11-05T03:34:39Z |
| Closed when | the last entry says TASK CLOSED (the header is never edited - this file is append-only) |

**Append-only.** Corrections are new entries. Entries are written by `scripts/log.sh` and the
`post-commit` hook; CI rejects a rewritten log (`scripts/check_agent_log.py`).

## Cards read

- (listed by `new-task.sh`; add any you read later as `READ` entries)

## Timeline

### 2026-11-05T03:35:46Z · READ · myan · claude-code/opus-5.5 · 0301eaf
Makefile:49-54 (db-test, skip fails the target); ci.yml s2 job; eval/harness/s2/ci.py:25-35 (DIRS, FILES); eval/harness/s2/compose.yml (postgres is the pinned ParadeDB, superuser wayfinder, 127.0.0.1:55433); db/tests/test_s2_build_path.py:110 (the 60k test); db-test went from 162 s to 933 s on #108 and #109.

### 2026-11-05T03:35:47Z · PLAN · myan · claude-code/opus-5.5 · 0301eaf
Mark the 60k test s2_scale (registered in pyproject). db-test deselects it with -m 'not s2_scale'. A new make s2-scale-test runs only that marker against WAYFINDER_TEST_DSN, failing on a skip or on no test run. The s2 job runs it after the harness's tests against S2's own compose Postgres (same pinned image). s2.ci FILES gains db/tests/test_s2_build_path.py and db/tests/conftest.py, so a change to the test runs the job. Rejected: a separate job with its own db-up, which would run on every PR and defeat the ruling.

### 2026-11-05T03:36:18Z · EDIT · myan · claude-code/opus-5.5 · 0301eaf
pyproject marker s2_scale; Makefile db-test -m 'not s2_scale' and new s2-scale-test; the 60k test marked; ci.yml s2 job step 'the exact 60,000-row build test' (compose up postgres, pg_isready loop, make s2-scale-test); s2.ci FILES + test_build_path, conftest, Makefile; test_s2_ci pins the step and the Makefile selection; platform, eval-harness and schema cards; hashes refreshed.

### 2026-11-05T03:36:18Z · TEST · myan · claude-code/opus-5.5 · 0301eaf
uv run pytest eval/harness/tests/test_s2_ci.py: 23 passed. Selection: -m s2_scale gives 1 selected and 5 deselected (it skips locally, with no DSN); -m 'not s2_scale' gives 2 passed, 3 skipped, 1 deselected. ruff clean, ci.yml parses, make -n s2-scale-test OK, freshness OK. The database run happens only in CI (Docker hangs on this Mac): the s2 job must show '1 passed, 5 deselected' and db-test must no longer run it.

### 2026-11-05T03:36:19Z · COMMIT · myan · claude-code/opus-5.5 · parent:0301eaf
ci(platform): run S2's 60,000-row build test in the s2 job, not db-test
10 files changed, 91 insertions(+), 13 deletions(-)
