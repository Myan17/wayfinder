"""Authorized scope assembly: DESIGN §9.1.1-9.1.2, card docs/context/modules/authz.md.

Pins the three rules the v0.2 review found missing: `verified_public` is a lease rather than a
column, anonymous principals hold no grants, and a fact that cannot be refreshed leaves the scope.
"""

from datetime import UTC, datetime, timedelta

import pytest

from wayfinder.authz.interface import Principal, PrincipalKind
from wayfinder.authz.metrics import anonymous_grants_rejected_total
from wayfinder.authz.scope import PUBLIC_ONLY, AnonymousGrantsError, RepoFact, build_scope

NOW = datetime(2026, 9, 21, 12, 0, tzinfo=UTC)


def fact(
    repo_id: int,
    *,
    public: bool = True,
    serving: bool = True,
    connection_live: bool = True,
    visibility_expired: bool = False,
    connection_expired: bool = False,
) -> RepoFact:
    past, future = NOW - timedelta(minutes=1), NOW + timedelta(minutes=9)
    return RepoFact(
        repo_id=repo_id,
        visibility="public" if public else "private",
        visibility_valid_until=past if visibility_expired else future,
        serving_state="active" if serving else "denied",
        connection_state="active" if connection_live else "suspended",
        connection_valid_until=past if connection_expired else future,
    )


def anonymous() -> Principal:
    return Principal(id=7, kind=PrincipalKind.ANONYMOUS)


def user(pid: int = 3) -> Principal:
    return Principal(id=pid, kind=PrincipalKind.USER)


def test_public_repository_is_visible_to_an_anonymous_principal():
    scope = build_scope(anonymous(), facts=[fact(1)], grants=frozenset(), grants_valid_until=None, now=NOW)

    assert scope.repo_ids == frozenset({1})


def test_expired_visibility_lease_denies_a_public_repository():
    """The public→private case with a lost webhook: nothing else about the repo changed."""
    scope = build_scope(
        anonymous(),
        facts=[fact(1, visibility_expired=True)],
        grants=frozenset(),
        grants_valid_until=None,
        now=NOW,
    )

    assert scope.repo_ids == frozenset()


def test_private_repository_needs_a_grant():
    facts = [fact(1, public=False)]

    without = build_scope(
        user(), facts=facts, grants=frozenset(), grants_valid_until=NOW + timedelta(minutes=5), now=NOW
    )
    with_grant = build_scope(
        user(), facts=facts, grants=frozenset({1}), grants_valid_until=NOW + timedelta(minutes=5), now=NOW
    )

    assert without.repo_ids == frozenset()
    assert with_grant.repo_ids == frozenset({1})


def test_expired_grant_lease_denies_the_private_repository_but_keeps_public_ones():
    facts = [fact(1, public=False), fact(2)]

    scope = build_scope(
        user(), facts=facts, grants=frozenset({1}), grants_valid_until=NOW - timedelta(seconds=1), now=NOW
    )

    assert scope.repo_ids == frozenset({2})
    assert "permissions_public_only" in scope.degraded


def test_denied_serving_state_beats_a_valid_grant():
    """A negative webhook denies the repository synchronously; a grant must not override it."""
    scope = build_scope(
        user(),
        facts=[fact(1, public=False, serving=False)],
        grants=frozenset({1}),
        grants_valid_until=NOW + timedelta(minutes=5),
        now=NOW,
    )

    assert scope.repo_ids == frozenset()


@pytest.mark.parametrize("kwargs", [{"connection_live": False}, {"connection_expired": True}])
def test_connection_state_gates_every_repository(kwargs):
    scope = build_scope(
        user(), facts=[fact(1, **kwargs)], grants=frozenset({1}), grants_valid_until=NOW, now=NOW
    )

    assert scope.repo_ids == frozenset()


def test_scope_expires_at_the_earliest_lease_it_depends_on():
    """A long request must not outlive the facts it was authorized by (DESIGN §9.1.5)."""
    soon = NOW + timedelta(minutes=2)
    facts = [fact(1), fact(2, public=False)]

    scope = build_scope(user(), facts=facts, grants=frozenset({2}), grants_valid_until=soon, now=NOW)

    assert scope.expires_at == soon


# --- regression tests for the review of #1 -----------------------------------------------------


def test_the_anonymous_grant_defect_is_counted_as_well_as_refused():
    """The reviewer asked for a counter without replacing the exception (F1)."""
    before = anonymous_grants_rejected_total.value

    with pytest.raises(AnonymousGrantsError):
        build_scope(
            anonymous(),
            facts=[fact(9, public=False)],
            grants=frozenset({9}),
            grants_valid_until=NOW,
            now=NOW,
        )

    assert anonymous_grants_rejected_total.value == before + 1


def test_anonymous_principal_carrying_grants_is_a_programming_error():
    """F1: no GitHub token stands behind an anonymous principal, so the kernel refuses rather than
    dropping the grants silently and letting a broken resolver look healthy."""
    with pytest.raises(AnonymousGrantsError):
        build_scope(
            anonymous(),
            facts=[fact(42, public=False)],
            grants=frozenset({42}),
            grants_valid_until=NOW + timedelta(minutes=5),
            now=NOW,
        )


def test_anonymous_principal_without_grants_is_fine():
    scope = build_scope(anonymous(), facts=[fact(1)], grants=frozenset(), grants_valid_until=None, now=NOW)

    assert scope.repo_ids == frozenset({1})
    assert scope.degraded == ()  # public-only is normal for anonymous, not a degradation


def test_stale_grant_lease_degrades_even_when_the_user_holds_no_grants():
    """F4: the flag must follow staleness, not whether we happen to hold a grant right now."""
    scope = build_scope(
        user(),
        facts=[fact(1)],
        grants=frozenset(),
        grants_valid_until=NOW - timedelta(seconds=1),
        now=NOW,
    )

    assert scope.degraded == (PUBLIC_ONLY,)


def test_missing_grant_lease_for_a_user_is_also_degraded():
    scope = build_scope(user(), facts=[fact(1)], grants=frozenset(), grants_valid_until=None, now=NOW)

    assert scope.degraded == (PUBLIC_ONLY,)


def test_scope_separates_granted_ids_from_the_full_visible_set():
    """F2 needs the granted half on its own: the SQL predicate binds only those ids."""
    facts = [fact(1), fact(2, public=False)]

    scope = build_scope(
        user(), facts=facts, grants=frozenset({2}), grants_valid_until=NOW + timedelta(minutes=5), now=NOW
    )

    assert scope.repo_ids == frozenset({1, 2})
    assert scope.granted_repo_ids == frozenset({2})
