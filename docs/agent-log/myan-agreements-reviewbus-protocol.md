# Task log — myan-agreements-reviewbus-protocol

| Field | Value |
|---|---|
| Task | Review bus PR 2a: protocol, tier and gates (ADR-0021; off-plan, directed by Myan) |
| Module | agreements |
| Branch | `myan/agreements/reviewbus-protocol` |
| Worktree | `../wayfinder-wt/myan-agreements-reviewbus-protocol` |
| Operator | myan |
| Agent | claude-code/opus-5.5 |
| Session | 2026-11-09T01:00Z/26772 |
| Started | 2026-11-09T01:53:29Z |
| Closed when | the last entry says TASK CLOSED (the header is never edited - this file is append-only) |

**Append-only.** Corrections are new entries. Entries are written by `scripts/log.sh` and the
`post-commit` hook; CI rejects a rewritten log (`scripts/check_agent_log.py`).

## Cards read

- (listed by `new-task.sh`; add any you read later as `READ` entries)

## Timeline

### 2026-11-09T01:53:29Z · DECIDE · myan · claude-code/opus-5.5 · 3e41c5c
Off-plan under AGENTS.md rule 6, by owner direction. Myan, 2026-11-09, asked whether I could get rulings from Codex directly, was told the bus is spec-only (ADR-0021 merged as #115, nothing built, Codex broken, no reviewer gh login), and chose between building it now or finishing S2 first. His words: "Build the bus now". S2 (item 7) pauses after #119.

### 2026-11-09T01:53:29Z · PLAN · myan · claude-code/opus-5.5 · 3e41c5c
REVIEW-BUS.md §10 PR 2 (protocol, state, tier, gates, github) exceeds 400 lines, so it splits. This PR, 2a: scripts/reviewbus/protocol.py (the hidden header <!-- reviewbus v1 {json} -->, build and parse, the type table of §3, rule 8's author check: Myan17 for review_request, ruling_request, fix_pushed, escalate; gupta958 for review_result and ruling; either for veto and confirm; anyone else ignored), tier.py (rule 6's human-only tier, the security modules' paths read from OWNERSHIP.md rather than copied, plus the rules and bus globs), gates.py (rule 5 (a)-(f), one function each returning (ok, reason), and decide() giving approve, changes, needs_human or shadow per mode). Tests in scripts/tests/reviewbus/. Next, 2b: state.py and github.py. Rejected: one 2 PR at about 600 lines, which the size rule forbids.

### 2026-11-09T01:58:10Z · TEST · myan · claude-code/opus-5.5 · 3e41c5c
scripts/tests/reviewbus: 52 passed (protocol: roster accounts, build/parse round trip, wrong author ignored with a reason, veto/confirm from either account only, ordinary comments ignored, five malformed headers, build refusals including '-->', rule 11 mentions; tier: every rule 6 path, non-tier paths, a path added in OWNERSHIP joins, a missing security module fails closed, the real OWNERSHIP reads; gates: all green approves in on, each of b c e blocks, shadow stops at would_approve, off does nothing, unknown mode refused, changes and blocking findings request changes in shadow and on, needs_human, round 4 escalates, six malformed verdicts never approve). make test: 553 passed, 43 skipped. ruff clean on the new files. A conftest.py in scripts/tests/reviewbus shadowed db/tests' conftest in test_s2_load.py's import, so each test file sets its own path instead.

### 2026-11-09T01:58:10Z · COMMIT · myan · claude-code/opus-5.5 · parent:3e41c5c
feat(agreements): review bus — message protocol, human-only tier and approval gates
8 files changed, 609 insertions(+)

### 2026-11-09T01:58:25Z · DECIDE · myan · claude-code/opus-5.5 · 3e41c5c
check_pr_size: 578 lines with gates, over 400. Split again: this PR is protocol and tier (with their tests); gates.py and test_gates.py (240 lines, written and passing, kept aside) become the next PR once this merges, from main. The TEST entry above counted the gates tests; for this PR's files: protocol 13 and tier 18 test cases.

### 2026-11-09T01:58:26Z · COMMIT · myan · claude-code/opus-5.5 · parent:3e41c5c
feat(agreements): review bus — message protocol and human-only tier
6 files changed, 376 insertions(+)
