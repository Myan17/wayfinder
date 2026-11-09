import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # scripts/, for the reviewbus package
from reviewbus import protocol, state

ROSTER = (protocol.ROOT / "docs/team/ROSTER.md").read_text()
HEAD, OLD = "a" * 40, "b" * 40


def request(head=HEAD, round=1, who="Myan17"):
    body = protocol.build("review_request", {"pr": 1, "head": head[:7], "round": round}, "Review.", ROSTER)
    return {"author": who, "body": body}


def result(verdict="changes", head=HEAD, round=1, who="Gupta958"):
    fields = {
        "pr": 1,
        "head": head[:7],
        "round": round,
        "verdict": verdict,
        "findings": [],
        "model": "m",
        "gates": {},
    }
    return {"author": who, "body": protocol.build("review_result", fields, "Result.", ROSTER)}


def bus(type_, who="Myan17", **fields):
    return {"author": who, "body": protocol.build(type_, {"pr": 1, **fields}, "x", ROSTER)}


def say(text, who="Myan17"):
    return {"author": who, "body": text}


def run(*comments):
    return state.state(list(comments), HEAD, ROSTER)


def test_no_request_for_the_current_head_is_idle():
    assert run().status == "idle"
    assert run(request(head=OLD), result(head=OLD)).status == "idle"  # an old head's review is history


def test_a_request_for_the_current_head_is_requested_until_its_result():
    assert run(request()) == state.State("requested", HEAD, 1)
    assert run(request(), result("approve")) == state.State("reviewed", HEAD, 1, "approve")


def test_a_later_request_for_the_same_head_asks_again():
    got = run(request(), result("changes"), request(round=2))  # the author asks again after a fix
    assert (got.status, got.round, got.verdict) == ("requested", 2, None)


def test_a_result_must_answer_the_current_request():
    assert run(result("approve")).status == "idle"  # no request yet
    got = run(request(), result("approve", round=2))
    assert got.status == "requested" and "round 2, request is 1" in got.ignored[0]


def test_wrong_accounts_are_skipped_and_logged():
    got = run(
        request(who="mallory"), request(), result("approve", who="Myan17"), result("approve", who="eve")
    )
    assert got.status == "requested" and len(got.ignored) == 3
    assert "review_request from 'mallory'" in got.ignored[0]


def test_escalate_stops_the_pr_until_either_account_says_resume():
    esc = bus("escalate", reason="round 4", question="q")
    assert run(request(), esc).status == "stopped"
    assert run(request(), esc, request(round=2)).status == "stopped"  # the author cannot restart it
    assert run(request(), esc, say("resume", who="mallory")).status == "stopped"
    assert run(request(), esc, say("@Gupta958 brief: fixed it", who="Myan17")).status == "stopped"
    for who in ("Myan17", "Gupta958"):
        assert run(request(), esc, say(" Resume\n", who=who)).status == "requested"


def test_a_dispute_stops_the_pr_but_an_undisputed_fix_does_not():
    disputed = bus("fix_pushed", head="c" * 7, round=1, addressed=[], disputes=["f1"])
    got = run(request(), disputed)
    assert got.status == "stopped" and "disputes ['f1']" in got.reason
    plain = bus("fix_pushed", head="c" * 7, round=1, addressed=["f1"], disputes=[])
    assert run(request(), plain).status == "requested"


def test_a_head_is_named_by_seven_or_more_hex_characters_of_the_current_head():
    assert state.names_head(HEAD[:7], HEAD) and state.names_head(HEAD, HEAD)
    for bad in (HEAD[:6], "A" * 7, "b" * 7, 7, None):
        assert not state.names_head(bad, HEAD)


def test_a_request_with_a_non_integer_round_is_skipped():
    body = protocol.build("review_request", {"pr": 1, "head": HEAD[:7], "round": "1"}, "x", ROSTER)
    got = run({"author": "Myan17", "body": body})
    assert got.status == "idle" and "an integer round" in got.ignored[0]


def test_inputs_must_be_plain():
    with pytest.raises(ValueError, match="full commit sha"):
        state.state([], HEAD[:7], ROSTER)
    with pytest.raises(TypeError, match="must be a list"):
        state.state(iter([]), HEAD, ROSTER)
    with pytest.raises(TypeError, match="comment 0"):
        state.state([{"author": "Myan17"}], HEAD, ROSTER)


def fix(head, round, disputes=()):
    return bus("fix_pushed", head=head[:7], round=round, addressed=["f1"], disputes=list(disputes))


def test_an_undisputed_fix_on_a_new_head_is_the_next_request():  # Codex f1
    got = run(request(head=OLD), result("changes", head=OLD), fix(HEAD, 2))
    assert (got.status, got.round) == ("requested", 2)
    got = run(request(head=OLD), result("changes", head=OLD), fix(HEAD, 2), result("approve", round=2))
    assert (got.status, got.verdict) == ("reviewed", "approve")


def test_needs_human_ends_the_bus_on_that_head():  # Codex f2
    got = run(request(), result("needs_human"), request(round=2))
    assert got.status == "needs_human" and "handed to Myan" in got.ignored[0]
    assert run(request(head=OLD), result("needs_human", head=OLD), fix(HEAD, 2)).status == "requested"


def test_rounds_count_up_by_one_and_a_third_failure_stops():  # Codex f3
    r1, r2, r3 = (result("changes", round=n) for n in (1, 2, 3))
    got = run(request(), r1, request(round=1))
    assert got.status == "reviewed" and "next round is 2" in got.ignored[0]
    assert run(request(round=2)).status == "idle"  # the first request must be round 1
    stopped = run(request(), r1, request(round=2), r2, request(round=3), r3)
    assert stopped.status == "stopped" and "three rounds without a pass" in stopped.reason
    assert (
        run(request(), r1, request(round=2), r2, request(round=3), result("approve", round=3)).status
        == "reviewed"
    )
    after = run(request(), r1, request(round=2), r2, request(round=3), r3, request(round=1))
    assert after.status == "stopped"  # no reset without Myan
    resumed = run(request(), r1, request(round=2), r2, request(round=3), r3, say("resume"), request(round=1))
    assert (resumed.status, resumed.round) == ("requested", 1)


@pytest.mark.parametrize(
    "bad, why",
    [
        (result("approve", round=True), "round True"),
        (result({"x": 1}), "verdict {'x': 1}"),
        (result("lgtm"), "verdict 'lgtm'"),
        (result("approve", head=OLD), "request is for aaaaaaa"),
    ],
)
def test_a_malformed_result_is_skipped_and_a_valid_one_still_counts(bad, why):  # Codex f4
    got = run(request(), bad, result("approve"))
    assert (got.status, got.verdict) == ("reviewed", "approve") and why in got.ignored[0]
