# Agent logs

One file per task, named after the branch: `<operator>-<module>-<slug>.md`. Created by
`scripts/new-task.sh`, appended to by `scripts/log.sh` and the `post-commit` hook, checked by CI.

## Why this exists

Three readers, all of whom arrive without your context:

- **the other engineer**, reviewing a change in an area they do not own;
- **your next session**, which starts from the last `HANDOFF` rather than re-deriving the work;
- **the phase gate**, where the weekly digest becomes the report rather than a memory exercise.

## Rules

1. **Append-only.** Corrections are new entries. CI checks every commit on the branch, so a rewrite
   fails the build — and a later "fix-up" commit does not clear it, because the rewriting commit is
   still in the branch's history. Drop or amend that commit instead (`git rebase -i`).
2. **Real output.** A `TEST` entry carries the command and its actual result. "Tests pass" without the
   command is not a log entry.
3. **Decisions with alternatives.** A `DECIDE` entry names what you chose *and* what you rejected. That
   is what makes it useful six weeks later.
4. **No secrets, no private content.** Log identifiers and counts, not payloads. Quote the shortest
   decisive line of an error.
5. **One entry per meaningful step**, and always one at the end of a session.

## Entry format

```
### 2026-09-21T14:07Z · TEST · myan · claude-code/opus-5 · 3f2a9c1
pytest apps/api/tests/authz -q
→ 41 passed, 2 failed: test_lease_expiry_denies, test_team_event_drops_grants
Both failures are the unimplemented lease path, expected at this point.
```

Fields: UTC timestamp, entry type, operator, agent, HEAD at the time. `scripts/log.sh` fills them in;
write only the body.

## Entry types

| Type | Use |
|---|---|
| `READ` | A card, design section or external document that changed what you did |
| `PLAN` | The approach, and the one you rejected |
| `EDIT` | Files changed and why |
| `TEST` | Command plus actual result |
| `DECIDE` | A decision worth not re-deriving; link the ADR if one exists |
| `BLOCKED` | What stopped you, what you need, from whom |
| `HANDOFF` | End of session: state, next step, anything half-finished |
| `COMMIT` | Written by the post-commit hook, inside the commit it describes |

## Lifecycle

Open while the branch lives; `scripts/end-task.sh` appends a closing entry with the merge commit.
Logs stay in the repository — they are small, they are the project's history of how decisions were
actually made, and the digest reads them.

## Digest

`scripts/weekly_digest.py [--week YYYY-Www]` produces `DIGEST-<year>-W<week>.md`: work by operator and
module, decisions, blockers, tests run, and commits. Run it before every gate review.
