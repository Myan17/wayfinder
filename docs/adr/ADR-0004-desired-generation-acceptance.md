# ADR-0004 — Acceptance rules for "a push during a build is never lost" (spike S5)

- **Status:** Proposed. **The decision is deliberately empty**; spike S5 fills it.
- **Date written:** 2026-09-24, **before** any S5 harness exists.
- **Decides:** assumption A-6 (`DESIGN` §7.1) and risk R-11 (§20). It is the evidence for §9.3.3,
  which Phase 1's ingestion and generation work builds on.
- **Pins:** River **v0.47.0** (latest release, 2026-08-31), by module version in
  `apps/ingestd/go.mod`, and the ParadeDB image digest S3 pinned. What is measured is what ships.

## Why this document exists before the experiment

For the same reason ADR-0007 did (#16): a spike that writes its pass condition after the run cannot
fail. These rules merge first, and the harness and its results come in a later pull request.

## The claim under test

`DESIGN` §9.3.3: correctness comes from `repository.desired_generation`, and the River queue is only a
wake-up. Every accepted push increments `desired_generation` **and** enqueues `IndexRepo{repo_id}` in
the same transaction. A worker claims the repository, builds toward the `D` it read, re-reads `D`
before activating, and re-claims if it advanced. A dead worker's claim expires, and the reconciler
re-enqueues any repository whose desired generation is ahead of its active one.

**Column names.** §9.3.3's prose says `lease_token` / `lease_expires_at`. Schema v1 (following §9.2)
has `repository.claim_token` / `claim_expires_at`. The harness uses the schema's names, and its pull
request corrects the §9.3.3 prose in the same change.

## Scenarios

One repository and a real River client (v0.47.0) against the pinned Postgres. The build step is a
stand-in that writes a `building` → `ready` generation (no chunking or embedding), because S5 tests
scheduling, not indexing. Every transaction around it is the real one: claim, final head check, and
§9.3.5's fenced activation. Injections happen at **deterministic barriers** in the worker, never on
timers, so a scenario that passes is reproducible.

The five boundaries are §9.3.3's own list:

| # | Boundary |
|---|---|
| B1 | After the event is accepted, before any worker claims |
| B2 | Mid-build, after the claim and before the generation is `ready` |
| B3 | During the final head check, between reading `D` and deciding to activate |
| B4 | During activation, inside the §9.3.5 transaction before `COMMIT` |
| B5 | During a retry, after a failed attempt and before the next claim |

At each boundary there are three injections:

- **push**: a new event is accepted, which increments `desired_generation` and enqueues, in one transaction.
- **kill**: the worker process gets `SIGKILL`.
- **push then kill**.

That makes 15 scenarios. Two more cover a **paused** worker: `SIGSTOP`, held past
`claim_expires_at` while another worker takes over, then `SIGCONT`. They pause at:

- **B2** (mid-build), and
- **B4′**: immediately **before** the activation transaction takes the repository row lock (§9.3.5's
  `SELECT … FOR UPDATE`). This is not inside the transaction. A worker paused while holding that lock
  would block the takeover it is supposed to lose to, and nothing would be tested. Pausing just
  before the lock lets the claim expire and another worker activate, so the resumed worker's refusal
  is real. Failure *inside* the transaction is still covered by the kill-at-B4 scenario.

That's **17 scenarios, each run 20 times.**

## Acceptance rules

Each rule is one falsifiable observation. **Any single failure, in any run of any scenario, fails the
rule.** There is no pass rate.

| # | Claim | PASS requires |
|---|---|---|
| S5-1 | **No lost push** | After the scenario quiesces (workers drained, one reconciler pass, claim expiry elapsed), the active generation's `desired_generation` equals `repository.desired_generation` |
| S5-2 | **No regression** | Across the run, each activation's `desired_generation` is ≥ the one it replaced. A slow worker never moves a repository backwards |
| S5-3 | **One active generation** | Never more than one `active` generation per repository at any observation, and `repository.active_generation_id` always names it |
| S5-4 | **An expired claim never activates** | In both paused-worker scenarios (B2 and B4′), after another worker has taken over, the resumed worker's activation is refused (§9.3.5's `UPDATE … WHERE active_generation_id IS NOT DISTINCT FROM $base` touches 0 rows, or its claim check fails). Its generation ends `failed`, and nothing it built is `live` |
| S5-5 | **Uniqueness is not load-bearing** | S5-1 to S5-4 hold with every `IndexRepo` insert made **without** River unique-job options. The design must not depend on which states River deduplicates (§9.3.3, WF-07) |

**What a FAIL means.** R-11's mitigation is that correctness lives in `desired_generation`, not in the
queue. So a failure is a defect in **our** protocol (§9.3.3–9.3.5), not in River's documentation. The
protocol is fixed, and its §9.3 text edited, before Phase 1 builds on it. There is no third outcome,
and no "PASS with a note".

## Review rulings (gupta958, 2026-09-24)

- 17 scenarios × 20 runs: **accepted**.
- River v0.47.0: **accepted**.
- Paused-worker coverage: **accepted at B2**. At B4 the barrier moves to B4′, before the row lock
  (above), so the takeover can happen and the refusal is meaningful.

## What is deliberately not a rule

- **No convergence-time threshold.** DESIGN gives none for this path. The harness records time to
  quiescence per scenario, and that number is reported, not judged.
- **No throughput or River-performance claim.** S5 is about correctness at boundaries.
- **River's own deduplication behaviour** is not tested. S5-5 exists so that it never needs to be.

## Decision

*Empty until S5 runs.* It will be completed with one of:

- **Accept §9.3.3 as designed.** S5-1 to S5-5 all PASS, with the run output quoted.
- **Revise the protocol.** Name the failing rule and the scenario, quote the output, and edit §9.3
  in the same pull request as the fix.
