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

### 2026-09-22T22:54:03Z · HANDOFF · myan · claude-code/opus-5 · 8e8dfbf
#24 open. gupta958 decides the six Reviewer-decides values listed in the PR body. When #23 merges, ORIENT.md item 1 is marked 'done #24' by whichever of the two merges second. Next per ORIENT: item 2, schema v1 (joint module; both owners approve).

### 2026-09-22T22:54:03Z · COMMIT · myan · claude-code/opus-5 · parent:8e8dfbf
docs(agreements): hand off #24
1 file changed, 3 insertions(+)

### 2026-09-23T02:31:48Z · DECIDE · myan · claude-code/opus-5 · efdb727
gupta958 requested changes (relayed by Myan, recorded on #24): define statistical tie-breaking and 'cheaper' for E5/E6; require dev precision >= 0.90 plus Wilson lower bound >= 0.70; zero accepted questions must fail; specify the temporal group-splitting algorithm.

### 2026-09-23T02:31:48Z · EDIT · myan · claude-code/opus-5 · efdb727
ADR-0013: D-5 now points to a seven-step deterministic split (issue-PR connected components including weak pairs; group time = latest merge; per-repository split, group assigned to its majority repository; sort by (t, smallest PR); cumulative 0.5N / 0.8N assignment of whole groups; weak pairs keep their group's split; manifest fields). Step 4 defines the statistical tie set (b plus qualifying challengers whose paired interval of b - c includes zero), then cheaper, then point estimate, then pre-registered arm order. Step 5 (E5/E6) requires cheaper AND lower bound above -0.02. 'Cheaper' defined: same host, median of five runs on dev, at least 5% lower, with a per-experiment cost measure table. ADR-0011: tau candidates are observed dev scores; qualify only with |A| >= 1, precision >= 0.90 and Wilson lower bound >= 0.70; worked consequences (>= 9 accepted; 19/20 not 18/20). ADR-0015 step 3 uses ADR-0013's tie-break with rerank CPU per call.

### 2026-09-23T02:31:48Z · TEST · myan · claude-code/opus-5 · efdb727
Wilson 95% lower bounds recomputed (z = 1.95996): 9/9 = 0.701, 8/8 = 0.676, 19/20 = 0.764, 18/20 = 0.699 - the minimum-accepted and 18/20 claims in ADR-0011 hold.

### 2026-09-23T02:31:48Z · COMMIT · myan · claude-code/opus-5 · parent:efdb727
docs(agreements): tie-breaking, cost, tau's two bars and the split algorithm, per review
4 files changed, 79 insertions(+), 13 deletions(-)

### 2026-09-23T02:35:58Z · HANDOFF · myan · claude-code/opus-5 · c2b3da6
#24 revised per review; re-review requested and gupta958 briefed on Discord with line references.

### 2026-09-23T02:35:58Z · COMMIT · myan · claude-code/opus-5 · parent:c2b3da6
docs(agreements): hand off after review
1 file changed, 3 insertions(+)
