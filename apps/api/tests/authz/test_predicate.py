"""The one sanctioned way to filter rows -- DESIGN 9.1.5, card docs/context/modules/authz.md.

The database decides public-ness through the eligible_repo view; we bind only the granted ids. That
keeps the filter on the scanned relation (so pgvector's iterative scan can keep scanning) and keeps
the parameter small for organisations with thousands of public repositories.
"""

from datetime import UTC, datetime, timedelta

import pytest
from hypothesis import given
from hypothesis import strategies as st

from wayfinder.authz.interface import AuthorizedScope, Principal, PrincipalKind
from wayfinder.authz.metrics import authorization_violation_total
from wayfinder.authz.predicate import AuthorizationViolation, assert_rows_authorized, sql_predicate

NOW = datetime(2026, 9, 21, 12, 0, tzinfo=UTC)


def scope(
    visible: set[int],
    granted: set[int] | None = None,
    *,
    expires_in_minutes: int = 5,
) -> AuthorizedScope:
    return AuthorizedScope(
        principal=Principal(id=1, kind=PrincipalKind.USER),
        repo_ids=frozenset(visible),
        granted_repo_ids=frozenset(granted if granted is not None else visible),
        expires_at=NOW + timedelta(minutes=expires_in_minutes),
    )


def test_predicate_lets_the_database_decide_public_and_binds_only_granted_ids():
    sql, params = sql_predicate("rep", scope({1, 4, 9}, granted={4, 9}), now=NOW)

    assert "eligible.verified_public" in sql
    assert "rep.repo_id = ANY(%(granted_repo_ids)s)" in sql
    assert params["granted_repo_ids"] == [4, 9]  # the public half is NOT enumerated
    assert "1" not in params["granted_repo_ids"]


def test_predicate_requires_live_rows():
    sql, _ = sql_predicate("rep", scope({1}), now=NOW)

    assert "rep.live" in sql


def test_predicate_accepts_a_custom_view_alias():
    sql, _ = sql_predicate("rep", scope({1}), eligible_alias="e", now=NOW)

    assert "e.verified_public" in sql


def test_a_user_with_no_grants_still_matches_public_rows():
    """An empty grant set is not an empty scope: the public half is the database's to decide."""
    sql, params = sql_predicate("rep", scope(set(), granted=set()), now=NOW)

    assert "eligible.verified_public" in sql
    assert params["granted_repo_ids"] == []


def test_an_expired_scope_matches_nothing():
    """Fail closed: a scope past its lease must not be turned into a query at all."""
    stale = scope({1, 2}, expires_in_minutes=-1)

    sql, params = sql_predicate("rep", stale, now=NOW)

    assert sql.strip() == "false"
    assert params == {}


def test_assert_rows_authorized_accepts_rows_inside_the_scope():
    assert_rows_authorized([{"repo_id": 1}, {"repo_id": 2}], scope({1, 2}))


def test_assert_rows_authorized_raises_and_counts_a_row_outside_the_scope():
    before = authorization_violation_total.value

    with pytest.raises(AuthorizationViolation) as excinfo:
        assert_rows_authorized([{"repo_id": 1}, {"repo_id": 99}], scope({1}))

    assert "99" in str(excinfo.value)
    assert authorization_violation_total.value == before + 1


def test_the_counter_does_not_move_when_every_row_is_authorized():
    before = authorization_violation_total.value

    assert_rows_authorized([{"repo_id": 1}], scope({1}))

    assert authorization_violation_total.value == before


@given(
    allowed=st.sets(st.integers(min_value=1, max_value=50), max_size=8),
    rows=st.lists(st.integers(min_value=1, max_value=50), max_size=12),
)
def test_assertion_accepts_exactly_the_rows_the_scope_allows(allowed, rows):
    """Property: the assertion agrees with the scope on every input, with no third outcome."""
    s = scope(allowed)
    row_dicts = [{"repo_id": r} for r in rows]

    if [r for r in rows if r not in allowed]:
        with pytest.raises(AuthorizationViolation):
            assert_rows_authorized(row_dicts, s)
    else:
        assert_rows_authorized(row_dicts, s)
