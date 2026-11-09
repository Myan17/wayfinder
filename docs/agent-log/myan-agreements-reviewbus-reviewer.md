# Task log — myan-agreements-reviewbus-reviewer

| Field | Value |
|---|---|
| Task | Review bus: the reviewer's pass over one PR (REVIEW-BUS.md §2, §4; off-plan, directed by Myan) |
| Module | agreements |
| Branch | `myan/agreements/reviewbus-reviewer` |
| Worktree | `../wayfinder-wt/myan-agreements-reviewbus-reviewer` |
| Operator | myan |
| Agent | claude-code/opus-5.5 |
| Session | 2026-11-09T08:00Z/28521 |
| Started | 2026-11-09T06:47:44Z |
| Closed when | the last entry says TASK CLOSED (the header is never edited - this file is append-only) |

**Append-only.** Corrections are new entries. Entries are written by `scripts/log.sh` and the
`post-commit` hook; CI rejects a rewritten log (`scripts/check_agent_log.py`).

## Cards read

- (listed by `new-task.sh`; add any you read later as `READ` entries)

## Timeline

### 2026-11-09T06:47:44Z · PLAN · myan · claude-code/opus-5.5 · 386f302
Off-plan (Myan's direction, quoted in myan-agreements-reviewbus-protocol's DECIDE). scripts/reviewbus/reviewer.py: review_pr(pr, gh, cfg, ...) is one pass over one PR. Read the mode (unset or unknown is off); read the PR and its comments; rebuild state, and act only when it is 'requested'; check the PR out at its head in a throwaway detached worktree of a local clone (fetching main and pull/N/head, which a public repository needs no credentials for); ask Codex through agents.review with the repository's visibility, an AgentError becoming a needs_human verdict; run gates.decide; re-read the head and post nothing if it moved; post review_result as gupta958 (approve for would_approve or approve_and_merge, changes, or needs_human, which also covers round-limit escalations because rule 8 keeps escalate for Myan17); and only for approve_and_merge in 'on' mode, approve and merge pinned to the reviewed head. Shadow never calls approve or merge, pinned by a test. dry_run posts nothing. github.py gains visibility() and pull()'s base sha. Rulings and cli.py follow in the next PR.

### 2026-11-09T06:49:26Z · TEST · myan · claude-code/opus-5.5 · 386f302
scripts/tests/reviewbus: 209 passed (reviewer: 14 — shadow posts would-approve with the @Gupta958 line and never approves or merges, and the next pass sees reviewed; on approves and merges pinned to the reviewed head only when every gate holds, and a tier path gets needs_human; unset, off, ON and unknown modes do nothing at all; no request, no review; codex gets the checkout, both shas, visibility and the PR text; changes posted with findings; a failed review or checkout posts needs_human and never approves; a head that moves mid-review posts nothing; a dry run reviews but posts nothing; every action maps to a verdict state accepts. github: base sha and visibility). Real checkout() smoke test on merged PR #125: fetched pull/125/head, the detached worktree was at that head with rulings.py present, and it was removed afterwards. ruff clean.

### 2026-11-09T06:49:27Z · COMMIT · myan · claude-code/opus-5.5 · parent:386f302
feat(agreements): review bus — the reviewer's pass over one pull request
5 files changed, 325 insertions(+), 1 deletion(-)

### 2026-11-09T06:53:28Z · EDIT · myan · claude-code/opus-5.5 · 4b54c36
Codex round 1 (before the PR): changes, four blocking, each verified. (f1) pull() read baseRefOid without asking gh for it, so a real run would crash; the query now asks for it, and the fake gh answers only the fields requested, so a test fails if a field is read but not asked for. (f2) this repository's core.hooksPath=.githooks made 'git worktree add' run a post-checkout hook the PR adds, outside the sandbox: every checkout git call now runs with core.hooksPath=/dev/null, fsmonitor off, no credential helper, submodules off, GIT_CONFIG_GLOBAL=/dev/null, GIT_CONFIG_NOSYSTEM, no prompt, and no GIT_/GH_/GITHUB_ variables. (f3) the mode, checks and description were read before the model ran; the switch, the PR and the bus are now all read again after it, and the gates decide on those. (f4) a stop or a duplicate pass during the review was missed; after the model, the state must still be 'requested' at the same round, and a per-PR flock lets only one pass act.

### 2026-11-09T06:53:29Z · TEST · myan · claude-code/opus-5.5 · 4b54c36
scripts/tests/reviewbus: 214 passed (new: the fake gh honours --json fields; a check failing during the review leaves only a needs_human comment; the switch turned off during the review posts nothing; an escalation posted during the review posts nothing; a second pass skips while the first holds the lock; and a real-git test in which a PR adds an executable .githooks/post-checkout to a clone configured with core.hooksPath=.githooks: the reviewer's checkout leaves the marker absent, and a plain worktree add of the same commit creates it, so the test can fail). ruff clean.

### 2026-11-09T06:53:29Z · COMMIT · myan · claude-code/opus-5.5 · parent:4b54c36
fix(agreements): review bus reviewer runs no PR hooks and decides on fresh evidence
5 files changed, 148 insertions(+), 22 deletions(-)

### 2026-11-09T06:56:01Z · DECIDE · myan · claude-code/opus-5.5 · b503f3c
Codex round 2: f1, f3 and f4 fixed; f2 only in part, verified: a filter defined in the clone's own .git/config can still be selected by the PR's .gitattributes, and git still saw HOME and SSH_AUTH_SOCK. The PR was also at 422 lines. So the checkout leaves this PR: review_pr now takes open_checkout as a required argument, and the hardened checkout (hooks, filters, credentials) moves to scripts/reviewbus/checkout.py in the next PR with the CLI, where it gets its own Codex review and real-git tests. The removed code is kept for that PR.

### 2026-11-09T06:56:01Z · COMMIT · myan · claude-code/opus-5.5 · parent:b503f3c
refactor(agreements): review bus reviewer takes its checkout as an argument
3 files changed, 7 insertions(+), 80 deletions(-)
