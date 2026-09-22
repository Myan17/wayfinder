# ADR-0013 — Evaluation protocol and the selection rule for retrieval experiments

- **Status:** Proposed. Written before S1 builds the dataset and before E1–E7 run.
- **Date written:** 2026-09-22.
- **Decides:** how the locate dataset is built and split (`DESIGN` §14.2), which split may inform
  which decision (§16.5), and the rule that picks a configuration from each experiment (§15.4).
- **Values marked "Reviewer decides"** are the ones `DESIGN` leaves open. They need `gupta958`'s
  approval before E1 runs. After that, changing one requires a new ADR, never an edit to this one.

## Why this exists before the experiment

An experiment whose selection rule is written after the results always finds a winner. v0.2 did
that: it scored its test set at G2 and then kept tuning, which turned the test set into a dev set
(WF-15). This ADR fixes the rule first. The ordering can be checked from merge order, not taken on
anyone's word.

## The dataset

Each rule restates §14.2 as a pass/fail check that the S1 manifest either satisfies or does not.

| # | Rule |
|---|---|
| D-1 | Every pair is indexed at its **own** pre-fix base commit: the parent of the PR's first commit |
| D-2 | Gold labels are the PR's modified source files. Tests, docs, changelogs, lockfiles and generated paths are excluded. Pairs with 0 or more than 10 source files are dropped |
| D-3 | A pair whose issue `updatedAt` is later than the PR merge time goes to the **weak** set. The weak set is reported separately and never pooled |
| D-4 | Each base-commit snapshot is its own pseudo-repository row, scoped through the production authorization predicate. The future-snapshot sentinel (RETR-03) must never be retrieved |
| D-5 | Pairs are grouped into connected components by shared issue or PR, then split **temporally by group**: dev 50%, test 30%, final held-out 20%. No group spans two splits |
| D-6 | Every exclusion is recorded with its reason. The manifest carries exclusion counts by reason |
| D-7 | The label audit samples by repository, language and PR size, and reports error rates by failure type |

**Size.** The target is at least 300 surviving pairs. Fewer does not lower any bar. The achieved
intervals are published at whatever size S1 delivers.

## Which split may inform what

| Split | May be used for | May never be used for |
|---|---|---|
| dev | Every configuration choice in E1–E7, τ calibration (ADR-0011), rerank selection (ADR-0015) | — |
| test | Reporting a configuration **after** it is frozen, and the G2 baseline report | Any decision. A decision that cites a test-split number is invalid |
| final held-out | One scoring, on the release commit, for the release report (§16.9) | Anything else. A second scoring voids it, and the release report says so |

If a test-split result prompts any configuration change, the test split is **spent**. From then on
it is reported as dev, and the change is recorded in the experiment report. That is the only honest
way to act on a result that should not have been seen.

## The selection rule for E1–E7

For each experiment, on dev, with the primary metric §15.4 names for it:

1. Every arm runs on the same dataset manifest and index manifest as the incumbent (§16.5).
2. The incumbent is the current default: RRF k = 60 (§9.5), the design's chunker, the pinned
   embedding specification, `vector` precision, and the iterative filtered scan.
3. A challenger **replaces the incumbent only if** the paired-bootstrap 95% interval of
   (challenger − incumbent) on the primary metric excludes zero in the challenger's favour. Use
   10,000 resamples, cluster-resampled by issue/PR group (§15.2).
4. If more than one challenger qualifies, take the one with the higher point estimate. On a tie
   within the interval, take the cheaper one by measured CPU.
5. If none qualifies, the incumbent stays. "Not significantly worse" is never grounds to switch,
   unless the experiment's stated purpose is cost (E5, E6). In E5 and E6, a cheaper arm replaces the
   incumbent only if its interval's **lower bound** is above −0.02 absolute Recall@10.
   **Reviewer decides** the 0.02 margin.
6. Multiple comparisons across experiments are labelled exploratory (§15.2). No experiment's rule is
   re-run with a different metric after its result is known.

**E1 is special.** It decides the headline locate claim (§3.3): hybrid must beat **both**
BM25-only and dense-only on Recall@10, each paired difference's interval excluding zero. If hybrid
fails either comparison, the release does not claim hybrid superiority. It ships the better single
leg as the published locate configuration, and the README says why. **Reviewer decides** this
fallback; `DESIGN` states the bar but not what happens when it is missed.

**E7 is not a selection experiment for quality.** Its bar is fixed by §3.3: neighbour overlap of at
least 0.95 with exact search over the **authorized** rows, at 1%, 10% and 100% visibility. An arm
that misses the bar at any visibility level is excluded, whatever its speed.

## What is deliberately not decided here

- **The rerank configuration.** ADR-0015 decides it. It is scored on dev with nDCG@10, but its CPU
  bar comes from S2, not from this ADR.
- **τ.** ADR-0011 decides it, on the explain and unanswerable dev halves (§14.3), not on the locate
  set.
- **Generation quality bars.** §3.3 and §15.3 set these, and they are measured on the held-out
  explain set. Nothing here touches them.

## Consequences

- S1's source manifest must record base commits, group ids and the temporal split boundary. A
  manifest without them cannot satisfy D-1 or D-5, and S1 is not done.
- Experiment reports cite the dataset manifest hash (§14.5) and state which split each number comes
  from.
- The final held-out split is never loaded into a development index until the release run.
