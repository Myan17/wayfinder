# Context index — read this before touching anything you do not own

Each row is a module. The **card** is what a caller reads; the **interface files** are what a caller may
read in code. Implementation outside your own modules is off-limits by rule (`AGENTS.md` §3.2) — not
because it is secret, but because reading it creates coupling that nobody reviewed and that no test
protects.

`scripts/check_context_freshness.py` hashes each interface file; a pull request that changes one
without updating the card's `Verified-at` fails CI.

**Card status:** ✅ written — a real contract you may build against. 🟡 placeholder — the module is
unspecified; do not build against it, open a BCR so the card gets written first (`AGENTS.md` §3.2).
The six drafted first are the ones on a boundary, where a thin card costs the reviewer or a parallel
session a day. The rest are filled in by whoever implements that module, in the pull request that
lands its first interface file — CI enforces this.

| Module | Owner | Card | Interface files (readable by anyone) | Fake for consumers |
|---|---|---|---|---|
| `authz` | myan | ✅ [modules/authz.md](modules/authz.md) | `apps/api/wayfinder/authz/interface.py`, `db/views/eligible_repo.sql` | `authz/fakes.py` |
| `retrieval` | myan | ✅ [modules/retrieval.md](modules/retrieval.md) | `apps/api/wayfinder/retrieval/interface.py` | `retrieval/fakes.py` |
| `answer` | myan | ✅ [modules/answer.md](modules/answer.md) | `apps/api/wayfinder/answer/interface.py`, `docs/api/sse.md` | `answer/fakes.py` |
| `egress` | myan | ✅ [modules/egress.md](modules/egress.md) | `apps/api/wayfinder/egress/interface.py`, `docs/api/egress-policy.md` | `egress/fakes.py` |
| `cache` | myan | 🟡 [modules/cache.md](modules/cache.md) | `apps/api/wayfinder/cache/interface.py` | `cache/fakes.py` |
| `http` | myan | 🟡 [modules/http.md](modules/http.md) | `openapi.json` (generated), `docs/api/errors.md` | generated client |
| `web` | myan | 🟡 [modules/web.md](modules/web.md) | `apps/web/src/api/client.ts` (generated) | — |
| `eval-harness` | myan | 🟡 [modules/eval-harness.md](modules/eval-harness.md) | `eval/harness/interface.py`, `eval/experiments/schema.json` | — |
| `sources` | myan | 🟡 [modules/sources.md](modules/sources.md) | `apps/ingestd/internal/source/source.go` | `source/fake` |
| `chunking` | myan | 🟡 [modules/chunking.md](modules/chunking.md) | `apps/ingestd/internal/chunk/chunk.go` | `chunk/fake` |
| `indexing` | myan | ✅ [modules/indexing.md](modules/indexing.md) | `apps/ingestd/internal/generation/api.go`, `db/views/retrieval_rows.sql` | `generation/fake` |
| `webhooks` | myan | ✅ [modules/webhooks.md](modules/webhooks.md) | `apps/ingestd/internal/webhook/events.go` | `webhook/fake` |
| `eval-data` | myan | 🟡 [modules/eval-data.md](modules/eval-data.md) | `eval/datasets/manifest.schema.json` | sample dataset |
| `platform` | myan | 🟡 [modules/platform.md](modules/platform.md) | `infra/compose/compose.yaml`, `Makefile` | — |
| `observability` | myan | 🟡 [modules/observability.md](modules/observability.md) | `apps/*/telemetry/interface.*`, `infra/compose/otel/policy.yaml` | in-memory exporter |
| `schema` | joint | ✅ [modules/schema.md](modules/schema.md) | `db/migrations/**` (read to write one), `db/views/**` | test fixtures |

Owner column is the **implementation** owner (today `myan` for everything). The required reviewer for
every path is `gupta958`, set in `.github/CODEOWNERS`.

## How to use this in an agent session

1. `scripts/new-task.sh` prints the cards for your module and its declared dependencies. Read those.
2. Need behaviour a card does not describe? Log `BLOCKED`, open a BCR (`boundary/TEMPLATE-BCR.md`).
   Do not read the implementation to find the answer.
3. Changing an interface you own? Update the card and the fake in the same pull request, and say so in
   the work record so the other engineer knows their consumers may need to move.

## Cross-module contracts that are easy to get wrong

| Contract | Between | Where it is written |
|---|---|---|
| Authorized-row predicate (`eligible_repo` + granted array) | `authz` → `retrieval`, `answer`, `cache` | `modules/authz.md` |
| Retrieval row shape and query plan guarantees | `indexing` → `retrieval` | `modules/indexing.md` |
| Generation activation semantics (what a reader may assume mid-switch) | `indexing` → `retrieval` | `modules/indexing.md`, DESIGN §9.3.5 |
| Data classification of a request envelope | `http` → `egress` → providers, telemetry | `modules/egress.md`, DESIGN §9.7.1 |
| Evidence manifest fields (stable identifiers) | `answer` ↔ `authz` ↔ `indexing` | `modules/answer.md`, DESIGN §9.1.5 |
| Skipped-material manifest surfaced to users | `chunking` → `http`/`web` | `modules/chunking.md` |
