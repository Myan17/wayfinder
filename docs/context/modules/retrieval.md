---
module: retrieval
owner: myan
paths:
  - apps/api/wayfinder/retrieval/**
  - docs/context/modules/retrieval.md
interface_files:
  - apps/api/wayfinder/retrieval/interface.py
tables_owned: []
depends_on:
  - authz
  - indexing
design_sections:
  - "DESIGN §9.5 (retrieval pipeline)"
  - "DESIGN §10.3 (rerank CPU budget)"
  - "DESIGN §15.4 E1–E7"
verified_at: 0000000
verified_on: 2026-09-18
---

# retrieval

## Purpose

Turns a question plus an authorized scope into a ranked, deterministic list of passages. Owns the
hybrid query, fusion, optional reranking and the shed policy. It owns no tables: it reads `indexing`'s
tables only in the query shape the indexing card documents (two authorized base-table scans,
then `retrieval_rows`), under `authz`'s predicate.

## Public interface

```python
# apps/api/wayfinder/retrieval/interface.py
@dataclass(frozen=True)
class Passage:
    representation_id: int; repo_id: int; path: str; blob_sha: str
    start_line: int; end_line: int; symbol: str | None
    header: str; body: str
    lexical_rank: int | None; dense_rank: int | None
    fused_score: float; rerank_score: float | None

@dataclass(frozen=True)
class RetrievalResult:
    passages: list[Passage]
    degraded: list[str]          # "rerank_shed" | "dense_unavailable" | "ann_underfill"
    trace: RetrievalTrace        # per-stage candidates, scores, filtered counts (counts only)

async def search(query: str, scope: AuthorizedScope, k: int, *, rerank: bool) -> RetrievalResult: ...
async def passages_for_answer(query: str, scope: AuthorizedScope) -> RetrievalResult: ...   # top 8
```

## Invariants a caller may rely on

- Every returned passage is inside `scope`; the predicate is applied in SQL and asserted again after
  retrieval.
- Ordering is deterministic for a fixed index state: relaxed HNSW results are re-sorted by exact
  distance before ranks are assigned. Each leg breaks ties before RRF ranks are assigned, the lexical
  leg on `(score desc, repo_id, path, representation_id)` and the dense leg on `(exact distance asc,
  repo_id, path, representation_id)`. The final order breaks ties on `(fused score desc, repo_id,
  path, start_line, representation_id)` (ADR-0007 Amendment 1).
- At most `per_file_cap` (default 3) passages come from one file, so a single large file cannot
  crowd out the candidate pool.
- Results span embedding specifications safely: one dense subquery per specification, fused by rank,
  never by raw distance.
- `degraded` is complete: if reranking was shed or dense retrieval was unavailable, it says so, and
  the caller must not treat the result as the quality-configuration result.
- `rerank_score` is `None` exactly when reranking did not run — which is the signal `answer` uses to
  refuse generation (`DESIGN` §9.6.1).

## What this module will never do

- Never widen a scope, cache across principals, or infer authorization.
- Never generate text or call an LLM provider.
- Never return a passage without its source location; a passage that cannot be cited is a bug.

## Failure modes the caller must handle

| Condition | Caller sees | Do this |
|---|---|---|
| Reranker queue wait > 150 ms | `degraded=["rerank_shed"]`, `rerank_score=None` | Locate: serve fused order. Explain: refuse or go extractive |
| Embedding instance down | `degraded=["dense_unavailable"]` | Lexical-only results; no generated answer |
| Iterative scan exhausted | `degraded=["ann_underfill"]` | Serve, and surface the flag in the trace |
| Empty authorized scope | Zero passages, no error | Render "nothing you can see matches", not "no results exist" |

## Tests that pin this contract

| Test | Pins |
|---|---|
| `apps/api/tests/retrieval/test_hybrid_sql.py` (all; pinned database, run by `make db-test`) | `hybrid_sql.py`, the canonical two-leg statement (ADR-0007 Amendment 1): only granted or verified-public repositories; an expired lease returns nothing, whether it expired before building, before the statement runs or during it; not-live and retired-generation rows excluded; a bypassed SQL filter is caught by `execute`'s assertion; RRF over both legs; a path alone matches; query-grammar characters are plain text; one dense leg per specification; no caller value in the SQL text; the relaxed scan set inside the query's transaction. No plan is inspected (Amendment 1 step 4) |
| `apps/api/tests/retrieval/test_hybrid_sql_order.py` (all; pinned database) | Every component of every pinned key: each leg's ranks (score or distance, repo_id, path, id), the lexical top-100 cut, equal fused scores decided in turn by repo_id, path, start_line and representation_id, and the per-file cap's (fused, start_line, representation_id) within each (repo_id, path); plus each `ORDER BY` key list on the statement itself, since three trailing-id drops are masked by an earlier sort over the same id |
| `apps/api/tests/retrieval/test_s3_6_plans.py` (all; the database cases run in `make db-test`) | `s3_6.py`, the S3-6 plan harness (ADR-0007 Amendments 1 and 2), which imports `hybrid_sql.build` unchanged: S3-6a reads only the lexical leg's subtree and fails without one; S3-6b reads the whole tree; S3-6d reads the rows against the harness's own count of granted repositories; each of the four mutation checks fails its rule; the observed S3-6a and S3-6b outcome of all six 7,175 cases is pinned, so a plan change either way fails |
| `apps/api/tests/retrieval/test_scope.py::test_no_row_outside_scope` | Authorization filter, including under underfill |
| `…/test_determinism.py::test_relaxed_order_resorted` | Stable ranking |
| `…/test_determinism.py::test_tie_break_stable_across_runs` | Tie-break |
| `…/test_fusion.py::test_rrf_properties` | Fusion invariants (property-based) |
| `…/test_shed.py::test_rerank_shed_sets_flag_and_null_score` | The signal `answer` depends on |
| `eval/harness/test_oracle.py::test_filtered_matches_exact_over_authorized` | Experiment E7's oracle |

## Fake

`apps/api/wayfinder/retrieval/fakes.py` — `FixtureRetrieval` over a small seeded corpus with
deterministic scores, so `answer`, `http` and `web` can be built and tested without a database.

## Open questions

- Per-file cap default (3) is a guess until E3/E8; it changes candidate diversity.
- Whether `passages_for_answer` should return more than 8 when passages are short.

## Change log

| Date | Change | BCR |
|---|---|---|
| 2026-09-18 | Card created from DESIGN v0.3 before implementation | — |
| 2026-10-19 | `hybrid_sql.py`'s ordering tests (step 3b) | — |
| 2026-10-19 | `hybrid_sql.py`: `build` and `execute` for the canonical two-leg statement, used by S3-6 and S2; internal, not yet behind `interface.py`'s `search` | — |
| 2026-10-19 | Reads the indexing card's documented query shape, not `retrieval_rows` alone; per-leg tie keys before RRF (ADR-0007 Amendment 1) | — |
| 2026-10-22 | `s3_6.py`: the S3-6 plan harness (cases, checks, fixture); `hybrid_sql.py` unchanged | — |
