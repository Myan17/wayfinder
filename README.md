# Wayfinder

Permission-aware retrieval and question answering over a GitHub organization's code and Markdown.
Ask *where* something is implemented, or *why* it behaves the way it does, and get an answer whose
citations resolve to passages you are authorized to see, or an explicit refusal.

**Status:** Phase 0 (spikes and foundations), gate G0 on 2026-10-11. Nothing is deployed. No claim in
this README is evidence until `manifests/` holds a release manifest that reproduces it.

## What it answers

| Question | Example | Answer |
|---|---|---|
| **Locate** | "Where is retry backoff configured?" | Ranked files and symbols with line-level links, pinned to the indexed commit |
| **Explain** | "Why does the client drop the connection after a 401?" | A streamed answer whose citations the asker may see, or a refusal when the evidence is insufficient |

v1 covers default-branch code and Markdown for Python and Go. Sources are repositories where the
GitHub App is installed, plus allow-listed public upstream repositories read read-only. Issue and
pull-request threads are out of v1 (DESIGN §9.13, WF-21).

## Design properties

Each is a design mechanism that the gates require tests for. What is implemented so far is listed
under [Where the project is](#where-the-project-is); the evaluation oracle is not built yet.

1. **Authorization is a lease, not a lookup.** Every fact that permits disclosure (the installation
   is active, the repository is selected, it is public, this user holds a grant) expires. A negative
   event is applied inside the webhook transaction, before any asynchronous refresh. Anything whose
   authority has expired is denied, including cached answers and in-flight streams (DESIGN §9.1).
2. **Derived data is identified by what produced it.** A searchable representation is keyed by the
   repository, the embedding specification and the hash of the exact embedded input, so a new model
   never reuses an old vector. Index generations activate under a fencing lease, so a slow worker
   cannot roll the index backwards (§9.2–9.4).
3. **Quality is measured against an oracle that can be achieved.** Filtered vector search is compared
   with exact search over the *authorized* rows. Locate quality is scored against mined issue→fix
   labels at each pair's own pre-fix commit (§15, ADR-0013).

Target: 1,000 concurrent users for locate and extractive answers, on one Oracle Cloud Always Free Arm
VM with at most $25/month of variable spend. Generated-answer capacity is published as a measured
number, not assumed to be 1,000 (DESIGN §3, §10, §11).

## Architecture

```
GitHub (App, webhooks, git, REST/GraphQL) ──► Caddy ──► /webhooks ──► ingestd (Go write path)
                                                 │                      ingestion, chunking, generations
browser / MCP client ──► Caddy ──► /api ──► api (Python, FastAPI read path)
                                                 │      authorization, retrieval, answers
                                                 ▼
                        Postgres: pgvector + ParadeDB pg_search + River job queue
                        Ollama (query and ingestion instances), in-process ONNX reranker
```

DESIGN §8 has the full context diagram and the data flows.

## Where the project is

| Phase | Dates | Gate | State |
|---|---|---|---|
| P0 Spikes, decisions, schema | Sep 21 – Oct 11 | G0: every spike answered, ADR-0013/0015 written first | In progress |
| P1 Safety and consistency kernel | Oct 12 – 25 | G1: authorization, generation fencing, GC, River scheduling proven by tests | Ordered list in `ORIENT.md` |
| P2 Authorized retrieval slice | Oct 26 – Nov 8 | G2: install → index → search → cite → revoke → deny → delete, end to end | |
| P3 Generated answers | Nov 9 – 15 | G3 | |
| P4 Measurement and hardening | Nov 16 – 22 | G4 | |
| P5 Release evidence | Nov 23 – 29 | G5: DESIGN §16.7 met on the release commit | |
| Launch review | Mon Nov 30 | Approve, or remove the unproven capability | |

P0 was extended twice under DESIGN §19.8 step 4; evidence is never cut to hold a date.

**Built so far:**

- Schema v1: authorization facts, three identities, generations, tombstones (`db/migrations/`).
- Pieces of the authorization kernel, built early: leases, the row predicate, fenced grant refresh
  and counters (`apps/api/wayfinder/authz/`).
- S5: River scheduling at every crash boundary, accepted in ADR-0004.
- S3 (local run): ParadeDB `pg_search` on arm64, ADR-0007. The run on the A1 VM is still to do.
- S1 miner core: ADR-0016's file universe, pair filters, the temporal split, corpus selection and
  the dataset landing checks, and acquisition's git half with ADR-0016 Amendment 1 (`eval/miners/s1/`,
  #59). Acquisition's GraphQL half is next.

## Repository layout

```
apps/api/        Python read path: authz (built so far), retrieval, answer, egress, cache, http
apps/ingestd/    Go write path; only the command scaffold exists yet
db/migrations/   numbered SQL, immutable once merged
eval/            the S1 miner and its datasets; harness and experiments come in P2
infra/           release-manifest format and spike harnesses
docs/            DESIGN.md, ADRs, contract cards, team agreements, agent logs
scripts/         task workflow, guardrails, orient brief, code map
```

`python3 scripts/codemap.py` prints the whole map, with each module's owner and real size.

## Working on it

```bash
make hooks                                  # once per clone and per worktree
git config wayfinder.operator myan
export WAYFINDER_AGENT="claude-code/opus-5"
make setup && make test                     # uv dev environment, then the Python suite

cat ORIENT.md && python3 scripts/orient.py  # what to work on next, and what is in flight
scripts/new-task.sh <module> <slug> "<task>"   # branch + worktree + task log
```

Other targets: `make authz` (the blocking authorization suite), `make db-up && make db-test` (schema
tests against the pinned ParadeDB), `make go-test`, `make guardrails`. `make help` lists them all.

Every task gets a branch, a worktree and an append-only log in `docs/agent-log/`. CI enforces that,
along with task scope, contract-card freshness, commit identity and a 400-line pull-request limit.
`ORIENT.md` decides the order of work; it is not a menu.

## Start here

| Document | What it is |
|---|---|
| [`docs/DESIGN.md`](docs/DESIGN.md) | The design (v0.3.3), including what the system will not claim |
| [`ORIENT.md`](ORIENT.md) | The ordered work list and each item's status |
| [`AGENTS.md`](AGENTS.md) | Operating rules for coding agents; read before any session |
| [`docs/adr/`](docs/adr/) | Decision records; acceptance rules are written before each experiment |
| [`docs/team/WORKING-AGREEMENT.md`](docs/team/WORKING-AGREEMENT.md) | How the two of us work: review, cadence, escalation |
| [`docs/team/OWNERSHIP.md`](docs/team/OWNERSHIP.md) | Modules, task scope, phase plan |
| [`docs/context/INDEX.md`](docs/context/INDEX.md) | Contract cards; read these instead of other modules' code |

## People

- **Myan Gupta** (`@Myan17`) — implementation.
- **Engineer B** (`@Gupta958`) — code review on every pull request.

Coding agents assist both of us and are named in every commit's trailers (`Agent:`, `Operator:`,
`Session:`). The accountable author is always a person.
