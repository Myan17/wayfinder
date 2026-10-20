---
module: indexing
owner: myan
paths:
  - apps/ingestd/internal/embed/**
  - apps/ingestd/internal/generation/**
  - apps/ingestd/internal/gc/**
  - docs/context/modules/indexing.md
interface_files:
  - apps/ingestd/internal/generation/api.go
  - db/views/retrieval_rows.sql
tables_owned:
  - generation
  - representation
  - vector_d768
  - occurrence
  - embedding_cache
  - tombstone
depends_on:
  - chunking
  - sources
design_sections:
  - "DESIGN §9.2 (data model)"
  - "DESIGN §9.3.3–9.3.6 (generations, activation, deletion closure)"
verified_hashes:
  "db/views/retrieval_rows.sql": "acf9bb56c489f0f7"
verified_on: 2026-09-22
---

# indexing

## Purpose

Turns chunks into searchable rows and decides which rows are live. Owns index generations, their
atomic activation, and the ordered deletion that follows retirement. It never answers a query and
never decides who may see a row.

## Public interface

```go
// apps/ingestd/internal/generation/api.go
type Claim struct { RepoID int64; Desired int64; Token uuid.UUID; ExpiresAt time.Time }

func ClaimRepo(ctx context.Context, db DB, repoID int64) (Claim, bool, error)
func Build(ctx context.Context, db DB, c Claim, changes chunk.ChangeSet) (GenerationID, error)
func Activate(ctx context.Context, db DB, c Claim, g GenerationID, base GenerationID) error
func CollectGarbage(ctx context.Context, db DB, repoID int64, grace time.Duration) (Stats, error)
```

```sql
-- db/views/retrieval_rows.sql — the shape `retrieval` uses for locations (see the query shape below).
-- Columns: representation_id, repo_id, spec_id, header, body_text, path, blob_sha,
--          start_line, end_line, symbol, content_hash, live
-- `live` is always true here. It is exposed so authz's row predicate (row.live AND ...) applies
-- to the view unchanged.
-- Guarantees: every row is live and belongs to its repository's active generation.
```

### The documented query shape (ADR-0007 Amendment 1)

`retrieval_rows` exposes neither embeddings nor the BM25 index, so `retrieval`'s two-leg query may
read exactly this, and nothing else of `indexing`'s tables:

- **`representation` through `rep_bm25`** (the lexical leg): the indexed fields `header`,
  `header_ident`, `body_text`, `body_ident`, `path` and `path_code`, and the columns `id`,
  `repo_id`, `path` and `live`;
- **`vector_d768` through `vec768_hnsw`** (the dense leg): `representation_id`, `repo_id`,
  `spec_id`, `live` and `embedding`, with `spec_id` as a parameter;
- **then `retrieval_rows`**, joined on `representation_id`, for the location in the active
  generation.

Each base-table scan joins `eligible_repo` and applies `authz`'s `sql_predicate` to its own scanned
alias. `retrieval` never writes these tables. A change to the indexes, their fields or these
columns is a contract change to this card.

## Invariants a caller may rely on

- Exactly one generation per repository is `active` (`one_active_per_repo`), and activation is a
  single transaction — a reader sees the old generation or the new one, never a mix.
- Activation requires a valid claim, the current `desired_generation`, and an unchanged base pointer.
  A slow worker cannot move a repository backwards.
- `representation` rows are keyed by `(repo_id, spec_id, input_hash)`. A different embedding
  specification produces different rows; an existing vector is never overwritten in place.
- `live` is true only for rows in the active generation, and it is maintained on both the
  representation row and its vector row inside the activation transaction.
- Two embedding specifications may be live across different repositories at the same time; the view
  exposes `spec_id` so `retrieval` can group by it.
- Deleted content stops being returned at activation and is physically removed within 24 h, with a
  tombstone retained ≥ 90 days.

## What this module will never do

- Never evaluate user authorization or filter by principal — that is `authz`, applied on top of the
  view.
- Never write to `repository` or `connection` other than the claim, generation pointer and
  desired-generation fields.
- Never block a reader: builds happen beside the active generation.
- Never call an LLM provider; embeddings come from the local Ollama instance for ingestion.

## Failure modes the caller must handle

| Condition | Caller sees | Do this |
|---|---|---|
| Build in progress | The old generation, unchanged | Nothing; the view only exposes live rows |
| Claim lost or expired mid-build | Activation refused; generation marked `failed` | Nothing; the reconciler re-claims |
| Repository has no active generation (first index, or restore) | Zero rows for that repository | Report freshness, not an error |
| GC running | Rows disappearing between two queries | Re-authorize and re-resolve by content hash, never by row id held across requests |

## Data owned

`generation` (one active per repo, lease and status), `representation` (identity + lexical fields),
`vector_d768` and future per-dimension tables (embeddings, with denormalized filter columns),
`occurrence` (paths and line ranges per generation), `embedding_cache` (compute reuse only, never a
serving path), `tombstone` (survives restore).

## Tests that pin this contract

| Test | Pins |
|---|---|
| `apps/ingestd/internal/generation/activate_test.go::TestReverseOrderActivation` | An older build cannot activate after a newer one |
| `…::TestClaimExpiryBlocksActivation` | Fencing |
| `…::TestSnapshotDuringSwitch` | A reader sees one generation, never a mix |
| `apps/ingestd/internal/gc/order_test.go::TestRetiredRefsThenRepresentations` | GC ordering against RESTRICT foreign keys |
| `…::TestReusedChunkSurvivesGC` | Revert case: a rebuilding generation's rows are not collected |
| `apps/ingestd/internal/embed/spec_test.go::TestSecondSpecCreatesNewRows` | Specification identity |

## Fake

`apps/ingestd/internal/generation/fake` — an in-memory generation store plus a seeded
`retrieval_rows` fixture, so `retrieval` and the evaluation harness can run without ingestion.

## Open questions

- Whether GC grace should be configurable per connection (currently 10 minutes everywhere).
- Whether a second live specification should be allowed *within* one repository during a migration
  (today: no — a repository has one specification per generation).

## Change log

| Date | Change | BCR |
|---|---|---|
| 2026-09-18 | Card created from DESIGN v0.3 before implementation | — |
| 2026-09-22 | `retrieval_rows` created (schema v1 part 3), with `live` for the authz predicate | — |
| 2026-10-19 | `representation.path` added, equal to every occurrence's path by a foreign key; `rep_bm25` now indexes `header`, `header_ident`, `body_text`, `body_ident`, `path` and `path_code` (schema migration `_representation_path_bm25`) | — |
| 2026-10-19 | Contract: `retrieval` may also scan `representation` (via `rep_bm25`) and `vector_d768` (via `vec768_hnsw`), authorized, before `retrieval_rows`; `retrieval_rows` is no longer the only shape (ADR-0007 Amendment 1) | — |
