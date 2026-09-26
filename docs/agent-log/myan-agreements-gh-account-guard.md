# Task log — myan-agreements-gh-account-guard

| Field | Value |
|---|---|
| Task | Refuse pushes and review posts made under a GitHub account other than the operator's (the #36-#39 wrong-author incident) |
| Module | agreements |
| Branch | `myan/agreements/gh-account-guard` |
| Worktree | `../wayfinder-wt/myan-agreements-gh-account-guard` |
| Operator | myan |
| Agent | claude-code/opus-5.5 |
| Session | 2026-09-26T16:40Z/89 |
| Started | 2026-09-26T22:23:06Z |
| Closed when | the last entry says TASK CLOSED (the header is never edited - this file is append-only) |

**Append-only.** Corrections are new entries. Entries are written by `scripts/log.sh` and the
`post-commit` hook; CI rejects a rewritten log (`scripts/check_agent_log.py`).

## Cards read

- (listed by `new-task.sh`; add any you read later as `READ` entries)

## Timeline

### 2026-09-26T22:23:06Z · DECIDE · myan · claude-code/opus-5.5 · 8435c4f
Incident on 2026-09-26: gh on myan's Mac is signed in to both Myan17 and gupta958, and gupta958 was active on github.com. #36-#39, today's pushes and every brief went out as gupta958. gupta958 could not approve its own PRs, and a self-mention never notifies. Fixed by hand: switched to Myan17 and reopened the PRs as #40-#43. myan approved the fix, including this guard: "Yes, do all of it".

### 2026-09-26T22:23:06Z · PLAN · myan · claude-code/opus-5.5 · 8435c4f
scripts/check_gh_account.py maps the operator (git config wayfinder.operator) to their ROSTER github login and compares it, case-insensitively, with gh api user. It fails closed on an unknown operator or a mismatch, and prints the gh auth switch command. It runs from a new .githooks/pre-push, and from review_handoff.py before request, brief and record, the verbs that post. If gh is not installed it warns and passes, because then gh is not the one pushing. Rejected: checking PR authors in CI, which only catches the problem after the PR exists.

### 2026-09-26T22:23:57Z · TEST · myan · claude-code/opus-5.5 · 8435c4f
uv run pytest scripts/tests: 70 passed (4 new guard tests, 1 new review_handoff refusal test). Live check: with gupta958 active, check_gh_account.py exits 1 with the switch command, and 'git push --dry-run' is refused by the pre-push hook. With Myan17 active it exits 0. Left on Myan17.

### 2026-09-26T22:23:57Z · COMMIT · myan · claude-code/opus-5.5 · parent:8435c4f
feat(agreements): refuse pushes and review posts under the wrong GitHub account
6 files changed, 180 insertions(+)
