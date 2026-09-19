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
| Status | open |

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
