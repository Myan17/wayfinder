---
module: schema
owner: joint
paths:
  - db/**
  - docs/context/modules/schema.md
interface_files:
  - db/views/eligible_repo.sql
  - db/views/retrieval_rows.sql
  - db/schema.sql
tables_owned:
  - "(the schema itself)"
depends_on: []
design_sections:
  - "DESIGN §9.2 (data model)"
  - "DESIGN §9.3.5–9.3.6 (activation, deletion closure)"
  - "DESIGN §18.3 (immutable migrations)"
verified_hashes:
  "db/views/eligible_repo.sql": "4c23a29fabcc67cc"
  "db/views/retrieval_rows.sql": "acf9bb56c489f0f7"
verified_on: 2026-09-22
---

# schema

> **Status (2026-09-22):** v1 is four migrations: `_index`, `_principals`, `_views`, `_deletion`. Tests
> run against the S3 ParadeDB digest with `WAYFINDER_TEST_DSN` set, and skip without it.

## Purpose

The shared contract every module depends on. It is joint because a unilateral change here breaks
someone silently: a column rename is a one-line diff and a day of somebody else's work.

## Public interface

Two views, which are what other modules are allowed to depend on:

```sql
-- db/views/eligible_repo.sql   — repository-side half of allowed() (authz owns the semantics)
-- db/views/retrieval_rows.sql  — the only row shape retrieval may query (indexing owns the semantics)
```

Plus `db/schema.sql`: a `pg_dump --schema-only` snapshot from the pinned image, so a reviewer reads
the result instead of replaying migrations. **It lands in its own pull request as soon as each
migration pull request merges** (a dump beside a migration exceeds AGENTS.md §2.2's limit). ORIENT.md
item 3's CI adds a drift check against a fresh dump.

## Invariants a caller may rely on

- **Migrations are immutable once merged.** Fixes are new migrations; CI rejects edits to files
  already on `main`.
- **Identity is three-part**: `content` (exact bytes), `representation`
  (`repo_id, spec_id, input_hash`), `occurrence` (location in a generation). Nothing collapses them.
- **Cross-repository bindings are unrepresentable**: composite keys `(id, repo_id)` on `generation`
  and `representation`, with `occurrence` referencing both.
- **One active generation per repository** (`one_active_per_repo`).
- **Delete modes are deliberate**: `occurrence` and `representation` references are `RESTRICT` so an
  out-of-order delete fails loudly; `base_generation_id` and `answer.cached_from` are
  `ON DELETE SET NULL` so GC and answer expiry are not blocked by their own descendants.
- **Tombstones are retained ≥ 90 days**, and `embedding_cache.data_class` is closed to
  `public`/`private`; both are `CHECK`s, not conventions.
- **Authorization facts carry leases** (`visibility_valid_until`, `user_access_state.valid_until`) and
  monotonic `authorization_revision` counters. A migration must not drop or default these away.
- Naming: `snake_case`, singular table names, `*_at` for timestamps, `*_id` for foreign keys.

## What this module will never do

- Never hold application logic in triggers or stored procedures — behaviour lives in code that tests
  can reach.
- Never store secrets in plaintext (`principal.token_ciphertext` is AES-256-GCM, key outside the DB).
- Never use `ON DELETE CASCADE` on anything reachable from an evidence manifest or an index
  generation; cascades hide deletion-order bugs that §9.3.6 exists to prevent. **Exception, from
  DESIGN §9.2:** `vector_d768` cascades from its `representation`. It is a 1:1 physical extension
  (pgvector needs a fixed dimension), §9.3.6's GC order has no vector step, and its composite key
  `(representation_id, repo_id, spec_id)` keeps it from binding to another repository's row or
  carrying another specification's label.
  `answer_trace` and `feedback` cascade from `answer`, as §9.2 wrote them: they are the answer's own
  derivatives, and §9.3.6 step 7 redacts or deletes all three together.

## Change protocol

1. BCR first if the change moves a view or a column another module reads.
2. One migration per change, timestamp-prefixed (`dbmate`), additive where possible.
3. Update every affected card in the same pull request; `db/schema.sql` follows in its own (above).
4. State in the work record: what breaks, what order things must ship in, and the rollback.
5. Reviewer reads the design argument, not just the DDL, and applies the schema section of
   `docs/team/REVIEW-CHECKLIST-SECURITY.md`.

## Failure modes the caller must handle

| Condition | Symptom | Response |
|---|---|---|
| Migration applied but code not deployed | New column unused; old code still correct | Migrations must be backward compatible with the previous release |
| Rollback after a destructive migration | Data written under the new shape is not recoverable | Destructive steps are separate migrations, shipped a release later |
| Dimension change in an embedding specification | New per-dimension vector table required | Additive: new table plus a new specification row; no in-place alteration |

## Tests that pin this contract

| Test | Pins |
|---|---|
| `db/tests/test_migrations.py::test_up_from_empty_and_from_previous_release` | Forward compatibility |
| `db/tests/test_constraints.py::test_cross_repo_occurrence_rejected` | Composite keys |
| `db/tests/test_constraints.py::test_cross_repo_vector_rejected` | Composite key on the vector table |
| `db/tests/test_constraints.py::test_vector_spec_must_match_representation` | Vector `spec_id` equals its representation's |
| `db/tests/test_deletion.py::test_tombstone_retained_at_least_90_days` | Tombstone retention |
| `db/tests/test_deletion.py::test_embedding_cache_data_class_is_closed` | GC step 6 cannot miss an entry |
| `db/tests/test_constraints.py::test_one_active_generation` | Partial unique index |
| `db/tests/test_delete_modes.py::test_gc_order_and_set_null` | Delete-mode assumptions in §9.3.6 |
| `db/tests/test_serving.py::test_cached_from_set_null` | `answer.cached_from` is `SET NULL` |
| `db/tests/test_views.py::test_eligible_repo_expiry` | Lease semantics in the view |
| `db/tests/test_views.py::test_retrieval_rows_active_generation_only_and_predicate_applies` | Only live rows of the active generation; authz's row predicate applies to the view unchanged |
| `db/tests/test_views.py::test_view_files_match_migration` | `db/views/*.sql` match what the migration creates |

## Fake

Schema has no fake; it has **fixtures**: `db/fixtures/minimal.sql` (one connection, two repositories,
one generation) and `db/fixtures/permission.sql` (the 12-repository authorization fixture).

## Open questions

- Whether per-dimension vector tables should be partitioned by repository once the corpus grows.

## Change log

| Date | Change | BCR |
|---|---|---|
| 2026-09-18 | Card created from DESIGN v0.3 before implementation | — |
| 2026-09-22 | v1 part 1; vector cascade exception; three-column vector key | — |
| 2026-09-22 | v1 part 2: principals and serving tables; answer cascades named | — |
| 2026-09-22 | v1 part 3: `eligible_repo` and `retrieval_rows` created | — |
| 2026-09-22 | v1 part 4: `embedding_cache`, `tombstone` | — |
