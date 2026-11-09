# Task log — myan-agreements-reviewbus-state

| Field | Value |
|---|---|
| Task | Review bus: the PR life cycle rebuilt from comments (REVIEW-BUS.md §4; off-plan, directed by Myan) |
| Module | agreements |
| Branch | `myan/agreements/reviewbus-state` |
| Worktree | `../wayfinder-wt/myan-agreements-reviewbus-state` |
| Operator | myan |
| Agent | claude-code/opus-5.5 |
| Session | 2026-11-09T04:00Z/22287 |
| Started | 2026-11-09T03:29:56Z |
| Closed when | the last entry says TASK CLOSED (the header is never edited - this file is append-only) |

**Append-only.** Corrections are new entries. Entries are written by `scripts/log.sh` and the
`post-commit` hook; CI rejects a rewritten log (`scripts/check_agent_log.py`).

## Cards read

- (listed by `new-task.sh`; add any you read later as `READ` entries)

## Timeline

### 2026-11-09T03:29:56Z · PLAN · myan · claude-code/opus-5.5 · 20d7d25
Off-plan (Myan's direction, quoted in myan-agreements-reviewbus-protocol's DECIDE). scripts/reviewbus/state.py: state(comments, head, roster) rebuilds one PR's bus state from its comments in order, as REVIEW-BUS.md §4 defines it: requested (a review_request for the current head with no result), reviewed with the latest review_result's verdict for that head, stopped after an escalate until either account posts an ordinary comment (rule 10: 'a comment from Myan restarts it'), and the round from the latest request. Comments are parsed by protocol.parse; ignored ones are kept with their reasons for the log. Inputs must be plain JSON data, as gates.decide requires. The local cache is left out: the state is cheap to rebuild every poll, and REVIEW-BUS says deleting it is always safe. github.py follows in its own PR for size. Rejected: storing state anywhere but the PR.

### 2026-11-09T03:31:03Z · DECIDE · myan · claude-code/opus-5.5 · 20d7d25
REVIEW-BUS.md §4 and rule 10 say a comment from Myan restarts a stopped PR. But the author session posts ordinary comments as Myan17 too (review_handoff briefs), so 'any comment' would let the agent restart its own escalation. state.py restarts only on a comment that is exactly 'resume' from either account. Raised in the PR as a question for gupta958.

### 2026-11-09T03:31:03Z · TEST · myan · claude-code/opus-5.5 · 20d7d25
scripts/tests/reviewbus: 112 passed (state: 12 — idle for no request or an old head; requested until its result; a later request for the same head asks again; a result must match the request's round; wrong accounts skipped and logged; escalate stops it and only 'resume' from either account restarts it, not a brief, not the author's new request, not a third account; a dispute stops it, an undisputed fix does not; head prefixes of 7+ lowercase hex; a non-integer round skipped; non-plain inputs refused). ruff clean.

### 2026-11-09T03:31:03Z · COMMIT · myan · claude-code/opus-5.5 · parent:20d7d25
feat(agreements): review bus — one PR's state rebuilt from its comments
3 files changed, 220 insertions(+)

### 2026-11-09T03:33:28Z · EDIT · myan · claude-code/opus-5.5 · 814fa3f
Codex round 1 (before the PR): changes, four blocking findings, each verified. (f1) an undisputed fix_pushed did not request the next round, so the loop stalled; it is now the next request. (f2) a later request overrode a needs_human result on the same head; that head is now closed to the bus, status needs_human. (f3) the author could restart rounds from 1 and escape rule 10; rounds must now count up by one from 1, a third failing round stops the PR, and only 'resume' resets the count. (f4) result field values were not checked; a result now needs the request's head, an int (not bool) round equal to the request's, and a verdict from gates.VERDICTS, and a bad one is skipped without consuming the request.

### 2026-11-09T03:33:28Z · TEST · myan · claude-code/opus-5.5 · 814fa3f
scripts/tests/reviewbus: 119 passed (new: a fix on a new head requests round 2 and takes its result; needs_human holds against a later request on that head but not a new head; round 1 repeated, a first request of round 2, three failing rounds stop, a third-round approve does not, a round-1 request after the stop does not reset, resume does; four malformed results skipped with a valid one after). ruff clean.

### 2026-11-09T03:33:28Z · COMMIT · myan · claude-code/opus-5.5 · parent:814fa3f
fix(agreements): review bus state enforces rounds, needs_human and result fields
3 files changed, 111 insertions(+), 25 deletions(-)
