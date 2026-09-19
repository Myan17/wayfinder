"""Assembling an AuthorizedScope from leased facts -- DESIGN §9.1.1-9.1.2.

    allowed(principal, repo, t) =
          connection_eligible(repo, t)
      AND repository_eligible(repo, t)
      AND ( verified_public(repo, t) OR valid_user_grant(principal, repo, t) )

Every clause is a fact with an expiry. Expiry denies: a fact we could not refresh is not evidence
that disclosure is still permitted.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from wayfinder.authz.interface import AuthorizedScope, Principal

PUBLIC_ONLY = "permissions_public_only"


@dataclass(frozen=True, slots=True)
class RepoFact:
    """One repository's authorization facts, as last observed from GitHub."""

    repo_id: int
    visibility: str
    visibility_valid_until: datetime
    serving_state: str
    connection_state: str
    connection_valid_until: datetime

    def connection_eligible(self, now: datetime) -> bool:
        return self.connection_state == "active" and self.connection_valid_until > now

    def repository_eligible(self, now: datetime) -> bool:
        return self.serving_state == "active" and self.visibility_valid_until > now

    def verified_public(self, now: datetime) -> bool:
        """Public *and* the observation is still within its lease. Not `visibility == 'public'`."""
        return self.visibility == "public" and self.visibility_valid_until > now


def build_scope(
    principal: Principal,
    *,
    facts: list[RepoFact],
    grants: frozenset[int],
    grants_valid_until: datetime | None,
    now: datetime,
    policy_revision: int = 0,
) -> AuthorizedScope:
    grants_live = grants_valid_until is not None and grants_valid_until > now
    usable_grants = grants if grants_live else frozenset()

    visible: set[int] = set()
    deadlines: list[datetime] = []

    for f in facts:
        if not (f.connection_eligible(now) and f.repository_eligible(now)):
            continue
        if f.verified_public(now):
            visible.add(f.repo_id)
            deadlines.append(min(f.visibility_valid_until, f.connection_valid_until))
        elif f.repo_id in usable_grants:
            visible.add(f.repo_id)
            deadlines.append(min(f.visibility_valid_until, f.connection_valid_until, grants_valid_until))

    degraded: tuple[str, ...] = ()
    if grants and not grants_live:
        # The user-token half failed past its lease; repository facts may still be fresh.
        degraded = (PUBLIC_ONLY,)

    return AuthorizedScope(
        principal=principal,
        repo_ids=frozenset(visible),
        expires_at=min(deadlines) if deadlines else now,
        policy_revision=policy_revision,
        degraded=degraded,
    )
