# Task log — myan-agreements-adr-0019-s2-inputs

| Field | Value |
|---|---|
| Task | ADR-0019 Amendment 1: pin S2's corpus, queries, selectivity and dev host before the harness (ORIENT item 7) |
| Module | agreements |
| Branch | `myan/agreements/adr-0019-s2-inputs` |
| Worktree | `../wayfinder-wt/myan-agreements-adr-0019-s2-inputs` |
| Operator | myan |
| Agent | claude-code/opus-5.5 |
| Session | 2026-10-22T04:32Z/17251 |
| Started | 2026-10-22T17:48:01Z |
| Closed when | the last entry says TASK CLOSED (the header is never edited - this file is append-only) |

**Append-only.** Corrections are new entries. Entries are written by `scripts/log.sh` and the
`post-commit` hook; CI rejects a rewritten log (`scripts/check_agent_log.py`).

## Cards read

- (listed by `new-task.sh`; add any you read later as `READ` entries)

## Timeline

### 2026-10-22T17:49:26Z · PLAN · myan · claude-code/opus-5.5 · dcd7bea
ORIENT item 7 (S2), ADR-0019 step 3 needs inputs ADR-0019 does not pin: no chunker exists (P1 item 5), issue text is not in the dataset, four repositories cannot express 1% selectivity, the dev/strong query set is unstated, and a Mac cannot read a container's cgroup or a host pid's CPU clock. Pin them in Amendment 1 before any harness code, as ADR-0007 Amendment 1 did for S3-6. Rejected: choosing them inside the harness PR, which is the post-hoc choice ADR-0019 exists to prevent.

### 2026-10-22T17:49:26Z · READ · myan · claude-code/opus-5.5 · dcd7bea
ADR-0019 in full; ADR-0016 Decision (7,175 = ceil(lines/60) estimate); eval/miners/s1/universe.py; pairs.jsonl (dev: 1,155 issues, 874 strong); DESIGN §14.2, §9.4.2, §191 (1/10/100% visibility); ADR-0013 D-3

### 2026-10-22T17:49:26Z · EDIT · myan · claude-code/opus-5.5 · dcd7bea
ADR-0019 Amendment 1: (1) 60-line windows over ADR-0016's universe at as-of commits, checked against chunk_estimate; (2) real nomic vectors via the ingestion container; (3) 100 pseudo-repositories by sha256(repo_id/path) mod 100; (4) strong dev issues (874), text fetched once outside git, >2,000 chars rejected, cold sample by sha256(group_id); (5) S2-dev on CI's Ubuntu runner, never a Mac. Order-of-work step 3 points at it.

### 2026-10-22T17:49:27Z · COMMIT · myan · claude-code/opus-5.5 · parent:dcd7bea
docs(agreements): ADR-0019 Amendment 1 — S2's corpus, vectors, selectivity, queries and dev host, before the harness
2 files changed, 109 insertions(+), 1 deletion(-)

### 2026-10-22T17:49:27Z · TEST · myan · claude-code/opus-5.5 · bf9a795
Docs only. Counts verified from pairs.jsonl (874 strong dev issues); universe.lines and chunks() read. Guardrails run before push.

### 2026-10-22T17:49:27Z · HANDOFF · myan · claude-code/opus-5.5 · bf9a795
Amendment 1 for gupta958's review. No harness code until it merges.

### 2026-10-22T17:49:27Z · COMMIT · myan · claude-code/opus-5.5 · parent:bf9a795
docs(agreements): ADR-0019 Amendment 1 task log
1 file changed, 6 insertions(+)

### 2026-10-22T18:35:43Z · DECIDE · myan · claude-code/opus-5.5 · f8956ed
gupta958's rulings on #94, applied verbatim in substance: (1) 60-line stand-in accepted, with a required full rerun of S2's SQL, rerank and indexing measurements once P1's chunker lands, values labelled 'measured on 60-line windows' until then; (2) pseudo-repository hash input is UTF-8, formula spelled out with .encode('utf-8').hexdigest(); (3) strong dev issues only, unchanged; (4) S2 CI job runs in full only on changes to the harness, retrieval query, database inputs, dependencies, model pins or its workflow, no-ops successfully otherwise, caches keyed by pinned digest and always verified. Rulings recorded in the ADR.

### 2026-10-22T18:35:43Z · EDIT · myan · claude-code/opus-5.5 · f8956ed
ADR-0019 Amendment 1: rerun paragraph in section 1, UTF-8 hash in section 3, CI path-gated job in section 5, 'Review rulings on Amendment 1' block; the scope sentence now names the one added obligation.

### 2026-10-22T18:35:43Z · COMMIT · myan · claude-code/opus-5.5 · parent:f8956ed
docs(agreements): ADR-0019 Amendment 1 — apply gupta958's rulings on #94
2 files changed, 55 insertions(+), 12 deletions(-)
