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
verified_at: 8f9f972
verified_on: 2026-09-19
---

# authz

> Worked example of a contract card. Written before the code so the shape is agreed first; the hash
> and `verified_at` are filled in by the first pull request that lands the interface.

## Purpose

Decides which repositories a principal may see, right now. Owns principals, sessions, grants and the
leases that make those facts expire. It is the only module that answers "is this allowed".

## Public interface

```python
# apps/api/wayfinder/authz/interface.py
class Principal(Protocol):
    id: int
    kind: Literal["user", "anonymous"]

async def resolve_principal(request) -> Principal: ...

async def authorized_repos(principal: Principal) -> AuthorizedScope: ...
# AuthorizedScope carries: granted_repo_ids: list[int]
#                          policy_revision: int
#                          degraded: list[str]        # e.g. ["permissions_public_only"]
#                          expires_at: datetime       # callers must not cache past this

def sql_predicate(row_alias, scope, *, eligible_alias="eligible", now=None) -> tuple[str, dict]: ...
# LANDED. The caller joins eligible_repo as `eligible_alias`; the fragment reads:
#   row.live AND (eligible.verified_public OR row.repo_id = ANY(%(granted_repo_ids)s))
# A scope past its lease returns "false": an expired authorization is not a query.

def assert_rows_authorized(rows, scope) -> None: ...
# LANDED. Post-retrieval defence in depth: increments authorization_violation_total (an unsampled
# in-process counter in wayfinder.authz.metrics) and raises AuthorizationViolation. Export to the
# collector lands with the observability module; the counter is the seam, not the wiring.

async def reauthorize_manifest(principal, manifest: EvidenceManifest) -> ManifestVerdict: ...
# For cached answers, stored traces and source expansion.
```

```sql
-- db/views/eligible_repo.sql : repository-side half of the predicate (see DESIGN §9.2)
```

## Invariants a caller may rely on

- `build_scope` never returns a repository whose connection, eligibility or visibility lease has
  expired; expiry denies rather than falling back to a stale set.
- `AuthorizedScope.repo_ids` is everything visible; `granted_repo_ids` is the granted half alone.
  The SQL predicate binds only the granted half and lets the database decide public-ness.
- `degraded` carries `permissions_public_only` whenever a *user's* grant lease is stale, whether or
  not any grant is currently held. Anonymous principals are never flagged: public-only is their
  normal state.
- Anonymous principals are real principals with their own ID; `user_id IS NULL` is never treated as
  "everyone".
- A negative authorization event is applied before the HTTP 202 that accepts its webhook, so a caller
  that asks after the event never sees the old answer (bound: 5 s end to end).
- `sql_predicate` is the only sanctioned way to filter rows; both halves come from here, so no call
  site can express them differently. The public half is decided by the database through
  `eligible_repo`, never by enumerating public repository ids into a query parameter.
- SQL and the post-retrieval assertion reach their answer by different routes (database view versus
  the Python scope). A disagreement fails the request instead of serving the difference.
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
| `apps/api/tests/authz/test_predicate.py::test_expired_visibility_denies` | Lease expiry denies public repositories |
| `apps/api/tests/authz/test_events.py::test_team_event_drops_grants` | 5-second bound for team-scoped revocation |
| `apps/api/tests/authz/test_refresh.py::test_stale_refresh_rejected` | Revision fencing |
| `apps/api/tests/authz/test_manifest.py::test_revoked_artifact_denied` | Artifact re-authorization |
| `apps/api/tests/authz/test_state_machine.py` | Sequence behaviour against the independent oracle |

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
