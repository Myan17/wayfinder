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
  "eval/datasets/manifest.schema.json": "9871b7a4d6bc55f6"
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
  `github_repo_id`s, the pairs file's path, SHA-256 and explicit `total_count`, `strong_count` and
  `weak_count` (total = strong + weak, checked by `s1.manifest.count_problem`), exclusion counts by reason, per-repository
  split counts and boundaries, and the API-call tally.
- **The pairs file**, committed at exactly `eval/datasets/s1/pairs.jsonl` (JSONL, one `$defs/pair` per line): `github_repo_id`, `issue`, `pr`, `base_commit`
  (40 hex characters), `gold` (at least 1 source path), `strong`, `group_id`, `t_g` and `split`.
- **The miner** (`eval/miners/s1/`): `universe.excluded / lines / chunks`, `pairs.gold_files / keep / weak`,
  `split.assign` and `select.best`. These are pure functions, and the acquisition code (clone,
  GraphQL) lands next. Callers use the dataset and manifest, not these functions.

## Invariants a caller may rely on

- Every pair's `base_commit` is the parent of the PR's first commit (D-1). A pair whose base did not
  resolve is excluded with a reason, never approximated.
- `gold` lists only **base-snapshot** paths: each existed at `base_commit` (a file the PR added is
  never a label, and a rename is labelled by its old path), and at the base it was a regular, non-generated,
  UTF-8 file in ADR-0016's universe with a `.py`, `.pyi` or `.go` extension. It has 1 to `max_files`
  entries (D-2; the extensions were accepted by gupta958 on #50, 2026-09-28).
- `strong` is false exactly when the issue was updated after the merge (D-3). Weak pairs are never
  pooled into strong counts.
- No `group_id` spans two splits, and within a repository every held-out group is at least as
  recent as every test group, and every test group at least as recent as every dev group (D-5).
- `selected` is `select.best`'s winner under ADR-0016's total order. The same inputs always give the
  same winner.
- A pairs file is only used once `s1.dataset.problems` returns nothing for it: lines strictly in
  (`github_repo_id`, `pr`, `issue`) order, so no duplicates; every line a valid `$defs/pair`; the
  manifest's SHA-256; total, strong and weak counts equal to the manifest's; and a final newline.
  `t_g` is an RFC 3339 date-time, and `NaN`/`Infinity` are refused as not JSON.

## What this module will never do

- Write outside `eval/`, or keep a clone after the run.
- Use an App installation or any write scope (ADR-0016 S1-5).
- Choose a candidate that ADR-0016 or a later pull request did not name before it was measured.

## Failure modes the caller must handle

| Condition | What the caller sees | What the caller should do |
|---|---|---|
| No feasible corpus | `selected` empty, and the last round carries `no_feasible_reason` | Treat A-3 as failed; do not evaluate |
| Fewer than 300 strong pairs | `pairs_file.strong_count` below 300 | Report intervals at the achieved size (ADR-0013) |
| `python -m s1.dataset <pairs.jsonl> <manifest.json>` (from `eval/miners`) exits 1 | Each problem on stderr, by line number | Refuse the dataset |

## Data owned

None in Postgres. It owns the files under `eval/datasets/`.

## Tests that pin this contract

| Test | Pins |
|---|---|
| `eval/miners/tests/test_s1_universe.py::test_the_file_universe_is_adr_0016s_seven_steps` | ADR-0016's seven steps, including test Markdown (S1-4) |
| `…::test_lines_and_chunks_are_byte_exact` | The line and chunk definitions |
| `eval/miners/tests/test_s1_pairs.py::test_gold_files_are_source_files_in_the_universe`, `…::test_d2_drops_pairs_with_0_or_too_many_source_files` | D-2 |
| `…::test_gold_labels_are_verified_against_the_base_snapshot` | D-2 labels at the base: added, renamed, symlink, generated, UTF-8, unread |
| `…::test_d3_an_issue_edited_after_the_merge_is_weak` | D-3 |
| `eval/miners/tests/test_s1_split_select.py::test_d5_reproduces_adr_0013s_worked_example`, `…::test_d5_a_group_is_placed_by_its_latest_merge`, `…::test_d5_issue_numbers_are_per_repository` | D-5 |
| `…::test_selection_is_the_total_order_of_adr_0016`, `…::test_the_last_key_is_the_sorted_id_tuple_not_a_sum`, `…::test_no_feasible_corpus_names_the_constraint_that_failed`, `…::test_selection_does_not_depend_on_candidate_input_order` | ADR-0016's selection, independent of input order |
| `eval/miners/tests/test_s1_dataset.py` (all) | The four landing checks: each line is validated by `Draft202012Validator` against the committed `$defs/pair` with a `FormatChecker` (RFC 3339 `t_g`), and NaN or Infinity is not JSON |

## Fake

A sample dataset under `eval/datasets/sample/` will land with the first run, so the harness can
build against it before the full dataset exists.

## Decisions

- **Where the pairs JSONL lives** (gupta958, #50, 2026-09-28: option A). It is committed at the one
  canonical path `eval/datasets/s1/pairs.jsonl`, exempt from the line limit by exact path (#52, which
  merges before the dataset). It is reviewed mechanically, and the eval-data checks must prove four
  things: canonical ordering (by `github_repo_id`, then `pr`, then `issue`), schema and JSONL
  validity for every line, the file's SHA-256 matching the manifest, and the counts matching the
  manifest. These checks land with the miner, before the file.

## Change log

- 2026-09-28: first contract, with the manifest schema and the pure core of the S1 miner.
- 2026-09-28 (review of #50): gold labels are verified against the base snapshot; the pairs file has
  explicit total, strong and weak counts; the pairs file's location is decided.
- 2026-10-04: the pairs file's four landing checks, `s1.dataset`, before the file.
