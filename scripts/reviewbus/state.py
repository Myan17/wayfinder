"""One PR's bus state, rebuilt from its comments every time (REVIEW-BUS.md §4). The PR is the only state.

- `idle`: no review request names the current head.
- `requested`: the latest bus event for the current head is a `review_request`; the reviewer acts on this.
- `reviewed`: a `review_result` answered that request; `verdict` says how. An undisputed `fix_pushed`
  is the next request. Rounds must count up by one from 1; a third failing round stops the PR.
- `needs_human`: the result handed this head to Myan; no later request for the same head counts.
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

from reviewbus import gates, protocol

_SHA = re.compile(r"[0-9a-f]{40}")
_PREFIX = re.compile(r"[0-9a-f]{7,40}")


@dataclass(frozen=True)
class State:
    status: str  # idle | requested | reviewed | needs_human | stopped
    head: str
    round: int | None = None
    verdict: str | None = None
    reason: str = ""
    ignored: tuple[str, ...] = ()


def names_head(value: object, head: str) -> bool:
    return type(value) is str and bool(_PREFIX.fullmatch(value)) and head.startswith(value)


def same_commit(a: str, b: str) -> bool:
    return a.startswith(b) or b.startswith(a)


def state(comments: Sequence[dict], head: str, roster: str) -> State:
    """`comments` in posting order, each `{"author": login, "body": text}` as GitHub returns them."""
    if type(head) is not str or not _SHA.fullmatch(head):
        raise ValueError(f"head {head!r} is not a full commit sha")
    if type(comments) not in (list, tuple):
        raise TypeError("comments must be a list")
    accounts = {a.lower() for a in protocol.logins(roster).values()}
    ignored: list[str] = []
    stopped, last_round = "", 0
    req: tuple[str, int] | None = None  # (head prefix, round) of the latest accepted request
    verdict: str | None = None
    for_human: list[str] = []  # heads a needs_human result handed to Myan

    def skip(i: int, why: str) -> None:
        ignored.append(f"comment {i}: {why}")

    for i, c in enumerate(comments):
        if type(c) is not dict or type(c.get("author")) is not str or type(c.get("body")) is not str:
            raise TypeError(f"comment {i} is not {{author: str, body: str}}")
        try:
            m = protocol.parse(c["body"], c["author"], roster)
        except protocol.Ignored as e:
            skip(i, f"by {c['author']}: {e}")
            continue
        if m is None:
            if stopped and c["author"].lower() in accounts and c["body"].strip().lower() == "resume":
                stopped, last_round = "", 0  # Myan restarts the bus on this PR, with fresh rounds
            continue
        f = m.fields
        if m.type == "escalate":
            stopped = f"escalated: {f.get('reason')}"
        elif m.type == "fix_pushed" and f.get("disputes"):
            stopped = f"the author disputes {f['disputes']}"
        elif m.type in ("review_request", "fix_pushed"):  # an undisputed fix asks for the next round
            h, rnd = f.get("head"), f.get("round")
            if type(h) is not str or not _PREFIX.fullmatch(h) or type(rnd) is not int:
                skip(i, f"{m.type} needs a hex head and an integer round, got {h!r}, {rnd!r}")
            elif rnd != last_round + 1:
                skip(i, f"{m.type} round {rnd}, but the next round is {last_round + 1}")
            elif any(same_commit(h, x) for x in for_human):
                skip(i, f"{m.type} for {h}, which a needs_human result handed to Myan")
            else:
                req, verdict, last_round = (h, rnd), None, rnd
                if rnd > gates.MAX_ROUND:
                    stopped = f"round {rnd}: three rounds without a pass (rule 10)"
        elif m.type == "review_result":
            h, rnd, v = f.get("head"), f.get("round"), f.get("verdict")
            if req is None or verdict is not None:
                skip(i, "review_result with no open request")
            elif type(h) is not str or not _PREFIX.fullmatch(h) or not same_commit(h, req[0]):
                skip(i, f"review_result for {h!r}, request is for {req[0]}")
            elif type(rnd) is not int or rnd != req[1]:
                skip(i, f"review_result for round {rnd!r}, request is {req[1]}")
            elif type(v) is not str or v not in gates.VERDICTS:
                skip(i, f"review_result verdict {v!r} is not one of {gates.VERDICTS}")
            else:
                verdict = v
                if v == "needs_human":
                    for_human.append(req[0])
                elif v != "approve" and rnd >= gates.MAX_ROUND:
                    stopped = f"round {rnd}: three rounds without a pass (rule 10)"
    rnd = req[1] if req else None
    if stopped:
        return State("stopped", head, rnd, verdict, stopped, tuple(ignored))
    if req is None or not same_commit(req[0], head) or not names_head(req[0], head):
        return State("idle", head, rnd, None, "", tuple(ignored))
    status = "requested" if verdict is None else "needs_human" if verdict == "needs_human" else "reviewed"
    return State(status, head, rnd, verdict, "", tuple(ignored))
