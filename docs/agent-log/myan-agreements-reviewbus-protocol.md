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

### 2026-11-09T01:58:34Z · HANDOFF · myan · claude-code/opus-5.5 · 7dc5fcf
PR open for gupta958 (human-only tier: scripts/reviewbus/**). Open question in the brief: ADR-0021 rule 8 lets only Myan17 send escalate, but REVIEW-BUS.md §3 says either, and §2 has the reviewer escalating on errors; protocol.py follows the ADR. Next, after the merge: gates.py and test_gates.py (kept in the session scratchpad, 240 lines, 21 passing tests), then state.py and github.py, then agents, rulings, reviewer, prompts and cli, then review_handoff request/ruling-request. S2 (item 7) resumes when Myan says.

### 2026-11-09T01:58:34Z · COMMIT · myan · claude-code/opus-5.5 · parent:7dc5fcf
docs(agents): hand off the review bus protocol task
1 file changed, 3 insertions(+)

### 2026-11-09T02:27:25Z · HANDOFF · myan · claude-code/opus-5.5 · a4eeada
Rebased onto main 32f665f (#119 merged), at Myan's request so #120 can merge. Old head 6b80cfa. No conflicts; the diff is unchanged.

### 2026-11-09T02:27:25Z · COMMIT · myan · claude-code/opus-5.5 · parent:a4eeada
docs(agents): log the rebase of the review bus protocol task onto #119
1 file changed, 3 insertions(+)

### 2026-11-09T02:52:01Z · EDIT · myan · claude-code/opus-5.5 · 321ae05
Codex (gpt-6.1-sol, read-only, run locally at Myan's request; nothing posted) returned changes with three blocking findings on 321ae05, each verified: (f1) a header whose type is a list or object raised TypeError before the author check, now Ignored; (f2) an empty security path list parsed as [''] and passed, and single-quoted paths kept their quotes, so tier.py now drops empty entries, strips either quote, refuses an unquoted path, and the empty list fails closed; (f3) the rule 11 mention was skipped when the text merely contained '@Gupta958' (e.g. '@Gupta958-other', in code, in an HTML comment), so build now always puts the mention on its own line first.

### 2026-11-09T02:52:01Z · TEST · myan · claude-code/opus-5.5 · 321ae05
scripts/tests/reviewbus: 39 passed (new: list, object and array headers ignored from Myan17 and a third account; five texts that once suppressed the mention, across escalate, confirm-only ruling, approve and needs_human; empty, empty-string and unquoted security path lists fail closed; a trailing comma keeps the path; single-quoted paths match). The real OWNERSHIP.md still yields 21 tier globs including all four security modules' paths. ruff clean.

### 2026-11-09T02:52:01Z · COMMIT · myan · claude-code/opus-5.5 · parent:321ae05
fix(agreements): review bus — malformed types ignored, tier fails closed on empty paths, mention on its own line
5 files changed, 62 insertions(+), 18 deletions(-)

### 2026-11-09T02:53:50Z · EDIT · myan · claude-code/opus-5.5 · d081c5a
Codex round 2 on d081c5a: f1 and f3 fixed; f2 still open, verified: a YAML escape such as \u0061 inside a quoted path was kept literally, so the glob never matched. tier.py now accepts only paths of [A-Za-z0-9._/*-] and refuses anything else; all 19 modules' real paths fit.

### 2026-11-09T02:53:50Z · TEST · myan · claude-code/opus-5.5 · d081c5a
scripts/tests/reviewbus: 42 passed (new: an escaped path, a single-quote escape and trailing spaces each fail closed). ruff clean.

### 2026-11-09T02:53:51Z · COMMIT · myan · claude-code/opus-5.5 · parent:d081c5a
fix(agreements): review bus tier refuses any path outside plain characters
3 files changed, 16 insertions(+), 1 deletion(-)
