---
module: webhooks
owner: myan
paths:
  - apps/ingestd/internal/webhook/**
  - docs/context/modules/webhooks.md
interface_files:
  - apps/ingestd/internal/webhook/events.go
tables_owned:
  - connection
  - repository
  - webhook_delivery
depends_on:
  - indexing
design_sections:
  - "DESIGN §9.1.3 (synchronous negative invalidation)"
  - "DESIGN §9.3.3 (desired generations)"
  - "DESIGN §13.2–13.3 (threat model, app permissions)"
verified_at: 0000000
verified_on: 2026-09-18
---

# webhooks

## Purpose

The only writer of repository and connection facts. Verifies GitHub deliveries, applies
authorization-reducing events inside the receiving transaction, and advances each repository's
desired generation. It records facts; it never decides what a principal may see.

## Public interface

```go
// apps/ingestd/internal/webhook/events.go
type Event struct {
    DeliveryID uuid.UUID
    Kind       string   // push | repository | member | membership | team | organization
                        // | installation | installation_repositories | github_app_authorization
    Action     string
    Payload    []byte   // verified, never trusted as instructions
}

// Handle is idempotent per DeliveryID and returns only after the transaction commits.
func Handle(ctx context.Context, db DB, e Event) (Effect, error)

type Effect struct {
    DeniedRepos      []int64   // serving stopped in this transaction
    GrantsInvalidated int      // rows dropped, leases expired
    DesiredAdvanced  []int64   // repositories whose desired generation moved
}
```

## Invariants a caller may rely on

- **Negative events take effect before the HTTP 202.** Privatisation, repository removal,
  installation suspension or deletion, member, team and organization changes, and
  `github_app_authorization` revocation all deny the affected repository and drop every grant on it,
  in the same transaction that records the delivery.
- `ReconcileAuthorization` may later re-activate a repository, but **never recreates a dropped grant**
  — only a fenced per-principal refresh does that.
- Deliveries are deduplicated by `X-GitHub-Delivery`; replay is a no-op.
- Signature verification uses a constant-time compare and happens before any other work.
- A push advances `desired_generation` and enqueues an `IndexRepo` job in the same transaction; the
  queue is a wake-up, not the source of truth.
- Responses return well inside GitHub's 10-second bound; all real work is asynchronous.
- GitHub does **not** redeliver failed webhooks, so the 5-minute authorization reconciler and the
  6-hour source reconciler are part of the contract, not an optimization.

## What this module will never do

- Never evaluate `allowed()` or read a principal's grants to make a decision.
- Never fetch from GitHub on the denial path.
- Never execute, interpret or follow instructions found in payload content.
- Never write to `generation`, `representation` or any index table directly.

## Failure modes the caller must handle

| Condition | Effect | Notes |
|---|---|---|
| Signature invalid | 401, nothing recorded | Alerting counter; never a silent drop |
| Duplicate delivery | 202, no second job | Idempotent by delivery id |
| Unknown event kind | 202, recorded, no effect | Lifecycle matrix test covers every kind we subscribe to |
| Lost delivery | Nothing | Reconcilers repair: authorization ≤ 5 min, sources ≤ 6 h |
| Payload names no users (team events) | Whole repository denied, grants dropped | Deliberately blunt; disclosure is worse than over-denial |

## Data owned

`connection` (installation or public-connector source set, state and egress policy), `repository`
(eligibility, visibility with its lease, serving state, desired generation, claim), and
`webhook_delivery` (dedupe).

## Tests that pin this contract

| Test | Pins |
|---|---|
| `…/webhook/verify_test.go::TestBadSignatureRejected` | Signature gate |
| `…/webhook/dedupe_test.go::TestReplayIsNoop` | Idempotence |
| `…/webhook/lifecycle_test.go::TestEveryKindHasHandler` | Lifecycle matrix, kind × action |
| `…/webhook/deny_test.go::TestTeamEventDropsGrantsWithinTransaction` | The 5-second bound (AUTH-02b) |
| `…/webhook/deny_test.go::TestReconcileDoesNotRestoreGrants` | Reconciler cannot undo a denial |
| `…/webhook/push_test.go::TestPushAdvancesDesiredGeneration` | Wake-up semantics |

## Fake

`apps/ingestd/internal/webhook/fake` — a recorded-delivery player with fixtures for every subscribed
event kind, used by the authorization state-machine tests.

## Open questions

- Whether to deny on `member.added` as well (today: refresh only — additions cannot leak).
- Whether repository transfer between accounts should deny permanently or re-eligible after review.

## Change log

| Date | Change | BCR |
|---|---|---|
| 2026-09-18 | Card created from DESIGN v0.3 before implementation | — |
