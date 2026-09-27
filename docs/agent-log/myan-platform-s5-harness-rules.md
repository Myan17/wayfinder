# Task log — myan-platform-s5-harness-rules

| Field | Value |
|---|---|
| Task | S5 part 2 of 3: harness (databases, seeding, worker processes) and ADR-0004 rules S5-1 to S5-5 (ORIENT item 4) |
| Module | platform |
| Branch | `myan/platform/s5-harness-rules` |
| Worktree | `../wayfinder-wt/myan-platform-s5-harness-rules` |
| Operator | myan |
| Agent | claude-code/opus-5.5 |
| Session | 2026-09-27T21:44Z/22484 |
| Started | 2026-09-27T21:44:29Z |
| Closed when | the last entry says TASK CLOSED (the header is never edited - this file is append-only) |

**Append-only.** Corrections are new entries. Entries are written by `scripts/log.sh` and the
`post-commit` hook; CI rejects a rewritten log (`scripts/check_agent_log.py`).

## Cards read

- (listed by `new-task.sh`; add any you read later as `READ` entries)

## Timeline

### 2026-09-27T21:44:30Z · PLAN · myan · claude-code/opus-5.5 · 6026ec1
Part 2 of the S5 split (plan in the part 1 log, myan/platform/s5-harness). Stacked on part 1. Adds harness.go (a fresh template0 database per run with every migration plus rivermigrate, ADR-0004's baseline seed, the five preconditions, pushes, and worker processes driven through stdin barriers and signals) and rules.go (S5-1 to S5-5 after quiescence, plus the S5-3 observer). The scenarios and the run command come in part 3, so nothing calls this code yet.

### 2026-09-27T21:44:30Z · TEST · myan · claude-code/opus-5.5 · 6026ec1
go vet ./... clean with parts 1+2. Behaviour is tested in part 3, where the scenarios drive this code. The same code passed 17x20 before the split (log of part 1).

### 2026-09-27T21:44:30Z · COMMIT · myan · claude-code/opus-5.5 · parent:6026ec1
feat(platform): S5 part 2 of 3 — the harness and ADR-0004's rules
3 files changed, 377 insertions(+)
