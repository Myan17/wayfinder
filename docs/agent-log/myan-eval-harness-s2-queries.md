# Task log — myan-eval-harness-s2-queries

| Field | Value |
|---|---|
| Task | S2 harness part 2: Amendment 1 §4's query set, normalization, rejection, cold sample, and the REST issue fetch (ORIENT item 7) |
| Module | eval-harness |
| Branch | `myan/eval-harness/s2-queries` |
| Worktree | `../wayfinder-wt/myan-eval-harness-s2-queries` |
| Operator | myan |
| Agent | claude-code/opus-5.5 |
| Session | 2026-11-03T15:12Z/17252 |
| Started | 2026-11-03T15:12:28Z |
| Closed when | the last entry says TASK CLOSED (the header is never edited - this file is append-only) |

**Append-only.** Corrections are new entries. Entries are written by `scripts/log.sh` and the
`post-commit` hook; CI rejects a rewritten log (`scripts/check_agent_log.py`).

## Cards read

- (listed by `new-task.sh`; add any you read later as `READ` entries)

## Timeline

### 2026-11-03T15:12:40Z · READ · myan · claude-code/opus-5.5 · d99ad47
docs/context/modules/eval-harness.md; docs/context/modules/eval-data.md (pairs.jsonl fields, manifest 'selected' holds repository ids only); ADR-0019 Amendment 1 §4; DESIGN §9.4.2, §9.5 step 1, §14.2 step 4.

### 2026-11-03T15:12:40Z · DECIDE · myan · claude-code/opus-5.5 · d99ad47
Ruling from gupta958 (relayed by myan, 2026-11-03): 'S2 part 2: accepted. Use the title alone when the body is missing or empty; otherwise use title + two LF characters + body. Apply DESIGN §9.4.2 normalization once to the completed query.'

### 2026-11-03T15:12:40Z · PLAN · myan · claude-code/opus-5.5 · d99ad47
Restore #97's split-out §4 functions (strong_dev_issues, query_text, normalize, accepted, cold_sample) from the previous session's scratchpad copy, add query(title, body) = normalize(query_text(...)) so normalization runs once on the joined text, and add s2/fetch_issues.py: resolves each repository id to owner/name with GET /repositories/{id}, then GET /repos/{owner}/{repo}/issues/{number} as §4 pins, writes JSONL outside git plus a meta file with SHA-256, fetch time and count. Transport injectable so tests use a fake; no network in tests. Record the ruling in ADR-0019 Amendment 1's review rulings (Scope: eval-harness, agreements). Rejected: calling /repositories/{id}/issues/{n} directly, because §4 names the owner/repo endpoint.

### 2026-11-03T15:12:59Z · PLAN · myan · claude-code/opus-5.5 · d99ad47
Correction to the plan above: the manifest's candidates carry 'repo' as owner/name beside github_repo_id, so the fetch reads names from the manifest and makes no /repositories/{id} call. GitHub answers a renamed repository's old path with a redirect, which urllib follows.

### 2026-11-03T15:15:06Z · EDIT · myan · claude-code/opus-5.5 · d99ad47
eval/harness/s2/inputs.py: §4 restored from #97's split (strong_dev_issues, Issue, query_text, normalize, accepted, cold_sample) plus query(); query_text's docstring cites the ruling. eval/harness/s2/fetch_issues.py (new): the REST fetch. eval/harness/tests/test_s2_inputs.py: §4 tests plus the join-ruling test; eval/harness/tests/test_s2_fetch_issues.py (new). docs/context/modules/eval-harness.md: §4 interface, invariants, failure modes, tests, the open question removed, change-log row, hash via check_context_freshness --fix. docs/adr/ADR-0019-s2-cpu-measurement.md: Amendment 1 §4 states the join and the single normalization, and the later ruling is recorded.

### 2026-11-03T15:15:06Z · TEST · myan · claude-code/opus-5.5 · d99ad47
uv run pytest eval/harness/tests → 22 passed; uv run pytest → 410 passed, 25 skipped; ruff check and ruff format --check on eval/harness clean; check_context_freshness → OK. No network call in any test: fetch tests use a fake transport, and the inside-git refusal test asserts no request is sent.

### 2026-11-03T15:15:06Z · COMMIT · myan · claude-code/opus-5.5 · parent:d99ad47
feat(eval-harness): S2 harness part 2 — the strong-dev query set, the ruled title/body join, and the REST issue fetch (ADR-0019 Amendment 1 §4)
7 files changed, 379 insertions(+), 8 deletions(-)
