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

### 2026-11-09T05:56:18Z · EDIT · myan · claude-code/opus-5.5 · fa2eac0
Codex round 1 (before the PR): changes. (f1, blocking, verified) an unlabeled ruling on docs/DESIGN.md could bind by silence, though DESIGN holds the gate dates and the §19.8 cuts; the always-confirm-only paths now include docs/DESIGN.md, ORIENT.md and all of docs/adr/** (acceptance rules), erring safe as rule 7 asks. (f2, minor, verified) the timestamp parser accepted '2026-11- 9' and a lowercase t; it now fullmatches YYYY-MM-DDTHH:MM:SSZ in ASCII digits.

### 2026-11-09T05:56:18Z · TEST · myan · claude-code/opus-5.5 · fa2eac0
scripts/tests/reviewbus: 194 passed (new: an ADR, DESIGN and ORIENT path confirm-only whatever the labels; an unlabeled or schedule-labeled DESIGN question confirm-only; the two loose timestamps refused). ruff clean.

### 2026-11-09T05:56:18Z · COMMIT · myan · claude-code/opus-5.5 · parent:fa2eac0
fix(agreements): review bus rulings protect DESIGN, ORIENT and ADRs, and parse times exactly
3 files changed, 27 insertions(+), 3 deletions(-)

### 2026-11-09T05:59:16Z · HANDOFF · myan · claude-code/opus-5.5 · 7554c1e
Codex round 2: approve, no findings. make test above. PR open for gupta958 (human-only tier). Next, after the merge: reviewer.py (one poll pass per open PR: state, checkout, agents, gates, post; rulings with binds_at and confirm-only) and cli.py (doctor, which refuses a plain-text login for either role; once <pr> --dry-run; watch), the example config and the launchd entry, split for size.

### 2026-11-09T05:59:17Z · COMMIT · myan · claude-code/opus-5.5 · parent:7554c1e
docs(agents): hand off the review bus rulings task
1 file changed, 3 insertions(+)
