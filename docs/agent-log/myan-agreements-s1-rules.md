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
