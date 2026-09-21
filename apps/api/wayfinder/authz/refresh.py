"""Fenced grant refresh -- DESIGN §9.1.3-9.1.4.

Refresh is *repair*, never enforcement: denial happens synchronously when the event arrives, and a
refresh can only ever agree with a newer decision, never overrule it. Three rules do that:

- **capture before fetching** -- a refresh carries the revision it started from;
- **compare before installing** -- if the revision moved, the result is discarded;
- **all or nothing** -- a partial page listing is not a successful refresh and never extends a lease.

This module is pure: the caller owns the advisory lock (single flight) and the transaction.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from enum import StrEnum


@dataclass(frozen=True, slots=True)
class AccessState:
    """A principal's grants and the lease that makes them expire."""

    principal_id: int
    revision: int
    grants: frozenset[int]
    valid_until: datetime


@dataclass(frozen=True, slots=True)
class RefreshToken:
    """Captured before any network call, checked before anything is installed."""

    principal_id: int
    revision: int


class RefreshOutcome(StrEnum):
    APPLIED = "applied"
    STALE = "stale"
    INCOMPLETE = "incomplete"


@dataclass(frozen=True, slots=True)
class RefreshResult:
    outcome: RefreshOutcome
    state: AccessState


def start_refresh(state: AccessState) -> RefreshToken:
    return RefreshToken(principal_id=state.principal_id, revision=state.revision)


def apply_refresh(
    state: AccessState,
    token: RefreshToken,
    *,
    fetched: set[int],
    complete: bool,
    now: datetime,
    lease: timedelta,
) -> RefreshResult:
    if not complete:
        # A failed page means we do not know the whole set. Leave the old lease expiring.
        return RefreshResult(RefreshOutcome.INCOMPLETE, state)
    if token.principal_id != state.principal_id or token.revision != state.revision:
        # Something decided after this refresh began. Newer decisions win.
        return RefreshResult(RefreshOutcome.STALE, state)
    return RefreshResult(
        RefreshOutcome.APPLIED,
        replace(state, grants=frozenset(fetched), valid_until=now + lease),
    )


def invalidate_repo(state: AccessState, *, repo_id: int, now: datetime) -> AccessState:
    """Drop a repository's grant and expire the lease immediately, bumping the revision.

    Bumping the revision is what fences any refresh already in flight.
    """
    return replace(
        state,
        revision=state.revision + 1,
        grants=state.grants - {repo_id},
        valid_until=now,
    )
