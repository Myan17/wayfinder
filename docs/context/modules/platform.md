---
module: platform
owner: myan
paths:
  - infra/**
  - .github/workflows/**
  - loadtest/**
  - Makefile
  - pyproject.toml
  - docs/context/modules/platform.md
interface_files:
  - Makefile
  - pyproject.toml
tables_owned: []
depends_on: []
design_sections:
  - "DESIGN §16.4 (load protocol)"
  - "DESIGN §17.5 (recovery tiers)"
  - "DESIGN §18 (CI/CD, environments, conventions)"
verified_hashes:
  "Makefile": "b05391f52d55e72d"
  "pyproject.toml": "9d94aa70a0730215"
verified_on: 2026-09-24
---

# platform

## Purpose

The environment every other module runs in: how you build and test locally, what CI enforces, how the
service is provisioned and deployed, and how load and recovery are exercised. Today only its
developer-facing half exists — the `Makefile`, the Python project definition and the guardrails
workflow. Infrastructure, deployment and the load stub land in phases P2 and P4.

## Public interface

The contract other modules depend on is the **command surface**, not the files behind it:

```make
make hooks       # install git hooks (per clone and per worktree)
make setup       # create the dev environment (uv sync --extra dev)
make test        # run the Python test suite
make authz       # run the blocking authorization suite
make lint        # ruff check + format --check
make fmt         # ruff format
make guardrails  # identity, scope, agent-log, card freshness, CODEOWNERS
make digest      # build this week's gate report from the task logs
make db-up       # start the pinned ParadeDB (S3 digest) and wait for a real query, not just health
make db-test     # db/tests against it; any skipped test fails the target
make db-down     # stop it
make schema-check  # db/dump-schema.sh --check: db/schema.sql equals a fresh dump
make manifest-check  # validate the example release manifest and print its cache keys
make go-test     # gofmt, go vet and go test for apps/ingestd
make go-build    # ingestd for linux/arm64, versioned with the commit
```

The release-manifest format (DESIGN §16.9): `infra/manifest/release_manifest.py` (`validate`, `cache-key`;
its docstring is the spec) and `infra/manifest/example.json`, where `unpinned-until-…` marks values not yet chosen.

And `.github/workflows/ci.yml` (jobs `unit`, `db`, `go`, `dispatcher`). The Go module is
`apps/ingestd` (`go.mod`, `cmd/ingestd`); its `internal/` packages belong to their own modules. Branch protection requires
`dispatcher` only; it passes only when every job in its `needs` reports `success`.

Plus the Python project definition:

- package root `apps/api`; tests in `apps/api/tests`, `scripts/tests` **and** `infra/manifest/tests`,
  so tooling is covered by the same `make test`; `pythonpath = ["apps/api"]`
- `requires-python = ">=3.13"`; the dev extra pins pytest, pytest-asyncio, hypothesis, ruff and
  `psycopg[binary]` (DESIGN §12 names psycopg 3 as the database driver; spike S3 is its first use)
- ruff: line length 110, target py313, rule set `E,F,I,UP,B,SIM,RUF`

Not yet part of the interface (planned): `make up`, `make load`, `make deploy`, the Compose stack,
the Terraform module and the load-test stub.

## Invariants a caller may rely on

- A test file placed under `apps/api/tests/<module>/` is collected by `make test` with no extra
  configuration, and imports the package as `wayfinder.<module>`.
- A test file under `scripts/tests/` is collected too. Guardrail and tooling scripts are not importable
  as a package, so those tests load the script by path.
- CI runs `make test` (job `unit`), and `make db-up db-test schema-check` (job `db`, on
  `ubuntu-24.04-arm` because the pinned image is arm64). A skipped, cancelled or failed job fails
  `dispatcher` (DESIGN §16.1). `make lint` is **not** gated yet: `main` is not lint-clean.
- A suite counts only once it is in `dispatcher`'s `needs`; a job outside that list can go red
  without blocking a merge.
- Every action in `ci.yml` is pinned by commit SHA (DESIGN §18.2).
- Cache keys: `index` moves with schema, image, extensions, grammars, chunker or any embedding-spec
  field (§15.5); `eval` also with retrieval, answerability, prompts, providers and datasets. **Neither
  moves with `code_commit` or `platform`.** A new manifest field must be scoped deliberately (tested).
- Ruff's `RUF002` is on, so docstrings use ASCII hyphens rather than en dashes. Section references
  (`§`) are fine.
- Guardrail scripts run on the system Python 3 with no third-party dependencies, so they work before
  `make setup` and inside CI's minimal image.

## What this module will never do

- Never hold business logic; if something needs a test beyond "the command runs", it belongs in a
  real module.
- Never weaken a guardrail to make a build pass — the guardrail is the product of the working
  agreement, and changing it is an `agreements` decision with both signatures.
- Never put a secret in `Makefile`, CI workflow or Compose file; secrets come from the environment or
  a mounted file (`.env.example` documents the variables).

## Failure modes the caller must handle

| Condition | Symptom | Response |
|---|---|---|
| `uv` missing | `make setup` fails immediately | Install uv; the version is recorded in the release manifest |
| Docker daemon not running | Integration tests that need Postgres are skipped or error | Pure-logic suites still run; DB-backed work waits for the daemon (current state on this machine) |
| Ollama not installed | Embedding-dependent work cannot run | Same: the affected suites are skipped, and the gap is recorded in the task log |
| A guardrail fails locally | `make guardrails` exits non-zero with the specific rule | Fix the cause, not the check |

## Data owned

_None._

## Tests that pin this contract

| Test | Pins |
|---|---|
| `make guardrails` in CI (`.github/workflows/guardrails.yml`) | Identity, scope, size, agent log, card freshness, CODEOWNERS sync |
| `ci.yml` job `unit` | `make test` passes on every pull request and on `main` |
| `ci.yml` job `db` | Schema tests on the pinned image, and `db/schema.sql` drift |
| `ci.yml` job `go` | `make go-test` (gofmt clean, vet, tests) and `make go-build` (linux/arm64) |
| `ci.yml` job `dispatcher` | No required suite was skipped, cancelled or failed |
| `infra/manifest/tests/test_release_manifest.py` | Strict validation; each input moves exactly its own keys; commit and platform move none |
| _not yet wired_ `make lint` | After the cross-module lint cleanup |
| _planned_ `infra/policy/allowed_resources.yaml` check | Terraform never provisions a non-allow-listed resource (DESIGN §11.1) |

## Fake

No fake: this module is the environment. Consumers depend on the command surface, which is exercised
by CI on every pull request.

## Open questions

- `make lint` is not gated. `main` has 6 ruff errors in `scripts/` and 19 unformatted files across
  modules; the gate arrives after a cleanup, which touches several modules.
- `guardrails.yml` still pins actions by tag (`@v4`, `@v5`), unlike `ci.yml`. Repinning it is a
  platform follow-up.
- The pinned database comes from the S3 spike's compose file. A development compose stack in
  `infra/compose/` replaces it with `make up`.
  - This card no longer states a test count. It has been wrong three times: a count goes stale
    whenever any pull request adds a test without touching an interface file, which is most of them,
    so the freshness check never catches it. `uv run pytest -q` is the answer and cannot go stale.
- Whether to pin Python 3.13 exactly (design text) or keep `>=3.13` and run on the local 3.14. Today:
  `>=3.13`, and the release manifest records the interpreter actually used.
- Where the load-test stub runs once the AMD micro instance exists (DESIGN §16.4).

## Change log

| Date | Change | BCR |
|---|---|---|
| 2026-09-18 | Card written when the bootstrap Makefile and pyproject landed, replacing the placeholder | — |
| 2026-09-21 | Re-read against `Makefile` and `pyproject.toml`; corrected the tooling test count (8 to 17, after the freshness tests landed). Card verification moved to content hashes | — |
| 2026-09-22 | `psycopg[binary]` added to the dev extra and locked. DESIGN §12 already names psycopg 3 as the driver, so this is the project's driver arriving early rather than a spike-only dependency | — |
| 2026-09-22 | Removed the test count rather than correcting it a third time: it had drifted to 17 against an actual 29, because a count goes stale whenever a pull request adds a test without touching an interface file | — |
| 2026-09-24 | CI skeleton: `ci.yml` (`unit`, `db`, `dispatcher`); `make db-up`, `db-test`, `db-down`, `schema-check` | — |
| 2026-09-24 | Release-manifest format and cache keys; `make manifest-check`; `infra/manifest/tests` collected | — |
| 2026-09-24 | Go `ingestd` scaffold: module, `cmd/ingestd`, `make go-test`/`go-build`, CI job `go` in the dispatcher | — |
