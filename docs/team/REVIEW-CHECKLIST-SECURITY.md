# Security review checklist

Required for any pull request touching `authz`, `egress`, `webhooks` or `schema`. The reviewer states
in the pull request **which items they checked**, not that "the checklist was done".

Each item maps to a finding from the v0.2 principal review or a mechanism in `docs/DESIGN.md` §9.1,
§9.7 or §13. They are here because each one has already been gotten wrong once, on paper.

## Authorization (`authz`)

- [ ] Every new query path filters through the predicate helper — no hand-written `WHERE repo_id`
- [ ] Nothing extends an authority lease as a side effect of a read
- [ ] Negative events are applied in the receiving transaction, not by a background job
- [ ] Grant refresh still compares the authorization revision it captured before fetching
- [ ] A failed or partial refresh cannot install grants or extend a lease
- [ ] Anonymous principals are principals: no code treats a missing user as "everyone"
- [ ] Artifact reads (answers, traces, feedback, source expansion) re-authorize the stored manifest
- [ ] Long-running work re-checks the lease; nothing can outlive it
- [ ] Failure is denial: no path falls back to a cached or default-allow answer

## Egress and classification (`egress`)

- [ ] Classification derives from the connection's input policy, not from which passages retrieval chose
- [ ] Mixed scopes take the intersection of approved providers; an empty intersection means extractive
- [ ] Derived artifacts inherit the classification: rewrites, judge inputs, exceptions, feedback, logs
- [ ] No prompt, passage or completion content leaves for a private-classified request
- [ ] Rendering blocks remote images and any link the server did not construct
- [ ] Provider reservations happen before dispatch, and errors are classified, not retried blindly

## Webhooks and sources (`webhooks`)

- [ ] Signature verified with a constant-time compare before any work
- [ ] Deliveries deduplicated; replay is a no-op
- [ ] Lifecycle events (`repository`, `member`, `membership`, `team`, `organization`,
      `installation*`, `github_app_authorization`) all have a handler and a test
- [ ] No repository-supplied code is executed: hooks, build scripts, LFS filters, submodules
- [ ] Ingestion bounds enforced: bytes, files, parse time, storage; skipped material surfaced
- [ ] Credentials never appear in a remote URL or in logged git output

## Schema (`schema`, joint)

- [ ] Migration is additive, or the incompatibility and its ordering are written down
- [ ] Both cards affected by the change are updated in this pull request
- [ ] Foreign keys and delete modes reviewed against the GC order in §9.3.6
- [ ] Composite keys still make a cross-repository binding unrepresentable
- [ ] Nothing already merged was edited
- [ ] Rollback stated: what a revert does to data written under the new schema

## Always

- [ ] No secret, token or private content in code, logs, tests, fixtures or the task log
- [ ] New counters exist for anything that can deny or degrade, and they are unsampled
- [ ] A test would fail if this change quietly widened what a principal can see
