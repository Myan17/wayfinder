"""The fake must never be more permissive than the real scope logic (AGENTS.md 3.4).

A consumer that builds against a lenient fake discovers the difference in production, which is the
failure mode fakes are supposed to prevent.
"""

from datetime import UTC, datetime

from wayfinder.authz.fakes import FixtureAuthz
from wayfinder.authz.scope import PUBLIC_ONLY

NOW = datetime(2026, 9, 21, 12, 0, tzinfo=UTC)


def test_fake_grants_private_access_only_with_a_grant():
    fixture = FixtureAuthz(public={1}, private={2, 3}, grants={5: {2}})

    scope = fixture.scope_for(fixture.user(5), now=NOW)

    assert scope.repo_ids == frozenset({1, 2})  # public + granted, never the ungranted private repo


def test_fake_anonymous_sees_public_only():
    # The grant belongs to a signed-in principal; the anonymous visitor is a different principal and
    # holds none. (Granting one to the anonymous id would now raise, which the test below covers.)
    fixture = FixtureAuthz(public={1}, private={2}, grants={5: {2}})

    scope = fixture.scope_for(fixture.anonymous(9), now=NOW)

    assert scope.repo_ids == frozenset({1})


def test_fake_honours_a_denied_repository():
    fixture = FixtureAuthz(public={1}, private={2}, grants={5: {2}}, denied={1, 2})

    scope = fixture.scope_for(fixture.user(5), now=NOW)

    assert scope.repo_ids == frozenset()


def test_fake_reproduces_the_public_only_degradation():
    fixture = FixtureAuthz(public={1}, private={2}, grants={5: {2}}, grants_stale_for={5})

    scope = fixture.scope_for(fixture.user(5), now=NOW)

    assert scope.repo_ids == frozenset({1})
    assert PUBLIC_ONLY in scope.degraded


def test_the_kernel_not_the_fake_is_what_forbids_anonymous_grants():
    """After the review of #1 the invariant lives in build_scope, so a fixture that tries to hand an
    anonymous principal a grant is refused even though the fake no longer filters them itself."""
    import pytest

    from wayfinder.authz.scope import AnonymousGrantsError, build_scope

    fixture = FixtureAuthz(public=set(), private={7}, grants={4: {7}})
    facts = fixture.facts(NOW)

    with pytest.raises(AnonymousGrantsError):
        build_scope(
            fixture.anonymous(4),
            facts=facts,
            grants=frozenset({7}),
            grants_valid_until=NOW,
            now=NOW,
        )


def test_the_fake_does_not_mask_a_resolver_that_hands_an_anonymous_principal_grants():
    """The fake used to drop those grants silently, so the kernel's guard was never reached through
    it - which made the card's claim about the kernel true only on paper (reviewer, #10)."""
    import pytest

    from wayfinder.authz.scope import AnonymousGrantsError

    fixture = FixtureAuthz(public={1}, private={2}, grants={4: {2}})

    with pytest.raises(AnonymousGrantsError):
        fixture.scope_for(fixture.anonymous(4), now=NOW)
