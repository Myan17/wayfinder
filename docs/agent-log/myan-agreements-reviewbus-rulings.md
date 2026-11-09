# Task log — myan-agreements-reviewbus-rulings

| Field | Value |
|---|---|
| Task | Review bus: when a ruling binds, which need Myan's confirm, veto and confirm (ADR-0021 rule 7; off-plan, directed by Myan) |
| Module | agreements |
| Branch | `myan/agreements/reviewbus-rulings` |
| Worktree | `../wayfinder-wt/myan-agreements-reviewbus-rulings` |
| Operator | myan |
| Agent | claude-code/opus-5.5 |
| Session | 2026-11-09T07:00Z/21263 |
| Started | 2026-11-09T05:53:36Z |
| Closed when | the last entry says TASK CLOSED (the header is never edited - this file is append-only) |

**Append-only.** Corrections are new entries. Entries are written by `scripts/log.sh` and the
`post-commit` hook; CI rejects a rewritten log (`scripts/check_agent_log.py`).

## Cards read

- (listed by `new-task.sh`; add any you read later as `READ` entries)

## Timeline

### 2026-11-09T05:53:36Z · PLAN · myan · claude-code/opus-5.5 · 28f5ac1
Off-plan (Myan's direction, quoted in myan-agreements-reviewbus-protocol's DECIDE). scripts/reviewbus/rulings.py, ADR-0021 rule 7: confirm_only(labels, files, ownership) is true for any confirm-only label (bus, agents-md, codeowners, roster, gate-date, cut, authz, egress, acceptance-rule), any unknown label (in doubt, confirm-only), any changed file on the bus, AGENTS.md, CODEOWNERS, ROSTER, ADR-0021 or authz/egress paths (read from OWNERSHIP.md through tier.module_paths), or an unlabeled question on any human-only tier path (REVIEW-BUS §9). binds_at(posted) is posted + 12 hours. status(ruling, posted_at, later comments, now) gives needs_human (the ruler abstained; never binds), vetoed (veto <id> from either account before it binds), confirmed (confirm <id> from either account), bound (12 hours passed, not confirm-only, no veto), awaiting_confirm (confirm-only, no confirm yet) or pending. Times are GitHub's ISO 8601 UTC strings, parsed strictly. A veto after binding does not unbind (the author may have built on it); Myan reverses a bound ruling with a new ruling_request.

### 2026-11-09T05:54:30Z · TEST · myan · claude-code/opus-5.5 · 28f5ac1
scripts/tests/reviewbus: 190 passed (rulings: 30 — each of the nine confirm-only labels; an ordinary label or none on an ordinary path may bind; the bus, AGENTS.md, CODEOWNERS, ROSTER, ADR-0021, authz and egress paths are confirm-only whatever the labels; an unlabeled question on a schema path is confirm-only, a labeled one is not; unknown, non-list and non-string labels and unreadable OWNERSHIP are doubt; binds at exactly 12 hours; veto from either account before the deadline, not a third account or another id; a late veto does not unbind; confirm binds at once, not from before the ruling; confirm-only waits forever, confirm binds, a veto stops it; needs_human never binds; malformed times, confirm_only and naive now refused). ruff clean.

### 2026-11-09T05:54:31Z · COMMIT · myan · claude-code/opus-5.5 · parent:28f5ac1
feat(agreements): review bus — when a ruling binds, and which only Myan can bind
3 files changed, 245 insertions(+)
