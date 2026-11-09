import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # scripts/, for the reviewbus package
from reviewbus import protocol as p

ROSTER = (p.ROOT / "docs/team/ROSTER.md").read_text()
REQ = {"pr": 7, "head": "abc1234", "round": 1}


def test_the_accounts_come_from_the_roster():
    assert p.logins(ROSTER) == {"author": "Myan17", "reviewer": "Gupta958"}
    with pytest.raises(ValueError, match="missing a bus account"):
        p.logins("engineers: []")


def test_a_built_message_parses_back_from_its_author():
    body = p.build("review_request", REQ, "Please review.", ROSTER)
    assert (
        body.splitlines()[0]
        == '<!-- reviewbus v1 {"head":"abc1234","pr":7,"round":1,"type":"review_request"} -->'
    )
    assert p.parse(body, "Myan17", ROSTER) == p.Message("review_request", REQ, "Myan17")


def test_a_message_from_the_wrong_account_is_ignored_with_a_reason():
    body = p.build("review_request", REQ, "x", ROSTER)
    for who in ("Gupta958", "mallory"):
        with pytest.raises(p.Ignored, match="may come only from"):
            p.parse(body, who, ROSTER)
    result = {**REQ, "verdict": "changes", "findings": [], "model": "m", "gates": {}}
    with pytest.raises(p.Ignored, match="review_result from 'Myan17'"):
        p.parse(p.build("review_result", result, "x", ROSTER), "Myan17", ROSTER)
    assert p.parse(p.build("review_result", result, "x", ROSTER), "gupta958", ROSTER).type == "review_result"


def test_veto_and_confirm_are_plain_comments_from_either_account_only():
    assert p.parse("veto r1-2", "Myan17", ROSTER) == p.Message("veto", {"id": "r1-2"}, "Myan17")
    assert p.parse("  confirm q3\nthanks", "Gupta958", ROSTER).fields == {"id": "q3"}
    with pytest.raises(p.Ignored):
        p.parse("veto r1-2", "mallory", ROSTER)
    assert p.parse("I would veto this", "Myan17", ROSTER) is None


def test_ordinary_comments_are_not_bus_messages():
    assert p.parse("LGTM", "Gupta958", ROSTER) is None
    assert p.parse("text\n<!-- reviewbus v1 {} -->", "Gupta958", ROSTER) is None  # header must be first


@pytest.mark.parametrize(
    "first, why",
    [
        ("<!-- reviewbus v1 not json -->", "unreadable header"),
        ("<!-- reviewbus v1 {nope} -->", "not JSON"),
        ('<!-- reviewbus v1 {"type":"approve_now"} -->', "unknown message type"),
        ('<!-- reviewbus v1 {"type":"veto","id":"x"} -->', "unknown message type"),
        ('<!-- reviewbus v1 {"type":"review_request","pr":1} -->', "missing"),
    ],
)
def test_a_malformed_header_is_ignored(first, why):
    with pytest.raises(p.Ignored, match=why):
        p.parse(first, "Myan17", ROSTER)


def test_build_refuses_what_parse_would_ignore():
    with pytest.raises(ValueError, match="missing"):
        p.build("review_request", {"pr": 1}, "x", ROSTER)
    with pytest.raises(ValueError, match="cannot build"):
        p.build("veto", {"id": "x"}, "x", ROSTER)
    with pytest.raises(ValueError, match="-->"):
        p.build("review_request", {**REQ, "head": "a --> b"}, "x", ROSTER)


def test_every_request_for_a_human_decision_mentions_gupta958():
    esc = p.build("escalate", {"pr": 1, "reason": "round 4", "question": "q"}, "Stopped.", ROSTER)
    assert esc.splitlines()[1] == "@Gupta958 Stopped."
    ruling = {"pr": 1, "id": "q1", "decision": "d", "rationale": "r", "model": "m", "binds_at": "t"}
    assert "@Gupta958" in p.build("ruling", {**ruling, "confirm_only": True}, "Confirm?", ROSTER)
    assert "@Gupta958" not in p.build("ruling", {**ruling, "confirm_only": False}, "Binds later.", ROSTER)
    result = {**REQ, "findings": [], "model": "m", "gates": {}}
    assert "@Gupta958" in p.build("review_result", {**result, "verdict": "approve"}, "Would approve.", ROSTER)
    assert "@Gupta958" not in p.build("review_result", {**result, "verdict": "changes"}, "Fix.", ROSTER)
    assert (
        p.build("escalate", {"pr": 1, "reason": "r", "question": "q"}, "@gupta958 x", ROSTER).count("@") == 1
    )


def test_the_header_is_one_line_of_sorted_json():
    body = p.build("fix_pushed", {**REQ, "addressed": ["f1"], "disputes": []}, "a\nb", ROSTER)
    header = body.splitlines()[0]
    assert json.loads(header[len("<!-- reviewbus v1 ") : -len(" -->")])["addressed"] == ["f1"]
