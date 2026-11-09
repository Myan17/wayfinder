"""ADR-0021 rule 7: when a ruling by gupta958's agent binds, and which rulings only Myan can bind.

A ruling binds 12 hours after it is posted unless either account comments `veto <id>` first.
`confirm <id>` binds it at once. A confirm-only ruling never binds by silence: it waits for `confirm`.
A ruling whose decision is `needs_human` (the ruler abstained) never binds. A veto that arrives after a
ruling has bound does not unbind it, because the author may already have built on it; Myan reverses a
bound ruling with a new question.

Confirm-only is decided here from the question's labels and the PR's changed paths, never by the
model, and in doubt a ruling is confirm-only.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime, timedelta

from reviewbus import protocol, tier

VETO_WINDOW = timedelta(hours=12)
ABSTAIN = "needs_human"
LABELS = frozenset(
    {"bus", "agents-md", "codeowners", "roster", "gate-date", "cut", "authz", "egress", "acceptance-rule"}
)  # rule 7's confirm-only list, one label per class
KNOWN = LABELS | {"design", "scope", "schedule", "evidence", "naming"}  # labels that may bind by silence
RULE_PATHS = (
    "AGENTS.md",
    ".github/CODEOWNERS",
    "docs/team/ROSTER.md",
    "docs/adr/ADR-0021-review-bus.md",
    "docs/team/REVIEW-BUS.md",
    "scripts/reviewbus/**",
    "scripts/tests/reviewbus/**",
)


def parse_time(value: object) -> datetime:
    """GitHub's `2026-11-09T05:23:00Z`, strictly; anything else raises ValueError."""
    if type(value) is not str or not value.endswith("Z") or len(value) != 20:
        raise ValueError(f"{value!r} is not a UTC timestamp like 2026-11-09T05:23:00Z")
    return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)


def binds_at(posted_at: str) -> str:
    return (parse_time(posted_at) + VETO_WINDOW).strftime("%Y-%m-%dT%H:%M:%SZ")


def confirm_only(labels: object, files: Sequence[str], ownership: str | None = None) -> bool:
    """True when only Myan's `confirm` may bind the ruling. Malformed input is treated as in doubt."""
    if type(labels) is not list or any(type(x) is not str for x in labels):
        return True
    if type(files) not in (list, tuple) or any(type(f) is not str for f in files):
        return True
    if any(x in LABELS or x not in KNOWN for x in labels):
        return True
    text = ownership if ownership is not None else (tier.ROOT / "docs/team/OWNERSHIP.md").read_text()
    try:
        modules, everything = tier.module_paths(text), tier.globs(text)
    except ValueError:
        return True  # cannot tell which paths are sensitive: in doubt
    sensitive = (*RULE_PATHS, *modules["authz"], *modules["egress"])
    if tier.human_only(files, sensitive):
        return True
    return not labels and bool(tier.human_only(files, everything))  # unlabeled, on a tier path


def status(ruling: dict, posted_at: str, comments: Sequence[dict], now: datetime, roster: str) -> str:
    """One of needs_human, vetoed, confirmed, bound, awaiting_confirm or pending.

    `comments` are the PR's comments posted after the ruling, in order, each
    `{"author", "body", "created_at"}`. Only `veto`/`confirm` from either account, naming this id, count.
    """
    if ruling.get("decision") == ABSTAIN:
        return "needs_human"
    if type(ruling.get("confirm_only")) is not bool:
        raise ValueError("ruling has no boolean confirm_only")
    if now.tzinfo is None:
        raise ValueError("now must be timezone-aware")
    deadline = parse_time(posted_at) + VETO_WINDOW
    for c in comments:
        try:
            m = protocol.parse(c["body"], c["author"], roster)
        except protocol.Ignored:
            continue
        if m is None or m.type not in ("veto", "confirm") or m.fields["id"] != ruling.get("id"):
            continue
        at = parse_time(c["created_at"])
        if at < parse_time(posted_at):
            continue  # a comment from before the ruling cannot answer it
        if m.type == "confirm":
            return "confirmed"
        if ruling["confirm_only"] or at < deadline:
            return "vetoed"
    if ruling["confirm_only"]:
        return "awaiting_confirm"
    return "bound" if now >= deadline else "pending"
