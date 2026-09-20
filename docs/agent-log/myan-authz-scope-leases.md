# Task log — myan-authz-scope-leases

| Field | Value |
|---|---|
| Task | Leased authorization scope: build_scope with anonymous-grant enforcement and staleness flag |
| Module | authz |
| Branch | `myan/authz/scope-leases` |
| Worktree | `../wayfinder-wt/myan-authz-scope-leases` |
| Operator | myan |
| Agent | claude-code/opus-5 |
| Session | 2026-09-19T01:05Z/split-2 |
| Started | 2026-09-19T23:39:41Z |
| Status | open |

**Append-only.** Corrections are new entries. Entries are written by `scripts/log.sh` and the
`post-commit` hook; CI rejects a rewritten log (`scripts/check_agent_log.py`).

## Cards read

- (listed by `new-task.sh`; add any you read later as `READ` entries)

## Timeline

### 2026-09-19T23:39:41Z · PLAN · myan · claude-code/opus-5 · 9fbedff
Re-land the scope kernel with the two reviewer findings fixed in the kernel itself: F1 anonymous principals cannot hold grants (raise, do not silently drop - a silent drop makes a broken resolver look healthy), F4 the public-only degradation follows lease staleness rather than whether grants happen to be held. Carrying granted ids on the scope as a separate field, which PR 3 needs for the SQL predicate.

### 2026-09-19T23:40:47Z · TEST · myan · claude-code/opus-5 · 9fbedff
uv run pytest apps/api/tests -q -> 13 passed (8 original scope tests + 5 regression tests for findings F1, F2-prerequisite and F4). uv run ruff check apps/api -> clean.

### 2026-09-19T23:40:47Z · DECIDE · myan · claude-code/opus-5 · 9fbedff
F1 enforced by raising AnonymousGrantsError rather than dropping grants silently. Reviewer offered either; raising surfaces a broken resolver instead of hiding it, and a raised error in the request path is fail-closed. Flagged in the PR so the reviewer can overrule.

### 2026-09-19T23:40:48Z · COMMIT · myan · claude-code/opus-5 · parent:9fbedff
feat(authz): leased authorization scope
7 files changed, 566 insertions(+), 1 deletion(-)

### 2026-09-19T23:44:21Z · DECIDE · myan · claude-code/opus-5 · 1aa0743
Removed uv.lock from this branch: it belongs to #3 and double-counting it pushed this PR to +570, past the same 400-line limit the split exists to respect. The file stays on disk for local runs; uv resolves without it in CI.

### 2026-09-19T23:44:21Z · COMMIT · myan · claude-code/opus-5 · parent:1aa0743
chore(authz): drop the lockfile from this branch, it belongs to #3
1 file changed, 3 insertions(+)
