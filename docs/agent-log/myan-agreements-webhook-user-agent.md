# Task log — myan-agreements-webhook-user-agent

| Field | Value |
|---|---|
| Task | notify() must send a User-Agent; Discord 403s the urllib default |
| Module | agreements |
| Branch | `myan/agreements/webhook-user-agent` |
| Worktree | `../wayfinder-wt/myan-agreements-webhook-user-agent` |
| Operator | myan |
| Agent | human |
| Session | 2026-09-21T20:55Z/85aed44 |
| Started | 2026-09-21T20:55:32Z |
| Closed when | the last entry says TASK CLOSED (the header is never edited - this file is append-only) |

**Append-only.** Corrections are new entries. Entries are written by `scripts/log.sh` and the
`post-commit` hook; CI rejects a rewritten log (`scripts/check_agent_log.py`).

## Cards read

- (listed by `new-task.sh`; add any you read later as `READ` entries)

## Timeline

### 2026-09-21T20:55:41Z · PLAN · myan · claude-code/opus-5 · 85aed44
notify() sends only Content-Type, so urllib supplies its default User-Agent (Python-urllib/3.x) and Discord's edge answers 403 Forbidden. Verified against the real webhook: identical request with a User-Agent header returns 204. Slack accepts the default, which is why #11 through #13 never surfaced it - the tooling was only ever tested against a Slack-shaped assumption and a fake urlopen. Adding a named User-Agent that identifies the tool and the repository, which is also what a channel admin wants to see when deciding whether traffic is legitimate. Rejected spoofing a browser User-Agent: it would work and it would be a lie about what is posting. Rejected requests/httpx: the guardrail and tooling scripts run on the system Python with no third-party dependencies (platform card invariant), and this is one header.

### 2026-09-21T20:58:04Z · PLAN · myan · claude-code/opus-5 · 85aed44
Second cause found while verifying the first. .env lives in the main checkout; REPO_ROOT is the worktree root, which has none, so from a worktree the tool reported 'not configured'. Every pull request here is authored from a worktree, so the lookup failed in the one place it is always used. main_checkout() resolves the shared clone through 'git rev-parse --path-format=absolute --git-common-dir' and takes its parent; webhook_url() tries the worktree's own .env first, then that. Rejected copying .env into every worktree - N copies of the same secret, each to be rotated by hand. Rejected walking parent directories: it would pick up an unrelated .env above the checkout.

### 2026-09-21T20:58:04Z · TEST · myan · claude-code/opus-5 · 85aed44
RED first on all four new tests. test_the_request_identifies_itself_with_a_user_agent failed with "urllib's default User-Agent is rejected by Discord; send an explicit one"; the three worktree tests failed with AttributeError, main_checkout not existing. All green after the fix; suite 65 passed. Verified against the real Discord webhook, not a fake: before, notify() returned 'webhook: FAILED (HTTP Error 403: Forbidden)'; an otherwise identical request carrying a User-Agent returned 204; after the fix, notify() from this worktree returned 'webhook: 204' and both messages arrived in the channel. Two existing tests had to be isolated - test_notify_is_a_no_op_without_a_configured_webhook and test_a_missing_dotenv_is_not_an_error asserted 'nothing is configured', which was only true while no .env existed on this machine. They began failing the moment a real webhook was set up. A no_env_file fixture now points the lookup at empty directories, so they test the code rather than the developer's machine. ruff clean on both files; the 17 errors across scripts/ are the pre-existing debt in six older scripts recorded on the platform card.

### 2026-09-21T20:58:19Z · HANDOFF · myan · claude-code/opus-5 · 85aed44
Ready for review. Two causes, one symptom: the tool could not deliver a notification. (1) notify() sent no User-Agent, and Discord's edge 403s urllib's default; Slack accepts it, which is why #11 through #13 passed. (2) .env is in the main checkout and every pull request is authored from a worktree, so the lookup found nothing there. Both verified against the live webhook rather than a fake - 403 before, 204 after, messages in the channel. The third finding is the one worth the reviewer's attention: two existing tests asserted 'no webhook is configured' and were passing only because no .env existed on this machine. That is a test measuring the developer's setup, not the code, and it is why a tool that could never reach Discord had a green suite through three pull requests.

### 2026-09-21T20:58:19Z · COMMIT · myan · claude-code/opus-5 · parent:85aed44
fix(agreements): notify() could not deliver -- no User-Agent, and .env unreachable from a worktree
3 files changed, 180 insertions(+), 11 deletions(-)
