---
module: sources
owner: myan
paths:
  - apps/ingestd/internal/source/**
  - docs/context/modules/sources.md
interface_files:
  - apps/ingestd/internal/source/source.go
tables_owned:
  []
depends_on:
  - webhooks
design_sections:
  - "DESIGN §9.3.1–9.3.2 (source modes, contract)"
  - "DESIGN §9.3.7 (hostile repositories)"
verified_at: 0000000
verified_on: 2026-09-18
---

# sources

> **PLACEHOLDER — not yet a contract.**
>
> This card exists so the index resolves and so nothing silently depends on an undocumented module.
> **Whoever implements `sources` fills it in, in the pull request that lands the first interface file**
> (`scripts/check_context_freshness.py` starts enforcing it from the moment `verified_at` is set).
> Copy the section structure from `docs/context/TEMPLATE-module-card.md`, and use
> `docs/context/modules/authz.md` or `indexing.md` as the quality bar.
>
> Until then, callers must treat this module as **unspecified**: do not build against it, and do not
> read its implementation to guess the contract. Open a BCR instead, which forces the card to be
> written before the coupling exists.

## Purpose

Fetches default-branch code and Markdown from two source modes: installed repositories and allow-listed public upstream repositories (read-only).

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
