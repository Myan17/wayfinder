"""Row-level enforcement -- DESIGN §9.1.5.

Two layers, deliberately redundant:

1. `sql_predicate` -- the filter every query must carry. It sits on the scanned relation so that
   pgvector's iterative scan keeps scanning until enough *authorized* rows are found; a filter
   applied after a join cannot drive that (DESIGN §9.5, finding WF-13).
2. `assert_rows_authorized` -- defence in depth. It should never fire. Its counter is an alert, and
   in tests it is a hard failure, because the alternative is discovering a disclosure from a user.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from wayfinder.authz.interface import AuthorizedScope

PARAM = "authorized_repo_ids"


class AuthorizationViolation(Exception):
    """A row outside the authorized scope reached the caller. Stop-the-line (DESIGN §13.2)."""


def sql_predicate(alias: str, scope: AuthorizedScope) -> tuple[str, dict[str, Any]]:
    """Return the SQL fragment and parameters that filter `alias` to this scope.

    An empty scope yields `false` rather than an empty `ANY(...)`, so a scope that authorizes
    nothing cannot be mistaken for a query with no filter.
    """
    if not scope.repo_ids:
        return "false", {}
    fragment = f"({alias}.live AND {alias}.repo_id = ANY(%({PARAM})s))"
    return fragment, {PARAM: sorted(scope.repo_ids)}


def assert_rows_authorized(rows: Iterable[Mapping[str, Any]], scope: AuthorizedScope) -> None:
    """Raise if any row belongs to a repository outside the scope."""
    for row in rows:
        repo_id = row["repo_id"]
        if not scope.allows(repo_id):
            raise AuthorizationViolation(
                f"row from repo {repo_id} is outside the authorized scope "
                f"of principal {scope.principal.id} ({scope.principal.kind})"
            )
