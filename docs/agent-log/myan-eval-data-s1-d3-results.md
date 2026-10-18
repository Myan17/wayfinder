# Task log — myan-eval-data-s1-d3-results

| Field | Value |
|---|---|
| Task | S1 D-3 diagnostic report: 48 sampled pairs' merge, close and update times (ORIENT item 5) |
| Module | eval-data |
| Branch | `myan/eval-data/s1-d3-results` |
| Worktree | `../wayfinder-wt/myan-eval-data-s1-d3-results` |
| Operator | myan |
| Agent | claude-code/opus-5.5 |
| Session | 2026-10-18T19:29Z/138 |
| Started | 2026-10-18T19:29:06Z |
| Closed when | the last entry says TASK CLOSED (the header is never edited - this file is append-only) |

**Append-only.** Corrections are new entries. Entries are written by `scripts/log.sh` and the
`post-commit` hook; CI rejects a rewritten log (`scripts/check_agent_log.py`).

## Cards read

- (listed by `new-task.sh`; add any you read later as `READ` entries)

## Timeline

### 2026-10-18T19:29:23Z · READ · myan · claude-code/opus-5.5 · 961f943
gupta958's D-3 ruling (2026-10-17): diagnostic, script and results in a small PR; do not alter D-3 or regenerate the dataset; if the closure explains the weak class, propose an ADR-0013 amendment that merges before any miner change or S1 re-run. Read ADR-0013 D-3 and D-5, ADR-0016 Amendment 1's form, the eval-data card, and the probe's report: written by myan's run of s1.d3_probe from main at 961f943 (#75), 2026-10-18T19:26:48Z, 4 GraphQL and 0 REST calls, pairs_sha256 d5ae8d34... (run 3's file), report sha256 89e1c674...

### 2026-10-18T19:29:23Z · PLAN · myan · claude-code/opus-5.5 · 961f943
This PR: commit eval/datasets/s1-d3-probe.json byte-for-byte as the probe wrote it, plus a test that the committed report is self-consistent (its summary is summary(rows), its text is encoded(report), its pairs hash is run 3's, it carries no title or body, 48 rows with 3 weak + 1 strong per cell), plus a card change-log line. The interpretation goes in the PR body. The ADR-0013 amendment proposal is a separate agreements PR, since it changes a rule and the ruling requires it to merge before any miner change. Rejected: one PR holding both, which would mix evidence with a rule change and put a joint-module edit under an eval-data task; and re-deriving the sample in the test, which needs the uncommitted pairs file.

### 2026-10-18T19:30:32Z · EDIT · myan · claude-code/opus-5.5 · 961f943
Added eval/datasets/s1-d3-probe.json unchanged from myan's run (sha256 89e1c674...), eval/miners/tests/test_s1_d3_report.py (4 tests: the file is encoded(report) plus a newline; its summary is summary(rows); each row equals measure() rebuilt from its own times; run 3's pairs hash, 4 GraphQL and 0 REST calls; 48 distinct rows, 3 weak + 1 strong in each of 24 cells, no title or body), and one eval-data card change-log line. No rule, miner or dataset change.

### 2026-10-18T19:30:32Z · TEST · myan · claude-code/opus-5.5 · 961f943
pytest eval/miners/tests -> 191 passed; ruff check and format clean. Tamper mutants on a copy of the report, each restored after and the sha256 rechecked: weak_now flipped on weak rows (1 failed; it survived before the per-row test was added), one delta changed (2), one updated_at changed (1), a strong control relabelled weak (2), rest calls 1 (1), a title field added (2), a row dropped (2), strong_controls changed (1), whitespace changed (1).

### 2026-10-18T19:30:33Z · DECIDE · myan · claude-code/opus-5.5 · 961f943
Reading of the report, for the PR body and the ADR-0013 amendment proposal: all 48 issues closed at or before the merge to the second (4 before it); all 12 strong controls have updatedAt <= mergedAt (9 at 0 s, 3 negative) and none is weak today. Of 36 weak: 17 updated 1-2 s after the merge, 2 at 13 s and 32 s, 17 more than 1 h after (smallest 6,240 s); none in (32 s, 6,240 s). Within 60 s by split: dev 3/12, test 9/12, held_out 7/12. So the merge-triggered closure accounts for about half the sampled weak class and most of it in test and held_out, which is the imbalance. The ruling's branch for this outcome is an ADR-0013 amendment proposal, in its own agreements PR.

### 2026-10-18T19:30:33Z · COMMIT · myan · claude-code/opus-5.5 · parent:961f943
feat(eval-data): the S1 D-3 probe's report over 48 sampled pairs, pinned to the probe's own output
3 files changed, 181 insertions(+)

### 2026-10-18T19:30:42Z · EDIT · myan · claude-code/opus-5.5 · 9685eec
The eval-data card's change-log line, which missed the first commit (the edit had not applied).

### 2026-10-18T19:30:43Z · COMMIT · myan · claude-code/opus-5.5 · parent:9685eec
docs(eval-data): the card records the D-3 probe's report
2 files changed, 5 insertions(+)

### 2026-10-18T19:30:50Z · HANDOFF · myan · claude-code/opus-5.5 · 54bc126
TASK CLOSED. Pull request open for review.

### 2026-10-18T19:30:50Z · COMMIT · myan · claude-code/opus-5.5 · parent:54bc126
docs(agents): close task log for myan-eval-data-s1-d3-results
1 file changed, 3 insertions(+)

### 2026-10-18T20:26:58Z · DECIDE · myan · claude-code/opus-5.5 · d30e2fa
Review of #76 (gupta958, relayed by myan, 2026-10-18): 'The sample is stratified equally by repository... applies the unweighted split rates (3/12, 9/12, 7/12) to the full weak populations to estimate 736/513/266 strong pairs. That is not a valid population estimate... Please remove those projected totals, or calculate and clearly label a repository-stratum-weighted estimate.' Removed them. On #77 they also asked for 'merge-adjacent updates' where causation is not established; the same applies here, so the PR body and title no longer say the closure explains the weak class, and the DECIDE entry above, which says it 'accounts for' it, is superseded by this one: the timestamps show merge-adjacent updates, consistent with the split imbalance. Changes are to the PR body and title only; no file in the diff changes.

### 2026-10-18T20:26:58Z · COMMIT · myan · claude-code/opus-5.5 · parent:d30e2fa
docs(eval-data): record the review of #76 in its task log
1 file changed, 3 insertions(+)

### 2026-10-18T20:26:58Z · HANDOFF · myan · claude-code/opus-5.5 · d9d6a5c
TASK CLOSED. Pull request open for review.

### 2026-10-18T20:26:58Z · COMMIT · myan · claude-code/opus-5.5 · parent:d9d6a5c
docs(agents): close task log for myan-eval-data-s1-d3-results
1 file changed, 3 insertions(+)
