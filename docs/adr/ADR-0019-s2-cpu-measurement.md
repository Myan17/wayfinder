# ADR-0019 — How spike S2 measures whole-system CPU, and when it is done

- **Status:** Proposed. **The decision is deliberately empty**; spike S2 fills it.
- **Date written:** 2026-10-19, **before** any S2 harness exists.
- **Decides:** how assumption A-4 (`DESIGN` §7.1) is tested, and the method behind every row of
  §10.3's CPU budget, which S2 replaces. It also supplies two inputs that other rules already wait
  for: ADR-0015 step 2's per-arm rerank CPU, and ADR-0013's cost measures for E2 and E5.
- **Values marked "Reviewer decides"** are the ones `DESIGN` leaves open. They need `gupta958`'s
  approval before the harness is written.

## Why this document exists before the experiment

A CPU measurement has more free choices than a pass/fail spike. The choices include which queries
to use, which cache state, which process is charged, whether background work is counted, and which
percentile is reported. Each one can move a total by tens of percent, and §10.3's estimates already
sit close to the 70% bar. If these choices were made after seeing the numbers, the budget could be
made to fit. They are fixed here so the measurement decides it.

S2 is a **measurement**, not a pass rule for the design. Whether the system fits two cores is
answered by the recomputed totals (S2-7) through rules that already exist: ADR-0015 for the rerank
arm and §10.3 decision 2 for a lower published concurrency. The rules below decide only whether the
measurement is **valid and complete**.

## Setup (pinned, so the harness cannot choose it after seeing results)

- **Host: the provisioned Oracle A1**, 2 OCPU / 12 GB, `aarch64` (§10.1). Every number that S2
  reports as evidence comes from it, because ADR-0013 requires the same host for every measured cost,
  and that host is the A1 once it exists. A run on a development machine is **S2-dev**. S2-dev can
  only check the harness before the A1 run, and its numbers are never evidence (ADR-0007, S3-1a).
- **Images and models:** the pinned ParadeDB image (ADR-0007's digest). Ollama is pinned by version.
  The query embedder is `nomic-embed-text` at digest `0a109f42…e59f`, the digest ADR-0005's run
  captured. The reranker is an ONNX MiniLM-class cross-encoder, `cross-encoder/ms-marco-MiniLM-L-6-v2`,
  pinned by file hash. **Reviewer decides** the reranker; ADR-0015 leaves the model to E3, and S2
  only needs one that has the §10.3 shape.
- **Corpus:** S1's accepted corpus (ADR-0016): pydantic, black, cli/cli and fiber, about 7,175
  chunks. §10.3 budgets SQL at **≤ 60k live representations**, so the SQL stage also runs at 60k. The
  extra rows are generated from the real chunks with stand-in vectors (ADR-0005's stand-in), and the
  report records the fraction that is padding. **Reviewer decides** whether 60k is padded this way or
  only the real size is measured.
- **Queries:** the dev split's issues (ADR-0013), using the issue title and body as §14.2's query
  provenance defines them. They are normalized by §9.4.2, and inputs above 2,000 characters are
  rejected, as §9.5 step 1 does in production. Test and held-out queries are never used.
- **Threads:** one inference thread per call (`intra_op_num_threads = 1`, §10.5). Ollama runs with
  `num_thread` 1.
- **Timing protocol:** ADR-0013's protocol: three warm-up passes, then five timed passes over the
  full query set. A stage's cost is the median of the five per-pass means. The per-call p50 and p95
  come from all calls in the timed passes.

## What is charged, and to which process

S2 measures **process CPU time** (user plus system), not wall time. Wall time is recorded but never
judged.

| Stage (§10.3 row) | Charged to | How |
|---|---|---|
| Query embedding | the Ollama runner process | the change in `utime + stime` from `/proc/<pid>/stat`, across the call |
| Hybrid SQL | the Postgres backend serving the call | the same, for `pg_backend_pid()`'s process |
| Rerank | the calling thread | `time.thread_time()` across the ONNX call |
| API overhead | the calling thread | the same, across authorization resolution and JSON encoding of a shaped response |
| Token relay | the calling thread | the same, across relaying 300 tokens from a stub provider |

A stage that crosses processes is charged to every process it touches.

## Acceptance rules

S2 is complete only if every rule holds on the A1.

| # | Rule | Complete when |
|---|---|---|
| S2-1 | **Every §10.3 row has a measured value or a named owner** | Each work item in §10.3 has a measured per-call p50 and p95 in core-ms, or is listed as not measurable in P0 and names the phase whose test measures it. The token relay and the tracing part of API overhead need `api`, which does not exist yet. **Reviewer decides** between a minimal stand-in endpoint now and deferring both to L1 (§16.4). Either way, a deferred row stays marked *estimate* in §10.3 |
| S2-2 | **Every rerank arm** | Per-call CPU for all eight arms of ADR-0015's grid (N ∈ {8, 16, 32, 50}, L ∈ {128, 256}). The input passages are the hybrid stage's top N for each dev query, truncated to L tokens. ADR-0015's consequences make this a precondition of its step 2 |
| S2-3 | **Query length** | The report gives the dev queries' token-length distribution under the embedder's tokenizer: p50, p95 and maximum. It gives embedding CPU per call at p50 and p95, and as a function of length. §10.3's "not a 20-token assumption" is checked here |
| S2-4 | **ACL selectivity** | The SQL stage runs with the `eligible_repo` predicate admitting 1%, 10% and 100% of repositories, the visibility levels E7 uses. Each level is reported separately and not averaged |
| S2-5 | **Cache states** | *Warm*: after the warm-up passes. *Cold*: after restarting Postgres and Ollama, and dropping the OS page cache. Both are reported. The budget uses the **warm** numbers, because §10.3 is a nominal-load budget. **Reviewer decides** this |
| S2-6 | **Concurrent indexing** | Stages 1, 2 and 4 are repeated while a full re-index of the corpus runs. The re-index uses the ingestion Ollama instance at lower OS priority (§10.5), through `db/s6_identity.py`'s build path. The report gives the per-call CPU under indexing and the indexing work's own CPU in core-seconds per second, compared with the 25% reservation |
| S2-7 | **The totals are recomputed, not edited** | A committed script recomputes §10.3's required-cores table from the report: every row, at the throughput its own mix implies, with **no answer-cache hit credited** (§10.3 decision 3). The script's output is committed with the report |
| S2-8 | **Provenance** | The report records `uname -m`, `lscpu`, the OCI shape, the image and model digests, the Ollama version, the reranker file hash and the commit. The results pull request commits it unchanged, as #84 did for S6 |

### The calibration control

Before and after every run, the harness measures a fixed busy-loop of known CPU through each
accounting path in the table above: the Ollama process, a Postgres backend (`pg_sleep` does not burn
CPU, so the backend runs a fixed arithmetic `generate_series`), and the calling thread. The loop is
calibrated against `getrusage`. **Every path must read within ±5% of the loop's known cost.** If one
does not, that accounting path is wrong, and S2 is an **error**, not a result.

## What is deliberately not a rule

- **Latency SLOs.** These are §10's and L1's. S2 records wall time but never judges it.
- **Throughput under load.** S2 measures per-call cost. Whether the system holds 30.5 req/s is L1,
  and S2-7's arithmetic is only the prediction L1 tests.
- **Rerank quality.** That is E3. S2 does not decide the arm; ADR-0015 does.
- **Memory.** §10.4 is checked under L3, not here.
- **The HNSW plan.** That is S3-6 (ORIENT item 9c). S2 times the query and does not check its plan.

## Order of work

1. This ADR, reviewed and merged.
2. **The SQL stage needs §9.5's two-leg query.** That is S3-6's harness, ORIENT item 9c, which comes
   after this item in the order. Item 9c needs no A1. **Reviewer decides** whether 9c's harness lands
   before S2's harness, so that S2 times the same query whose plan S3-6 captures, or whether S2 writes
   its own query and 9c reuses it.
3. The S2 harness, tested in CI on a small fixture with S2-dev's numbers marked as not evidence.
4. The A1 run, by Myan, once ORIENT item 9b provisions the A1. **Until then item 7 is blocked on the
   A1**, and ORIENT rule 4 sends work to the next item.
5. The results pull request: the report and S2-7's output unchanged, this Decision, and §10.3's rows
   replaced by the measured values in the same pull request (§16.8).

## Decision

*Empty until S2 runs on the A1.* It will be completed with:

- **Measured:** every §10.3 row's p50 and p95, or its named owner (S2-1); every rerank arm's CPU
  (S2-2); the recomputed totals table (S2-7); and A-4 marked **holds** or **does not hold** at the
  70% bar with no cache credit. If it does not hold, nothing is re-run with different choices.
  ADR-0015 step 5 and §10.3 decision 2 apply as written.
- **Error:** the calibration control failed, or a rule could not be completed. Name it. The method
  is fixed before the next run, and the run is repeated in full.
