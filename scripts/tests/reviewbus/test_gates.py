import dataclasses
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # scripts/, for the reviewbus package
from reviewbus import gates as g

HEAD = "a" * 40
TIER = ("db/**", "scripts/reviewbus/**")
CLEAN = {"verdict": "approve", "findings": []}
NOTE = {"id": "n1", "file": "x.py", "line": None, "severity": "low", "blocking": False, "text": "nit"}
BLOCKER = {"id": "f1", "file": "x.py", "line": 3, "severity": "high", "blocking": True, "text": "bug"}


def review(**kw):
    base = dict(
        mode="on",
        round=1,
        reviewed_head=HEAD,
        pr_head=HEAD,
        files=["eval/harness/s2/passes.py"],
        checks={"unit": "success", "guardrails": "success"},
        required=["unit", "guardrails"],
        description=f"head `{HEAD[:7]}`",
        verdict=CLEAN,
        tier=TIER,
    )
    return g.Review(**{**base, **kw})


def test_every_gate_passing_in_on_mode_approves_and_merges():
    d = g.decide(review())
    assert (
        d.action == g.APPROVE and all(ok for ok, _ in d.gates.values()) and sorted(d.gates) == list("abcdef")
    )


@pytest.mark.parametrize(
    "change, gate",
    [
        (dict(files=["db/migrations/0009.sql"]), "b"),
        (dict(files=["scripts/reviewbus/gates.py"]), "b"),
        (dict(checks={"unit": "failure", "guardrails": "success"}), "c"),
        (dict(checks={"unit": "success"}), "c"),
        (dict(pr_head="b" * 40), "c"),
        (dict(description="head `0123456`"), "e"),
        (dict(description=f"head `b{HEAD[:7]}`"), "e"),
        (dict(description=f"head `{HEAD[:7]}b`"), "e"),
        (dict(tier=()), "b"),
        (dict(files=[]), "b"),
        (dict(files="db/migrations/0009.sql"), "b"),
        (dict(files=["ok.py", ""]), "b"),
        (dict(files=iter(["db/migrations/0009.sql"])), "b"),
        (dict(files={"db/migrations/0009.sql"}), "b"),
        (dict(files=["./db/migrations/0009.sql"]), "b"),
        (dict(files=["/db/migrations/0009.sql"]), "b"),
        (dict(files=["x/../db/migrations/0009.sql"]), "b"),
        (dict(files=["db//migrations/0009.sql"]), "b"),
        (dict(files=["db/migrations/"]), "b"),
        (dict(files=["db\\migrations\\0009.sql"]), "b"),
        (dict(reviewed_head="", pr_head="", description=""), "c"),
        (dict(reviewed_head="x", pr_head="x", description="x"), "c"),
        (dict(reviewed_head=HEAD[:7], pr_head=HEAD[:7]), "c"),
        (dict(reviewed_head="A" * 40, pr_head="A" * 40, description="AAAAAAA"), "e"),
        (dict(required=[], checks={}), "c"),
    ],
)
def test_each_gate_can_block_an_approval(change, gate):
    d = g.decide(review(**change))
    assert d.action == g.NEEDS_HUMAN and not d.gates[gate][0]


def test_shadow_never_goes_beyond_would_approve_even_with_every_other_gate_green():
    d = g.decide(review(mode="shadow"))
    assert d.action == g.WOULD_APPROVE and d.gates["a"] == (False, "WAYFINDER_AGENT_APPROVAL is shadow")


def test_off_does_nothing_and_an_unknown_mode_is_refused():
    assert (
        g.decide(review(mode="off", verdict={"verdict": "changes", "findings": [BLOCKER]})).action == g.NONE
    )
    with pytest.raises(ValueError, match="treats it as off"):
        g.decide(review(mode="ON"))


@pytest.mark.parametrize("mode", ["shadow", "on"])
def test_changes_or_a_blocking_finding_requests_changes_in_shadow_and_on(mode):
    assert (
        g.decide(review(mode=mode, verdict={"verdict": "changes", "findings": []})).action
        == g.REQUEST_CHANGES
    )
    approve_but_blocking = {"verdict": "approve", "findings": [BLOCKER]}
    d = g.decide(review(mode=mode, verdict=approve_but_blocking))
    assert d.action == g.REQUEST_CHANGES and d.gates["d"] == (False, "1 blocking finding(s)")


def test_a_needs_human_verdict_is_passed_to_a_human():
    assert g.decide(review(verdict={"verdict": "needs_human", "findings": []})).action == g.NEEDS_HUMAN


def test_round_four_escalates_whatever_the_verdict():
    d = g.decide(review(round=4))
    assert d.action == g.ESCALATE and d.gates["f"] == (False, "round 4 of 3")
    assert g.decide(review(round=3)).action == g.APPROVE


@pytest.mark.parametrize(
    "verdict, problem",
    [
        ("approve", "not a JSON object"),
        ({"verdict": "lgtm", "findings": []}, "is not one of"),
        ({"verdict": "approve"}, "findings is not a list"),
        ({"verdict": "approve", "findings": ["bad"]}, "finding 0 is not an object"),
        ({"verdict": "approve", "findings": [{**BLOCKER, "blocking": "yes"}]}, "no bool 'blocking'"),
        ({"verdict": "approve", "findings": [{**BLOCKER, "line": "3"}]}, "null or a positive integer"),
        ({"verdict": "approve", "findings": [{**BLOCKER, "line": 0}]}, "null or a positive integer"),
        ({"verdict": "approve", "findings": [{**NOTE, "severity": "garbage"}]}, "severity 'garbage'"),
        (
            {"verdict": "approve", "findings": [{k: v for k, v in NOTE.items() if k != "line"}]},
            "null or a positive integer",
        ),
    ],
)
def test_a_malformed_verdict_goes_to_a_human_and_never_approves(verdict, problem):
    assert problem in g.verdict_problem(verdict)
    for mode in ("shadow", "on"):
        assert g.decide(review(mode=mode, verdict=verdict)).action == g.NEEDS_HUMAN


def test_a_finding_with_a_null_line_is_valid_and_a_nonblocking_one_still_approves():
    assert g.decide(review(verdict={"verdict": "approve", "findings": [NOTE]})).action == g.APPROVE


def test_a_finding_with_a_null_line_is_valid():
    assert g.verdict_problem({"verdict": "changes", "findings": [{**BLOCKER, "line": None}]}) is None


def test_the_review_is_frozen():
    with pytest.raises(dataclasses.FrozenInstanceError):
        review().mode = "on"


def test_the_description_may_name_the_head_in_full_or_by_any_prefix_of_seven_or_more():
    for named in (HEAD, HEAD[:7], HEAD[:12]):
        assert g.description_current(review(description=f"head {named}."))[0], named
    assert not g.description_current(review(description=f"head {HEAD[:6]}"))[0]


def test_round_zero_or_a_non_integer_round_never_approves():
    for bad in (0, "1", True):
        d = g.decide(review(round=bad))
        assert d.action != g.APPROVE and not d.gates["f"][0], bad
