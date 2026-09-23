# ADR-0015 — Rerank admission control and the (N, L) selection rule

- **Status:** Proposed. Written before S2 measures CPU and before E3 runs.
- **Date written:** 2026-09-22.
- **Decides:** which cross-encoder configuration production runs, where it runs, and what happens
  under load (`DESIGN` §9.5 step 7, §9.12, §10.3).
- **Values marked "Reviewer decides"** are the ones `DESIGN` leaves open. They need `gupta958`'s
  approval before E3 runs.

## Why this exists before the experiment

§10.3's own planning estimates show that no configuration reranking every ask clears the CPU bar
once background work is reserved. That makes this decision easy to get wrong in a convenient
direction: after the numbers arrive, it is tempting to assume a cache hit rate, relax the bar, or
pick the configuration that happened to fit. The rule is fixed here so the measurement decides it.

## Inputs

| Input | Source | Never taken from |
|---|---|---|
| Quality of each (N, L) | E3 on the **dev** split, nDCG@10 (ADR-0013) | test or held-out |
| CPU per rerank call | S2, measured per stage on the target hardware across the real query-length distribution | §10.3's estimates, which S2 replaces |
| Available cores | 1.5 after the 25% background reservation (§10.3) | — |
| Nominal load | The request mix and rate §10.3 defines for the configuration being tested | — |

**The grid.** N ∈ {8, 16, 32, 50} passages, L ∈ {128, 256} tokens: eight arms, plus "no rerank".
The endpoints are the configurations §10.3 already names. **Reviewer decides** the grid.

## The rule

1. **Quality bar.** An (N, L) qualifies only if its nDCG@10 beats "no rerank" on dev, with the
   paired-bootstrap 95% interval excluding zero (ADR-0013 step 3). An arm that does not beat
   fused order is not a reranker worth its CPU.
2. **CPU bar.** An arm's measured nominal CPU demand must be at most **70% of available cores**
   (1.05 core-seconds per second), assuming **no answer-cache hits**. The cache hit rate is measured
   and reported, never credited (§10.3 decision 3).
3. **Selection.** Production runs the qualifying arm with the **highest dev nDCG@10** among those
   that pass the CPU bar. Ties are broken by ADR-0013 step 4: the statistical tie set, then the
   cheaper arm by measured rerank CPU per call (at least 5% lower, median of five runs), then the
   higher point estimate.
4. **Reranking runs on asks only.** §10.3 shows reranking every search is out of reach at nominal
   load. At peak, search returns fused order. E3 reports that fallback's nDCG cost, and every
   capacity report states what fraction of requests ran in the quality configuration.
5. **If quality-qualifying arms exist but none passes the CPU bar,** production runs the
   **cheapest** quality-qualifying arm. The generated-answer concurrency is then published as the
   measured number it supports, lower than 1,000 (§10.3 decision 2, §3.3). Search still holds
   1,000 users, because it does not depend on reranking.
6. **If no arm meets the quality bar,** there is no reranker. Without a reranker there is no
   relevance signal, so ADR-0011 forbids generated answers. The release ships locate and extractive
   only, which is §19.8 step 3, reached by measurement instead of schedule.

## Admission control (fixed by §9.5 and §9.12, restated as rules)

- Rerank requests wait in a bounded queue. If the wait exceeds **150 ms** or the reranker errors,
  the request proceeds in fused order with `degraded: ["rerank_shed"]`.
- A shed request has no relevance signal, so it can never produce a generated answer (ADR-0011).
- Asks are shed before searches.

## What is deliberately not decided here

- **The cross-encoder model.** §10.3 assumes a MiniLM-class model. A larger model is an E3 arm
  ("larger model"), and it goes through the same two bars, with no separate rule.
- **A latency SLO for rerank alone.** CPU at nominal load is the binding constraint in §10.3.
  Per-outcome latency SLOs are §10's and are measured under L1.

## Consequences

- S2 must report per-call rerank CPU for every grid arm, not only the two §10.3 names. Otherwise
  step 2 cannot be evaluated and S2 is not done.
- The selected (N, L), its dev nDCG@10 interval and its measured CPU go into the release manifest.
- Changing the model, N or L after selection is a new selection under this rule, not a tweak.
