# Task log — myan-eval-data-s1-d3-probe

| Field | Value |
|---|---|
| Task | Read-only D-3 diagnostic: closedAt and updatedAt against mergedAt for 48 sampled S1 pairs (ORIENT item 5) |
| Module | eval-data |
| Branch | `myan/eval-data/s1-d3-probe` |
| Worktree | `../wayfinder-wt/myan-eval-data-s1-d3-probe` |
| Operator | myan |
| Agent | claude-code/opus-5.5 |
| Session | 2026-10-17T23:51Z/32321 |
| Started | 2026-10-17T23:51:19Z |
| Closed when | the last entry says TASK CLOSED (the header is never edited - this file is append-only) |

**Append-only.** Corrections are new entries. Entries are written by `scripts/log.sh` and the
`post-commit` hook; CI rejects a rewritten log (`scripts/check_agent_log.py`).

## Cards read

- (listed by `new-task.sh`; add any you read later as `READ` entries)

## Timeline

### 2026-10-17T23:51:30Z · DECIDE · myan · claude-code/opus-5.5 · bf0e8e2
Owner direction (gupta958's ruling relayed by myan, 2026-10-17): 'investigate D-3 before accepting the S1 corpus ... Run a bounded, read-only diagnostic—this is not an S1 rerun': three weak pairs and one strong control per repository x split cell, picked by the lowest SHA-256 of github_repo_id:issue:pr (48 pairs); query only PR mergedAt, issue closedAt and updatedAt; record no titles or bodies; report closedAt - mergedAt and updatedAt - mergedAt in <=5 s, <=60 s, <=1 h and >1 h buckets, by repository and split, and any strong control now updated after its merge. Put the diagnostic, script and results in a small PR; do not alter D-3 or regenerate the dataset.

### 2026-10-17T23:51:30Z · PLAN · myan · claude-code/opus-5.5 · bf0e8e2
eval/miners/s1/d3_probe.py, pure except main: sample(rows) by the ruling's key; one GraphQL query per repository (4 calls) through s1.github.Client, so S1-5's no-scope token check and the call tally apply; issue and PR numbers go in as aliased integer literals, owner and name as variables; fields are mergedAt, closedAt and updatedAt only. Buckets are disjoint: <=5 s (negative included, and counted separately), (5 s, 60 s], (60 s, 1 h], > 1 h, and 'not closed' for a null closedAt. Writes eval/datasets/s1-d3-probe.json: the pairs file's SHA-256, the query time, the call tally, 48 rows of ids, times and deltas, and the summaries. Myan runs it (it needs WAYFINDER_S1_TOKEN); the results land in this PR. Rejected: reusing linked_pairs (it pages every PR, which is the re-run the ruling excludes).

### 2026-10-17T23:55:20Z · DECIDE · myan · claude-code/opus-5.5 · bf0e8e2
Split by function: the script and its tests alone are about 400 counted lines, so the report JSON (about 100 lines) goes in a follow-up PR with the interpretation. Order unchanged: code first, then evidence.

### 2026-10-17T23:55:20Z · TEST · myan · claude-code/opus-5.5 · bf0e8e2
pytest eval/miners/tests -> 187 passed (test_s1_d3_probe: 14). ruff check eval/miners and format --check clean. On run 3's pairs file (uncommitted, d5ae8d34...) sample() picks 48 distinct pairs, 3 weak + 1 strong in each of the 12 cells. Mutants, all killed: 2 weak per cell (2 failed), key by (issue, pr) not SHA-256 (1), each bucket edge < for <= (1 each), weak_now with >= (1), title added to the query (1), shared PR not deduplicated (1), negative count <= 0 (1, after adding the 0 s assertion; it survived the first version), small-cell guard off (1).

### 2026-10-17T23:55:21Z · COMMIT · myan · claude-code/opus-5.5 · parent:bf0e8e2
feat(eval-data): s1.d3_probe, a read-only diagnostic of D-3 over 48 sampled S1 pairs
4 files changed, 431 insertions(+)

### 2026-10-17T23:55:33Z · HANDOFF · myan · claude-code/opus-5.5 · e9367f2
Ready for gupta958. The probe and its tests, no results. Myan runs it (4 GraphQL calls with WAYFINDER_S1_TOKEN) from this worktree; the report eval/datasets/s1-d3-probe.json and its reading land in a follow-up PR, with an ADR-0013 amendment proposal if the closure accounts for the weak class.

### 2026-10-17T23:55:33Z · COMMIT · myan · claude-code/opus-5.5 · parent:e9367f2
docs(eval-data): record the s1-d3-probe handoff in its task log
1 file changed, 3 insertions(+)

### 2026-10-17T23:55:33Z · HANDOFF · myan · claude-code/opus-5.5 · 9127ee8
TASK CLOSED. Pull request open for review.

### 2026-10-17T23:55:33Z · COMMIT · myan · claude-code/opus-5.5 · parent:9127ee8
docs(agents): close task log for myan-eval-data-s1-d3-probe
1 file changed, 3 insertions(+)
