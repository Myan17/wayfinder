# Task log — myan-platform-ci-skeleton

| Field | Value |
|---|---|
| Task | CI skeleton: unit job, pinned-extension DB job with the schema drift check, dispatcher (ORIENT item 3, part a) |
| Module | platform |
| Branch | `myan/platform/ci-skeleton` |
| Worktree | `../wayfinder-wt/myan-platform-ci-skeleton` |
| Operator | myan |
| Agent | claude-code/opus-5 |
| Session | 2026-09-24T17:03Z/5530 |
| Started | 2026-09-24T17:03:29Z |
| Closed when | the last entry says TASK CLOSED (the header is never edited - this file is append-only) |

**Append-only.** Corrections are new entries. Entries are written by `scripts/log.sh` and the
`post-commit` hook; CI rejects a rewritten log (`scripts/check_agent_log.py`).

## Cards read

- (listed by `new-task.sh`; add any you read later as `READ` entries)

## Timeline

### 2026-09-24T17:03:52Z · READ · myan · claude-code/opus-5 · 2d3aa08
DESIGN 16.1 (change classes, dispatcher: a skip never counts as a pass), 16.9 (release manifest), 18.1-18.2 (environments, pipeline; actions pinned by SHA), Appendix C (layout); platform card; Makefile; .github/workflows/guardrails.yml; infra/spikes/s3/compose.yml.

### 2026-09-24T17:03:52Z · PLAN · myan · claude-code/opus-5 · 2d3aa08
ORIENT item 3 splits into three pull requests under the size limit: (a) this one, the CI skeleton; (b) the release-manifest format and cache-key derivation (16.9); (c) the Go ingestd scaffold (Appendix C). This part: .github/workflows/ci.yml with three jobs - unit (uv sync --locked, pytest), db on ubuntu-24.04-arm (the pinned ParadeDB digest is linux/arm64, and arm64 is the A1's architecture, so no emulation) running db/tests and the db/dump-schema.sh --check drift check gupta958 asked for, and dispatcher, which runs if: always() and fails unless every required job reports success, so a skipped job can never count as a pass (16.1). Every action pinned by commit SHA to its latest release (18.2). Makefile gains db-up (compose up plus a real-connection wait, because the compose healthcheck reports healthy before first boot finishes - seen in #19), db-test and schema-check, so CI and a laptop run the same commands. Deliberately not in this part: a lint gate - main is not lint-clean (6 ruff errors in scripts/, 19 unformatted files across modules), so gating it now would fail every pull request; it follows a cross-module cleanup. Branch protection must add 'dispatcher' as a required check; that is a repository setting for an owner, not a file.

### 2026-09-24T17:06:00Z · EDIT · myan · claude-code/opus-5 · 2d3aa08
.github/workflows/ci.yml (new): unit, db (ubuntu-24.04-arm), dispatcher (if: always(), fails unless every need is success); checkout v7.0.1 and setup-uv v10.2.0 pinned by commit SHA. Makefile: db-up (compose up plus a real-query wait), db-down, db-test (fails on any skipped test), schema-check. Platform card: interface, invariants, test table, open questions (lint not gated, guardrails.yml still tag-pinned, spike compose reused), change log; hashes recorded.

### 2026-09-24T17:06:00Z · TEST · myan · claude-code/opus-5 · 2d3aa08
make db-up -> healthy and queryable; make db-test -> 15 passed, exit 0; with WAYFINDER_TEST_DSN empty -> 'tests were skipped', exit non-zero; with the database down -> exit non-zero; make schema-check -> current. First version of db-test PASSED with no database: pytest's addopts -q plus the target's -q suppressed the summary line, so the skip check never saw 'skipped' - fixed by dropping the extra -q. Dispatcher script extracted from the YAML and run with four needs payloads: all success -> 0; db skipped, unit cancelled, db failure -> 1 each. Its first version was a Python SyntaxError (escaped quotes inside a single-quoted shell string) that would have failed every run including all-green ones; an earlier check of it was void because PyYAML was missing and the extracted script was empty. Rewritten as a heredoc. uv run pytest -> 98 passed; context-freshness OK.

### 2026-09-24T17:06:00Z · COMMIT · myan · claude-code/opus-5 · parent:2d3aa08
feat(platform): CI skeleton — unit, pinned-extension DB with schema drift, dispatcher
4 files changed, 150 insertions(+), 11 deletions(-)

### 2026-09-24T17:07:52Z · TEST · myan · claude-code/opus-5 · 11383d8
The pull request's own ci run 36031987066: unit success (13 s); pinned-extension integration success (28 s) on the ubuntu24-arm64 runner - paradedb Healthy, db/tests '15 passed in 2.15s', 'db/schema.sql is current'; dispatcher success (unit: success, db: success).

### 2026-09-24T17:07:52Z · HANDOFF · myan · claude-code/opus-5 · 11383d8
#31 open and green end to end. Owner action after merge: add 'dispatcher' as a required status check on main. Next: item 3 part b, the release-manifest format and cache-key derivation (DESIGN 16.9).

### 2026-09-24T17:07:53Z · COMMIT · myan · claude-code/opus-5 · parent:11383d8
docs(platform): CI evidence and handoff
1 file changed, 6 insertions(+)

### 2026-09-24T17:31:21Z · DECIDE · myan · claude-code/opus-5 · 98a3824
gupta958 (relayed by Myan, recorded on #31): ci.yml line 28 ran 'uv run pytest', but the platform card promises CI uses the public command surface. Changed to 'run: make test' so CI and the documented local command cannot diverge. The setup steps keep 'uv sync --extra dev --locked': make setup omits --locked on purpose (a developer adding a dependency re-locks), while CI must fail on a stale lock; raised with the reviewer rather than changed.

### 2026-09-24T17:31:21Z · TEST · myan · claude-code/opus-5 · 98a3824
make test locally -> 98 passed. Every test command in ci.yml is now a make target (make test, make db-test, make schema-check).

### 2026-09-24T17:31:21Z · COMMIT · myan · claude-code/opus-5 · parent:98a3824
fix(platform): CI runs make test, the public command, per review
2 files changed, 7 insertions(+), 1 deletion(-)
