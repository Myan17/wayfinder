"""Public interface of the `authz` module -- see docs/context/modules/authz.md.

Nothing outside this file is part of the contract. Callers depend on these types, `scope.build_scope`
and `predicate.sql_predicate`; everything else in the package may change without notice.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum


class PrincipalKind(StrEnum):
    USER = "user"
    ANONYMOUS = "anonymous"


@dataclass(frozen=True, slots=True)
class Principal:
    """Who is asking. Anonymous visitors are principals too, with their own id.

    `user_id IS NULL` is never treated as "everyone" (DESIGN §9.1.5, finding WF-04).
    """

    id: int
    kind: PrincipalKind

    @property
    def is_anonymous(self) -> bool:
        return self.kind is PrincipalKind.ANONYMOUS


@dataclass(frozen=True, slots=True)
class AuthorizedScope:
    """What this principal may see, and until when.

    `expires_at` is authoritative: a caller must not serve from this scope past it, and a long
    request re-checks rather than assuming (DESIGN §9.1.5).
    """

    principal: Principal
    repo_ids: frozenset[int]
    """Everything this principal may see: verified-public plus granted. Used for cache keys and the
    post-retrieval assertion."""

    granted_repo_ids: frozenset[int] = frozenset()
    """The granted half alone. The SQL predicate binds only these, and lets the database decide
    public-ness through the eligible_repo view (DESIGN 9.1.5)."""

    expires_at: datetime = None  # type: ignore[assignment]
    policy_revision: int = 0
    degraded: tuple[str, ...] = field(default_factory=tuple)

    def allows(self, repo_id: int) -> bool:
        return repo_id in self.repo_ids
