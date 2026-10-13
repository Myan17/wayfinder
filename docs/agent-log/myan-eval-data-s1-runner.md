# Task log — myan-eval-data-s1-runner

| Field | Value |
|---|---|
| Task | S1 runner: measure the ten candidates, select the corpus, write pairs.jsonl and manifest.json (ORIENT item 5) |
| Module | eval-data |
| Branch | `myan/eval-data/s1-runner` |
| Worktree | `../wayfinder-wt/myan-eval-data-s1-runner` |
| Operator | myan |
| Agent | claude-code/opus-5.5 |
| Session | 2026-10-13T05:21Z/2e86468 |
| Started | 2026-10-13T05:21:28Z |
| Closed when | the last entry says TASK CLOSED (the header is never edited - this file is append-only) |

**Append-only.** Corrections are new entries. Entries are written by `scripts/log.sh` and the
`post-commit` hook; CI rejects a rewritten log (`scripts/check_agent_log.py`).

## Cards read

- (listed by `new-task.sh`; add any you read later as `READ` entries)

## Timeline

### 2026-10-13T05:21:46Z · DECIDE · myan · claude-code/opus-5.5 · 9552da2
Stacked on myan/eval-data/s1-license (#63, not yet merged) because the runner calls license.file_spdx and s1_1. Myan, 2026-10-13: "continue building wayfinder ... decide what you can finish in one hour according to the plan or things that do not need my approval". The runner is HANDOFF step (3) of that task; the PR stays draft and is not merged before #63.

### 2026-10-13T05:21:46Z · PLAN · myan · claude-code/opus-5.5 · 9552da2
New s1/run.py. measure(client, slug, lang, workdir, as_of): github.repo, repo.mirror into a temporary directory removed after the run, as_of_commit on the default branch, license.file_spdx plus s1_1 (S1-1), github.linked_pairs (S1-2, pass at >= 100), repo.resolve per pair (S1-3, pass at >= 95% of bases resolving, merge-excluded pairs count as resolved), repo.measure (S1-4, >= 5 .md files and >= 2,000 words), S1-5 pass when every read went through Client (a scoped token raises before anything is recorded); for each resolved, non-merge pair, repo.changed then pairs.gold_files once per PR. The rest is pure and testable without network: survivors(measured, max_files) applies pairs.keep and counts D-6 reasons; rounds() runs select.best at max_files 10 and, only when a winner exists with fewer than 300 strong pairs, again at 15 (R-03 step 2; step 1, widening, needs a new PR so the runner stops and says so); build() runs split.assign over the winner pairs (weak included), writes pairs.jsonl in (github_repo_id, pr, issue) order and the manifest, and refuses to write when s1.dataset.problems or the manifest schema finds anything. The token comes from WAYFINDER_S1_TOKEN and is never printed. Rejected: one script that does network and selection together (the selection and file format could then only be tested by a live run).

### 2026-10-13T05:27:41Z · DECIDE · myan · claude-code/opus-5.5 · 9552da2
Split by function to stay under the 400-line limit (497 counted lines as one file plus tests). This branch carries s1/corpus.py, the pure half (survivors, rounds, build) and its tests. The network half, s1/run.py (measure and main), follows as its own task stacked on this one.

### 2026-10-13T05:27:41Z · TEST · myan · claude-code/opus-5.5 · 9552da2
PYTHONDONTWRITEBYTECODE=1 uv run --extra dev pytest -> 270 passed (test_s1_corpus 7). Mutation check on s1/corpus.py, 15 mutants: merge-reason classification, unresolved test, max_files passed to keep, all vs any rule, the A-3 boundary (>= vs >, test at exactly 300), the second round at 15, the single-round condition, weak_count, strong-only survivors, the winner filter, selected and max_files from the final round, the canonical sort key, exclusions dropped, exclusions accumulated. 14 killed; the survivor replaced done[0]["winner"] in a conjunct that still requires final["winner"] membership, so it is equivalent. Two tests were added during the check: the winner changing between rounds, and a pair sorted differently by (pr, issue) than by (issue, pr). The check also found a real bug before commit: select.best returns tuples, which the manifest schema rejects as arrays. ruff check and ruff format --check clean on the new files.

### 2026-10-13T05:27:55Z · COMMIT · myan · claude-code/opus-5.5 · parent:9552da2
feat(eval-data): S1 corpus from measured candidates — survivors, selection rounds, the dataset
4 files changed, 332 insertions(+), 2 deletions(-)

### 2026-10-13T05:29:16Z · HANDOFF · myan · claude-code/opus-5.5 · 1386020
Paused for gupta958's review (s1/corpus.py, code at 1386020), stacked on #63. Next, in order: (1) #63 merges, then rebase this branch onto main with rebase -X theirs and force-push with a lease, retarget the PR to main (close and reopen to re-run guardrails), refresh the body; (2) this PR merges; (3) myan/eval-data/s1-measure (s1/run.py) rebases the same way; (4) after it merges, Myan runs WAYFINDER_S1_TOKEN=<no-scope classic PAT> uv run --extra dev python -m s1.run from eval/miners on a clean checkout of main, then python -m s1.dataset eval/datasets/s1/pairs.jsonl eval/datasets/s1/manifest.json; (5) the results PR: the two files, the ADR-0016 Decision (every selection round, A-3 at 300 strong pairs), ORIENT item 5 done. Test: PYTHONDONTWRITEBYTECODE=1 uv run --extra dev pytest; guardrails with B=<parent branch head> while stacked, GITHUB_HEAD_REF set for check_ownership.

### 2026-10-13T05:29:16Z · COMMIT · myan · claude-code/opus-5.5 · parent:1386020
docs(agents): handoff for the S1 corpus review pause
1 file changed, 3 insertions(+)

### 2026-10-13T17:06:25Z · DECIDE · myan · claude-code/opus-5.5 · b058911
Review from gupta958, relayed by Myan on 2026-10-13: "#65: Do not approve yet. It incorrectly runs R-03 step 2 immediately when the original corpus is short. ADR-0016 requires candidate widening first. D-6 exclusions should cover all measured candidates, not only the selected repositories. The proposed exclusion-key wording is acceptable." Fix: rounds and build take widened (default False). On the original candidates, a short winner is one round at 10 and stops there. Only a run over a widened list (step 1: a merged PR that names the new candidates before they are measured) that is still short runs step 2 at 15. The caller states widened explicitly; corpus does not infer it. build now counts D-6 exclusions over every measured candidate at the final max_files, while only the winner's pairs land.

### 2026-10-13T17:06:25Z · TEST · myan · claude-code/opus-5.5 · b058911
PYTHONDONTWRITEBYTECODE=1 uv run --extra dev pytest gives 275 passed. The R-03 test now covers three cases: the original list short (one round at 10), the widened list short (10 then 15), and the widened list meeting the bar (one round). The build test adds a D-2 exclusion in the unqualified candidate and expects it in exclusions. Mutation check used 5 mutants: the widened guard removed, widened not passed to rounds, exclusions counted only for winners, winner pairs dropped, and the A-3 boundary. All 5 were killed. ruff is clean.

### 2026-10-13T17:06:26Z · COMMIT · myan · claude-code/opus-5.5 · parent:b058911
fix(eval-data): R-03 widens before relaxing D-2; D-6 counts every candidate
4 files changed, 35 insertions(+), 20 deletions(-)
