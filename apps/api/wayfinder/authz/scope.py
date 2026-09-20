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
from wayfinder.authz.metrics import anonymous_grants_rejected_total

PUBLIC_ONLY = "permissions_public_only"


class AnonymousGrantsError(ValueError):
    """An anonymous principal was given grants: no GitHub token stands behind one, so the resolver is
    wrong. The kernel refuses rather than dropping them silently, which would let a broken resolver
    look healthy in every test that does not check for it (review of #1, F1)."""


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
    if principal.is_anonymous and grants:
        # Counted where it is raised, so the signal exists before a handler does (reviewer, F1).
        anonymous_grants_rejected_total.increment()
        raise AnonymousGrantsError(
            f"anonymous principal {principal.id} was given {len(grants)} grant(s); "
            "anonymous visitors hold none"
        )

    grants_live = grants_valid_until is not None and grants_valid_until > now
    usable_grants = grants if grants_live else frozenset()

    visible: set[int] = set()
    granted_visible: set[int] = set()
    deadlines: list[datetime] = []

    for f in facts:
        if not (f.connection_eligible(now) and f.repository_eligible(now)):
            continue
        if f.verified_public(now):
            visible.add(f.repo_id)
            deadlines.append(min(f.visibility_valid_until, f.connection_valid_until))
        elif f.repo_id in usable_grants:
            visible.add(f.repo_id)
            granted_visible.add(f.repo_id)
            deadlines.append(min(f.visibility_valid_until, f.connection_valid_until, grants_valid_until))

    # Staleness drives the flag, not whether a grant is held: an empty-but-stale set hid the
    # degradation before (F4). Anonymous principals are never flagged - public-only is normal there.
    degraded: tuple[str, ...] = ()
    if not principal.is_anonymous and not grants_live:
        degraded = (PUBLIC_ONLY,)

    return AuthorizedScope(
        principal=principal,
        repo_ids=frozenset(visible),
        granted_repo_ids=frozenset(granted_visible),
        expires_at=min(deadlines) if deadlines else now,
        policy_revision=policy_revision,
        degraded=degraded,
    )
