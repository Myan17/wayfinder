# Task log — myan-agreements-reviewbus-github

| Field | Value |
|---|---|
| Task | Review bus: every gh call, each under its role's login (REVIEW-BUS.md §7; off-plan, directed by Myan) |
| Module | agreements |
| Branch | `myan/agreements/reviewbus-github` |
| Worktree | `../wayfinder-wt/myan-agreements-reviewbus-github` |
| Operator | myan |
| Agent | claude-code/opus-5.5 |
| Session | 2026-11-09T05:00Z/8761 |
| Started | 2026-11-09T04:01:00Z |
| Closed when | the last entry says TASK CLOSED (the header is never edited - this file is append-only) |

**Append-only.** Corrections are new entries. Entries are written by `scripts/log.sh` and the
`post-commit` hook; CI rejects a rewritten log (`scripts/check_agent_log.py`).

## Cards read

- (listed by `new-task.sh`; add any you read later as `READ` entries)

## Timeline

### 2026-11-09T04:01:00Z · PLAN · myan · claude-code/opus-5.5 · 7fa8252
Off-plan (Myan's direction, quoted in myan-agreements-reviewbus-protocol's DECIDE). #122 merged with no comment on the 'resume' question; its merge keeps the exact-'resume' rule, and REVIEW-BUS.md's wording is fixed in a later docs PR. scripts/reviewbus/github.py: one GitHub class per role. Every gh call runs with that role's GH_CONFIG_DIR (the reviewer's from config; the author's default, with GH_CONFIG_DIR, GH_TOKEN and GITHUB_TOKEN removed so neither inherits the other's login) and the run function injected for tests. Reads: login(), pull(n) (head, files, body, check conclusions), open_pulls(), comments(n) in posting order as {author, body}, variable(name). Writes check the role's login against ROSTER before every call, refuse an author approving or merging, and pin to the reviewed head: comment(n, body), approve(n, sha) through the reviews API with commit_id, merge(n, sha) with --squash --match-head-commit. Rejected: reading required checks from branch protection, which needs admin; they come from the config in the watcher PR.

### 2026-11-09T04:02:11Z · TEST · myan · claude-code/opus-5.5 · 7fa8252
scripts/tests/reviewbus: 132 passed (github: 13 — each role's env carries only its own GH_CONFIG_DIR and no inherited token; the reviewer needs a directory; a role logged in as the other account writes nothing; the author can never approve or merge; approve posts commit_id and merge uses --match-head-commit; bad numbers and shas refused before any call; a comment goes as JSON on stdin, never as an argument; reads parsed with a failing duplicate check winning; an unreadable variable is None). A null comment body or deleted author comes back as an empty string, so state.state never sees null. ruff clean.

### 2026-11-09T04:02:11Z · COMMIT · myan · claude-code/opus-5.5 · parent:7fa8252
feat(agreements): review bus — every gh call under its role's login
3 files changed, 316 insertions(+)
