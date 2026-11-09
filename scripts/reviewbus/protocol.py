"""The review bus's messages (ADR-0021, REVIEW-BUS.md §3): build them, parse them, check who sent them.

A bus message is a PR comment whose first line is a hidden header,
`<!-- reviewbus v1 {"type": ...} -->`; the rest is for humans. `veto <id>` and `confirm <id>` are plain
comments. A message counts only when its GitHub author is its role's account (rule 8): the repository is
public, so anyone else's comment is ignored, and `parse` says why. The two accounts are read from
`docs/team/ROSTER.md`, never written here.
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from check_gh_account import expected_login  # noqa: E402

VERSION = "v1"
AUTHOR, REVIEWER, EITHER = "author", "reviewer", "either"
HANDLES = {AUTHOR: "myan", REVIEWER: "gupta958"}  # ROSTER handles; their `github:` is the login

# type -> (required fields, the role that may send it). ADR-0021 rule 8 decides the roles.
TYPES: dict[str, tuple[frozenset[str], str]] = {
    "review_request": (frozenset({"pr", "head", "round"}), AUTHOR),
    "ruling_request": (frozenset({"pr", "questions"}), AUTHOR),
    "fix_pushed": (frozenset({"pr", "head", "round", "addressed", "disputes"}), AUTHOR),
    "escalate": (frozenset({"pr", "reason", "question"}), AUTHOR),
    "review_result": (frozenset({"pr", "head", "round", "verdict", "findings", "model", "gates"}), REVIEWER),
    "ruling": (
        frozenset({"pr", "id", "decision", "rationale", "model", "binds_at", "confirm_only"}),
        REVIEWER,
    ),
    "veto": (frozenset({"id"}), EITHER),
    "confirm": (frozenset({"id"}), EITHER),
}
PLAIN = ("veto", "confirm")  # written by hand as `veto <id>`, so they carry no header

_HEADER = re.compile(rf"<!-- reviewbus {VERSION} (\{{.*\}}) -->[ \t]*")
_PLAIN = re.compile(r"(veto|confirm)\s+(\S+)")


class Ignored(ValueError):
    """A comment that looks like a bus message but does not count; the reason is logged."""


@dataclass(frozen=True)
class Message:
    type: str
    fields: dict
    author: str
    text: str = field(default="", compare=False)


def logins(roster: str) -> dict[str, str]:
    out = {role: expected_login(roster, handle) for role, handle in HANDLES.items()}
    if not all(out.values()):
        raise ValueError(f"ROSTER.md is missing a bus account: {out}")
    return out  # type: ignore[return-value]


def needs_human(type_: str, fields: dict) -> bool:
    """Rule 11: a message asking for a human decision @-mentions the approving account."""
    return (
        type_ == "escalate"
        or (type_ == "ruling" and fields.get("confirm_only") is True)
        or (type_ == "review_result" and fields.get("verdict") in ("approve", "needs_human"))
    )


def build(type_: str, fields: dict, text: str, roster: str) -> str:
    """The comment body. Refuses an unknown type, a missing field, or a plain type."""
    if type_ not in TYPES or type_ in PLAIN:
        raise ValueError(f"cannot build a {type_!r} message")
    missing = TYPES[type_][0] - fields.keys()
    if missing:
        raise ValueError(f"{type_} is missing {sorted(missing)}")
    header = json.dumps({"type": type_, **fields}, sort_keys=True, separators=(",", ":"))
    if "-->" in header:
        raise ValueError("a field contains '-->', which would end the header early")
    mention = f"@{logins(roster)[REVIEWER]}"
    if needs_human(type_, fields) and mention.lower() not in text.lower():
        text = f"{mention} {text}"
    return f"<!-- reviewbus {VERSION} {header} -->\n{text}"


def parse(body: str, author: str, roster: str) -> Message | None:
    """The bus message in a comment, or None when the comment is not one. Raises `Ignored` when it
    looks like one but does not count: a bad header, a missing field, or the wrong author."""
    first, _, rest = body.lstrip().partition("\n")
    first = first.strip()
    if m := _PLAIN.fullmatch(first):
        type_, fields, text = m.group(1), {"id": m.group(2)}, rest
    elif first.startswith("<!-- reviewbus"):
        h = _HEADER.fullmatch(first)
        if not h:
            raise Ignored(f"unreadable header: {first[:80]!r}")
        try:
            data = json.loads(h.group(1))
        except ValueError as e:
            raise Ignored(f"header is not JSON: {e}") from e
        if not isinstance(data, dict) or data.get("type") not in TYPES or data["type"] in PLAIN:
            raise Ignored(f"unknown message type: {data.get('type') if isinstance(data, dict) else data!r}")
        type_ = data.pop("type")
        if missing := TYPES[type_][0] - data.keys():
            raise Ignored(f"{type_} is missing {sorted(missing)}")
        fields, text = data, rest
    else:
        return None
    role = TYPES[type_][1]
    accounts = logins(roster)
    allowed = set(accounts.values()) if role == EITHER else {accounts[role]}
    if author.lower() not in {a.lower() for a in allowed}:
        raise Ignored(f"{type_} from {author!r}, which may come only from {sorted(allowed)}")
    return Message(type_, fields, author, text)
