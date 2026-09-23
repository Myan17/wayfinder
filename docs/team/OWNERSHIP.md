# Ownership map

Two engineers, one repository, **two different jobs**: `myan` implements, `gupta958` reviews every
pull request and merges it. Ownership is by **module** — a set of path globs plus the tables and
contracts it owns.

Today every module's implementation owner is `myan`, so the boundary that does the day-to-day work is
not owner-vs-owner but **task scope**: a branch named `myan/authz/lease-predicate` may touch the
`authz` module, and nothing else, without saying why. That keeps parallel agent sessions from colliding
and keeps each pull request reviewable by someone who did not write it. When `gupta958` starts
implementing, move modules into their `owns:` list and the same machinery enforces owner boundaries
instead — no other change.

Owner handles come from `docs/team/ROSTER.md`. The YAML block at the bottom of this file is the
machine-readable source: `.github/CODEOWNERS` is generated from it, and the ownership guardrail reads
it. Edit the YAML and the table together; CI checks they agree.

## 1. The split, and why

The system already has a clean seam: the **write path** turns GitHub into an index, and the **read
path** turns a question plus an authorization decision into an answer. They share only the database
schema and coordinate through it (`docs/DESIGN.md` §8.2). That seam is the ownership boundary, so most
tasks touch one side only.

| | `myan` (implementer) | `gupta958` (reviewer) |
|---|---|---|
| Writes | All modules | Nothing today |
| Reviews | Nothing (author) | **Every** pull request, via CODEOWNERS on `*` |
| Merges | Never merges own work | Approves and merges |
| Carries the risk of | Getting it wrong | Letting it through |
| Uses | Claude Code | ChatGPT, for review assistance only (`[agent-draft]` comments) |

## 2. Modules

| Module | Owner | Paths | Owns tables | Card |
|---|---|---|---|---|
| `authz` | myan | `apps/api/wayfinder/authz/**` | `principal`, `session`, `user_repo_access`, `user_access_state`, `connection_admin` | [authz](../context/modules/authz.md) |
| `retrieval` | myan | `apps/api/wayfinder/retrieval/**` | — (reads B's tables through the retrieval view contract) | [retrieval](../context/modules/retrieval.md) |
| `answer` | myan | `apps/api/wayfinder/answer/**` | `answer`, `answer_trace`, `feedback` | [answer](../context/modules/answer.md) |
| `egress` | myan | `apps/api/wayfinder/egress/**` | — | [egress](../context/modules/egress.md) |
| `cache` | myan | `apps/api/wayfinder/cache/**` | `answer_cache` | [cache](../context/modules/cache.md) |
| `http` | myan | `apps/api/wayfinder/http/**` | — | [http](../context/modules/http.md) |
| `web` | myan | `apps/web/**` | — | [web](../context/modules/web.md) |
| `eval-harness` | myan | `eval/harness/**`, `eval/experiments/**` | — | [eval-harness](../context/modules/eval-harness.md) |
| `sources` | myan | `apps/ingestd/internal/source/**` | — | [sources](../context/modules/sources.md) |
| `chunking` | myan | `apps/ingestd/internal/chunk/**` | `content` | [chunking](../context/modules/chunking.md) |
| `indexing` | myan | `apps/ingestd/internal/{embed,generation,gc}/**` | `generation`, `representation`, `vector_d*`, `occurrence`, `embedding_cache`, `tombstone` | [indexing](../context/modules/indexing.md) |
| `webhooks` | myan | `apps/ingestd/internal/webhook/**` | `connection`, `repository`, `webhook_delivery` | [webhooks](../context/modules/webhooks.md) |
| `eval-data` | myan | `eval/miners/**`, `eval/datasets/**` | — | [eval-data](../context/modules/eval-data.md) |
| `platform` | myan | `infra/**`, `.github/workflows/**`, `loadtest/**` | — | [platform](../context/modules/platform.md) |
| `observability` | myan | `apps/*/**/telemetry*`, `infra/compose/otel/**` | `audit_event` | [observability](../context/modules/observability.md) |
| `schema` | **joint** | `db/migrations/**` | the schema itself | [schema](../context/modules/schema.md) |
| `agreements` | **joint** | `AGENTS.md`, `CLAUDE.md`, `ORIENT.md`, `.claude/**`, `docs/adr/**`, `docs/team/**`, `.github/CODEOWNERS`, `docs/DESIGN.md` | — | — |

**Joint** (`schema`, `agreements`) means the change is structural: it needs the reviewer's explicit
sign-off on the *design*, not just the diff, and the review checklist for schema applies. Since
`gupta958` reviews everything, joint is a signal about depth of review rather than a second approver.

### Boundary notes

- `retrieval` (A) reads tables `indexing` (B) owns. The contract between them is a **SQL view plus a
  documented query shape** in the `indexing` card, not the physical tables. B may change physical
  layout freely as long as the view and its plan characteristics hold; anything else is a BCR.
- `authz` (A) publishes the `eligible_repo` view and the granted-repository parameter helper. B's jobs
  never evaluate authorization; they only record facts and enqueue refreshes (`docs/DESIGN.md` §8.2).
- `observability` (B) owns the collector and policy; each module owns its own spans and counters and
  must not export content that the policy forbids (§17.1).
- Tests live with the module they pin. The cross-cutting authorization suite (`apps/api/tests/authz/**`)
  is A's, and B reviews it as a required reviewer because it protects B's ingestion paths too.

## 3. Work by phase

`myan` implements all of it; the table below is the review load `gupta958` should expect, phase by
phase, and which checklist applies. Hours are from `docs/DESIGN.md` §19.

| Phase | Implementation (`myan`) | Review focus (`gupta958`) |
|---|---|---|
| P0 spikes | All six spikes, schema v1, ADR-0011/0013/0015, scaffold and CI | Are the selection rules written *before* the experiments? Is the schema's identity model right — it is the expensive thing to change later |
| P1 kernel | Authorization predicate and refresh; ingestion, chunking, generations, GC, tombstones | Security checklist on every authorization and webhook pull request; the fencing and GC ordering arguments |
| P2 slice | Retrieval, auth flows, artifact authorization, cache, web client, evaluation dataset, deployment | Does the predicate reach every path, including cache replay and traces? Is the historical protocol leak-free? |
| P3 answers | Answer state machine, citations, answerability, egress and providers | Classification of the whole envelope; no generation without a relevance signal; partial-stream handling |
| P4 measurement | Experiments E1–E7, capacity profiles, faults, recovery drill | Are the oracles achievable and the intervals honest? Do the load profiles measure what they claim? |
| P5 release | Final held-out scoring, release report, CI gates, manifests, runbook | Does every README claim match an artifact? Any open P1 still attached to a shipped capability? |

## 4. When ownership should change

Two triggers. First, if `gupta958` starts implementing: move those modules into their `owns:` list,
flip their role in the roster, regenerate `CODEOWNERS`. Second, if review keeps stalling on one area,
that area's card is probably too thin — fix the card before moving the module. Either change goes
through a BCR labelled `ownership`, approved by both.


## 5. Machine-readable ownership

```yaml
modules:
  authz:         {owner: myan, paths: ["apps/api/wayfinder/authz/**", "apps/api/tests/authz/**", "docs/context/modules/authz.md"]}
  retrieval:     {owner: myan, paths: ["apps/api/wayfinder/retrieval/**", "apps/api/tests/retrieval/**", "docs/context/modules/retrieval.md"]}
  answer:        {owner: myan, paths: ["apps/api/wayfinder/answer/**", "apps/api/tests/answer/**", "docs/context/modules/answer.md"]}
  egress:        {owner: myan, paths: ["apps/api/wayfinder/egress/**", "apps/api/tests/egress/**", "docs/context/modules/egress.md"]}
  cache:         {owner: myan, paths: ["apps/api/wayfinder/cache/**", "apps/api/tests/cache/**", "docs/context/modules/cache.md"]}
  http:          {owner: myan, paths: ["apps/api/wayfinder/http/**", "apps/api/tests/http/**", "docs/context/modules/http.md"]}
  web:           {owner: myan, paths: ["apps/web/**", "docs/context/modules/web.md"]}
  eval-harness:  {owner: myan, paths: ["eval/harness/**", "eval/experiments/**", "docs/context/modules/eval-harness.md"]}
  sources:       {owner: myan, paths: ["apps/ingestd/internal/source/**", "docs/context/modules/sources.md"]}
  chunking:      {owner: myan, paths: ["apps/ingestd/internal/chunk/**", "docs/context/modules/chunking.md"]}
  indexing:      {owner: myan, paths: ["apps/ingestd/internal/embed/**", "apps/ingestd/internal/generation/**", "apps/ingestd/internal/gc/**", "docs/context/modules/indexing.md"]}
  webhooks:      {owner: myan, paths: ["apps/ingestd/internal/webhook/**", "docs/context/modules/webhooks.md"]}
  eval-data:     {owner: myan, paths: ["eval/miners/**", "eval/datasets/**", "docs/context/modules/eval-data.md"]}
  platform:      {owner: myan, paths: ["infra/**", ".github/workflows/**", "loadtest/**", "Makefile", "pyproject.toml", "uv.lock", ".gitignore", ".env.example", "README.md", "docs/context/modules/platform.md"]}
  observability: {owner: myan, paths: ["infra/compose/otel/**", "docs/context/modules/observability.md"]}
  schema:        {owner: joint, paths: ["db/**", "docs/context/modules/schema.md"]}
  agent-logs:    {owner: any,   paths: ["docs/agent-log/**"]}
  boundary:      {owner: any,   paths: ["docs/context/boundary/**"]}
  agreements:    {owner: joint, paths: ["AGENTS.md", "CLAUDE.md", "ORIENT.md", ".claude/**", "docs/adr/**", "docs/team/**", ".github/CODEOWNERS", "docs/DESIGN.md", "scripts/**", ".githooks/**"]}
```
