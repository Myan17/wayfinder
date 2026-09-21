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
verified_at: 2f81df2
verified_on: 2026-09-21
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
```

Plus the Python project definition:

- package root `apps/api`; tests in `apps/api/tests` **and** `scripts/tests`, so tooling under
  `scripts/` is covered by the same `make test`; `pythonpath = ["apps/api"]`
- `requires-python = ">=3.13"`; the dev extra pins pytest, pytest-asyncio, hypothesis, ruff
- ruff: line length 110, target py313, rule set `E,F,I,UP,B,SIM,RUF`

Not yet part of the interface (planned): `make up`, `make load`, `make deploy`, the Compose stack,
the Terraform module and the load-test stub.

## Invariants a caller may rely on

- A test file placed under `apps/api/tests/<module>/` is collected by `make test` with no extra
  configuration, and imports the package as `wayfinder.<module>`.
- A test file under `scripts/tests/` is collected too. Guardrail and tooling scripts are not importable
  as a package, so those tests load the script by path.
- `make lint` and `make test` are the commands CI *will* run: today CI runs the collaboration
  guardrails only, and the product suites are wired in the pull request that lands the first suite.
  Until then a green pull request means the guardrails passed, not that anything was tested.
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
| `make guardrails` in CI (`.github/workflows/guardrails.yml`) | Identity, scope, size, agent log, card freshness, CODEOWNERS sync — **the only gate running today** |
| _not yet wired_ `make lint`, `make test` | Arrive with the first product suite |
| _planned_ `infra/policy/allowed_resources.yaml` check | Terraform never provisions a non-allow-listed resource (DESIGN §11.1) |

## Fake

No fake: this module is the environment. Consumers depend on the command surface, which is exercised
by CI on every pull request.

## Open questions

- `make lint` and `make test` are still not wired into CI, and the suites now exist (38 + 8 tests).
  That wiring is the next platform pull request, together with the ruff-format debt in six older
  scripts. Until then a green pull request means the guardrails passed, not that anything was tested.
- Whether to pin Python 3.13 exactly (design text) or keep `>=3.13` and run on the local 3.14. Today:
  `>=3.13`, and the release manifest records the interpreter actually used.
- Where the load-test stub runs once the AMD micro instance exists (DESIGN §16.4).

## Change log

| Date | Change | BCR |
|---|---|---|
| 2026-09-18 | Card written when the bootstrap Makefile and pyproject landed, replacing the placeholder | — |
