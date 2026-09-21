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

| # | Claim | PASS requires | FAIL means |
|---|---|---|---|
| S3-1 | The image runs on this architecture | The pinned ParadeDB image starts on `linux/arm64` **natively** — `uname -m` inside the container reports an aarch64 machine, and the image is not running under emulation | Fallback. An emulated image is not evidence about the A1 target |
| S3-2 | The extension installs with the privileges we will actually have | `CREATE EXTENSION pg_search` succeeds, and the BM25 index DDL of §9.2 is accepted verbatim against a table with `key_field = 'id'` | Fallback, **or** a documented privilege requirement that Oracle A1 can satisfy — recorded here, not assumed |
| S3-3 | **Snapshot visibility, quiet case** | In `REPEATABLE READ`, a BM25 query run twice in one transaction returns identical results while a concurrent session inserts and commits matching rows between the two | Fallback. This is the weakest form of the claim; failing it ends the discussion |
| S3-4 | **Snapshot visibility, under an activation** | With a concurrent generation switch running — the workload A-5 actually names — a reader's transaction returns rows from exactly one generation, never a row whose generation differs from the one its snapshot began with | Fallback |
| S3-5 | Deleted rows leave the index with their row | After `DELETE` + `COMMIT`, a BM25 query in a **new** transaction never returns the deleted row; a transaction whose snapshot predates the delete still does | Fallback. Deletion closure (§9.3.6) depends on the index not outliving its rows |
| S3-6 | The planner uses the index, and we can see that it does | `EXPLAIN (ANALYZE, BUFFERS)` on the two-leg hybrid query of §9.5 shows the BM25 scan in use rather than a sequential scan with a filter, and the plan is capturable as text for the release manifest | **Not** an automatic fallback. Record the plan and raise it at G0 — a planner problem is tunable, an MVCC problem is not |

### What is deliberately not a rule here

- **No latency threshold.** `DESIGN` sets no per-engine latency budget for the lexical leg alone;
  §10.3's numbers are whole-system planning estimates that S2 replaces outright. A threshold invented
  today would read as evidence in three weeks.
- **No ranking-quality comparison.** R-06 places the fallback's measurement in E1 (§15.4), whose
  stated question is whether lexical and dense complement each other, scored on Recall@10. S3 asks
  only whether the engine is *safe to build on*, which is a different question and answerable now.
- **No opinion on AGPL-3.0.** Settled in ADR-0002 and open question Q-3 (§7.3).

## Decision

_Empty until S3 runs._ It will record, per rule, the observed result and the command that produced
it, then one of:

- **Accept `pg_search`** — all of S3-1 … S3-5 PASS. S3-6 recorded either way.
- **Fall back to built-in FTS** — any of S3-1 … S3-5 FAIL, naming which, with the failing output
  quoted. That changes §9.2's DDL and the lexical half of §9.5, and both are edited in the same pull
  request as the decision.

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
