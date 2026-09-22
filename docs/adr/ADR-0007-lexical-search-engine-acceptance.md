# ADR-0007 — Acceptance rules for ParadeDB `pg_search` on arm64

- **Status:** Proposed. **The decision is deliberately empty**; spike S3 fills it.
- **Date written:** 2026-09-21, **before** S3 runs.
- **Decides:** assumption A-5 (`DESIGN` §7.1) and risk R-06 (§20).
- **Supersedes nothing.** ADR-0002 (§12.1) already chose `pg_search` for BM25 and named built-in FTS
  as the fallback; this records what evidence would force that fallback.

## Why this document exists before the experiment

A spike that writes its threshold after seeing the measurement cannot fail. With the rule and the
result in the same change, the author picks the number the run happened to produce, and nobody
reading it afterwards — including the author — can separate a passed test from a moved goalpost. So
the rules land in their own pull request, ahead of the harness and ahead of any measurement, and the
ordering is checkable from the merge order rather than from anyone's word.

This is not a formality. R-06 is rated impact **H**: if `pg_search` is unusable here, the lexical
half of hybrid retrieval changes engine, the BM25 index DDL in §9.2 changes shape, and the retrieval
tests change with it.

## The question

`DESIGN` §7.1, assumption A-5:

> The ParadeDB image runs on arm64 and `pg_search` honours MVCC snapshot visibility.

Two claims, and the second is load-bearing. The system builds a new index **generation** while the
current one keeps serving, then activates it atomically under a fence (§9.3.5). A reader holding a
transaction snapshot must see one generation for the whole of its query. If `pg_search`'s BM25 index
answers from state outside the caller's snapshot, then during an activation a query can match a row
from the generation being retired and score it against statistics from the generation arriving — and
no care in the application layer prevents it, because the application never sees the inconsistency.

The vector leg (pgvector) is ordinary Postgres index machinery and is not in question. What is in
question is whether the lexical leg is a first-class MVCC citizen or an index that happens to live in
the same process.

## Acceptance rules

Each rule is a single falsifiable observation. **Any FAIL sends the decision to built-in FTS**, per
R-06's stated mitigation. There is no partial credit and no "acceptable with a workaround" column,
because a workaround invented after a failure is the same goalpost problem in a different place.
Every rule below obeys that sentence without exception — an earlier draft let S3-2 offer "fallback,
**or** a documented privilege requirement", contradicting the governing rule in the one place the
governing rule was load-bearing.

Every command named here runs against the image **pinned by digest**, never by tag, so the artifact
that was measured is the artifact that ships.

| # | Claim | PASS requires | FAIL means |
|---|---|---|---|
| S3-1a | The architecture chain agrees on a development machine | All four points below, on any aarch64 development host. **Precondition only** — never an acceptance | Investigate before spending A1 time |
| S3-1b | The architecture chain agrees **on the A1** | The same four points, on the provisioned Oracle A1, against the same digest | Fallback |
| S3-2 | The extension installs with the privileges we have declared **in advance** | Under ADR-0007 **option A** — a single Oracle VM where we provision Postgres ourselves, so the role is `SUPERUSER` — `CREATE EXTENSION pg_search` succeeds and the BM25 index DDL of §9.2 is accepted verbatim against a table with `key_field = 'id'` | Fallback. No exception. If it needs something a self-provisioned instance cannot grant, that is a failure, not a workaround |
| S3-3 | **Snapshot visibility, quiet case** | In `REPEATABLE READ`, a BM25 query run twice in one transaction returns identical results while a concurrent session inserts and commits matching rows between the two | Fallback. This is the weakest form of the claim; failing it ends the discussion |
| S3-4 | **Snapshot visibility, under an activation** | The five-step interleaving below, all five steps | Fallback |
| S3-5 | Deleted rows leave the index with their row | After `DELETE` + `COMMIT`, a BM25 query in a **new** transaction never returns the deleted row; a transaction whose snapshot predates the delete still does | Fallback. Deletion closure (§9.3.6) depends on the index not outliving its rows |
| S3-6 | The planner uses the index, and we can see that it does | `EXPLAIN (ANALYZE, BUFFERS)` on the two-leg hybrid query of §9.5 shows the BM25 scan in use rather than a sequential scan with a filter, and the plan is capturable as text for the release manifest | **Not** an automatic fallback. Record the plan and raise it at G0 — a planner problem is tunable, an MVCC problem is not |

### S3-1: the four points that establish native execution

All four, in the same run, against the same digest:

| # | Point | Command | Required |
|---|---|---|---|
| 1 | Host architecture | `uname -m` **on the host, outside any container** | `aarch64`, or `arm64` — the same architecture under two spellings. **On the A1 (S3-1b) it must be `aarch64`**, because the A1 is Linux and Linux spells it that way; `arm64` there would mean the host is not what we think it is |
| 2 | Docker daemon architecture | `docker version --format '{{.Server.Arch}}'` | `arm64` |
| 3 | Selected image architecture | `docker image inspect <digest> --format '{{.Architecture}}'`, and `{{.Variant}}` separately | `Architecture` is `arm64`. `Variant`, **if the image declares one**, is `v8`; an empty variant is not a failure |
| 4 | It actually ran | The container starts and Postgres accepts a connection | Exit 0 |

**Why this is sufficient, and why the check it replaces was not.** Emulation is how Docker executes
an image whose architecture does not match the host. If host, daemon and selected image all report
arm64 and the container runs, there is no foreign format to emulate — the question does not arise.

An earlier draft instead required that `/proc/sys/fs/binfmt_misc/` register no `qemu-aarch64`
interpreter on the A1. That reasoning was backwards. A `qemu-aarch64` handler is what lets an
**amd64** host run arm64 binaries; on an aarch64 host it is irrelevant, and its registration would
not mean Docker had used it for this container. Absence of the handler was neither necessary nor
sufficient. Points 1–4 are both.

An earlier draft before that used `uname -m` *inside* the container, which reports what the binary
sees: an arm64 image emulated on an amd64 host reports `aarch64` and passes. Point 1 is deliberately
outside the container for that reason.

**Corrected 2026-09-22, before any S3 result was recorded.** Reconnaissance against the pinned
digest showed this table failing a genuinely arm64 image, twice over:

- Point 3 demanded `arm64/v8`. ParadeDB's manifest advertises `{"architecture": "arm64", "os":
  "linux"}` with **no variant key**, so `{{.Variant}}` is empty and the rule failed. `alpine:3.20`
  and `postgres:17` do set `v8` on their arm64 builds, which is what the draft was written from.
  Variant is optional in the OCI platform object, and its absence is not evidence about
  architecture — so the rule was asking for something that does not have to exist.
- Point 1 demanded `aarch64`. Linux spells it that way, macOS spells it `arm64`, and S3-1a is
  defined to run on a development machine.

Both were errors in **what to observe**, not thresholds that turned out inconvenient, and both
failed *closed* — they would have sent a working engine to the fallback. They are corrected here in
their own change, with no S3 result recorded anywhere yet, precisely so the correction cannot be
mistaken for adjusting a rule to fit a measurement. Choosing a different image that does set `v8`
would have been the same error wearing a different hat: picking the artifact to suit the rule.

### S3-2: the privilege set, declared before the experiment

`SUPERUSER` on a Postgres instance we provision ourselves. That is what ADR-0007 **option A** gives
us, and option A is the default. Declaring it in advance is the point: otherwise "it needed more
privileges than expected, but we can arrange those" is a pass written after the fact.

A PASS under these privileges says nothing about **option B** (Cloud Run + Neon), where the risk
register already records extension support as unverified. If option B is ever taken, S3-2 is re-run
there; this result does not transfer.

### S3-4: the required interleaving

A single query issued after an activation would trivially return one generation and prove nothing.
The reader's snapshot must be established **before** the switch and must survive it:

| Step | Session | Action | Required observation |
|---|---|---|---|
| 1 | Reader | `BEGIN ISOLATION LEVEL REPEATABLE READ`, then a statement that forces the snapshot to be taken | Snapshot is on the **old** generation |
| 2 | Reader | BM25 query | Returns rows from **only** the old generation |
| 3 | Writer | Activate the new generation and `COMMIT` | Activation completes |
| 4 | Reader | **Same transaction**, BM25 query again | Returns rows from **only** the old generation — identical to step 2 |
| 5 | New session | `BEGIN`, BM25 query | Returns rows from **only** the new generation |

Step 4 is the rule. If the reader's second query sees any row from the new generation, the BM25
index is answering from outside the caller's snapshot and `pg_search` fails A-5. Step 5 exists so a
"nothing ever changes" implementation cannot pass by being uniformly stale.

### What is deliberately not a rule here

- **No latency threshold.** `DESIGN` sets no per-engine latency budget for the lexical leg alone;
  §10.3's numbers are whole-system planning estimates that S2 replaces outright. A threshold invented
  today would read as evidence in three weeks.
- **No ranking-quality comparison.** R-06 places the fallback's measurement in E1 (§15.4), whose
  stated question is whether lexical and dense complement each other, scored on Recall@10. S3 asks
  only whether the engine is *safe to build on*, which is a different question and answerable now.
- **No opinion on AGPL-3.0.** Settled in ADR-0002 and open question Q-3 (§7.3).

## Decision

**Still Proposed. Measured locally on 2026-09-22; S3-1b outstanding, so this is not an acceptance.**

Image `paradedb/paradedb@sha256:c17153b8…64f4` (0.25.9, `linux/arm64`), PostgreSQL 18.6,
`pg_search` 0.25.9. Reproduce with `infra/spikes/s3/`.

| Rule | Result | Observed |
|---|---|---|
| S3-1a | PASS | `host=arm64 daemon=arm64 image=arm64 variant=(absent)` |
| **S3-1b** | **OUTSTANDING** | Requires the provisioned Oracle A1. Cannot be measured from a development machine, and is not being approximated by one |
| S3-2 | PASS | `pg_search 0.25.9`, `is_superuser=on`, §9.2's BM25 DDL accepted verbatim |
| S3-3 | PASS | 5 rows, then 5 rows, in one `REPEATABLE READ` snapshot across a concurrent commit |
| S3-4 | PASS | Reader saw gen `[1]`; writer activated gen 2 and retired gen 1; **same transaction still saw `[1]`**; a new transaction saw `[2]` |
| S3-5 | PASS | Snapshot predating the delete kept 4 rows; a new transaction saw 0 |
| S3-6 | PASS | `Custom Scan (ParadeDB Base Scan)`, `Index: rep_bm25`, no `Seq Scan` |

S3-4 is the result that matters, and a test that passes first time deserves suspicion, so it was
mutation-checked: weakening the reader to `READ COMMITTED` makes step 4 return gen `[2]` and the
rule fail. The PASS therefore reflects `pg_search` honouring the caller's snapshot rather than a
test that cannot fail.

S3-6's plan, for the record:

```
->  Parallel Custom Scan (ParadeDB Base Scan) on representation
      Table: representation
      Index: rep_bm25
      Exec Method: TopKScanExecState
      Tantivy Query: {"boolean":{"must":[{"with_index":{"query":{"parse_with_field":
                     {"field":"body_text","query_string":"widget"}}}},
                     {"term":{"field":"live","value":true}}]}}
```

**What this does not establish.** Everything above ran on an Apple M2 Pro, not on an Oracle A1. The
architecture is the same and the image digest is the same, but A-5 is a claim about the deployment
target and §19.2 puts A1 provisioning inside S3. Nothing here should be cited as A-5 being settled.

When S3-1b runs, this section is completed with one of:

- **Accept `pg_search`** — every one of S3-1b, S3-2, S3-3, S3-4 and S3-5 PASS, each measured on the
  A1. S3-6 recorded either way. S3-1a is a precondition and carries no weight here: passing it on a
  development machine is not evidence about the deployment target.
- **Fall back to built-in FTS** — any one of them FAILs, naming which, with the failing output
  quoted. That changes §9.2's DDL and the lexical half of §9.5, and both are edited in the same pull
  request as the decision.

**There is no third outcome**, and in particular no "PASS with a note". A rule that needed a note is
a rule that failed.

**S3-1b cannot be settled until the A1 exists**, so this ADR stays Proposed until then even if every
other rule passes on a development machine. That is deliberate: a local aarch64 machine and an
Oracle A1 are both arm64, but A-5 is a claim about the deployment target, and the same digest
behaving here is a precondition, not the evidence. §19.2 puts A1 provisioning inside S3 for this
reason. A partial result is recorded as *"S3-1a..S3-6 measured locally, S3-1b outstanding"* — never
as an acceptance.

## Consequences if the fallback is taken

- §9.2's BM25 index DDL is replaced by `tsvector` + GIN, and the "real BM25 ranking in the same
  database" advantage claimed in §12's comparison table is lost — the table gets corrected rather
  than quietly left standing.
- The AGPL-3.0 obligation accepted in ADR-0002 no longer applies. That is a simplification, not a
  reason to prefer the fallback.
- RRF fusion (§9.5) is unaffected: it consumes **ranks, not scores**, so the fusion layer does not
  care which engine produced the lexical ranking. This is why the fallback is cheap enough to be
  credible rather than a threat.

## References

Every section number below was checked against `docs/DESIGN.md` at the commit this ADR lands on.

- §7.1 A-5 · §7.3 Q-3 · §9.2 data model and BM25 DDL · §9.3.5 fenced activation ·
  §9.3.6 deletion closure and GC order · §9.5 retrieval pipeline and RRF · §10.3 CPU budget ·
  §12 technology comparison · §12.1 ADRs · §15.4 experiments (E1) · §19.2 S3 · §20 risk register
  (R-06)
- ParadeDB `pg_search` — https://github.com/paradedb/paradedb
