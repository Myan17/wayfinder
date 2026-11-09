"""One PR's bus state, rebuilt from its comments every time (REVIEW-BUS.md §4). The PR is the only state.

- `idle`: no review request names the current head.
- `requested`: the latest bus event for the current head is a `review_request`; the reviewer acts on this.
- `reviewed`: a `review_result` answered that request; `verdict` says how.
- `stopped`: after an `escalate`, or a `fix_pushed` that disputes a finding (rule 10), both sides stop
  until either account comments `resume` ("a comment from Myan restarts it"). Only that word counts:
  the author session's own briefs are ordinary comments from Myan17 and must not restart it.

Comments from anyone else, and bus messages from the wrong account, are skipped and their reasons kept
for the log (rule 8). A request names a head by at least its first 7 hex characters.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass

from reviewbus import protocol

_SHA = re.compile(r"[0-9a-f]{40}")
_PREFIX = re.compile(r"[0-9a-f]{7,40}")


@dataclass(frozen=True)
class State:
    status: str  # idle | requested | reviewed | stopped
    head: str
    round: int | None = None
    verdict: str | None = None
    reason: str = ""
    ignored: tuple[str, ...] = ()


def names_head(value: object, head: str) -> bool:
    return type(value) is str and bool(_PREFIX.fullmatch(value)) and head.startswith(value)


def state(comments: Sequence[dict], head: str, roster: str) -> State:
    """`comments` in posting order, each `{"author": login, "body": text}` as GitHub returns them."""
    if type(head) is not str or not _SHA.fullmatch(head):
        raise ValueError(f"head {head!r} is not a full commit sha")
    if type(comments) not in (list, tuple):
        raise TypeError("comments must be a list")
    accounts = {a.lower() for a in protocol.logins(roster).values()}
    ignored: list[str] = []
    stopped = ""
    current: State = State("idle", head)
    for i, c in enumerate(comments):
        if type(c) is not dict or type(c.get("author")) is not str or type(c.get("body")) is not str:
            raise TypeError(f"comment {i} is not {{author: str, body: str}}")
        try:
            m = protocol.parse(c["body"], c["author"], roster)
        except protocol.Ignored as e:
            ignored.append(f"comment {i} by {c['author']}: {e}")
            continue
        if m is None:
            if stopped and c["author"].lower() in accounts and c["body"].strip().lower() == "resume":
                stopped = ""  # Myan restarts the bus on this PR
            continue
        f = m.fields
        if m.type == "escalate":
            stopped = f"escalated: {f.get('reason')}"
        elif m.type == "fix_pushed" and f.get("disputes"):
            stopped = f"the author disputes {f['disputes']}"
        elif m.type == "review_request" and names_head(f.get("head"), head):
            if type(f.get("round")) is not int:
                ignored.append(f"comment {i}: review_request round {f.get('round')!r} is not an integer")
                continue
            current = State("requested", head, f["round"])
        elif m.type == "review_result" and names_head(f.get("head"), head) and current.status == "requested":
            if f.get("round") != current.round:
                ignored.append(
                    f"comment {i}: result for round {f.get('round')!r}, request is {current.round}"
                )
                continue
            current = State("reviewed", head, current.round, f.get("verdict"))
    if stopped:
        return State("stopped", head, current.round, current.verdict, stopped, tuple(ignored))
    return State(current.status, head, current.round, current.verdict, "", tuple(ignored))
