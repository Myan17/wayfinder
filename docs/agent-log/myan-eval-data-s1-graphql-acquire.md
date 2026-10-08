# Task log — myan-eval-data-s1-graphql-acquire

| Field | Value |
|---|---|
| Task | S1 acquisition, GitHub API half: linkable pairs, PR first commits, merge and issue times, license cross-check, call tally (ORIENT item 5) |
| Module | eval-data |
| Branch | `myan/eval-data/s1-graphql-acquire` |
| Worktree | `../wayfinder-wt/myan-eval-data-s1-graphql-acquire` |
| Operator | myan |
| Agent | claude-code/opus-5.5 |
| Session | 2026-10-08T05:03Z/16928 |
| Started | 2026-10-08T05:03:06Z |
| Closed when | the last entry says TASK CLOSED (the header is never edited - this file is append-only) |

**Append-only.** Corrections are new entries. Entries are written by `scripts/log.sh` and the
`post-commit` hook; CI rejects a rewritten log (`scripts/check_agent_log.py`).

## Cards read

- (listed by `new-task.sh`; add any you read later as `READ` entries)

## Timeline

### 2026-10-08T05:03:36Z · PLAN · myan · human · 826c674
New s1/github.py: a GraphQL client over urllib (no new dependency) with an injectable transport, so tests replay recorded responses and CI makes no network call. It (1) checks S1-5 from X-OAuth-Scopes: the header must be present and empty (Myan, 2026-10-08: a no-scope classic PAT), (2) reads repository metadata (databaseId, default branch, licenseInfo.spdxId), (3) pages every merged PR and keeps those merged before as_of with closingIssuesReferences to same-repository issues, yielding (issue, pr, first commit, head oid, mergedAt, issue updatedAt), and (4) tallies GraphQL and REST calls. Rejected: the search API with merged:<as_of, which caps at 1,000 results and would undercount S1-2 on large candidates. The clone-side license read and the S1-1 comparison go in the same module if the PR stays under 400 lines, else a follow-up.

### 2026-10-08T05:06:49Z · TEST · myan · claude-code/opus-5.5 · 826c674
PYTHONDONTWRITEBYTECODE=1 uv run --extra dev pytest → 251 passed (eval/miners/tests 86, test_s1_github 6). Mutation check on s1/github.py, 9 mutants (as-of boundary, scope check, same-repo filter, closing-reference truncation, cursor, issue order, status check, tally, skip of PRs closing nothing): all 9 killed; the last one only after PR 11's fixture listed no commits. ruff check and ruff format --check clean on both new files. Live smoke check, not S1 evidence: the gh token (scopes gist, read:org, repo, workflow) is refused with 'S1-5: token has scopes: …'; PRS_QUERY returns 200 without errors against pallets/click, 22 GraphQL calls.

### 2026-10-08T05:06:49Z · DECIDE · myan · claude-code/opus-5.5 · 826c674
S1-5's token (Myan, 2026-10-08): the S1 run uses a classic PAT with no scopes, so S1-5 is measured from X-OAuth-Scopes on every response rather than assumed. A fine-grained token sends no such header and is refused. The clone-side license read for S1-1's cross-check is split into the next PR, to keep this one reviewable and because how a license file maps to an SPDX id is its own decision.

### 2026-10-08T05:06:50Z · COMMIT · myan · claude-code/opus-5.5 · parent:826c674
feat(eval-data): S1 acquisition, API side — linkable pairs, S1-5 token check, call tally
4 files changed, 306 insertions(+), 1 deletion(-)
