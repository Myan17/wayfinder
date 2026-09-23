# Task log — myan-schema-snapshot

| Field | Value |
|---|---|
| Task | db/dump-schema.sh and the full generated db/schema.sql (gupta958 ruling, step 3; closes ORIENT item 2) |
| Module | schema |
| Branch | `myan/schema/snapshot` |
| Worktree | `../wayfinder-wt/myan-schema-snapshot` |
| Operator | myan |
| Agent | claude-code/opus-5 |
| Session | 2026-09-23T20:24Z/12692 |
| Started | 2026-09-23T20:24:58Z |
| Closed when | the last entry says TASK CLOSED (the header is never edited - this file is append-only) |

**Append-only.** Corrections are new entries. Entries are written by `scripts/log.sh` and the
`post-commit` hook; CI rejects a rewritten log (`scripts/check_agent_log.py`).

## Cards read

- (listed by `new-task.sh`; add any you read later as `READ` entries)

## Timeline

### 2026-09-23T20:24:58Z · PLAN · myan · claude-code/opus-5 · 71415ef
Step 3 of gupta958's ruling. db/dump-schema.sh: applies every migration's up section to a fresh template0 database inside the pinned ParadeDB container (template0, because the image's template1 pre-installs postgis and friends that are not ours), dumps with the container's own pg_dump 18.6 (client matches server; the local Homebrew pg_dump is 14), strips only the lines that vary run to run (psql 18's \restrict/\unrestrict tokens and the 'Dumped from/by' version comments), and writes db/schema.sql; --check exits 1 on drift. The output is the full canonical dump, not a compacted form. ORIENT item 2 becomes done #25-#30 (Scope: schema, agreements for that line). Opened only after #29 merges, so the exemption this relies on is already on main.

### 2026-09-23T20:25:34Z · EDIT · myan · claude-code/opus-5 · 71415ef
db/dump-schema.sh (new, 41 lines) and db/schema.sql (new, 1,104 lines, generated). ORIENT.md item 2: done #25-#30. Schema card: status names the snapshot and generator; change-log row; db/schema.sql's hash recorded with --fix schema (it is a listed interface file, now present).

### 2026-09-23T20:25:35Z · TEST · myan · claude-code/opus-5 · 71415ef
db/dump-schema.sh -> wrote db/schema.sql (1104 lines); run twice, sha256 302e84b53272e328 both times; --check -> 'db/schema.sql is current'. Contents: 21 CREATE TABLE public.*, 2 views and 5 indexes; only our objects (template0), extensions vector and pg_search. Drift mutation: renaming tombstone in the committed file -> --check exits 1; restored, --check current again. context-freshness OK.

### 2026-09-23T20:25:35Z · COMMIT · myan · claude-code/opus-5 · parent:71415ef
feat(schema): db/schema.sql snapshot and its generator; ORIENT item 2 done
5 files changed, 1177 insertions(+), 4 deletions(-)
