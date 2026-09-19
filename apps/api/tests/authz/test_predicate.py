"""The one sanctioned way to filter rows -- DESIGN §9.1.5, card docs/context/modules/authz.md.

Both halves of the predicate come from here, so no call site can express them differently, and the
filter sits on the scanned relation so pgvector's iterative scan can keep scanning (DESIGN §9.5).
"""

from datetime import UTC, datetime, timedelta

import pytest
from hypothesis import given
from hypothesis import strategies as st

from wayfinder.authz.interface import AuthorizedScope, Principal, PrincipalKind
from wayfinder.authz.predicate import AuthorizationViolation, assert_rows_authorized, sql_predicate

NOW = datetime(2026, 9, 21, 12, 0, tzinfo=UTC)


def scope(repo_ids: set[int]) -> AuthorizedScope:
    return AuthorizedScope(
        principal=Principal(id=1, kind=PrincipalKind.USER),
        repo_ids=frozenset(repo_ids),
        expires_at=NOW + timedelta(minutes=5),
    )


def test_predicate_binds_repository_ids_as_a_parameter():
    sql, params = sql_predicate("r", scope({4, 9}))

    assert "r.repo_id = ANY(%(authorized_repo_ids)s)" in sql
    assert sorted(params["authorized_repo_ids"]) == [4, 9]
    assert "4" not in sql and "9" not in sql  # ids are bound, never formatted into the statement


def test_predicate_requires_live_rows():
    sql, _ = sql_predicate("r", scope({1}))

    assert "r.live" in sql


def test_empty_scope_produces_a_predicate_that_matches_nothing():
    """Fail closed: an empty scope must not degrade into an unfiltered query."""
    sql, params = sql_predicate("r", scope(set()))

    assert sql.strip() == "false"
    assert params == {}


def test_assert_rows_authorized_accepts_rows_inside_the_scope():
    assert_rows_authorized([{"repo_id": 1}, {"repo_id": 2}], scope({1, 2}))


def test_assert_rows_authorized_raises_on_a_row_outside_the_scope():
    with pytest.raises(AuthorizationViolation) as excinfo:
        assert_rows_authorized([{"repo_id": 1}, {"repo_id": 99}], scope({1}))

    assert "99" in str(excinfo.value)
    assert "repo" in str(excinfo.value).lower()


@given(
    allowed=st.sets(st.integers(min_value=1, max_value=50), max_size=8),
    rows=st.lists(st.integers(min_value=1, max_value=50), max_size=12),
)
def test_assertion_accepts_exactly_the_rows_the_scope_allows(allowed, rows):
    """Property: the assertion agrees with the scope on every input, with no third outcome."""
    s = scope(allowed)
    row_dicts = [{"repo_id": r} for r in rows]
    leaks = [r for r in rows if r not in allowed]

    if leaks:
        with pytest.raises(AuthorizationViolation):
            assert_rows_authorized(row_dicts, s)
    else:
        assert_rows_authorized(row_dicts, s)
