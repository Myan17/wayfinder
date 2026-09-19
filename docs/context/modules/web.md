---
module: web
owner: myan
paths:
  - apps/web/**
  - docs/context/modules/web.md
interface_files:
  - apps/web/src/api/client.ts
tables_owned:
  []
depends_on:
  - http
design_sections:
  - "DESIGN §9.11 (web client)"
  - "DESIGN §6.2 NFR-14 (accessibility)"
verified_at: 0000000
verified_on: 2026-09-18
---

# web

> **PLACEHOLDER — not yet a contract.**
>
> This card exists so the index resolves and so nothing silently depends on an undocumented module.
> **Whoever implements `web` fills it in, in the pull request that lands the first interface file**
> (`scripts/check_context_freshness.py` starts enforcing it from the moment `verified_at` is set).
> Copy the section structure from `docs/context/TEMPLATE-module-card.md`, and use
> `docs/context/modules/authz.md` or `indexing.md` as the quality bar.
>
> Until then, callers must treat this module as **unspecified**: do not build against it, and do not
> read its implementation to guess the contract. Open a BCR instead, which forces the card to be
> written before the coupling exists.

## Purpose

Static Next.js client: search, ask with streaming citations, repositories, answer and trace views, tokens.

## Public interface

_To be written with the first interface file._

## Invariants a caller may rely on

_None promised yet._

## What this module will never do

_To be written._

## Failure modes the caller must handle

_To be written._

## Data owned

_None._

## Tests that pin this contract

_To be written._

## Fake

_Required before any other module builds against this one (`AGENTS.md` §3.4)._

## Open questions

- Everything below the design sections above; this card is the place to record them as they are settled.

## Change log

| Date | Change | BCR |
|---|---|---|
| 2026-09-18 | Placeholder created alongside the framework | — |
