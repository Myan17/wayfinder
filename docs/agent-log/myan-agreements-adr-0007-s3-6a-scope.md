# Task log — myan-agreements-adr-0007-s3-6a-scope

| Field | Value |
|---|---|
| Task | ADR-0007 Amendment 2: S3-6a judges the lexical leg only (gupta958's ruling on #90) |
| Module | agreements |
| Branch | `myan/agreements/adr-0007-s3-6a-scope` |
| Worktree | `../wayfinder-wt/myan-agreements-adr-0007-s3-6a-scope` |
| Operator | myan |
| Agent | claude-code/opus-5.5 |
| Session | 2026-10-22T04:32Z/17251 |
| Started | 2026-10-22T04:56:37Z |
| Closed when | the last entry says TASK CLOSED (the header is never edited - this file is append-only) |

**Append-only.** Corrections are new entries. Entries are written by `scripts/log.sh` and the
`post-commit` hook; CI rejects a rewritten log (`scripts/check_agent_log.py`).

## Cards read

- (listed by `new-task.sh`; add any you read later as `READ` entries)

## Timeline

### 2026-10-22T04:57:05Z · READ · myan · claude-code/opus-5.5 · 6bf7cc5
gupta958's rulings on #90 (relayed by Myan): S3-6a applies only to the lexical leg, by an ADR-0007 amendment before the harness changes; S3-6b stays exactly as written, with no threshold after seeing the plans, and its small-scan failures are raised at G0; CI pins the full observed scan outcome of all six 7,175 cases; 60,000 stays local; harness location, the stand-in reuse and the parameter rewrite are accepted. Do not merge #90 until these are pushed.

### 2026-10-22T04:57:05Z · PLAN · myan · claude-code/opus-5.5 · 6bf7cc5
Amendment 2 in ADR-0007, stated as written after the plans were seen. It defines the lexical leg's subtree structurally (Subquery Scan aliased lexical, or the CTE lexical subplan; fails closed if absent), so the harness cannot choose which nodes count. The S3-6a row in Amendment 1's table points at it. S3-6b and the query are unchanged, and the CI matrix pin and the 60,000 local-only ruling are recorded. Rejected: rewriting Amendment 1's text in place, because that would hide that the rule moved after a measurement.

### 2026-10-22T04:57:05Z · TEST · myan · claude-code/opus-5.5 · 6bf7cc5
Docs only. Checked that the amendment's subtree definition matches a real 7,175 generic plan: the lexical leg is 'Subquery Scan on lexical' and holds the ParadeDB Custom Scan rep_1; the Seq Scan rep_2 sits under dense_0_ranked, outside it.

### 2026-10-22T04:57:06Z · COMMIT · myan · claude-code/opus-5.5 · parent:6bf7cc5
docs(agreements): ADR-0007 Amendment 2 — S3-6a judges the lexical leg only (gupta958's ruling on #90)
2 files changed, 72 insertions(+), 1 deletion(-)
