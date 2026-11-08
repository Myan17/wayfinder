# Task log — myan-agreements-review-bus-spec

| Field | Value |
|---|---|
| Task | Review bus: ADR-0016 delegated approval rules and docs/team/REVIEW-BUS.md architecture and reading list (off-plan, directed by myan) |
| Module | agreements |
| Branch | `myan/agreements/review-bus-spec` |
| Worktree | `../wayfinder-wt/myan-agreements-review-bus-spec` |
| Operator | myan |
| Agent | claude-code/opus-5.5 |
| Session | 2026-09-26T16:40Z/89 |
| Started | 2026-09-26T19:01:26Z |
| Closed when | the last entry says TASK CLOSED (the header is never edited - this file is append-only) |

**Append-only.** Corrections are new entries. Entries are written by `scripts/log.sh` and the
`post-commit` hook; CI rejects a rewritten log (`scripts/check_agent_log.py`).

## Cards read

- (listed by `new-task.sh`; add any you read later as `READ` entries)

## Timeline

### 2026-09-26T19:01:27Z · DECIDE · myan · claude-code/opus-5.5 · 8435c4f
Off-plan, directed by myan on 2026-09-26: "i want you and engineer B to communicate to request pr approvals as I can't manually do all this ... Set up an agent harness between you and Engineer B". Myan's answers: B's agent approves for B; it runs on B's own machine; the provider is whatever B already pays for. Design approved: "yes i approve he design, i want you to include all the files that B needs to review to understand this architecture ... ensure that codebase is easy to manage, lookup, onboard and expand".

### 2026-09-26T19:02:40Z · PLAN · myan · claude-code/opus-5.5 · 8435c4f
Spec as two files, the repo's own way: ADR-0016 holds the rules (delegated approval, the gates, the human-only tier, author roles, stopping, shadow rollout), and docs/team/REVIEW-BUS.md holds the architecture, gupta958's reading list, setup, the package layout and how to extend and test it. AGENTS.md §1 forbids agents editing AGENTS.md and the roster, so the ADR gives exact text for a human to commit. Rejected: docs/superpowers/specs/, which no OWNERSHIP module claims.

### 2026-09-26T19:02:40Z · TEST · myan · claude-code/opus-5.5 · 8435c4f
Spec self-review: no TBD; the round limits agree (gate f allows rounds 1-3, round 4 escalates); the tier is derived from OWNERSHIP, not copied; gh pr merge --match-head-commit ties the merge to the reviewed head. No code in this PR.

### 2026-09-26T19:02:40Z · COMMIT · myan · claude-code/opus-5.5 · parent:8435c4f
docs(agreements): ADR-0016 and REVIEW-BUS.md — review bus spec
3 files changed, 268 insertions(+)

### 2026-09-26T22:26:52Z · DECIDE · myan · claude-code/opus-5.5 · b939b3a
Spec revised. Myan, 2026-09-26: gupta958 is 'my other account', and asked for the review model: 'Keep gupta958 as a reviewer hat'. So ADR-0016 now says plainly that gupta958 is Myan's second account and not a second person, and the human-committed AGENTS and ROSTER text corrects the 'Engineer B' wording. Both roles run on Myan's Mac with separate GH_CONFIG_DIRs, and each checks its own login before writing (#44's guard). The reviewer uses a fresh session and a different model where available. Myan is accountable for every approval.

### 2026-09-26T22:26:52Z · COMMIT · myan · claude-code/opus-5.5 · parent:b939b3a
docs(agreements): ADR-0016 for a reviewer account that is Myan's own
3 files changed, 106 insertions(+), 64 deletions(-)

### 2026-09-28T20:41:03Z · DECIDE · myan · claude-code/opus-5.5 · a7fc587
Renumbered to ADR-0019. DESIGN §12 pre-assigns 0016 to 'Two source modes', which S1's acceptance rules will use; 0017 and 0018 are also taken (deletion closure, recovery tiers).

### 2026-09-28T20:41:04Z · COMMIT · myan · claude-code/opus-5.5 · parent:a7fc587
docs(agreements): renumber the review bus ADR to 0019 (0016 is DESIGN's source modes)
3 files changed, 14 insertions(+), 11 deletions(-)

### 2026-11-08T06:54:48Z · DECIDE · myan · claude-code/opus-5.5 · dda28b4
Myan, 2026-11-08 (ORIENT rule 2 direction): 'i want to setup an agent harness where chatgpt and claude this session can communicate by requesting and approving pr approvals and rulings'. His choices: approvals start in shadow; ChatGPT's rulings bind directly unless vetoed; the author side is the live Claude session, not a daemon; ChatGPT through the Codex CLI on his ChatGPT login. Plan approved the same day with a 12 h veto window and a confirm-only list. Rebased onto 27b74e6 and renumbered to ADR-0021, since 0019 (S2) and 0020 (S4) are taken.

### 2026-11-08T06:54:49Z · PLAN · myan · claude-code/opus-5.5 · dda28b4
Spec PR only (REVIEW-BUS.md §10 PR 1): ADR-0021 and REVIEW-BUS.md, with no code. Rewritten for Codex as the reviewer, the live session as the author (author.py and prompts/fix.md dropped), ruling_request/ruling/veto/confirm messages with a 12 h window and a confirm-only list, and shadow as the starting mode. AGENTS.md and ROSTER text is given for Myan to commit by hand. Rejected: building the watcher first; the rules merge before the code, as with ADR-0004 and ADR-0007.

### 2026-11-08T06:54:49Z · COMMIT · myan · claude-code/opus-5.5 · parent:dda28b4
docs(agreements): ADR-0021 — the review bus with ChatGPT as the reviewer account's agent
4 files changed, 215 insertions(+), 159 deletions(-)

### 2026-11-08T06:54:55Z · HANDOFF · myan · claude-code/opus-5.5 · 681b718
Spec PR open for gupta958 (Myan, by hand). It is human-tier and joint. After it merges: Myan commits the AGENTS.md and ROSTER text from ADR-0021 by hand and does setup step 0 (reinstall Codex, codex login, the reviewer GH_CONFIG_DIR); then PR 2 (protocol, state, tier, gates, github, with tests).

### 2026-11-08T06:54:55Z · HANDOFF · myan · claude-code/opus-5.5 · 681b718
TASK CLOSED. Pull request open for review.

### 2026-11-08T06:54:56Z · COMMIT · myan · claude-code/opus-5.5 · parent:681b718
docs(agents): close task log for myan-agreements-review-bus-spec
1 file changed, 6 insertions(+)
