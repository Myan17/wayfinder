---
module: authz
owner: myan
paths:
  - apps/api/wayfinder/authz/**
interface_files:
  - apps/api/wayfinder/authz/interface.py
  - db/views/eligible_repo.sql
tables_owned:
  - principal
  - session
  - user_repo_access
  - user_access_state
  - connection_admin
depends_on:
  - webhooks          # records negative authorization events; never decides
design_sections:
  - "DESIGN §9.1 (authorization model)"
  - "DESIGN §9.2 (data model)"
  - "DESIGN §13.2 (threat model rows for stale authorization)"
verified_at: 91b31fd
verified_on: 2026-09-18
---

# authz

> **Implementation status (2026-09-18):** the pure kernel has landed — `build_scope`,
> `sql_predicate`, `assert_rows_authorized`, the fenced refresh, and `FixtureAuthz`. Still to come in
> this module: `resolve_principal` (needs sessions), `authorized_repos` (needs the database layer) and
> `reauthorize_manifest` (needs stored evidence manifests). Those three are marked below; everything
> else on this card is real and pinned by a test.

## Purpose

Decides which repositories a principal may see, right now. Owns principals, sessions, grants and the
leases that make those facts expire. It is the only module that answers "is this allowed".

## Public interface

```python
# apps/api/wayfinder/authz/interface.py
class Principal(Protocol):
    id: int
    kind: Literal["user", "anonymous"]

async def resolve_principal(request) -> Principal: ...        # NOT YET IMPLEMENTED (needs sessions)

async def authorized_repos(principal: Principal) -> AuthorizedScope: ...   # NOT YET IMPLEMENTED (needs the DB layer)
# Landed today, and what `authorized_repos` will be built from:
def build_scope(principal, *, facts, grants, grants_valid_until, now, policy_revision=0) -> AuthorizedScope: ...
def start_refresh(state) -> RefreshToken: ...
def apply_refresh(state, token, *, fetched, complete, now, lease) -> RefreshResult: ...
def invalidate_repo(state, *, repo_id, now) -> AccessState: ...
# AuthorizedScope carries: granted_repo_ids: list[int]
#                          policy_revision: int
#                          degraded: list[str]        # e.g. ["permissions_public_only"]
#                          expires_at: datetime       # callers must not cache past this

def sql_predicate(alias: str, scope: AuthorizedScope) -> tuple[str, dict]: ...
# Returns the SQL fragment + params that every query MUST use to filter rows:
#   (eligible.verified_public OR <alias>.repo_id = ANY(:granted_repo_ids))

async def assert_rows_authorized(rows, scope) -> None: ...
# Post-retrieval defence in depth; raises AuthorizationViolation and increments the alert counter.

async def reauthorize_manifest(principal, manifest: EvidenceManifest) -> ManifestVerdict: ...  # NOT YET IMPLEMENTED
# For cached answers, stored traces and source expansion.
```

```sql
-- db/views/eligible_repo.sql : repository-side half of the predicate (see DESIGN §9.2)
```

## Invariants a caller may rely on

- `authorized_repos` never returns a repository whose connection, eligibility or visibility lease has
  expired; expiry denies rather than falling back to a stale set.
- Anonymous principals are real principals with their own ID; `user_id IS NULL` is never treated as
  "everyone".
- A negative authorization event is applied before the HTTP 202 that accepts its webhook, so a caller
  that asks after the event never sees the old answer (bound: 5 s end to end).
- `sql_predicate` is the only sanctioned way to filter rows; both halves of the predicate come from
  here, so no call site can express them differently.
- `AuthorizedScope.expires_at` is authoritative: a long-running request must re-check before each
  provider call and at least every 15 s of streaming.

## What this module will never do

- Never fetch from GitHub on the denial path (refresh is repair, never enforcement).
- Never write to `repository`, `connection` or any index table — those are `webhooks` and `indexing`.
- Never widen a scope as a side effect of a read; refresh is explicit and fenced.
- Never log, trace or export grant contents; counters only.

## Failure modes the caller must handle

| Condition | Caller sees | Do this |
|---|---|---|
| Grant lease expired, refresh failed | `AuthorizedScope` with public repositories only, `degraded=["permissions_public_only"]` | Serve, and surface the notice to the user |
| GitHub unreachable past every lease | Empty scope | Return an empty result set; do not serve stale rows |
| Manifest no longer resolves | `ManifestVerdict.denied` | Deny or redact the whole artifact, never hide one citation |
| Post-retrieval assertion fails | `AuthorizationViolation` | Fail the request; the counter pages, stop-the-line |

## Data owned

`principal`, `session` (opaque tokens, revocation epoch), `user_repo_access` (grants),
`user_access_state` (revision, lease), `connection_admin` (installation administrators). Anyone else
touching these needs a BCR.

## Tests that pin this contract

| Test | Pins |
|---|---|
| `test_scope.py::test_expired_visibility_lease_denies_a_public_repository` | Lease expiry denies public repositories |
| `test_scope.py::test_denied_serving_state_beats_a_valid_grant` | Synchronous denial outranks a grant |
| `test_scope.py::test_scope_expires_at_the_earliest_lease_it_depends_on` | Scope lifetime |
| `test_predicate.py::test_empty_scope_produces_a_predicate_that_matches_nothing` | Fail closed |
| `test_predicate.py::test_assertion_accepts_exactly_the_rows_the_scope_allows` | Property: assertion agrees with the scope |
| `test_refresh.py::test_refresh_is_rejected_when_the_revision_moved_while_it_was_fetching` | Revision fencing (WF-02) |
| `test_refresh.py::test_partial_pagination_is_never_treated_as_success` | All-or-nothing refresh |
| `test_fake_matches_contract.py` | The fake is never more permissive than the real logic |
| _planned_ `test_events.py`, `test_manifest.py`, `test_state_machine.py` | Webhook bound, artifact re-authorization, sequences |

## Fake

`apps/api/wayfinder/authz/fakes.py` — `FixtureAuthz` built from `eval/datasets/permission_fixture.yaml`.
Consumers (retrieval, answer, cache, http) build against it; the contract tests above run against both
the fake and the real implementation, so the fake cannot drift into being more permissive.

## Open questions

- Logout propagation bound is stated as ≤ 30 s (session cache TTL). If P2 measurement shows the cache
  is not worth 30 s of ambiguity, drop it and read per request.
- Whether `connection_admin` membership should itself carry a lease. Currently administrative, no lease.

## Change log

| Date | Change | BCR |
|---|---|---|
| 2026-09-18 | Card created from DESIGN v0.3 before implementation | — |
