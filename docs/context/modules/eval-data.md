---
module: eval-data
owner: myan
paths:
  - eval/miners/**
  - eval/datasets/**
  - docs/context/modules/eval-data.md
interface_files:
  - eval/datasets/manifest.schema.json
tables_owned:
  []
depends_on:
  []                  # S1 reads upstream repositories directly in public_readonly mode (ADR-0016); not through `sources`
design_sections:
  - "DESIGN §14.1-14.2, §14.5 (corpus, historical protocol, dataset versioning)"
  - "ADR-0013 (dataset rules D-1 to D-7), ADR-0016 (S1's candidates, rules and selection)"
verified_hashes:
  "eval/datasets/manifest.schema.json": "eb4c5b6e885b03d0"
verified_on: 2026-09-28
---

# eval-data

## Purpose (three lines, no more)

It mines issue→fix pairs at their own pre-fix base commits from the S1 corpus and publishes the locate
dataset as a JSONL file plus a manifest. It is responsible for ADR-0013's D-1 to D-6 and ADR-0016's
selection. It never runs retrieval, and it never scores anything; that is `eval-harness`.

## Public interface

- **`eval/datasets/manifest.schema.json`**: the manifest every consumer reads first. It holds the as-of
  time, the miner commit, the rules applied (`max_files`, gold extensions, chunk lines), each
  candidate's S1-1 to S1-5 results and chunk estimate, every selection round, the selected
  `github_repo_id`s, the pairs file's path, SHA-256 and count, exclusion counts by reason, per-repository
  split counts and boundaries, and the API-call tally.
- **The pairs file** (JSONL, one `$defs/pair` per line): `github_repo_id`, `issue`, `pr`, `base_commit`
  (40 hex characters), `gold` (at least 1 source path), `strong`, `group_id`, `t_g` and `split`.
- **The miner** (`eval/miners/s1/`): `universe.excluded / lines / chunks`, `pairs.gold_files / keep / weak`,
  and, in the next pull request, `split.assign` and `select.best`. These are pure functions; the
  acquisition code (clone, GraphQL) follows them. Callers use the dataset and manifest, not these functions.

## Invariants a caller may rely on

- Every pair's `base_commit` is the parent of the PR's first commit (D-1). A pair whose base did not
  resolve is excluded with a reason, never approximated.
- `gold` lists only files in ADR-0016's file universe with a `.py`, `.pyi` or `.go` extension, and
  has 1 to `max_files` entries (D-2).
- `strong` is false exactly when the issue was updated after the merge (D-3). Weak pairs are never
  pooled into strong counts.
- No `group_id` spans two splits, and within a repository every held-out group is at least as
  recent as every test group, and every test group at least as recent as every dev group (D-5).
- `selected` is `select.best`'s winner under ADR-0016's total order. The same inputs always give the
  same winner.

## What this module will never do

- Write outside `eval/`, or keep a clone after the run.
- Use an App installation or any write scope (ADR-0016 S1-5).
- Choose a candidate that ADR-0016 or a later pull request did not name before it was measured.

## Failure modes the caller must handle

| Condition | What the caller sees | What the caller should do |
|---|---|---|
| No feasible corpus | `selected` empty, and the last round carries `no_feasible_reason` | Treat A-3 as failed; do not evaluate |
| Fewer than 300 strong pairs | `pairs_file.count` of strong pairs below 300 | Report intervals at the achieved size (ADR-0013) |
| The manifest's SHA-256 does not match the file | — | Refuse the dataset |

## Data owned

None in Postgres. It owns the files under `eval/datasets/`.

## Tests that pin this contract

| Test | Pins |
|---|---|
| `eval/miners/tests/test_s1_universe.py::test_the_file_universe_is_adr_0016s_seven_steps` | ADR-0016's seven steps, including test Markdown (S1-4) |
| `…::test_lines_and_chunks_are_byte_exact` | The line and chunk definitions |
| `…::test_gold_files_are_source_files_in_the_universe`, `…::test_d2_drops_pairs_with_0_or_too_many_source_files` | D-2 |
| `…::test_d3_an_issue_edited_after_the_merge_is_weak` | D-3 |
| The D-5 and selection tests | They land with `split.py` and `select.py` in the next pull request, which pins the D-5 and `selected` invariants above |

## Fake

A sample dataset under `eval/datasets/sample/` will land with the first run, so the harness can
build against it before the full dataset exists.

## Open questions

- **Where the full pairs JSONL lives.** A dataset of about 1,000 lines exceeds the 400-line PR limit.
  The options are a reviewer exemption like `db/schema.sql`'s, or a release asset with only the
  manifest committed. This needs gupta958's decision before the results PR.

## Change log

- 2026-09-28: first contract, with the manifest schema and the pure core of the S1 miner.
