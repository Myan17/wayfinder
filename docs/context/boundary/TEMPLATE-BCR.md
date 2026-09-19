---
bcr: <n>
title: <short title>
requester: <handle>            # who needs the change
owner: <handle>                # who owns the thing being changed
modules: [<module>, …]
status: proposed               # proposed | accepted | amended | refused | superseded
opened: <YYYY-MM-DD>
decided: <YYYY-MM-DD | —>
labels: []                     # e.g. schema, ownership, agreements
---

# BCR-<n>: <title>

## What I need

<One paragraph. The capability, not your implementation of it.>

## Why

<What task this unblocks, and what happens to the schedule if it waits. Link the task log.>

## Proposed contract

<Exact signature, SQL view, event shape or route. Precise enough that the owner can accept it as
written and that a consumer could code against it today.>

```text
<signature / schema / example payload>
```

## Compatibility and migration

| Question | Answer |
|---|---|
| Is this additive? | <yes / no — if no, what breaks> |
| Existing consumers affected | <list, from the context index> |
| Migration order | <what ships first, what can follow> |
| Feature flag needed | <yes/no> |
| Rollback | <how we undo it if it is wrong> |

## What I will do if this is refused

<The alternative, and its cost. A BCR without this section is a demand rather than a request.>

## Owner's decision

- **Decision:** <accept / amend / refuse>
- **Reasoning:** <written by the owner, not the requester>
- **If amended, the contract that was actually agreed:** <…>
- **Follow-up owed:** <card updated? fake published? consumers notified?>

## Closure checklist (owner)

- [ ] Card updated, `Verified-at` bumped in the implementing pull request
- [ ] Fake updated so consumers can build before the implementation lands
- [ ] Contract test added that pins the new invariant
- [ ] Requester told in the pull request that the contract is ready
