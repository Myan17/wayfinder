# Task log — myan-agreements-schema-snapshot-exemption

| Field | Value |
|---|---|
| Task | Exempt exactly db/schema.sql from the 400-line limit (gupta958 ruling, option A) |
| Module | agreements |
| Branch | `myan/agreements/schema-snapshot-exemption` |
| Worktree | `../wayfinder-wt/myan-agreements-schema-snapshot-exemption` |
| Operator | myan |
| Agent | claude-code/opus-5 |
| Session | 2026-09-23T19:45Z/9620 |
| Started | 2026-09-23T19:45:36Z |
| Closed when | the last entry says TASK CLOSED (the header is never edited - this file is append-only) |

**Append-only.** Corrections are new entries. Entries are written by `scripts/log.sh` and the
`post-commit` hook; CI rejects a rewritten log (`scripts/check_agent_log.py`).

## Cards read

- (listed by `new-task.sh`; add any you read later as `READ` entries)

## Timeline

### 2026-09-23T19:45:36Z · PLAN · myan · claude-code/opus-5 · a6cae0e
gupta958's ruling (relayed by Myan): option A, in its own pull request before the snapshot. Exempt exactly the repository-root path db/schema.sql; every other generated file still counts; the snapshot is the full canonical pg_dump output. Changes: scripts/check_pr_size.py - pure function over numstat rows so the rule is testable without a repository, exact string equality on the path, and git diff --no-renames so a rename into or out of the path is counted as the add and delete it really is rather than a '{a => b}' string; AGENTS.md 2.2 and 7 and WORKING-AGREEMENT.md size row name the exemption and why (generated, verified mechanically by db/dump-schema.sh and the drift check). Tests: exact path exempt; lookalikes counted (db/schema.sql.bak, db/Schema.sql, db/schema.sqlx, sub/db/schema.sql, ./db/schema.sql as git never prints, db/schema/sql); other generated files counted (uv.lock); task log still exempt; one end-to-end run on a temporary repository. This pull request contains no schema.sql, so it does not benefit from its own rule.

### 2026-09-23T19:47:06Z · EDIT · myan · claude-code/opus-5 · a6cae0e
scripts/check_pr_size.py: rule moved into exempt_paths(branch) and tally(numstat, branch), pure and testable; exemption is string equality against {the task log, 'db/schema.sql'}; git diff now passes --no-renames; docstring states both exceptions and the ruling; output names the exempt paths. AGENTS.md 2.2: two exact-path exceptions with the reasons, every other generated file counts, an exemption never ships in the pull request that benefits from it; section 7's size row names db/schema.sql. WORKING-AGREEMENT.md size row: same. scripts/tests/test_check_pr_size.py: 17 tests.

### 2026-09-23T19:47:06Z · TEST · myan · claude-code/opus-5 · a6cae0e
uv run pytest -> 98 passed (81 + 17 new). New: exact db/schema.sql exempt; task log still exempt; ten lookalikes counted (db/schema.sql.bak, db/schema.sqlx, db/Schema.sql, db/schema/sql, sub/db/schema.sql, apps/api/db/schema.sql, schema.sql, db/schema.sql/extra, ./db/schema.sql, db/{old => schema.sql}); uv.lock, CODEOWNERS and a view file counted; another task's log counted; end to end on a temporary repository, moving a 500-line file onto db/schema.sql exits 1 with 500 counted. Mutations, each restored: exemption widened to endswith('schema.sql') -> lookalike tests fail; --no-renames removed -> the end-to-end rename test fails. ruff clean on both files.

### 2026-09-23T19:47:07Z · COMMIT · myan · claude-code/opus-5 · parent:a6cae0e
feat(agreements): exempt exactly db/schema.sql from the size limit, per ruling
5 files changed, 177 insertions(+), 31 deletions(-)

### 2026-09-23T19:47:49Z · HANDOFF · myan · claude-code/opus-5 · 11a71ce
#29 open, CI green. After it merges: #30 (db/dump-schema.sh + full db/schema.sql, ORIENT item 2 done #25-#30), which needs #28 merged first.

### 2026-09-23T19:47:49Z · COMMIT · myan · claude-code/opus-5 · parent:11a71ce
docs(agreements): hand off #29
1 file changed, 3 insertions(+)

### 2026-09-23T20:24:08Z · DECIDE · myan · claude-code/opus-5 · 3583478
#28 merged as 71415ef, putting this branch BEHIND. Rebased onto origin/main, no conflicts. Force-push over c81a43d required (AGENTS.md 2.2); main dismisses stale approvals.

### 2026-09-23T20:24:08Z · TEST · myan · claude-code/opus-5 · 3583478
After the rebase: uv run pytest -> 98 passed; identity, ownership, size (177), agent-log, CODEOWNERS, context-freshness OK.

### 2026-09-23T20:24:09Z · COMMIT · myan · claude-code/opus-5 · parent:3583478
docs(agreements): record the rebase onto #28
1 file changed, 6 insertions(+)
