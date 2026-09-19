# Task log — <TASK>

| Field | Value |
|---|---|
| Task | <DESC> |
| Module | <MODULE> |
| Branch | `<BRANCH>` |
| Worktree | `<WORKTREE>` |
| Operator | <OPERATOR> |
| Agent | <AGENT> |
| Session | <SESSION> |
| Started | <STARTED> |
| Closed when | the last entry says TASK CLOSED (the header is never edited - this file is append-only) |

**Append-only.** Corrections are new entries. Entries are written by `scripts/log.sh` and the
`post-commit` hook; CI rejects a rewritten log (`scripts/check_agent_log.py`).

## Cards read

- (listed by `new-task.sh`; add any you read later as `READ` entries)

## Timeline
