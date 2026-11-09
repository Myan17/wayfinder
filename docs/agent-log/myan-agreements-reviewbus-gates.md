# Task log — myan-agreements-reviewbus-gates

| Field | Value |
|---|---|
| Task | Review bus PR 2b: the approval gates (ADR-0021 rules 4, 5 and 10; off-plan, directed by Myan) |
| Module | agreements |
| Branch | `myan/agreements/reviewbus-gates` |
| Worktree | `../wayfinder-wt/myan-agreements-reviewbus-gates` |
| Operator | myan |
| Agent | claude-code/opus-5.5 |
| Session | 2026-11-09T03:00Z/28821 |
| Started | 2026-11-09T03:04:08Z |
| Closed when | the last entry says TASK CLOSED (the header is never edited - this file is append-only) |

**Append-only.** Corrections are new entries. Entries are written by `scripts/log.sh` and the
`post-commit` hook; CI rejects a rewritten log (`scripts/check_agent_log.py`).

## Cards read

- (listed by `new-task.sh`; add any you read later as `READ` entries)

## Timeline

### 2026-11-09T03:04:46Z · PLAN · myan · claude-code/opus-5.5 · 5427abb
REVIEW-BUS.md §10 PR 2, second part (off-plan; Myan's direction, quoted in myan-agreements-reviewbus-protocol's DECIDE: "Build the bus now"). scripts/reviewbus/gates.py: rule 5's six gates (a mode on, b no human-only path, c every required check green on the reviewed head and the head unmoved, d the verdict parses and has no blocking finding, e the description names the reviewed head, f round 1 to 3), each (ok, reason), and decide(): off does nothing, round over 3 escalates (rule 10), a malformed verdict or needs_human goes to a human, changes or a blocking finding requests changes in shadow and on (rule 4), shadow stops at would_approve, on approves only when all six hold. Written in #120's task and held back for size. Hardened before review: an empty tier or empty required-check list fails its gate, the description must name the head as a whole hex word, and a round that is not an int from 1 to 3 fails. Codex reviews it read-only before the PR opens, so the reviewer approves only the final head.

### 2026-11-09T03:04:46Z · TEST · myan · claude-code/opus-5.5 · 5427abb
scripts/tests/reviewbus: 69 passed (gates: 38, including the new empty-tier, empty-required, prefixed and suffixed sha, full and 12-character names, and rounds 0, "1" and True). ruff clean.

### 2026-11-09T03:04:47Z · COMMIT · myan · claude-code/opus-5.5 · parent:5427abb
feat(agreements): review bus — the approval gates and decide()
3 files changed, 293 insertions(+)

### 2026-11-09T03:06:34Z · EDIT · myan · claude-code/opus-5.5 · e3b72d5
Codex round 1 (gpt-6.1-sol, read-only, before the PR opened) returned changes with three blocking findings, each verified: (f1) empty or non-hex heads passed gates c and e, so both heads must now be full 40-character lowercase shas; (f2) a bare string or empty files list passed gate b, so files must be a non-empty list of non-empty paths; (f3) a finding with an unknown severity or no line field passed gate d, so severity must be high, medium or low and line must be present, null or a positive integer.

### 2026-11-09T03:06:34Z · TEST · myan · claude-code/opus-5.5 · e3b72d5
scripts/tests/reviewbus: 80 passed (new: empty, string and empty-entry files; empty, short, one-character and uppercase heads; line 0, absent line and garbage severity; a nonblocking finding still approves). ruff clean.

### 2026-11-09T03:06:34Z · COMMIT · myan · claude-code/opus-5.5 · parent:e3b72d5
fix(agreements): review bus gates refuse missing heads, files and finding fields
3 files changed, 47 insertions(+), 4 deletions(-)

### 2026-11-09T03:07:50Z · EDIT · myan · claude-code/opus-5.5 · 4934ea0
Codex round 2: f1 and f3 fixed; f2 still open, verified: an iterator of files was consumed by validation before the tier check, and './db/...' passed the db/** glob. Gate b now takes only a non-empty list or tuple of canonical repository-relative paths (no leading ./ or /, no . or .. segment, no doubled or trailing slash, no backslash).

### 2026-11-09T03:07:50Z · TEST · myan · claude-code/opus-5.5 · 4934ea0
scripts/tests/reviewbus: 88 passed (new: an iterator, a set, ./, /, .., //, a trailing slash and backslashes, each failing gate b). ruff clean.

### 2026-11-09T03:07:50Z · COMMIT · myan · claude-code/opus-5.5 · parent:4934ea0
fix(agreements): review bus gate b takes only canonical repository paths
3 files changed, 28 insertions(+), 3 deletions(-)

### 2026-11-09T03:09:14Z · EDIT · myan · claude-code/opus-5.5 · 1e29158
Codex round 3: changes, two blocking findings of round 2's class, verified: an empty or exhausted iterator passed as tier (gate b) or required (gate c) passed the emptiness check and then checked nothing. tier and required must now be non-empty lists or tuples of non-empty strings, checks a mapping, and the description text. Rule 10 stops the review loop after round 3: these fixes are not yet reviewed by Codex, and Myan decides whether to run a fourth round or review them himself.

### 2026-11-09T03:09:14Z · TEST · myan · claude-code/opus-5.5 · 1e29158
scripts/tests/reviewbus: 96 passed (new: empty and live iterators for tier and required, an empty name in each, a list of pairs as checks, a non-text description). ruff clean.

### 2026-11-09T03:09:14Z · COMMIT · myan · claude-code/opus-5.5 · parent:1e29158
fix(agreements): review bus gates b and c refuse iterators and empty names
3 files changed, 29 insertions(+), 4 deletions(-)

### 2026-11-09T03:10:40Z · DECIDE · myan · claude-code/opus-5.5 · 3d5cfea
Rule 10's stop after round 3 went to Myan, who chose a fourth Codex round on 3d5cfea before the PR opens. His words: "Option A".

### 2026-11-09T03:10:41Z · COMMIT · myan · claude-code/opus-5.5 · parent:3d5cfea
docs(agents): record Myan's choice of a fourth review round for the gates
1 file changed, 3 insertions(+)

### 2026-11-09T03:15:47Z · EDIT · myan · claude-code/opus-5.5 · ee639c5
Codex round 4 on 3d5cfea: round 3's findings fixed; the requested sweep found five subclass bypasses (a str subclass lying about equality for mode, heads and conclusions; list subclasses lying about truthiness or iteration for tier, files, required and findings; dict subclasses overriding get), each verified. None is reachable from the watcher, whose inputs are all parsed JSON. Myan chose ("Option A") one fix and the PR without a fifth round: decide() first requires every Review field to be plain JSON data of exact built-in types, recursively, and raises TypeError otherwise, which can only end in a human's review.

### 2026-11-09T03:15:47Z · TEST · myan · claude-code/opus-5.5 · ee639c5
scripts/tests/reviewbus: 109 passed (new: twelve round-4 objects each raise TypeError from decide; plain() accepts json.loads output and refuses non-string keys and sets; the gate-blocking test now proves each gate fails alone and that decide either returns needs_human or refuses the input).

### 2026-11-09T03:15:47Z · COMMIT · myan · claude-code/opus-5.5 · parent:ee639c5
fix(agreements): review bus decide() accepts only plain JSON data
3 files changed, 82 insertions(+), 3 deletions(-)
