# Task log — myan-platform-readme

| Field | Value |
|---|---|
| Task | Rewrite README: what Wayfinder answers, its three design properties, architecture, current status by phase, what is built and proven, layout and workflow (directed by myan 2026-10-04) |
| Module | platform |
| Branch | `myan/platform/readme` |
| Worktree | `../wayfinder-wt/myan-platform-readme` |
| Operator | myan |
| Agent | claude-code/opus-5.5 |
| Session | 2026-10-05T03:44Z/9d28c1f |
| Started | 2026-10-05T03:44:35Z |
| Closed when | the last entry says TASK CLOSED (the header is never edited - this file is append-only) |

**Append-only.** Corrections are new entries. Entries are written by `scripts/log.sh` and the
`post-commit` hook; CI rejects a rewritten log (`scripts/check_agent_log.py`).

## Cards read

- (listed by `new-task.sh`; add any you read later as `READ` entries)

## Timeline

### 2026-10-05T03:44:35Z · DECIDE · myan · claude-code/opus-5.5 · 9d28c1f
Off the ORIENT list under rule 2, directed by myan on 2026-10-04: 'before you get done for today's part can you make a good readme.md and add it to github'.

### 2026-10-05T03:44:35Z · PLAN · myan · claude-code/opus-5.5 · 9d28c1f
Rewrite README.md from DESIGN section 1 (locate and explain, v1 scope, the three properties), section 8.1 (read path, write path, Postgres), section 19.1 (phases at v0.3.3), ORIENT (P0 status) and the merged PRs (schema v1, authz kernel pieces, S5 River proof, S1 miner). It keeps the existing evidence caveat, workflow commands and the People section as written. Facts only, each tied to a document or PR, and nothing claimed as proven unless an ADR records it. Rejected: copying DESIGN's mermaid diagram, which would duplicate a section that changes by revision.

### 2026-10-05T03:45:45Z · TEST · myan · claude-code/opus-5.5 · 9d28c1f
Docs only. Every path and document the README links or names exists (ORIENT.md, DESIGN, AGENTS, docs/adr, WORKING-AGREEMENT, OWNERSHIP, INDEX, codemap.py, db/migrations, authz, eval/miners/s1); make help exists. The layout block was checked against the tree, and its first draft overstated infra/ and apps/ingestd/, so it now says what exists. Phase dates match DESIGN 0.3.3 section 19.1.

### 2026-10-05T03:45:45Z · COMMIT · myan · claude-code/opus-5.5 · parent:9d28c1f
docs(platform): README says what Wayfinder answers, where it stands and how to work on it
2 files changed, 133 insertions(+), 13 deletions(-)
