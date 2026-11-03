---
module: eval-harness
owner: myan
paths:
  - eval/harness/**
  - eval/experiments/**
  - docs/context/modules/eval-harness.md
interface_files:
  - eval/harness/s2/inputs.py
  - eval/harness/interface.py
  - eval/experiments/schema.json
tables_owned:
  []
depends_on:
  - retrieval
  - answer
  - eval-data
design_sections:
  - "DESIGN §15 (evaluation methodology)"
  - "DESIGN §16.5 (quality gates)"
  - "ADR-0019 and its Amendment 1 (spike S2's method and inputs)"
verified_hashes:
  "eval/harness/s2/inputs.py": "d4230c1d79a2ee04"
verified_on: 2026-11-02
---

# eval-harness

## Purpose (three lines, no more)

It will hold the metrics, intervals, experiment runner and CI regression gate (DESIGN §15, §16.5).
Today it holds only spike S2's harness (ADR-0019), whose first part is S2's inputs. It never
mines or edits a dataset (`eval-data`), and it never changes retrieval (`retrieval`).

## Public interface

Only S2's own later parts call these. `eval/harness/interface.py` and
`eval/experiments/schema.json`, the experiment runner's interface, do not exist yet.

- **`s2.inputs`** (`eval/harness/s2/inputs.py`, importable as `s2.inputs` with `eval/harness` on
  the path):
  - `snapshot(git_dir, commit, github_repo_id) -> list[Window]`: every ADR-0016 universe file at
    `commit`, as `s1.universe` decides, cut into windows, in path order.
  - `windows(github_repo_id, path, content) -> list[Window]` and `split_lines(content)`.
    `Window` holds `github_repo_id`, `path`, `index`, `first_line`, `text` and `pseudo_repo`.
  - `count_problems(counts, manifest) -> list[str]`: empty only when every selected repository's
    window count equals its `chunk_estimate`.
  - `pseudo_repo(github_repo_id, path) -> int`, `GRANTS` (percent → granted pseudo-repository
    ids) and `admitted_fraction(windows, percent)`.
  - `strong_dev_issues(pairs) -> list[Issue]`, where `Issue` holds `github_repo_id`, `issue` and
    `group_id`. Also `cold_sample(issues) -> list[Issue]`.
  - `query_text(title, body)`, `normalize(text)` and `accepted(text)`.

## Invariants a caller may rely on

- A file's windows are consecutive `s1.universe.CHUNK_LINES` (60) line cuts, and the last window
  may be shorter. Lines are counted as `s1.universe.lines` counts them, so a repository's window
  count equals `s1.repo.measure(...).chunk_estimate`. The windows' text concatenates back to the
  file's bytes.
- `pseudo_repo` is `int(sha256(f"{github_repo_id}/{path}" as UTF-8).hexdigest(), 16) % 100`, and
  all of a file's windows share it. `GRANTS` is `{1: 0, 10: 0–9, 100: 0–99}` (Amendment 1 §3).
- `strong_dev_issues` keeps only pairs with `strong` true and `split` `dev`, one row per
  (`github_repo_id`, `issue`), in that order. It raises if one issue appears in two groups. Over
  the committed S1 dataset it returns 874 issues.
- `normalize` applies NFC and strips trailing whitespace per line, and does nothing else (DESIGN
  §9.4.2). `accepted` is false above 2,000 characters (§9.5 step 1). `query_text` is the title, a
  blank line and the body, or just the title when there is no body.
- `cold_sample` orders by SHA-256 of `group_id`, then by issue number. It takes the first issue of
  each of the first 50 distinct groups, whatever order the input is in.

## What this module will never do

- Write a dataset or a manifest, or reimplement ADR-0016's universe steps.
- Fetch from the network in `s2.inputs`. Issue text is fetched by a separate script.
- Produce evidence off the A1. S2-dev's numbers are never evidence (ADR-0019).

## Failure modes the caller must handle

| Condition | What the caller sees | What the caller should do |
|---|---|---|
| A window count differs from the manifest | `count_problems` returns one line per repository | Refuse to run S2 (Amendment 1 §1) |
| An issue is in two groups | `ValueError` from `strong_dev_issues` | Refuse the dataset |
| A git object is missing or unreadable | `subprocess.CalledProcessError` or `AssertionError` from `snapshot` | Stop; never run on a partial corpus |

## Data owned

None in Postgres. No committed files yet.

## Tests that pin this contract

| Test | Pins |
|---|---|
| `eval/harness/tests/test_s2_inputs.py::test_windows_are_60_line_cuts_with_a_shorter_last_window` | Window boundaries, first lines, a file with no final newline, an empty file, the universe's drops |
| `…::test_the_window_count_is_eval_datas_own_chunk_estimate`, `…::test_line_split_matches_universe_lines` | Agreement with `s1.repo.measure` and `s1.universe.lines` |
| `…::test_count_problems_refuses_any_difference_from_the_manifest`, `…::test_the_committed_manifest_estimates_sum_to_7175` | Amendment 1 §1's refusal, and the corpus size |
| `…::test_pseudo_repo_is_amendment_1s_exact_hash`, `…::test_a_files_windows_share_one_pseudo_repo`, `…::test_grant_levels_are_0_then_0_to_9_then_0_to_99` | Amendment 1 §3 |
| `…::test_the_strong_dev_query_set_is_874_issues`, `…::test_weak_and_non_dev_pairs_are_excluded_and_a_split_group_is_refused` | Amendment 1 §4's set |
| `…::test_normalization_is_nfc_and_trailing_whitespace_only`, `…::test_queries_above_2000_characters_are_rejected`, `…::test_the_cold_sample_is_the_first_of_each_of_the_first_50_groups` | Normalization, rejection and the cold sample |

## Fake

None. Only S2's own parts call this module. A fake is required before any other module builds
against it (`AGENTS.md` §3.4).

## Open questions

- How the title and body are joined is not written in DESIGN §14.2 step 4. `query_text` uses one
  blank line. This needs gupta958's ruling.
- The experiment runner's interface (`eval/harness/interface.py`) is still to be written.

## Change log

| Date | Change | BCR |
|---|---|---|
| 2026-09-18 | Placeholder created alongside the framework | — |
| 2026-11-03 | First contract: S2's inputs (ADR-0019 Amendment 1 §1, §3, §4) | — |
