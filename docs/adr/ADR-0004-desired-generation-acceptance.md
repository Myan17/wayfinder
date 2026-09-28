# ADR-0004 — Acceptance rules for "a push during a build is never lost" (spike S5)

- **Status:** **Accepted** on 2026-09-27: §9.3.3 as designed (#45–#48). The Decision below was
  written after the run, and the rules above are unchanged since #34.
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

### Starting state (pinned, so the harness cannot choose it after seeing results)

Every run of every scenario starts in a **freshly created database** (all migrations applied, nothing
carried over from an earlier run), with one repository in this **quiescent** state:

1. **Exactly one active baseline generation** exists for the repository. It has status `active`,
   `desired_generation = 1`, and a baseline `commit_sha`, and no other generation exists.
2. `repository.active_generation_id` **points to that generation**.
3. `repository.desired_generation = 1`, **equal** to the baseline generation's `desired_generation`.
4. **No live claim:** `claim_token` and `claim_expires_at` are `NULL`.
5. **No outstanding River job:** the River job table holds no `IndexRepo` in any non-finalized
   state for this repository.

Then **the initial push is accepted**: `desired_generation` goes 1 → 2, and `IndexRepo` is enqueued,
in one transaction. At that moment the scenario begins, and its injections happen after it. The
harness asserts all five preconditions before the initial push. A run whose preconditions fail is
an **error**, not a pass or a fail, and it is reported as such.

This is what makes S5-2 and S5-3 meaningful. A baseline of 1 gives every activation a predecessor to
be compared with (S5-2), and there is an active generation from the first observation onward (S5-3).

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

**Accept §9.3.3 as designed.** S5-1 to S5-5 hold in every run of every scenario, with every insert
made without unique-job options (S5-5).

The harness was `apps/ingestd/cmd/s5spike` with `apps/ingestd` at tree `15e1d8c`, which is #47's
code (a tree hash survives rebases; a commit SHA does not). It ran against River v0.47.0 and the
pinned ParadeDB, on a fresh template0 database per run, with a 1.5 s claim TTL:

```
$ s5spike run -admin postgresql://…@localhost:55432/s3spike -root . -runs 20
B1-push      pass 20  fail  0  error  0
B1-kill      pass 20  fail  0  error  0
B1-pushkill  pass 20  fail  0  error  0
B2-push      pass 20  fail  0  error  0
B2-kill      pass 20  fail  0  error  0
B2-pushkill  pass 20  fail  0  error  0
B3-push      pass 20  fail  0  error  0
B3-kill      pass 20  fail  0  error  0
B3-pushkill  pass 20  fail  0  error  0
B4-push      pass 20  fail  0  error  0
B4-kill      pass 20  fail  0  error  0
B4-pushkill  pass 20  fail  0  error  0
B5-push      pass 20  fail  0  error  0
B5-kill      pass 20  fail  0  error  0
B5-pushkill  pass 20  fail  0  error  0
B2-pause     pass 20  fail  0  error  0
B4'-pause    pass 20  fail  0  error  0
run time (not judged, ADR-0004): median 2.226s, max 3.142s over 340 runs
S5-1..S5-5: no failure in any run of any scenario
```

**Found on the way. None of these revises the protocol:**

- **NULL is not live.** The stand-in `activate()` read `claim_expires_at > now()` into a boolean.
  After a takeover released its claim, that column was NULL, and pgx failed instead of refusing, so
  River retried and the resumed worker could activate a redundant rebuild. §9.3.5 already says to
  abort unless `claim_expires_at > now()`, so the protocol was right and the implementation wrong.
  The fix is `coalesce(…, false)`, and §9.3.5 now says so explicitly for implementers.
- **B3 was in the wrong place** (review of #45). The barrier fired before the final read of `D`,
  so a push at B3 was seen by the read and the worker only rebuilt. It now fires after the read and
  before the decision, as this ADR defines B3. A push there leaves the read stale, and the
  activation fence refuses it: in B3-push, generation D=2 ends `failed` and D=3 is active. The run
  above has the corrected B3; the earlier 340/340 with the wrong order is superseded.
- **The rules fail closed** (review of #46 and #47). A query or scan error in any rule is a run
  ERROR, never a judged rule. The verdict is read after the final S5-3 observation. Before this,
  an S5-4 or S5-5 read error counted as 0 bad rows, and a failure from the final observe() was
  dropped. `-runs` below 1 and an unknown `-scenario` are rejected before anything runs. They
  used to run nothing and print a passing verdict. The run above is on this code.
- **A harness read bug.** The paused-takeover read stopped on the `failed … "activation refused"`
  line, before the `refused` event that S5-4 checks. It now matches the event prefix.
- **Mutation checks show S5-4 is enforced in depth.** The task log of part 1 has the details.
  - Removing only the claim fence (M1) is caught by the compare-and-swap on `active_generation_id`.
  - Removing only the compare-and-swap (M4) is caught by the claim fence.
  - Removing both (M5) is caught by schema v1's `one_active_per_repo` index, whose unique violation
    fails the job.
  - A naive activation that retires whatever is active (M6) **fails S5-4** in both pause scenarios.
    That shows the harness can detect the violation.
  - Removing the reconciler (M3) fails S5-1 in 9 scenarios.
  - Removing the final head check (M2) survives. The activation fence's `desired != D` and the
    re-read after activation back it up, so it is an early exit, not the safety mechanism.
  - Removing the activation fence's `desired != D` (M7) **also survives** B3-push, B3-kill and
    B3-pushkill, 3/3 each. The stale target activates for a moment. The re-read after activation
    sees `D` advanced and rebuilds, so S5-1 (the final state) and S5-2 (never backwards) still
    hold. **These rules do not detect a briefly stale activation.**
    **Reviewer decision (gupta958, 2026-09-28): accept the limitation.** This ADR tests eventual
    "no lost push", not a guarantee that a briefly stale generation never activates. The rules
    above were written before the run and are not changed after it. §9.3.5's
    `desired_generation = D` activation fence stays in production. **The production worker's
    implementation must include a direct test of that fence**, because S5 does not exercise it on
    its own.

**Consequences.** P1 builds ingestion on §9.3.3 unchanged, with no River uniqueness options. The
production worker must carry the `coalesce` rule. It must also keep the `desired_generation = D`
fence, with a direct test of it (the M7 decision above). §9.3.3's prose now uses schema v1's
`claim_*` names (the column-name note above).
