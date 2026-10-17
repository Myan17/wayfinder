# Task log — myan-agreements-size-manifest-exemption

| Field | Value |
|---|---|
| Task | Exempt eval/datasets/s1/manifest.json from the size limit by exact path (reviewer ruling, ORIENT item 5) |
| Module | agreements |
| Branch | `myan/agreements/size-manifest-exemption` |
| Worktree | `../wayfinder-wt/myan-agreements-size-manifest-exemption` |
| Operator | myan |
| Agent | claude-code/opus-5.5 |
| Session | 2026-10-17T18:33Z/17612 |
| Started | 2026-10-17T18:33:52Z |
| Closed when | the last entry says TASK CLOSED (the header is never edited - this file is append-only) |

**Append-only.** Corrections are new entries. Entries are written by `scripts/log.sh` and the
`post-commit` hook; CI rejects a rewritten log (`scripts/check_agent_log.py`).

## Cards read

- (listed by `new-task.sh`; add any you read later as `READ` entries)

## Timeline

### 2026-10-17T18:34:04Z · DECIDE · myan · claude-code/opus-5.5 · af7685e
Owner direction (reviewer ruling relayed by myan in session, 2026-10-17): 'Add eval/datasets/s1/manifest.json as the fourth exact-path size exemption, in a separate agreements PR that merges before the results PR. The exemption must use exact string equality; lookalikes and renames must continue to count. Update the size-check tests and agreements wording accordingly. Do not include manifest.json in that exemption PR.' AGENTS.md is human-owned: myan makes that edit from wording supplied in session.

### 2026-10-17T18:34:04Z · PLAN · myan · claude-code/opus-5.5 · af7685e
check_pr_size.py: add S1_MANIFEST to exempt_paths (frozenset, string equality, unchanged mechanism); docstring gains exception 4. Tests: exact-path exemption, lookalike parametrize (manifest.json.bak, s2/, ./ prefix, {old => manifest.json}, Manifest.json, nested), end-to-end --no-renames rename onto the manifest path still counts the delete. Rejected: a glob over eval/datasets/s1/* (would exempt any future file there).

### 2026-10-17T18:35:31Z · TEST · myan · claude-code/opus-5.5 · af7685e
uv run --extra dev pytest scripts/tests -> 105 passed (test_check_pr_size: 37). ruff check on both changed files clean (main already has 21 ruff findings elsewhere, untouched). Mutants on check_pr_size.py, all killed: manifest dropped from exempt_paths (2 failed), endswith('manifest.json') match (4), leading './' stripped before lookup (3), --no-renames removed (2).

### 2026-10-17T18:35:32Z · COMMIT · myan · claude-code/opus-5.5 · parent:af7685e
chore(agreements): exempt eval/datasets/s1/manifest.json from the size limit by exact path
3 files changed, 98 insertions(+), 7 deletions(-)

### 2026-10-17T20:27:40Z · COMMIT · myan · human · parent:c2c94cc
docs(agreements): AGENTS.md §2.2 lists the S1 manifest as the fourth exact-path size exemption
1 file changed, 11 insertions(+), 2 deletions(-)
