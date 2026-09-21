"""Row-level enforcement -- DESIGN 9.1.5.

Two layers, deliberately redundant:

1. `sql_predicate` -- the filter every query must carry. The database decides public-ness through
   the `eligible_repo` view; we bind only the granted repository ids. Both halves sit on relations
   the scan touches, so pgvector's iterative scan can keep scanning until enough *authorized* rows
   are found, and the parameter stays small for an organisation with thousands of public
   repositories.
2. `assert_rows_authorized` -- defence in depth against the first layer being wrong or bypassed. It
   should never fire; when it does it increments an unsampled counter and raises, because the
   alternative is learning about a disclosure from a user.

The two layers deliberately compute the answer differently: SQL asks the database, the assertion
asks the scope that Python built from leased facts. If they disagree, the request fails rather than
serving the difference.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from datetime import UTC, datetime
from typing import Any

from wayfinder.authz.interface import AuthorizedScope
from wayfinder.authz.metrics import authorization_violation_total

PARAM = "granted_repo_ids"


class AuthorizationViolation(Exception):
    """A row outside the authorized scope reached the caller. Stop-the-line (DESIGN 13.2)."""


def sql_predicate(
    row_alias: str,
    scope: AuthorizedScope,
    *,
    eligible_alias: str = "eligible",
    now: datetime | None = None,
) -> tuple[str, dict[str, Any]]:
    """Return the SQL fragment and parameters that filter `row_alias` for this principal.

    The caller joins `eligible_repo` as `eligible_alias`; this fragment then reads:

        row.live AND (eligible.verified_public OR row.repo_id = ANY(%(granted_repo_ids)s))

    A scope past its lease yields `false`: an expired authorization is not evidence that disclosure
    is still permitted, and turning it into a query would be exactly that. `now` exists so tests can
    pin the boundary; it defaults to the real clock, because an optional expiry check is one omitted
    argument away from being no check at all.
    """
    if now is None:
        now = datetime.now(UTC)
    if scope.expires_at <= now:
        return "false", {}
    fragment = (
        f"({row_alias}.live AND ({eligible_alias}.verified_public OR {row_alias}.repo_id = ANY(%({PARAM})s)))"
    )
    return fragment, {PARAM: sorted(scope.granted_repo_ids)}


def assert_rows_authorized(rows: Iterable[Mapping[str, Any]], scope: AuthorizedScope) -> None:
    """Raise if any row belongs to a repository outside the scope, counting the violation first."""
    for row in rows:
        repo_id = row["repo_id"]
        if not scope.allows(repo_id):
            authorization_violation_total.increment()
            raise AuthorizationViolation(
                f"row from repo {repo_id} is outside the authorized scope "
                f"of principal {scope.principal.id} ({scope.principal.kind})"
            )
