"""Grant refresh is fenced, single-flight and all-or-nothing -- DESIGN §9.1.3-9.1.4 (finding WF-02).

The race that motivates this: refresh A starts, a revocation lands, refresh B installs the denied
set, then A completes and reinstalls the older grants with a fresh lease. The authorization revision
captured before fetching is what makes that impossible.
"""

from datetime import UTC, datetime, timedelta

from wayfinder.authz.refresh import (
    AccessState,
    RefreshOutcome,
    apply_refresh,
    invalidate_repo,
    start_refresh,
)

NOW = datetime(2026, 9, 21, 12, 0, tzinfo=UTC)
LEASE = timedelta(minutes=10)


def state(revision: int = 1, grants: set[int] | None = None, valid_for: timedelta = LEASE) -> AccessState:
    return AccessState(
        principal_id=3,
        revision=revision,
        grants=frozenset(grants or {1, 2}),
        valid_until=NOW + valid_for,
    )


def test_completed_refresh_installs_grants_and_extends_the_lease():
    before = state(grants={1})
    token = start_refresh(before)

    result = apply_refresh(before, token, fetched={1, 5}, complete=True, now=NOW, lease=LEASE)

    assert result.outcome is RefreshOutcome.APPLIED
    assert result.state.grants == frozenset({1, 5})
    assert result.state.valid_until == NOW + LEASE


def test_refresh_is_rejected_when_the_revision_moved_while_it_was_fetching():
    before = state(revision=4, grants={1, 2})
    token = start_refresh(before)  # captured revision 4
    revoked = invalidate_repo(before, repo_id=2, now=NOW)  # revision 5, lease expired

    result = apply_refresh(revoked, token, fetched={1, 2}, complete=True, now=NOW, lease=LEASE)

    assert result.outcome is RefreshOutcome.STALE
    assert result.state.grants == frozenset({1})  # the revocation stands
    assert result.state.valid_until == NOW  # and its lease was not extended


def test_partial_pagination_is_never_treated_as_success():
    before = state(grants={1, 2}, valid_for=timedelta(minutes=1))
    token = start_refresh(before)

    result = apply_refresh(before, token, fetched={1}, complete=False, now=NOW, lease=LEASE)

    assert result.outcome is RefreshOutcome.INCOMPLETE
    assert result.state.grants == frozenset({1, 2})
    assert result.state.valid_until == NOW + timedelta(minutes=1)  # old lease keeps expiring


def test_invalidating_a_repository_drops_its_grant_and_expires_the_lease_now():
    """A team or org event names no users, so every grant on that repository goes (DESIGN §9.1.3)."""
    before = state(revision=7, grants={1, 2, 3})

    after = invalidate_repo(before, repo_id=2, now=NOW)

    assert after.grants == frozenset({1, 3})
    assert after.valid_until == NOW
    assert after.revision == 8


def test_invalidation_during_a_refresh_wins_even_if_the_refresh_finishes_last():
    before = state(revision=1, grants={9})
    token = start_refresh(before)

    denied = invalidate_repo(before, repo_id=9, now=NOW)
    late = apply_refresh(denied, token, fetched={9}, complete=True, now=NOW, lease=LEASE)

    assert late.outcome is RefreshOutcome.STALE
    assert 9 not in late.state.grants
