# ADR-0011 — Answerability from a versioned relevance signal

- **Status:** Proposed. Written before τ is calibrated and before any generation eval runs.
- **Date written:** 2026-09-22.
- **Decides:** when the system may generate an answer, and how τ is chosen (`DESIGN` §9.6.1,
  §14.3, §3.3 "Refusal behaviour").
- **Values marked "Reviewer decides"** are the ones `DESIGN` leaves open. They need `gupta958`'s
  approval before τ is calibrated.

## Why RRF cannot be the gate

With k = 60, a document ranked first by both legs always scores 2/61, whether it is the perfect
answer or the least irrelevant document in the corpus. RRF encodes rank agreement, not relevance
(WF-10). An answerability gate has to come from a model that scores the query against the passage.

## The relevance signal

- **Computed from** the cross-encoder scores of the top passages (ADR-0015's selected (N, L)): the
  best passage's score, the margin to the second, and the count of passages above τ.
- **Versioned.** The version string names the cross-encoder model, N, L and the scoring code. It
  is recorded in every answer manifest. A change to any of them is a new version, and a new
  version has no τ until it is recalibrated. **Uncalibrated means no generation**, not "reuse the
  old τ".

## The decision

| Condition | Mode |
|---|---|
| Signal unavailable (`rerank_shed`, `dense_unavailable`, lexical-only, reranker down) | `extractive` |
| Signal available, best-passage score < τ | `refused` |
| Signal available, best-passage score ≥ τ | may generate: `generated`, subject to egress and provider policy |

- **v1 gates on the best-passage score alone.** The margin and the count are recorded in every
  trace and analysed on dev, but they do not gate in v1. Adding them to the gate is a new signal
  version with its own calibration. **Reviewer decides**: gating on one quantity keeps a 20-question
  calibration set from being fitted three ways.
- **Unavailable signal gives `extractive`, not `refused`.** The passages were retrieved; only the
  evidence to vouch for them is missing. A below-τ score is positive evidence of irrelevance, so
  that case refuses. **Reviewer decides**; §9.6.1 permits either.
- A degraded mode never inherits the normal mode's quality numbers.
- Multi-part questions: a high best-passage score does not certify every part. The answer prompt
  requires the model to name the parts it cannot support, and those cases are measured separately
  (§9.6.1).

## Calibrating τ

- **Data:** the dev halves of the explain set (20 answerable) and the unanswerable set (20)
  (§14.3). Nothing from test is seen.
- **Target:** answer precision of at least **0.90** on dev. Answer precision is the fraction of
  questions the gate lets through that are answerable. **Reviewer decides** the 0.90, which mirrors
  §3.3's answer-support point target.
- **Rule:** τ is the **lowest** threshold that meets the target on dev. That maximises coverage
  subject to precision. If no threshold meets it, there is no τ, the signal version is not
  permitted to generate, and the release ships locate plus extractive (§19.8 step 3).
- **Reporting:** on the **test** halves, a risk-coverage curve per mode, the answerable/unanswerable
  confusion matrix, and Wilson 95% intervals. At n = 20, 18/20 spans 0.699–0.972. The release
  quotes the interval, never the point estimate alone (§3.3, WF-28).
- τ is not re-tuned after the test halves are scored (ADR-0013's "spent" rule applies).

## What is deliberately not decided here

- **Claim support and citation quality.** §3.3 and §15.3 set those bars, and the judged
  generation eval measures them. Answerability only decides whether generation may start.
- **Provider choice and egress.** §9.7 and ADR-0008 decide those. A `generated` decision here is
  still subject to them.

## Consequences

- The answer manifest schema carries `relevance_signal_version`, the three signal values and τ.
- A reranker change under ADR-0015 disables generation until τ is recalibrated for the new version.
  That cost is intended.
