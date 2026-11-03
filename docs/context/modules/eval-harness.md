---
module: eval-harness
owner: myan
paths:
  - eval/harness/**
  - eval/experiments/**
  - docs/context/modules/eval-harness.md
interface_files:
  - eval/harness/s2/inputs.py
  - eval/harness/s2/counters.py
  - eval/harness/s2/preflight.py
  - eval/harness/s2/calibration.py
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
  "eval/harness/s2/calibration.py": "bec8e7bd551d3503"
  "eval/harness/s2/counters.py": "d395c78424b6b9b9"
  "eval/harness/s2/inputs.py": "e9864d746f2e2e1b"
  "eval/harness/s2/preflight.py": "2751fca282127674"
verified_on: 2026-11-03
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
  - `query(title, body)`, the query S2 sends, and its parts `query_text(title, body)` and
    `normalize(text)`. Also `accepted(text)`.
- **`s2.fetch_issues`** (`python -m s2.fetch_issues --out <path>`, with `eval/harness` and
  `eval/miners` on the path): fetches the query set's issue text once into a JSONL file outside git,
  with a `.meta.json` beside it holding `count`, `fetched_at` and `sha256`. Each line holds
  `github_repo_id`, `issue`, `title` and `body`, as GitHub returned them.

- **`s2.counters`** (Linux-only readers; parsers take paths, so they run anywhere): `cgroup_of(pid)`
  and `cgroup_usage_usec(cgroup)` for query embedding; `backend_host_pid(backend_pid,
  postgres_cgroup)`, `process_clock(host_pid)` and `process_cpu_ns(clock)` for hybrid SQL;
  `thread_cpu_ns()` for rerank; `schedstat_ns(host_pid)`; `executed_ticks(proc_stat) -> Executed`
  for the calibration; the checks `check_cgroup_v2()` and `check_resolution(read_ns, name)`; and
  `CounterError`.
- **`s2.preflight`**: `strace_command(host_pid)`, `classify(strace_output) -> Creations` (`threads`,
  `children`, `kind` of `none`, `threads` or `child`), `check_clock(found, process_ns,
  schedstat_ns)`, `cases()` (12 `Case`s) and `run_case(case, reset, connect, traced_query) ->
  Result`, where `traced_query` returns `Traced` (strace output, the two clock deltas, thread names).
- **`s2.calibration`**: `calibrate(machine, path, call) -> Calibration` for `path` in `PATHS`
  (`embedding`, `sql`, `rerank`), built from `background(machine)`, `block(machine, call)` and
  `check(path, before, block, after)`. `call` makes one real call and returns its CPU in ns through
  the path's own counter. `Machine` holds the `/proc/stat` reader, monotonic clock, harness process
  clock, sleep and `USER_HZ`; `Machine.linux()` is the real one. `Calibration` gives the three
  `Window`s (executed, `iowait` and `steal` seconds, elapsed), the noise, the reference and `ratio`.
  `accounting(kernel_config())` names the kernel's CPU-time accounting for S2-8.

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
  §9.4.2). `accepted` is false above 2,000 characters (§9.5 step 1). `query_text` is the title
  alone when the body is missing, empty or only whitespace, and otherwise the title, two LF characters and the body
  (gupta958's ruling, 2026-11-03). `query` applies `normalize` once, to the joined text.
- The counters are ADR-0019's and no others: cgroup v2 `usage_usec` for the query Ollama container,
  the backend's process CPU clock (`clock_getcpuclockid`, so exited threads count), the harness
  thread clock for rerank. No per-call value is read from `/proc/<pid>/stat`. `backend_host_pid`
  matches `NSpid` only among the Postgres cgroup's processes and needs exactly one match.
  `executed_ticks` is `user + nice + system + irq + softirq`, never adding `guest`.
- `check_resolution` takes two back-to-back reads while the caller keeps the target busy, and
  needs `0 < diff < 10 µs`.
- `classify` counts only successful creations, joins strace's split `unfinished`/`resumed` lines,
  and raises on a creation it cannot parse. `check_clock`: with no creations, the process clock and
  `schedstat` agree within 10 µs per call; with threads only, the process clock is at least
  `schedstat`; any child process is a `CounterError`.
- `cases()` is two sizes (`real`, `60k`) by three levels (1, 10, 100), warm and cold. `run_case`
  resets before a cold case and then connects afresh, so no pid or attachment crosses a reset.
  `Result.thread_names` keeps names only for threads strace saw created; a thread that exited before
  its name was read is still counted.
- The calibration runs 60 s of background, then calls until their summed CPU reaches 30 s, then
  60 s of background. The reference is the block's executed CPU minus the mean background rate
  times its elapsed time, minus the harness's process CPU except on `rerank`. The noise gate fails
  when `|b_after - b_before|` times the elapsed time exceeds 1% of the reference, and the check fails
  when the per-call sum is outside 95% to 105% of it, both bounds inclusive. `iowait` and `steal` are reported, never added.
- `cold_sample` orders by SHA-256 of `group_id`, then by issue number. It takes the first issue of
  each of the first 50 distinct groups, whatever order the input is in.

## What this module will never do

- Write a dataset or a manifest, or reimplement ADR-0016's universe steps.
- Fetch from the network in `s2.inputs`. Only `s2.fetch_issues` does, with `GET
  /repos/{owner}/{repo}/issues/{number}` (Amendment 1 §4), and it never writes inside a git checkout
  or records the token.
- Produce evidence off the A1. S2-dev's numbers are never evidence (ADR-0019).

## Failure modes the caller must handle

| Condition | What the caller sees | What the caller should do |
|---|---|---|
| A window count differs from the manifest | `count_problems` returns one line per repository | Refuse to run S2 (Amendment 1 §1) |
| A counter is missing, unreadable, coarser than 10 µs or not cgroup v2; a backend pid matches 0 or 2+ host pids | `CounterError` | S2 stops as an error (ADR-0019) |
| The backend's clocks disagree, or it creates a child process | `CounterError` from `check_clock` | S2 stops as an error |
| The calibration's background moves more than 1%, its per-call sum is outside 95% to 105% of the reference, a call reports no CPU, `/proc/stat` goes backwards, or the kernel config sets other than one accounting option | `CounterError` from `s2.calibration` | S2 stops as an error (ADR-0019) |
| strace output has a creation that cannot be parsed, or a call that never resumes | `ValueError` from `classify` | Treat as an error; never assume none |
| An issue is in two groups | `ValueError` from `strong_dev_issues` | Refuse the dataset |
| An issue fetch is not a 200, or returns a pull request | `RuntimeError` naming `owner/repo#n` | Stop; a partial query set changes what S2 measures |
| `--out` is inside a git checkout, judged at its nearest existing ancestor | exit status 2, nothing fetched | Choose a path outside git |
| A git object is missing or unreadable | `subprocess.CalledProcessError` or `AssertionError` from `snapshot` | Stop; never run on a partial corpus |

## Data owned

None in Postgres. No committed files. The fetched issue file lives outside git, by design.

## Tests that pin this contract

| Test | Pins |
|---|---|
| `eval/harness/tests/test_s2_inputs.py::test_windows_are_60_line_cuts_with_a_shorter_last_window` | Window boundaries, first lines, a file with no final newline, an empty file, the universe's drops |
| `…::test_the_window_count_is_eval_datas_own_chunk_estimate`, `…::test_line_split_matches_universe_lines` | Agreement with `s1.repo.measure` and `s1.universe.lines` |
| `…::test_count_problems_refuses_any_difference_from_the_manifest`, `…::test_the_committed_manifest_estimates_sum_to_7175` | Amendment 1 §1's refusal, and the corpus size |
| `…::test_pseudo_repo_is_amendment_1s_exact_hash`, `…::test_a_files_windows_share_one_pseudo_repo`, `…::test_grant_levels_are_0_then_0_to_9_then_0_to_99` | Amendment 1 §3 |
| `…::test_the_strong_dev_query_set_is_874_issues`, `…::test_weak_and_non_dev_pairs_are_excluded_and_a_split_group_is_refused` | Amendment 1 §4's set |
| `…::test_normalization_is_nfc_and_trailing_whitespace_only`, `…::test_queries_above_2000_characters_are_rejected`, `…::test_the_cold_sample_is_the_first_of_each_of_the_first_50_groups` | Normalization, rejection and the cold sample |
| `…::test_the_query_joins_title_and_body_as_ruled_then_normalizes_once` | gupta958's join ruling (whitespace-only bodies count as empty) and one normalization |
| `eval/harness/tests/test_s2_fetch_issues.py` (all seven tests) | The pinned endpoint, stop on any non-200 or pull request, names from the manifest, the meta file, refusal inside git, including a missing subdirectory of a checkout from outside it |
| `eval/harness/tests/test_s2_counters.py` | cgroup lookup and `usage_usec`, `NSpid` matching inside the cgroup only, `schedstat`, executed CPU, the resolution and v2 checks; on Linux, the real process clock counting an exited thread, real resolution, an unknown pid |
| `eval/harness/tests/test_s2_preflight.py` | The strace command, classification (none, threads incl. split lines and failures, every child form, fail-closed parsing), the clock rules, the 12 cases, no pid crossing a cold reset, and thread names |
| `eval/harness/tests/test_s2_calibration.py` | The 30 s block, agreement within boundary ticks, harness CPU subtracted except on rerank, the inclusive 95% and 105% bounds and values just outside both, the 1% noise gate, `iowait` and `steal` reported only, a counter that does not count, no work, `/proc/stat` going backwards, the run order, and the accounting option |

## Fake

None. Only S2's own parts call this module. A fake is required before any other module builds
against it (`AGENTS.md` §3.4).

## Open questions

- The experiment runner's interface (`eval/harness/interface.py`) is still to be written.

## Change log

| Date | Change | BCR |
|---|---|---|
| 2026-09-18 | Placeholder created alongside the framework | — |
| 2026-11-03 | First contract: S2's corpus windows and pseudo-repositories (ADR-0019 Amendment 1 §1, §3). The query set (§4) follows in the next part | — |
| 2026-11-03 | Amendment 1 §4: the query set, `query` with gupta958's join ruling, and `s2.fetch_issues` | — |
| 2026-11-03 | ADR-0019's counters and counter checks (`s2.counters`). The backend thread preflight follows in the next part | — |
| 2026-11-03 | The backend thread preflight (`s2.preflight`) | — |
