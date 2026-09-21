---
module: authz
owner: myan
paths:
  - apps/api/wayfinder/authz/**
interface_files:
  - apps/api/wayfinder/authz/interface.py
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
verified_hashes:
  "apps/api/wayfinder/authz/interface.py": "5907b1ff0610df5c"
verified_on: 2026-09-21
---

# authz

> **Status (2026-09-21):** the pure kernel is on `main` and pinned by 38 tests — `build_scope`,
> `sql_predicate`, `assert_rows_authorized`, the counters, the fenced refresh and `FixtureAuthz`.
> Three entry points are **not implemented**: `resolve_principal` (needs sessions),
> `authorized_repos` (needs the database layer) and `reauthorize_manifest` (needs stored evidence
> manifests). They are marked NOT YET IMPLEMENTED below. Anything not marked LANDED is not a contract.

## Purpose

Decides which repositories a principal may see, right now. Owns principals, sessions, grants and the
leases that make those facts expire. It is the only module that answers "is this allowed".

## Public interface

```python
# apps/api/wayfinder/authz/interface.py
class PrincipalKind(StrEnum):            # USER = "user", ANONYMOUS = "anonymous"

@dataclass(frozen=True, slots=True)
class Principal:
    id: int
    kind: PrincipalKind
    @property
    def is_anonymous(self) -> bool: ...  # kind is ANONYMOUS; anonymous visitors have their own id

async def resolve_principal(request) -> Principal: ...        # NOT YET IMPLEMENTED (needs sessions)

async def authorized_repos(principal: Principal) -> AuthorizedScope: ...   # NOT YET IMPLEMENTED (needs the DB layer)

# LANDED. What authorized_repos will be assembled from:
def build_scope(principal, *, facts, grants, grants_valid_until, now, policy_revision=0) -> AuthorizedScope: ...
# Raises AnonymousGrantsError (and counts it) if an anonymous principal is given grants.
def start_refresh(state) -> RefreshToken: ...
def apply_refresh(state, token, *, fetched, complete, now, lease) -> RefreshResult: ...
def invalidate_repo(state, *, repo_id, now) -> AccessState: ...

# AuthorizedScope (frozen dataclass) carries:
#   principal: Principal
#   repo_ids: frozenset[int]         # everything visible: verified-public plus granted
#   granted_repo_ids: frozenset[int] # the granted half alone; only this half is bound into SQL
#   expires_at: datetime             # callers must not cache past this
#   policy_revision: int
#   degraded: tuple[str, ...]        # e.g. ("permissions_public_only",)
#   def allows(self, repo_id: int) -> bool   # membership in repo_ids

def sql_predicate(row_alias, scope, *, eligible_alias="eligible", now=None) -> tuple[str, dict]: ...
# LANDED. The caller joins eligible_repo as `eligible_alias`; the fragment reads:
#   row.live AND (eligible.verified_public OR row.repo_id = ANY(%(granted_repo_ids)s))
# A scope past its lease returns "false": an expired authorization is not a query.

def assert_rows_authorized(rows, scope) -> None: ...
# LANDED. Post-retrieval defence in depth: increments authorization_violation_total (an unsampled
# in-process counter in wayfinder.authz.metrics) and raises AuthorizationViolation. Export to the
# collector lands with the observability module; the counter is the seam, not the wiring.

async def reauthorize_manifest(principal, manifest: EvidenceManifest) -> ManifestVerdict: ...
# NOT YET IMPLEMENTED. For cached answers, stored traces and source expansion.
```

```sql
-- PLANNED, NOT WRITTEN: db/views/eligible_repo.sql, the repository-side half of the predicate
-- (DESIGN §9.2). It lands with the database layer; until then sql_predicate names the alias its
-- caller must join, and nothing in the tree provides that view.
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

All paths below are under `apps/api/tests/authz/`. Names are exact; if one does not exist, the card
is wrong and that is a defect, not a rounding error.

| Test | Pins |
|---|---|
| `test_scope.py::test_expired_visibility_lease_denies_a_public_repository` | Lease expiry denies public repositories |
| `test_scope.py::test_denied_serving_state_beats_a_valid_grant` | A synchronous denial outranks a grant |
| `test_scope.py::test_scope_expires_at_the_earliest_lease_it_depends_on` | Scope lifetime |
| `test_scope.py::test_anonymous_principal_carrying_grants_is_a_programming_error` | The kernel refuses; it does not normalise |
| `test_scope.py::test_the_anonymous_grant_defect_is_counted_as_well_as_refused` | The defect is counted, not silent |
| `test_scope.py::test_stale_grant_lease_degrades_even_when_the_user_holds_no_grants` | Staleness drives the degraded flag |
| `test_predicate.py::test_predicate_lets_the_database_decide_public_and_binds_only_granted_ids` | The public half is never enumerated |
| `test_predicate.py::test_an_expired_scope_matches_nothing` | Fail closed |
| `test_predicate.py::test_an_expired_scope_matches_nothing_even_when_now_is_not_passed` | The expiry check is not optional |
| `test_fake_matches_contract.py::test_the_fake_does_not_mask_a_resolver_that_hands_an_anonymous_principal_grants` | The fake does not hide the kernel's guard |
| `test_predicate.py::test_assertion_accepts_exactly_the_rows_the_scope_allows` | Property: assertion agrees with the scope |
| `test_predicate.py::test_assert_rows_authorized_raises_and_counts_a_row_outside_the_scope` | Violations raise and count |
| `test_refresh.py::test_refresh_is_rejected_when_the_revision_moved_while_it_was_fetching` | Revision fencing |
| `test_refresh.py::test_partial_pagination_is_never_treated_as_success` | All-or-nothing refresh |
| `test_fake_matches_contract.py` (6 tests) | The fake is never more permissive than the kernel |
| `test_metrics.py` (3 tests) | Counter semantics |

**Not yet written**, because they need the database layer: the delivered-event revocation bound
(AUTH-02), artifact re-authorization (AUTH-08), and the state-machine sequences against an
independent oracle (DESIGN §16.3).

## Fake

`apps/api/wayfinder/authz/fakes.py` — `FixtureAuthz`, constructed in code from sets of public,
private, denied and granted repository ids. Consumers (retrieval, answer, cache, http) build against
it. `test_fake_matches_contract.py` pins that it is never more permissive than the kernel, and that
it passes grants through unchanged: a fixture granting an anonymous principal access reaches
`build_scope` and raises, rather than being tidied away where no test would see it.

The YAML fixture of 1,000 synthetic principals described in DESIGN §14.4 does **not** exist yet; it
arrives with the leak suite.

## Open questions

- Logout propagation bound is stated as ≤ 30 s (session cache TTL). If P2 measurement shows the cache
  is not worth 30 s of ambiguity, drop it and read per request.
- Whether `connection_admin` membership should itself carry a lease. Currently administrative, no lease.

## Change log

| Date | Change | BCR |
|---|---|---|
| 2026-09-18 | Card created from DESIGN v0.3 before implementation | — |
| 2026-09-20 | Corrected after the stack landed: the card still opened as a pre-implementation sketch, named three test files that do not exist, and pointed at a fixture that was never created | — |
| 2026-09-21 | Re-read against `interface.py`: the card described `Principal` as a `Protocol` with a `Literal` kind and the scope's collections as lists. They are a frozen dataclass with a `PrincipalKind` enum, frozensets and a tuple, and `allows()` was undocumented. Card verification moved to content hashes | — |
