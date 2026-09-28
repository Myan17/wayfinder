# Task log — myan-agreements-s1-rules

| Field | Value |
|---|---|
| Task | ADR-0016: source modes and S1's acceptance rules, before S1 measures anything (ORIENT item 5) |
| Module | agreements |
| Branch | `myan/agreements/s1-rules` |
| Worktree | `../wayfinder-wt/myan-agreements-s1-rules` |
| Operator | myan |
| Agent | claude-code/opus-5.5 |
| Session | 2026-09-28T20:41Z/18055 |
| Started | 2026-09-28T20:41:31Z |
| Closed when | the last entry says TASK CLOSED (the header is never edited - this file is append-only) |

**Append-only.** Corrections are new entries. Entries are written by `scripts/log.sh` and the
`post-commit` hook; CI rejects a rewritten log (`scripts/check_agent_log.py`).

## Cards read

- (listed by `new-task.sh`; add any you read later as `READ` entries)

## Timeline

### 2026-09-28T20:41:31Z · PLAN · myan · claude-code/opus-5.5 · 46397f0
ORIENT item 5 (S1) starts with its rules, as S5 did with ADR-0004 (#34) and S3 with ADR-0007. DESIGN §12 pre-assigns ADR-0016 to 'Two source modes: installation and public read-only', and S1 measures the public read-only mode, so S1's acceptance rules go there. The ADR fixes: 10 candidates named before any measurement (5 Python, 5 Go, checked only to exist); pass/fail criteria per candidate from DESIGN §14.1 with a stated measurement for each; the rule that picks 3-4 repositories from the passing ones; the aggregate bar A-3 (>= 300 pairs under ADR-0013 D-1 to D-6) and R-03's pre-stated fallback; and what the manifest must carry. The Decision is empty until S1 runs. Rejected: measuring the candidates first and choosing criteria afterwards, which could not fail.

### 2026-09-28T20:42:08Z · TEST · myan · claude-code/opus-5.5 · 46397f0
No code. Checked the references: A-3, R-03 and R-14 exist in DESIGN (§7.1 and §20), and ADR-0013 D-1 to D-7 is quoted as merged. The 10 candidates were checked only to exist and be unarchived (gh api repos/<r>); no license, PR or file was measured before this ADR.

### 2026-09-28T20:42:08Z · COMMIT · myan · claude-code/opus-5.5 · parent:46397f0
docs(agreements): ADR-0016 — source modes and S1's acceptance rules, before S1
2 files changed, 130 insertions(+)

### 2026-09-28T21:12:23Z · DECIDE · myan · claude-code/opus-5.5 · 035d1ca
Review of #49 by gupta958, relayed by myan (the first round never reached GitHub; #49 had no review or comment). Four blockers, all fixed:
(1) R-03's order now follows DESIGN ('Wider candidate list; relax file-count filter to 15; report the weak set separately'): widen first, then relax.
(2) The tie-break is a total order: surviving pairs, then repository count, then chunk estimate, then the lexicographically smaller sorted tuple of github_repo_ids. The sum of ids could tie.
(3) The chunk estimate has an exact file universe: git ls-tree regular files, the extension list, and test, vendored, generated, Markdown and binary exclusions; lines and ceil(lines/60) are defined. S1-4 uses the same Markdown universe.
(4) After each R-03 step, selection re-runs from scratch over all qualifying candidates. 'No feasible corpus' is defined (fewer than 3 qualify, or no subset meets language mix and chunk bound): only widening applies, then A-3 fails with the reason, and R-14 is recorded if acquisition is the cause. The Decision options cover each outcome.

### 2026-09-28T21:12:23Z · COMMIT · myan · claude-code/opus-5.5 · parent:035d1ca
docs(agreements): ADR-0016 — R-03 in DESIGN's order, total tie-break, exact file universe
2 files changed, 75 insertions(+), 21 deletions(-)

### 2026-09-28T22:22:34Z · DECIDE · myan · claude-code/opus-5.5 · 3d0ccef
Review of #49 by gupta958, round 2: S1-4 listed steps 1, 2, 4, 6 and 7, skipping the test (3) and generated (5) exclusions, while step 6 claimed the universes were the same. S1-4 is now the chunk-estimate universe restricted to .md after all seven steps. There is no test-Markdown exception, so the 'same universe' statement is now true, and it is reworded to say so exactly.

### 2026-09-28T22:22:34Z · COMMIT · myan · claude-code/opus-5.5 · parent:3d0ccef
docs(agreements): ADR-0016 — S1-4 counts the full file universe's Markdown
2 files changed, 5 insertions(+), 2 deletions(-)
