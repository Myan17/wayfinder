"""Fake authorization for consumers -- see docs/context/modules/authz.md, AGENTS.md 3.4.

`retrieval`, `answer`, `cache` and `http` build against this instead of waiting for the database
layer. It implements the same invariants the card claims, and the contract tests in
apps/api/tests/authz run against both this and the real implementation, so the fake cannot drift
into being more permissive than production.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta

from wayfinder.authz.interface import AuthorizedScope, Principal, PrincipalKind
from wayfinder.authz.scope import RepoFact, build_scope

DEFAULT_LEASE = timedelta(minutes=10)


@dataclass
class FixtureAuthz:
    """An in-memory authorization source driven by a fixture, not by GitHub.

    `public` and `private` are repository ids; `grants` maps principal id -> repository ids.
    """

    public: set[int] = field(default_factory=set)
    private: set[int] = field(default_factory=set)
    grants: dict[int, set[int]] = field(default_factory=dict)
    denied: set[int] = field(default_factory=set)
    grants_stale_for: set[int] = field(default_factory=set)

    def facts(self, now: datetime) -> list[RepoFact]:
        horizon = now + DEFAULT_LEASE
        return [
            RepoFact(
                repo_id=repo_id,
                visibility="public" if repo_id in self.public else "private",
                visibility_valid_until=horizon,
                serving_state="denied" if repo_id in self.denied else "active",
                connection_state="active",
                connection_valid_until=horizon,
            )
            for repo_id in sorted(self.public | self.private)
        ]

    def scope_for(self, principal: Principal, *, now: datetime) -> AuthorizedScope:
        stale = principal.id in self.grants_stale_for
        # An anonymous principal cannot hold a grant: grants come from a GitHub user token, and
        # there is no user. Modelling that here keeps the fake from being more permissive than
        # production, where the join simply returns no rows (DESIGN 9.1.1 rule 2).
        held = set() if principal.is_anonymous else self.grants.get(principal.id, set())
        return build_scope(
            principal,
            facts=self.facts(now),
            grants=frozenset(held),
            grants_valid_until=(now - timedelta(seconds=1)) if stale else (now + DEFAULT_LEASE),
            now=now,
        )

    def anonymous(self, principal_id: int = 1) -> Principal:
        return Principal(id=principal_id, kind=PrincipalKind.ANONYMOUS)

    def user(self, principal_id: int) -> Principal:
        return Principal(id=principal_id, kind=PrincipalKind.USER)
