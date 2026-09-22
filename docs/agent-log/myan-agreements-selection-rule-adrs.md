# Task log — myan-agreements-selection-rule-adrs

| Field | Value |
|---|---|
| Task | ADR-0013, ADR-0015, ADR-0011: selection rules written before any experiment (ORIENT item 1, DESIGN 19.2) |
| Module | agreements |
| Branch | `myan/agreements/selection-rule-adrs` |
| Worktree | `../wayfinder-wt/myan-agreements-selection-rule-adrs` |
| Operator | myan |
| Agent | claude-code/opus-5 |
| Session | 2026-09-22T22:52Z/20360 |
| Started | 2026-09-22T22:52:31Z |
| Closed when | the last entry says TASK CLOSED (the header is never edited - this file is append-only) |

**Append-only.** Corrections are new entries. Entries are written by `scripts/log.sh` and the
`post-commit` hook; CI rejects a rewritten log (`scripts/check_agent_log.py`).

## Cards read

- (listed by `new-task.sh`; add any you read later as `READ` entries)

## Timeline

### 2026-09-22T22:52:31Z · READ · myan · claude-code/opus-5 · a45d283
DESIGN §3.3, §9.5, §9.6.1-9.6.2, §9.12, §10.3, §12.1, §14.2-14.3, §15.1-15.5, §16.5, §19.2; docs/adr/ADR-0007 for the house form (rules fixed before the measurement, no third outcome).

### 2026-09-22T22:52:32Z · PLAN · myan · claude-code/opus-5 · a45d283
ORIENT.md item 1 (ORIENT.md is in #23, not yet merged). Three ADRs, each Status: Proposed, each a pre-registered rule with no numbers from any run. Where DESIGN fixes a value (70% CPU bar, 150 ms shed, 10,000 bootstrap resamples, 50/30/20 split, beat-both on Recall@10) the ADR cites it. Where DESIGN leaves a value open (the target answer precision for tau, the (N, L) grid, what happens if hybrid does not beat both legs, extractive vs refused when the signal is missing) the ADR proposes one and marks it 'Reviewer decides' so gupta958 approves it before E1-E7 and before tau is calibrated. Rejected: leaving those values blank - an empty rule is filled after the measurement, which is exactly what G0 forbids. Module agreements: docs/adr/** maps to no module, and these ADRs extend DESIGN §12.1, which agreements owns. Not touching ORIENT.md here; its status line for item 1 changes in a follow-up once #23 is on main.

### 2026-09-22T22:53:36Z · EDIT · myan · claude-code/opus-5 · a45d283
docs/adr/ADR-0013 (dataset rules D-1..D-7 from 14.2; split-use table - dev decides, test reports frozen configs, held-out scored once; the E1-E7 selection rule: challenger replaces incumbent only if the paired cluster-bootstrap 95% interval excludes zero; E1 beat-both; E7 fixed 0.95 bar). docs/adr/ADR-0015 (inputs, grid N in {8,16,32,50} x L in {128,256}; quality bar, 70% CPU bar with no cache credit, highest dev nDCG@10 wins; asks only; no-arm-fits and no-arm-qualifies outcomes; 150 ms shed). docs/adr/ADR-0011 (signal = cross-encoder best/margin/count, versioned; unavailable -> extractive, below tau -> refused; tau = lowest threshold meeting 0.90 dev answer precision; test-half reporting with Wilson intervals). Reviewer-decides values: 0.02 non-inferiority margin (E5/E6), E1 fallback, the rerank grid, one-quantity gate, extractive-on-missing-signal, 0.90 target precision.

### 2026-09-22T22:53:36Z · TEST · myan · claude-code/opus-5 · a45d283
No code. Cross-checked every cited value against DESIGN: 2/61 (9.6.1), 150 ms (9.5, 9.12), 70% / 1.05 core-s/s / 1.5 cores / 25% reservation (10.3), 50/30/20 and >= 300 pairs (14.2), 20/20 dev halves and 0.699-0.972 (14.3, 3.3), 10,000 resamples cluster-bootstrapped (15.2), 0.95 overlap at 1/10/100% (3.3), RETR-03 (14.2), 19.8 step 3. No measured number appears in any ADR; none has been taken.

### 2026-09-22T22:53:37Z · COMMIT · myan · claude-code/opus-5 · parent:a45d283
docs(agreements): ADR-0013, ADR-0015, ADR-0011 — selection rules before any experiment
4 files changed, 264 insertions(+)
