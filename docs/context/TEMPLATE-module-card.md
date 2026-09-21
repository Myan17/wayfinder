---
module: <name>
owner: <A|B handle>
paths:
  - <glob>
interface_files:          # hashed by CI; changing one requires updating Verified-at below
  - <path>
tables_owned:
  - <table>
depends_on:               # modules this one calls; their cards are required reading
  - <module>
design_sections:
  - "DESIGN §x.y"
verified_hashes:           # scripts/check_context_freshness.py --fix writes these, once you have
  "<interface file>": "<sha256 prefix>"   # actually re-read the card against the code
verified_on: <YYYY-MM-DD>
---

# <module>

## Purpose (three lines, no more)

<What it does. What it is responsible for. What it deliberately is not.>

## Public interface

<The exact symbols, routes, jobs, views or events a caller uses. Signatures, not prose. If it is not
listed here, it is not part of the contract and may change without notice.>

## Invariants a caller may rely on

- <Statement a caller can build on, each pinned by a test named below.>

## What this module will never do

- <The negative space. Often more useful than the positive: "never evaluates user authorization",
  "never writes outside its own tables", "never calls a provider".>

## Failure modes the caller must handle

| Condition | What the caller sees | What the caller should do |
|---|---|---|
| <…> | <…> | <…> |

## Data owned

<Tables, and the one-line reason each belongs here. Anyone else touching them needs a BCR.>

## Tests that pin this contract

| Test | Pins |
|---|---|
| `<path::test_name>` | <invariant> |

## Fake

`<path to fake>` — implements the same invariants; consumers build against it while this module is
being implemented. The contract tests run against both the fake and the real implementation.

## Open questions

- <Anything a caller might reasonably ask that is not yet decided. Empty is fine; unwritten is not.>

## Change log

| Date | Change | BCR |
|---|---|---|
| <YYYY-MM-DD> | <what moved in the interface> | <BCR-n or —> |
