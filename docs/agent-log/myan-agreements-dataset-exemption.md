# Task log — myan-agreements-dataset-exemption

| Field | Value |
|---|---|
| Task | Exact-path size exemption for eval/datasets/s1/pairs.jsonl, before the PR that commits it (ORIENT item 5) |
| Module | agreements |
| Branch | `myan/agreements/dataset-exemption` |
| Worktree | `../wayfinder-wt/myan-agreements-dataset-exemption` |
| Operator | myan |
| Agent | claude-code/opus-5.5 |
| Session | 2026-09-28T23:34Z/24379 |
| Started | 2026-09-28T23:34:35Z |
| Closed when | the last entry says TASK CLOSED (the header is never edited - this file is append-only) |

**Append-only.** Corrections are new entries. Entries are written by `scripts/log.sh` and the
`post-commit` hook; CI rejects a rewritten log (`scripts/check_agent_log.py`).

## Cards read

- (listed by `new-task.sh`; add any you read later as `READ` entries)

## Timeline

### 2026-09-28T23:34:35Z · PLAN · myan · claude-code/opus-5.5 · ccc79cc
gupta958's ruling on #50, relayed by myan on 2026-09-28: option A. The pairs JSONL is committed at one exact canonical path, the exact-path exemption from the line limit lands in a separate earlier PR, and the file requires canonical ordering, schema and JSONL validation, and SHA-256 and count drift checks. This PR adds only the exemption, the way #29 did for db/schema.sql: the exact path eval/datasets/s1/pairs.jsonl, matched by string equality, with look-alike paths still counted. The drift checks are eval-data code and land with the miner. AGENTS.md §2.2 lists the exemptions, and agents may not edit it, so the sentence to add is in the PR for myan to commit.

### 2026-09-28T23:35:08Z · TEST · myan · claude-code/opus-5.5 · ccc79cc
pytest scripts/tests/test_check_pr_size.py: 25 passed (8 new: the exact path is exempt and the manifest still counts; 7 look-alikes count, including a sample/ path, .json, s2/, ./ and a rename string). ruff check clean. ruff format --check was not applied: main's scripts/ is not ruff-formatted (13 of 17 files would change) and CI does not enforce it, so reformatting would bury this change. gupta958's format ruling covers the new files in #50 and #51.

### 2026-09-28T23:35:08Z · COMMIT · myan · claude-code/opus-5.5 · parent:ccc79cc
feat(agreements): exact-path size exemption for the S1 pairs dataset
3 files changed, 57 insertions(+), 2 deletions(-)

### 2026-09-30T20:33:18Z · DECIDE · myan · claude-code/opus-5.5 · 93c68a5
Review of #52 by gupta958: the governing rules still say two exemptions. docs/team/WORKING-AGREEMENT.md's size row now names three exact paths, including eval/datasets/s1/pairs.jsonl and its mechanical review. AGENTS.md §2.2 and §7 need the same change, and agents may not edit AGENTS.md (§1), so the patch is at ~/Downloads/Jobs/Projects/wayfinder-agents-52.patch for myan to apply and commit by hand (Agent: human).

### 2026-09-30T20:33:18Z · COMMIT · myan · claude-code/opus-5.5 · parent:93c68a5
docs(agreements): WORKING-AGREEMENT names the third size exemption
2 files changed, 4 insertions(+), 1 deletion(-)
