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
| S3-6 | The planner uses the index, and we can see that it does | `EXPLAIN (ANALYZE, BUFFERS)` on the two-leg hybrid query of §9.5 (pinned by Amendment 1) shows the BM25 scan in use rather than a sequential scan with a filter, and the plan is capturable as text for the release manifest | **Not** an automatic fallback. Record the plan and raise it at G0 — a planner problem is tunable, an MVCC problem is not |

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

### Amendment 1 — S3-6's query and plan checks, pinned before the harness (2026-10-19)

S3-6 names "the two-leg hybrid query of §9.5", but that query did not exist as text. If it were
written while looking at plans, it could be shaped until the plan passed. This is the goalpost
problem this ADR exists to prevent, so the query and the checks are fixed here first. S3-6's
consequence is unchanged: a failing plan is recorded and raised, and is **not** an automatic
fallback. ADR-0019 adds one use: S2 times this exact query (gupta958's ruling 5 on #85). S2 must
therefore time the production query, not a simplified probe, so the query below meets every
lexical requirement of §9.5, and the schema change it needs lands first.

#### The prerequisite schema change

§9.5 step 2 requires three things of the lexical leg:
- a code-aware tokenizer that splits identifiers on camelCase, snake_case and dots;
- the original token, indexed as well;
- paths indexed as a separate field.

The v1 BM25 index, `rep_bm25 (id, header, body_text, repo_id, live)`, uses the default tokenizer and
has no path field. The path exists only inside `header` (§9.4.2) and in `occurrence`. That is a
contradiction between §9.5 and §9.2. It is resolved in favour of §9.5, by one schema migration
that lands, in its own pull request, **before** the query and the S3-6 harness:

- **`representation.path`** (text, not null). A representation's path is fixed by its embedded
  input: the header carries the path, so two paths always make two representations (INDEX-02). The
  migration adds `UNIQUE (id, repo_id, path)` to `representation`, and a foreign key from
  `occurrence (representation_id, repo_id, path)` to it, so an occurrence's path cannot differ from
  its representation's. The migration refuses to run if `representation` has rows, because no
  environment has ingested anything yet and a backfill from `header` would be a guess.
- **`rep_bm25` rebuilt** with the fields below. The tokenizers were checked on the pinned image
  (pg_search 0.25.9) before this was written:

  | Field | Column | Tokenizer | What it matches |
  |---|---|---|---|
  | `header` | `header` | `pdb.source_code` | identifier parts: `parseWidget_value` gives `parse`, `widget`, `value` |
  | `header_ident` | `header` | `pdb.regex_pattern` for dotted identifiers | the original token, lowercased: `parsewidget_value`, `foo.bar_baz` |
  | `body_text` | `body_text` | `pdb.source_code` | as `header` |
  | `body_ident` | `body_text` | as `header_ident` | as `header_ident` |
  | `path` | `path` | `pdb.regex_pattern('[^/]+')` | path segments: `src`, `app`, `widget_parser.py` |
  | `path_code` | `path` | `pdb.source_code` | parts of path segments: `widget`, `parser`, `py` |

  `repo_id` and `live` stay in the index, as in v1. The migration's tests show each row's example
  matching. §9.2's DDL is edited in the same pull request.

#### Where the query lives, and what it may read

The query goes in `apps/api/wayfinder/retrieval/hybrid_sql.py`, in the retrieval module, which owns
the hybrid query (retrieval card). It is a function that returns SQL and parameters. The S3-6
harness and S2 both import it, and neither copies it.

`retrieval_rows` does not expose embeddings or the BM25 index, so the indexing card's contract
(`retrieval_rows` is "the ONLY shape `retrieval` may query") cannot be met by a two-leg query. The
contract changes, in the indexing, retrieval and schema cards, to this documented shape:
- **two authorized base-table scans:** `representation` through `rep_bm25`, and `vector_d768`
  through `vec768_hnsw`. Each scan joins `eligible_repo` and applies `authz`'s `sql_predicate` to
  its own scanned alias, the one helper §9.1.5 requires;
- **then `retrieval_rows`,** for the location in the active generation.

`retrieval` reads no other column of those tables, and writes none.

#### The query (§9.5 steps 2, 3, 5 and 6, in one statement)

| Part | Pinned |
|---|---|
| Lexical leg | `representation`, matched with `paradedb.match` on each of the six fields above, combined with `paradedb.boolean(should => …)`. `match` tokenizes the input with the field's own tokenizer and has no query grammar, so user text cannot inject query syntax (WF-25). The top 100, cut and ranked by the lexical key below |
| Dense leg | One subquery per specification in scope, over `vector_d768` with `spec_id` bound as a parameter, ordered by `embedding <=> $query`. Top 100, with `hnsw.iterative_scan = relaxed_order` set by `SET LOCAL` in the query's transaction. The candidates are then ranked by the dense key below, using exact distance. S3-6 and S2 run it with one specification |
| Filter | As above: on each scanned relation, through `sql_predicate` |
| Fusion | RRF with `k = 60` across the legs, over each leg's ranks. The result is joined to `retrieval_rows` for the location |
| Per-file cap | At most 3 passages per `(repo_id, path)`, chosen by the final key |

**Deterministic ordering inside each leg, before RRF ranks are assigned.** §9.5 step 3's tie key,
`(score desc, repo_id, path, start_line)`, cannot be applied inside a leg: `start_line` belongs to an
occurrence, and a leg ranks representations. RRF ranks have to be fixed per leg, because a final
sort cannot repair two different ranks. This amendment therefore amends step 3, and §9.5 is edited
to match in the same pull request:

| Where | Key |
|---|---|
| Lexical leg (cut and rank) | `paradedb.score` desc, `repo_id`, `path`, `representation.id` |
| Dense leg (rank, after the index cut) | exact `embedding <=> $query` asc, `repo_id`, `path`, `representation.id` |
| Final order and per-file cap | fused score desc, `repo_id`, `path`, `start_line`, `representation_id` |

Each key ends in a unique column, so every order is total. The dense leg's cut is the HNSW index's
own order, which is deterministic for a fixed index state, and only its ranks use the key.

#### Fixture

The data is synthetic and deterministic, because S1's real chunks need the chunker (P1). There are
100 private repositories, so `verified_public` is false and only the granted array admits rows. The
fixture is built at the two sizes ADR-0019 uses: **7,175** and **60,000** live representations,
spread evenly across repositories. Vectors use ADR-0005's stand-in, seeded by row number.

- **The query text** matches exactly **5 representations in every repository**, through at least
  one field each, so every granted set has lexical candidates. That makes 500 matches at either size.
- **The query vector** is the stand-in vector of a fixed row.
- `ANALYZE` runs before any plan is captured.

#### Session settings

`max_parallel_workers_per_gather = 0`, as ADR-0019 requires for S2, so the captured plan is the plan
S2 times. Everything else uses the pinned image's defaults.

#### Cases

There are two sizes, and three selectivities in which the granted array admits 1, 10 or 100 of the
100 repositories. Each combination runs **the same prepared, parameterized statement** twice:

- under `SET plan_cache_mode = force_custom_plan`;
- under `SET plan_cache_mode = force_generic_plan`.

Each is captured with `EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) EXECUTE`. No case uses literal SQL. The
generic plan is the one §9.2 asks for: it shows the partial indexes are chosen with a parameterized
`spec_id` and granted array. That makes 12 plans.

#### The checks

Each plan is read as a tree. S3-6 passes only if all five checks hold on all 12 cases:

| # | Check |
|---|---|
| S3-6a | The lexical leg is served by `pg_search`: a `Custom Scan` node whose provider is ParadeDB, on `representation`. No node is a `Seq Scan` on `representation`. **Scoped to the lexical leg's subtree by Amendment 2** |
| S3-6b | The dense leg is served by the HNSW index: an `Index Scan` using `vec768_hnsw` on `vector_d768`. No node is a `Seq Scan` on `vector_d768` |
| S3-6c | S3-6a and S3-6b hold on the generic plans as well as the custom ones |
| S3-6d | **The case is not vacuous.** The executed statement returns at least one candidate from the lexical leg and at least one from the dense leg. Every candidate of either leg, and every returned row, belongs to a granted repository. The harness checks each row against the granted array, separately from the SQL |
| S3-6e | Every plan is also captured with `FORMAT TEXT`, and the text is written to the evidence report with the image digest and the commit, for the release manifest |

**Mutation checks.** These show the checks can fail, and run as tests:
- dropping `rep_bm25` must fail S3-6a;
- dropping `vec768_hnsw` must fail S3-6b;
- a query text that matches nothing must fail S3-6d;
- granting a repository the harness does not count as granted must fail S3-6d.

**What S3-6 does not judge.** It does not judge the plan's other joins, such as how
`retrieval_rows` reaches `occurrence`, or its timing. Those plans are captured in S3-6e, and S2
times the whole statement. A slow join is S2's finding, not an S3-6 failure.

**Where it runs.** The evidence run is local, on the pinned image, at both sizes, and its report is
committed unchanged. CI's pinned job runs the 7,175 cases on every pull request, so a change that
breaks the plan fails before it merges. The 60,000 cases join CI too if they fit the job's time;
otherwise they stay local.

#### Order of work

The query is fixed before anyone sees its plans, so it and the plan harness land in separate pull
requests (gupta958, review of #86):

1. This amendment, with the card contract change and §9.5 step 3's tie keys.
2. The schema migration above, with §9.2's DDL.
3. **The query alone:** `hybrid_sql.py`, with tests of its results, its authorization and its
   determinism. This pull request contains no plan harness, no `EXPLAIN` capture and no plan
   evidence.
4. **The plan harness, after step 3 has merged:** the S3-6 cases, checks S3-6a–e and the mutation
   checks. From step 3's merge on, the query is frozen for S3-6. This pull request may not change
   `hybrid_sql.py`. A change to the query after its plans have been seen is a new amendment to this
   ADR, and the plans are captured again.
5. The evidence run, with its report committed unchanged, and the results pull request, which
   completes ORIENT item 9c.

#### Review rulings (gupta958, 2026-10-19)

Relayed by Myan on #86. All are applied above:
- `hybrid_sql.py` belongs in the retrieval module.
- The deterministic synthetic fixture is acceptable.
- The plan's sequential scan of `occurrence` in the `retrieval_rows` join is captured, but it is not
  an S3-6 failure. S2 measures its cost.
- The query and the plan harness land in separate pull requests, in the order above.

### Amendment 2 — S3-6a judges the lexical leg only (2026-10-22)

**Written after the first plans were seen**, on gupta958's ruling in the review of #90. It is
recorded as such, because ADR-0007 exists to stop rules from moving after a measurement.

**What the plans showed.** Amendment 1's S3-6a says "no node is a `Seq Scan` on `representation`",
anywhere in the plan. At 7,175 representations, every case served the lexical leg with a ParadeDB
Base Scan. Every case also seq-scanned `representation` in a different place: the dense leg's rank
step, which joins `representation` to read `path` for the dense tie key. At 60,000 that join used
`representation_pkey`. Read literally, S3-6a failed all 6 cases at 7,175 on a join that it was not
written to judge.

**Why this is a scope correction, not a moved threshold.** S3-6 asks whether the BM25 index serves
the lexical leg (the S3-6 row: "the BM25 scan in use rather than a sequential scan with a filter").
Amendment 1 also says S3-6 "does not judge the plan's other joins … A slow join is S2's finding, not
an S3-6 failure." The two sentences conflict for the dense leg's join to `representation`. This
amendment resolves the conflict in favour of the second sentence. It changes no number, and it
does not touch S3-6b.

**The rule.** S3-6a is evaluated on the **lexical leg's subtree**: the plan node that scans the
`lexical` CTE (a `Subquery Scan` with alias `lexical` when the planner inlines it, or the
`CTE lexical` subplan when it materializes it), and every node beneath it. Within that subtree there
must be a ParadeDB `Custom Scan` on `representation`, and no `Seq Scan` on `representation`. If the
plan has no such subtree, S3-6a fails. Nodes outside the subtree are not judged by S3-6a, including
the dense leg's join to `representation` and `retrieval_rows`' join. They stay in the captured
plans (S3-6e), and S2 times them.

**What does not change.**
- **S3-6b stays exactly as written** (gupta958): any `Seq Scan` on `vector_d768` fails it, and there
  is no minimum candidate count. Its small-scan failures are recorded and raised at G0. At 7,175 the
  planner seq-scans `vector_d768` and sorts exactly in 5 of 6 cases. At 60,000 it does so in 1 of 6
  (1 granted repository, custom plan).
- S3-6c, S3-6d, S3-6e and the four mutation checks.
- The query. `hybrid_sql.py` is not changed.

**CI.** The pinned job pins the complete observed outcome of all six 7,175 cases: S3-6a, S3-6b
and the Seq Scan aliases of each, for each selectivity and plan mode. A plan change in either
direction then fails CI and is seen, instead of staying green because the overall verdict was
already a failure. The 60,000 cases stay local: their fixture takes about 389 s to build (gupta958).

### What is deliberately not a rule here

- **No latency threshold.** `DESIGN` sets no per-engine latency budget for the lexical leg alone;
  §10.3's numbers are whole-system planning estimates that S2 replaces outright. A threshold invented
  today would read as evidence in three weeks.
- **No ranking-quality comparison.** R-06 places the fallback's measurement in E1 (§15.4), whose
  stated question is whether lexical and dense complement each other, scored on Recall@10. S3 asks
  only whether the engine is *safe to build on*, which is a different question and answerable now.
- **No opinion on AGPL-3.0.** Settled in ADR-0002 and open question Q-3 (§7.3).

## Decision

**Still Proposed. Measured locally on 2026-09-22; S3-1b and S3-6 outstanding, so this is not an
acceptance.**

Image `paradedb/paradedb@sha256:c17153b8…64f4` (0.25.9, `linux/arm64`), PostgreSQL 18.6,
`pg_search` 0.25.9. Reproduce with `infra/spikes/s3/`.

| Rule | Result | Observed |
|---|---|---|
| S3-1a | PASS | All four points: `host=arm64 daemon=arm64 image=arm64 variant=(absent) connection=accepted` |
| **S3-1b** | **OUTSTANDING** | Requires the provisioned Oracle A1. Cannot be measured from a development machine, and is not being approximated by one |
| S3-2 | PASS | `pg_search 0.25.9`, `is_superuser=on`, §9.2's BM25 DDL accepted verbatim |
| S3-3 | PASS | 5 rows, then 5 rows, in one `REPEATABLE READ` snapshot across a concurrent commit |
| S3-4 | PASS | Reader saw gen `[1]`; writer activated gen 2 and retired gen 1; **same transaction still saw `[1]`**; a new transaction saw `[2]` |
| S3-5 | PASS | Snapshot predating the delete kept 4 rows; a new transaction saw 0 |
| **S3-6** | **OUTSTANDING** | The rule names §9.5's **two-leg** query. This harness has no dense leg — no vector column, no pgvector index, no embeddings — so nothing was measured. The two-leg harness and its plan capture are their own pull request |

**Three results were mutation-checked**, because a rule that passes first time and cannot fail is
worth nothing:

- **S3-4**, the load-bearing one. Weakening the reader to `READ COMMITTED` makes step 4 return gen
  `[2]` and the rule fail. The PASS reflects `pg_search` honouring the caller's snapshot.
- **S3-2**. Connecting as a `NOSUPERUSER` role records `S3-2 FAIL is_superuser=off`, and the §9.2
  DDL is not attempted — a success under some other privilege set would be evidence for a rule
  nobody wrote.
- **S3-1a point 4**. With the container stopped, S3-1a records `FAIL … failed: ['postgres accepts a
  connection']`. An earlier harness recorded PASS on points 1–3 and opened the connection
  afterwards, so S3-1a could read PASS in a run where Postgres never answered.

**What this does not establish.** Everything above ran on an Apple M2 Pro, not on an Oracle A1. The
architecture is the same and the image digest is the same, but A-5 is a claim about the deployment
target and §19.2 puts A1 provisioning inside S3. Nothing here should be cited as A-5 being settled.

When S3-1b and S3-6 run, this section is completed with one of:

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
reason. A partial result is recorded as *"S3-1a and S3-2..S3-5 measured locally; S3-1b and S3-6
outstanding"* — never as an acceptance.

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
