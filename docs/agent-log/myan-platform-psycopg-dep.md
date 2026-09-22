# Task log — myan-platform-psycopg-dep

| Field | Value |
|---|---|
| Task | Add psycopg to the dev extra and lock it, split out of the S3 harness branch |
| Module | platform |
| Branch | `myan/platform/psycopg-dep` |
| Worktree | `../wayfinder-wt/myan-platform-psycopg-dep` |
| Operator | myan |
| Agent | claude-code/opus-5 |
| Session | 2026-09-22T18:18Z/18506 |
| Started | 2026-09-22T18:18:12Z |
| Closed when | the last entry says TASK CLOSED (the header is never edited - this file is append-only) |

**Append-only.** Corrections are new entries. Entries are written by `scripts/log.sh` and the
`post-commit` hook; CI rejects a rewritten log (`scripts/check_agent_log.py`).

## Cards read

- (listed by `new-task.sh`; add any you read later as `READ` entries)

## Timeline

### 2026-09-22T18:18:55Z · PLAN · myan · claude-code/opus-5 · d4a5535
Split out of myan/platform/s3-harness, which measured 421 changed lines against the 400 limit in AGENTS.md 2.2. The harness itself is 297 of that and cannot be trimmed without the pressure the task-log exception was written against; uv.lock is 68, and 2.2 already says a generated file large enough to matter gets its own pull request. So the dependency lands first and the harness rebases onto it. Rejected asking for a size waiver: the only agreed exception is the task log, and inventing a second one in a pull request thread puts the reviewer in the position of overriding a rule rather than reviewing code.

### 2026-09-22T18:18:55Z · EDIT · myan · claude-code/opus-5 · d4a5535
pyproject.toml (psycopg[binary]>=3.2 in the dev extra), uv.lock (resolved), docs/context/modules/platform.md (dev-extra bullet, pyproject hash eb49 to 3eff, verified_on, change-log row)

### 2026-09-22T18:18:55Z · TEST · myan · claude-code/opus-5 · d4a5535
uv sync --extra dev then uv run pytest -> 67 passed. uv run python -c 'import psycopg' -> psycopg 3.3.6 on Python 3.14. scripts/check_context_freshness.py -> OK, 3 interface files across 16 cards.

### 2026-09-22T18:19:07Z · HANDOFF · myan · claude-code/opus-5 · d4a5535
Ready for review. Dependency only: psycopg[binary] in the dev extra, its lock entries, and the platform card caught up. Nothing imports it on this branch - the first caller is infra/spikes/s3/run.py on myan/platform/s3-harness, which is held until this merges and then rebases onto it. Review question worth an answer: DESIGN 12 names psycopg 3 as the driver, so this is a dev-extra placement for a dependency the API will need at runtime. Moving it to the main dependency list is a one-line follow-up whenever the API first opens a connection.

### 2026-09-22T18:19:08Z · COMMIT · myan · claude-code/opus-5 · parent:d4a5535
chore(platform): add psycopg to the dev extra and lock it
4 files changed, 108 insertions(+), 3 deletions(-)
