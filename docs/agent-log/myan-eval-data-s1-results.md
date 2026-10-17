# Task log — myan-eval-data-s1-results

| Field | Value |
|---|---|
| Task | Commit the S1 dataset and manifest with mechanical manifest checks; ADR-0016 Decision (ORIENT item 5) |
| Module | eval-data |
| Branch | `myan/eval-data/s1-results` |
| Worktree | `../wayfinder-wt/myan-eval-data-s1-results` |
| Operator | myan |
| Agent | claude-code/opus-5.5 |
| Session | 2026-10-17T23:08Z/32134 |
| Started | 2026-10-17T23:08:22Z |
| Closed when | the last entry says TASK CLOSED (the header is never edited - this file is append-only) |

**Append-only.** Corrections are new entries. Entries are written by `scripts/log.sh` and the
`post-commit` hook; CI rejects a rewritten log (`scripts/check_agent_log.py`).

## Cards read

- (listed by `new-task.sh`; add any you read later as `READ` entries)

## Timeline

### 2026-10-17T23:09:27Z · READ · myan · claude-code/opus-5.5 · 023b6ae
S1 run 3 at miner af7685e (main), over ADR-0016's ten plus Amendment 2's ten: 13 of 20 qualify (S1-4 fails flask, requests, pytest, tox, viper; S1-2 fails cobra, chi, bubbletea, viper). One round at D-2 10 files, 645 feasible subsets, winner pydantic, black, httpx, cli/cli (90194616, 125266328, 179492861, 212613049), chunk estimate 6,040. 699 strong (172, 100, 88, 339), 1,507 weak; A-3 bar 300. GraphQL 858, REST 0. python -m s1.dataset on the output exits 0. Manifest exemption merged as #72.

### 2026-10-17T23:09:27Z · PLAN · myan · claude-code/opus-5.5 · 023b6ae
Per gupta958's ruling (2026-10-17): new pure module s1/landing.py with the manifest's mechanical checks, and python -m s1.landing <pairs> <manifest> running them plus s1.dataset's four. Checks: schema; canonical encoding (bytes == json.dumps(indent=2, sort_keys=True)+newline, NaN refused); candidate ids unique; each round's candidate set == sorted candidate ids; each round's feasible list rebuilt independently from recorded pass flags, lang and chunk_estimate (3/4-subsets, py+go, <= 60,000) and compared exactly, or no_feasible_reason == the constraint that fails; winner in feasible; max_files rounds are [10] or [10, 15] and rules.max_files == last; selected == final winner; pairs only from selected repos; splits keyed by exactly the selected ids, with dev/test/held_out equal to the file's per-repo counts. It does NOT recompute the winner (non-selected strong counts are not in the manifest). A test runs it on the committed files. Rejected: reusing select.best for feasibility (the check would share the code it checks).

### 2026-10-17T23:12:39Z · DECIDE · myan · claude-code/opus-5.5 · 023b6ae
Split by function, as #50 did: the checks plus card and the files plus Decision come to more than 400 counted lines. This branch carries s1.landing, its tests and the card (344 counted). A follow-up task commits pairs.jsonl and manifest.json (both exempt), a test that runs s1.landing on them, ADR-0016's Decision and ORIENT item 5's status. The checks land before the files they review.

### 2026-10-17T23:12:39Z · TEST · myan · claude-code/opus-5.5 · 023b6ae
pytest eval/miners/tests -> 170 passed (test_s1_landing: 26); make test -> 348 passed before the committed-dataset test moved out. ruff check and format clean on both new files. python -m s1.landing on run 3's pairs.jsonl and manifest.json (sha256 d5ae8d34..., 1796ef2e...) -> exit 0. Mutants on landing.py, all killed: encoding check off (5 failed), 3-subsets only (3), language mix ignored (3), chunk bound ignored (1), pass flags ignored (2), feasible comparison off (7), winner membership off (1), selected-vs-winner off (2), max_files steps off (2), duplicate ids off (1), split counts off (1), stray repositories off (1), round candidates off (1), unsorted feasible list (3).

### 2026-10-17T23:12:40Z · COMMIT · myan · claude-code/opus-5.5 · parent:023b6ae
feat(eval-data): the S1 manifest's mechanical checks, s1.landing, before the manifest lands
4 files changed, 378 insertions(+)

### 2026-10-17T23:12:50Z · HANDOFF · myan · claude-code/opus-5.5 · 0fc0d02
Ready for gupta958. s1.landing and its tests, and the eval-data card. No dataset files in this PR. After merge: the follow-up task commits pairs.jsonl and manifest.json with a test running s1.landing on them, ADR-0016's Decision (accept with fallback, R-03 step 1) and ORIENT item 5 done.

### 2026-10-17T23:12:50Z · COMMIT · myan · claude-code/opus-5.5 · parent:0fc0d02
docs(eval-data): record the s1-results handoff in its task log
1 file changed, 3 insertions(+)

### 2026-10-17T23:26:15Z · EDIT · myan · claude-code/opus-5.5 · 3f5e494
Review of #73 (gupta958, blocking): landing._feasible used select.MAX_CHUNKS, so a drifted producer bound would be accepted by the check too. landing.py no longer imports s1.select; ADR_MAX_CHUNKS = 60_000 is pinned in landing.py and used in _feasible. Tests: exactly 60,000 across a py/go subset is feasible; 60,001 gives ([], 'chunk bound'); and with s1.select's bound patched to 60,001 (constant and best's default) the producer's manifest is refused. Card guarantee and tests row updated. Dataset untouched, no re-run.

### 2026-10-17T23:26:15Z · TEST · myan · claude-code/opus-5.5 · 3f5e494
pytest eval/miners/tests/test_s1_landing.py -> 29 passed; eval/miners/tests -> 173 passed; make test -> 350 passed (before the last test change; eval/miners re-run after it). ruff check and format --check clean. python -m s1.landing on run 3's files -> exit 0. Mutants, all killed: ADR_MAX_CHUNKS 60_001 (2 failed), 59_999 (1), < for <= (1), reading select.MAX_CHUNKS (1; it survived the first version of the drift test, which patched only best, so the test now patches the constant as well).

### 2026-10-17T23:26:15Z · COMMIT · myan · claude-code/opus-5.5 · parent:3f5e494
fix(eval-data): s1.landing pins ADR-0016's 60,000-chunk bound instead of reading s1.select's
4 files changed, 48 insertions(+), 7 deletions(-)
