<!-- The Work record is not optional: CI checks for it, and the reviewer reads it instead of
     rebuilding your context. Keep it short and specific. -->

## What and why

<One paragraph. What changes, and which story or design section it serves.>

Closes: <task / issue>
Design: DESIGN §<x.y>
BCR: <BCR-n, or "none — inside my own modules">
<!-- Only if this pull request touches more than its branch's module. CI requires it. -->
Scope: <module>, <module>

## Work record

- **Task log:** `docs/agent-log/<operator>-<module>-<slug>.md`
- **Operator / agent:** <handle> / <tool/model>
- **Cards read:** <the contract cards this work depended on>
- **Contract change:** <none | the interface that moved, and the card commit that records it>
- **Evidence:** <commands run and their real results — tests, benchmarks, plans>

```
<paste the decisive output, shortest form: "pytest apps/api/tests/authz -q → 43 passed">
```

## Risk

| Question | Answer |
|---|---|
| Does this touch authorization, egress or the schema? | <yes/no — if yes, the security checklist is required> |
| Can it disclose data that was previously hidden? | <no, because …> |
| What happens if it is wrong in production? | <blast radius, and how we would notice> |
| Rollback | <revert is enough / needs a migration step / feature flag> |

## Reviewer checklist

- [ ] Diff matches the stated scope; no unrelated files; any `Scope:` widening is justified
- [ ] Contract cards accurate; `Verified-at` bumped if an interface moved
- [ ] Tests pin the behaviour claimed, and I saw real output
- [ ] Design claims edited in this same pull request where affected
- [ ] For `authz` / `egress` / `webhooks` / `schema`: `docs/team/REVIEW-CHECKLIST-SECURITY.md` worked
      through, and I say below which items I actually checked

<!-- Reviewer: approve, approve-with-follow-up, or request changes. Then you merge (squash). -->
