# Task log — myan-authz-lease-predicate

| Field | Value |
|---|---|
| Task | Implement the authorization predicate: leases, fail-closed scope, SQL fragment |
| Module | authz |
| Branch | `myan/authz/lease-predicate` |
| Worktree | `../wayfinder-wt/myan-authz-lease-predicate` |
| Operator | myan |
| Agent | claude-code/opus-5 |
| Session | 2026-09-18T19:10Z/authz-1 |
| Started | 2026-09-19T00:13:50Z |
| Status | closed |

**Append-only.** Corrections are new entries. Entries are written by `scripts/log.sh` and the
`post-commit` hook; CI rejects a rewritten log (`scripts/check_agent_log.py`).

## Cards read

- (listed by `new-task.sh`; add any you read later as `READ` entries)

## Timeline

### 2026-09-19T00:13:59Z · READ · myan · claude-code/opus-5 · 91b31fd
docs/context/modules/authz.md (own card), docs/context/modules/webhooks.md (dependency: records facts, never decides), DESIGN 9.1.

### 2026-09-19T00:13:59Z · PLAN · myan · claude-code/opus-5 · 91b31fd
Pure-logic core first: AuthorizedScope assembly from leased facts + the SQL predicate builder, with a RepoFactStore protocol so tests use fixtures instead of Postgres (no Docker daemon on this machine). Rejected starting with the DB layer: it would block every test behind an unavailable service and would not exercise the lease semantics any earlier.

### 2026-09-19T00:17:30Z · TEST · myan · claude-code/opus-5 · 91b31fd
uv run pytest apps/api/tests -q -> 23 passed (8 scope, 6 predicate incl. 1 hypothesis property, 5 refresh, 4 fake-contract). uv run ruff check apps/api -> All checks passed!

### 2026-09-19T00:17:30Z · DECIDE · myan · claude-code/opus-5 · 91b31fd
Anonymous principals hold no grants, enforced in the resolver (fake + future DB query), not inside build_scope. Rejected enforcing it in build_scope: that would silently mask a caller passing grants for an anonymous principal instead of failing the test that found it.

### 2026-09-19T00:17:30Z · EDIT · myan · claude-code/opus-5 · 91b31fd
authz: interface.py (Principal, PrincipalKind, AuthorizedScope), scope.py (RepoFact, build_scope), predicate.py (sql_predicate, assert_rows_authorized, AuthorizationViolation), refresh.py (AccessState, start_refresh, apply_refresh, invalidate_repo), fakes.py (FixtureAuthz).

### 2026-09-19T00:17:30Z · COMMIT · myan · claude-code/opus-5 · parent:91b31fd
feat(authz): leased authorization scope, row predicate and fenced refresh
12 files changed, 884 insertions(+), 1 deletion(-)

### 2026-09-19T00:18:05Z · COMMIT · myan · claude-code/opus-5 · parent:6d17d75
docs(authz): verify the contract card against the landed interface
1 file changed, 22 insertions(+), 10 deletions(-)

### 2026-09-19T00:18:26Z · DECIDE · myan · claude-code/opus-5 · 71e5f5f
Widened scope to 'agreements' for one file: scripts/check_context_freshness.py reported a stale card but never queued it for --fix when the interface did not exist at verified_at, which blocks every first-implementation PR. Fixed here rather than opening a separate branch because the bug blocks this branch's own green build; declared as Scope: authz, agreements in the PR.

### 2026-09-19T00:18:26Z · COMMIT · myan · claude-code/opus-5 · parent:71e5f5f
fix(agents): queue a card for --fix when its interface postdates verified_at
3 files changed, 6 insertions(+), 1 deletion(-)

### 2026-09-19T00:18:36Z · BLOCKED · myan · claude-code/opus-5 · 0b28ab8
scripts/check_context_freshness.py fails on docs/context/modules/platform.md: it is still a PLACEHOLDER while the bootstrap Makefile already exists. Out of this task's scope. Next task: myan/platform/bootstrap-card writes that card (and fixes the ownership globs so tests/ and root files map to a module).

### 2026-09-19T00:18:49Z · HANDOFF · myan · claude-code/opus-5 · 0b28ab8
Authorization kernel complete and green: 23 tests, ruff clean. Landed build_scope (leases, fail-closed), sql_predicate + assert_rows_authorized, fenced refresh (revision token, all-or-nothing pagination, invalidate_repo), FixtureAuthz for consumers. Card verified. Not in this branch: resolve_principal (sessions), authorized_repos (DB layer), reauthorize_manifest (evidence manifests), and the AUTH-01..AUTH-11 suite which needs Postgres. Reviewer: the interesting diffs are scope.py (expiry-denies) and refresh.py (the fencing race). PR must declare Scope: authz, agreements.

### 2026-09-19T00:18:49Z · HANDOFF · myan · claude-code/opus-5 · 0b28ab8
Task closed locally; pull request open for review.

### 2026-09-19T00:18:50Z · COMMIT · myan · claude-code/opus-5 · parent:0b28ab8
docs(agents): close task log for myan-authz-lease-predicate
1 file changed, 10 insertions(+), 1 deletion(-)
