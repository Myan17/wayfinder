# ADR-0019 — How spike S2 measures whole-system CPU, and when it is done

- **Status:** Proposed. **The decision is deliberately empty**; spike S2 fills it.
- **Date written:** 2026-10-19, **before** any S2 harness exists.
- **Decides:** how assumption A-4 (`DESIGN` §7.1) is tested, and the method behind every row of
  §10.3's CPU budget, which S2 replaces. It also supplies two inputs that other rules already wait
  for: ADR-0015 step 2's per-arm rerank CPU, and ADR-0013's cost measures for E2 and E5.

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
  only check the harness, and its numbers are never evidence (ADR-0007, S3-1a). The A1 runs nothing
  except S2 during a run; the load-test stub lives on the AMD micro (§10.1).
- **Services:** Postgres and the query Ollama instance each run in their own container, so each has
  its own cgroup. The ingestion Ollama instance gets a third container, used only for S2-6.
  - Postgres uses the pinned ParadeDB image (ADR-0007's digest), with `max_parallel_workers_per_gather = 0`.
    That way every call runs in one backend process, which the per-call accounting below charges. If
    production later allows parallel query, the SQL stage is measured again.
  - Ollama is pinned by version. The query embedder is `nomic-embed-text` at digest
    `0a109f422b47e3a30ba2b10eca18548e944e8a23073ee3f3e947efcf3c45e59f`, the digest ADR-0005's run
    captured.
- **The S2 reference reranker** (gupta958, ruling 1):

  | Item | Pinned value |
  |---|---|
  | Repository | `cross-encoder/ms-marco-MiniLM-L6-v2` on Hugging Face |
  | Revision | `233902d25c440f23af6f7d6e94d2946bac0bee0a` |
  | ARM64 ONNX artifact | `onnx/model_qint8_arm64.onnx`, 23,200,716 bytes, SHA-256 `3573b6b9593cb2f75987a31815d409ca3dd8808629118fd20451bb1a5d90cec7` |
  | Tokenizer | the same revision: `tokenizer.json` SHA-256 `d241a60d5e8f04cc1b2b3e9ef7a4921b27bf526d9f6050ab90f9267a1f9e5c66`, `tokenizer_config.json` `a5c2e5a7b1a29a0702cd28c08a399b5ecc110c263009d17f7e3b415f25905fd8`, `vocab.txt` `07eced375cec144d27c900241f3e339478dec958f92fddbc551f295c992038a3`, `special_tokens_map.json` `3c3507f36dff57bce437223db3b3081d1e2b52ec3e56ee55438193ecb2c94dd6` |

  The harness refuses to run if any of these hashes differ. If E3 selects a different artifact (a
  different model, quantization or export), that artifact's CPU is measured again under this ADR
  before ADR-0015 step 2 uses it.
- **Corpus:** S1's accepted corpus (ADR-0016): pydantic, black, cli/cli and fiber, about 7,175
  chunks. The SQL stage runs at **both** sizes (gupta958, ruling 2):
  - at the real corpus size;
  - at **60k** live representations, §10.3's budget size. The extra rows are copies of real chunks
    with deterministic stand-in vectors (ADR-0005's stand-in, seeded by row number).

  The report labels the 60k run **scale evidence** and records its padding fraction. It is never
  retrieval-quality evidence.
- **Queries:** the dev split's issues (ADR-0013), using the issue title and body as §14.2's query
  provenance defines them. They are normalized by §9.4.2, and inputs above 2,000 characters are
  rejected, as §9.5 step 1 does in production. Test and held-out queries are never used.
- **The SQL query** is item 9c's canonical two-leg query (§9.5), imported from 9c's harness and not
  rewritten (gupta958, ruling 5). S2 times the exact query whose plan S3-6 validates.
- **Threads:** one inference thread per call (`intra_op_num_threads = 1`, §10.5). Ollama runs with
  `num_thread` 1.

## How CPU is accounted

S2 measures **CPU time** at microsecond or finer resolution, never wall time. Wall time is recorded
but never judged. Tick-based counters, such as `utime` and `stime` in `/proc/<pid>/stat`, are never
used for a per-call value: at 100 Hz they resolve 10 ms, which is the same size as the stages being
measured.

| Stage (§10.3 row) | Charged to | Counter | Resolution |
|---|---|---|---|
| Query embedding | **every thread of every process** in the query Ollama container: `ollama serve`, its model runner, and any thread that starts or exits during the call | cgroup v2 `cpu.stat` `usage_usec` for that container, read before and after the call | 1 µs |
| Hybrid SQL | the Postgres backend process serving the call (one thread; parallel query is off) | field 1 of `/proc/<host pid>/schedstat`, the scheduler's on-CPU time in nanoseconds. The host pid comes from the backend's `NSpid` entry, matched against `pg_backend_pid()` | 1 ns |
| Rerank | the calling thread in the harness | `clock_gettime(CLOCK_THREAD_CPUTIME_ID)`, through `time.thread_time_ns()` | 1 ns |

The cgroup counter is used for Ollama because Ollama is multi-threaded, and its runner is a child
process. A per-thread counter would miss threads that exit before the second read. The cgroup counts
them, and it counts both processes. Ollama's idle background CPU is measured over 60 s with no
calls, and reported as a rate. It is not subtracted. The report gives that rate multiplied by the
median call duration beside the p50.

The harness checks each counter before use. It confirms that `/proc/<pid>/schedstat` exists (the
kernel was built with `CONFIG_SCHED_INFO`) and that the cgroup is v2. It reads each counter twice
across a busy target and requires a nonzero difference below 10 µs, to show the counter's real
resolution. If any check fails, S2 is an **error**.

## Warm and cold measurements are separate passes

- **Warm** (gupta958, ruling 4): ADR-0013's protocol. Three warm-up passes over the full dev query
  set, then five timed passes. A stage's cost is the median of the five per-pass means, and per-call
  p50 and p95 come from all the timed calls. **The nominal budget uses the warm numbers**, and no
  answer-cache hit is credited.
- **Cold:** separate passes, reported separately, and never mixed into the warm statistics. No
  warm-up passes apply. A cold pass measures **one** query, because only the first call after a
  reset is cold. The cold sample is 50 dev queries, fixed before the run: the first 50 by SHA-256 of
  `group_id`. Each of the 50 queries gets one cold pass, and the report gives p50 and p95 over them.
  **Before every cold pass, the harness runs this reset, in order:**
  1. Stop the Postgres and query Ollama containers (`docker compose stop`, so Postgres makes its
     shutdown checkpoint).
  2. Run `sync`.
  3. Run `echo 3 > /proc/sys/vm/drop_caches`.
  4. Start both containers. Wait for `pg_isready` and for Ollama's `/api/version`.
  5. Load the embedding model with one fixed input that is not in the query set. Its CPU is reported
     separately as **model load**. The ONNX session is created in a new harness process, and its
     CPU is reported the same way.
  6. Open a new database connection, so the call gets a new backend. Then measure the one call
     through each stage.

## The calibration cross-check

The calibration does not trust any one counter. Its reference is **machine idle time**, which the
kernel keeps by recording when each CPU enters and leaves idle (`/proc/stat`'s idle column, from the
`NO_HZ` idle accounting; the report records whether the kernel has it). That is a different mechanism from the cgroup's runtime sum, the
scheduler's per-task runtime and the thread clock, so it can catch an error in any of the three. It
also covers processes the harness does not run, which a `getrusage` in the harness cannot.

For each accounting path, before and after the run:

1. Measure the machine's busy rate with the services up and idle for 60 s: elapsed time × 2 cores,
   minus idle time.
2. Run a calibration block of that stage's own work: real embedding calls, real two-leg queries, or
   real rerank calls, back to back, for at least 30 s of CPU. Sum the path's per-call values.
3. Compute the reference as the machine's busy time during the block, minus the idle busy rate ×
   elapsed time, minus the harness process's own CPU (`CLOCK_PROCESS_CPUTIME_ID`). For the rerank
   path, the harness's CPU is the work itself, so it is not subtracted.
4. **The summed per-call values must be within ±5% of the reference.** If they are not, that path
   misses or double-counts CPU, and S2 is an **error**, not a result.

Over 30 s, a one-tick error in the idle accounting is under 0.1%, so the ±5% band measures the path
and not the reference.

## Acceptance rules

S2 is complete only if every rule holds on the A1.

| # | Rule | Complete when |
|---|---|---|
| S2-1 | **Every §10.3 row has a measured value or a named owner** | Query embedding, hybrid SQL and every rerank arm have a measured per-call p50 and p95 in core-ms. **API overhead and token relay belong to L1** (§16.4, gupta958, ruling 3). They stay marked *estimate* in §10.3 until L1 measures them, and no stand-in endpoint is built for S2 |
| S2-2 | **Every rerank arm** | Per-call CPU for all eight arms of ADR-0015's grid (N ∈ {8, 16, 32, 50}, L ∈ {128, 256}), on the reference reranker. The input passages are the two-leg query's top N for each dev query, truncated to L tokens. ADR-0015's consequences make this a precondition of its step 2 |
| S2-3 | **Query length** | The report gives the dev queries' token-length distribution under the embedder's tokenizer: p50, p95 and maximum. It gives embedding CPU per call at p50 and p95, and as a function of length. §10.3's "not a 20-token assumption" is checked here |
| S2-4 | **ACL selectivity** | The SQL stage runs with the `eligible_repo` predicate admitting 1%, 10% and 100% of repositories, the visibility levels E7 uses. It runs at both corpus sizes, and each combination is reported separately, never averaged |
| S2-5 | **Cache states** | Warm and cold as defined above, both reported. The budget uses warm |
| S2-6 | **Concurrent indexing** | Warm passes of query embedding, SQL and rerank are repeated while a full re-index of the corpus runs. The re-index uses the ingestion Ollama container at lower OS priority (§10.5), through `db/s6_identity.py`'s build path. The report gives the per-call CPU under indexing, and the indexing work's own CPU in core-seconds per second, from the ingestion container's cgroup, compared with the 25% reservation |
| S2-7 | **The totals are recomputed, not edited** | A committed script recomputes §10.3's required-cores table from the report, using warm numbers. It covers every row, at the throughput its own mix implies, with **no answer-cache hit credited** (§10.3 decision 3). The L1-owned rows enter as their §10.3 estimates, labelled as estimates. The script's output is committed with the report |
| S2-8 | **Provenance** | The report records `uname -a`, `lscpu`, the OCI shape, the kernel's `CONFIG_SCHED_INFO` and cgroup version, the image and model digests, the Ollama version, the reranker revision and hashes, the padding fraction and the commit. The results pull request commits the report unchanged, as #84 did for S6 |

## What is deliberately not a rule

- **Latency SLOs.** These are §10's and L1's. S2 records wall time but never judges it.
- **Throughput under load.** S2 measures per-call cost. Whether the system holds 30.5 req/s is L1,
  and S2-7's arithmetic is only the prediction L1 tests.
- **Rerank quality.** That is E3. S2 does not decide the arm; ADR-0015 does.
- **Memory.** §10.4 is checked under L3, not here.
- **The HNSW plan.** That is S3-6 (ORIENT item 9c). S2 times 9c's query, and does not check its plan.

## Order of work

1. This ADR, reviewed and merged.
2. **Item 9c's canonical two-leg query and its harness** (gupta958, ruling 5). It needs no A1.
3. The S2 harness. It is tested in CI on a small fixture, and S2-dev's numbers are marked as not
   evidence.
4. The A1 run, by Myan, once ORIENT item 9b provisions the A1. **Only this step is blocked on the
   A1.**
5. The results pull request. It commits the report and S2-7's output unchanged, fills in this
   Decision, and replaces the measured §10.3 rows in the same pull request (§16.8).

## Review rulings (gupta958, 2026-10-19)

Relayed by Myan on #85. All are applied above:

1. The reranker is `cross-encoder/ms-marco-MiniLM-L6-v2`, pinned by its ARM64 ONNX artifact,
   repository revision, SHA-256 and tokenizer revision. It is the S2 reference reranker. A different
   artifact chosen by E3 is measured again.
2. SQL runs at the real S1 size and at 60k. The 60k run may use deterministic stand-in padding, but
   it is scale evidence only, with its padding fraction reported.
3. API overhead and token relay are deferred to L1, which is named as their owner. No stand-in
   endpoint is built.
4. Warm measurements are used for the nominal budget, and cold is reported separately. No
   answer-cache hit is credited.
5. Item 9c's canonical two-leg query lands before the S2 harness.

Method corrections from the same review:
- Per-call values use high-resolution counters, not `/proc/<pid>/stat`. All Ollama threads are
  counted through the container's cgroup.
- Cold passes are separate, with an exact reset before each one.
- The calibration is established independently of the processes being measured.

## Decision

*Empty until S2 runs on the A1.* It will be completed with one of:

- **Measured:** every measured §10.3 row's p50 and p95, with the L1-owned rows named (S2-1); every
  rerank arm's CPU (S2-2); the recomputed totals table (S2-7); and A-4 marked **holds** or **does not
  hold** at the 70% bar, with no cache credit. If it does not hold, nothing is re-run with different
  choices. ADR-0015 step 5 and §10.3 decision 2 apply as written.
- **Error:** a counter check or the calibration cross-check failed, or a rule could not be
  completed. Name it. The method is fixed before the next run, and the run is repeated in full.
