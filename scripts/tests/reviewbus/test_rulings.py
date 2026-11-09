import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # scripts/, for the reviewbus package
from reviewbus import protocol, rulings

ROSTER = (protocol.ROOT / "docs/team/ROSTER.md").read_text()
OWNERSHIP = """
```yaml
modules:
  authz:         {owner: myan, paths: ["apps/api/wayfinder/authz/**"]}
  egress:        {owner: myan, paths: ["apps/api/wayfinder/egress/**"]}
  webhooks:      {owner: myan, paths: ["apps/ingestd/internal/webhook/**"]}
  schema:        {owner: joint, paths: ["db/**"]}
  eval-harness:  {owner: myan, paths: ["eval/harness/**"]}
```
"""
POSTED = "2026-11-09T05:00:00Z"
T0 = datetime(2026, 11, 9, 5, tzinfo=UTC)


def only(labels, files=("eval/harness/s2/passes.py",)):
    return rulings.confirm_only(labels, list(files), OWNERSHIP)


@pytest.mark.parametrize("label", sorted(rulings.LABELS))
def test_every_confirm_only_class_never_binds_by_silence(label):
    assert only([label])


def test_an_ordinary_label_on_an_ordinary_path_may_bind():
    assert not only(["design"]) and not only([])


@pytest.mark.parametrize(
    "files",
    [
        ["scripts/reviewbus/gates.py"],
        ["AGENTS.md"],
        [".github/CODEOWNERS"],
        ["docs/team/ROSTER.md"],
        ["docs/adr/ADR-0021-review-bus.md"],
        ["docs/adr/ADR-0019-s2.md"],  # acceptance rules (Codex f1)
        ["docs/DESIGN.md"],  # gate dates and §19.8 cuts (Codex f1)
        ["ORIENT.md"],
        ["apps/api/wayfinder/authz/predicate.py"],
        ["eval/harness/x.py", "apps/api/wayfinder/egress/proxy.py"],
    ],
)
def test_a_pr_touching_the_bus_its_rules_authz_or_egress_is_confirm_only_whatever_the_labels(files):
    assert only(["design"], files)


def test_an_unlabeled_gate_date_or_cut_question_on_design_is_confirm_only():  # Codex f1
    assert only([], ["docs/DESIGN.md"]) and only(["schedule"], ["docs/DESIGN.md"])


def test_an_unlabeled_question_on_any_human_only_path_is_confirm_only():
    assert only([], ["db/migrations/0009.sql"])
    assert not only(["design"], ["db/migrations/0009.sql"])  # labeled, and schema is not a confirm-only class


@pytest.mark.parametrize("labels", [["typo-label"], "design", None, [1]])
def test_in_doubt_it_is_confirm_only(labels):
    assert only(labels)


def test_unreadable_ownership_is_doubt():
    assert rulings.confirm_only([], ["eval/x.py"], "no yaml here")
    assert rulings.confirm_only([], ["eval/x.py"], OWNERSHIP.replace("  egress:", "  outbound:"))


def ruling(confirm_only=False, decision="A", id_="q1"):
    return {"id": id_, "decision": decision, "confirm_only": confirm_only}


def say(body, who="Myan17", at="2026-11-09T06:00:00Z"):
    return {"author": who, "body": body, "created_at": at}


def status(r, comments=(), hours=1):
    return rulings.status(r, POSTED, list(comments), T0 + timedelta(hours=hours), ROSTER)


def test_a_ruling_binds_exactly_twelve_hours_after_it_is_posted():
    assert rulings.binds_at(POSTED) == "2026-11-09T17:00:00Z"
    assert status(ruling(), hours=11.99) == "pending"
    assert status(ruling(), hours=12) == "bound"


def test_a_veto_from_either_account_before_the_deadline_stops_it():
    for who in ("Myan17", "Gupta958"):
        assert status(ruling(), [say("veto q1", who)], hours=20) == "vetoed"
    assert status(ruling(), [say("veto q1", "mallory")], hours=20) == "bound"  # a third account is ignored
    assert status(ruling(), [say("veto q2")], hours=20) == "bound"  # another question's id


def test_a_veto_after_it_bound_does_not_unbind_it():
    assert status(ruling(), [say("veto q1", at="2026-11-09T17:00:01Z")], hours=20) == "bound"


def test_confirm_binds_at_once_and_a_comment_from_before_the_ruling_does_not_count():
    assert status(ruling(), [say("confirm q1")], hours=1) == "confirmed"
    assert status(ruling(), [say("confirm q1", at="2026-11-09T04:59:59Z")], hours=1) == "pending"


def test_a_confirm_only_ruling_waits_for_confirm_however_long_it_takes():
    assert status(ruling(True), hours=1000) == "awaiting_confirm"
    assert status(ruling(True), [say("confirm q1", "Gupta958")], hours=1000) == "confirmed"
    assert status(ruling(True), [say("veto q1", at="2026-11-12T00:00:00Z")], hours=1000) == "vetoed"


def test_an_abstained_ruling_never_binds():
    assert status(ruling(decision="needs_human"), hours=1000) == "needs_human"
    assert status(ruling(decision="needs_human"), [say("confirm q1")], hours=1000) == "needs_human"


def test_bad_times_and_fields_are_refused():
    for bad in (
        "2026-11-09 05:00:00",
        "2026-11-09T05:00:00+00:00",
        "",
        None,
        "2026-11- 9T05:00:00Z",
        "2026-11-09t05:00:00Z",
    ):
        with pytest.raises(ValueError):
            rulings.binds_at(bad)
    with pytest.raises(ValueError, match="confirm_only"):
        status({"id": "q1", "decision": "A", "confirm_only": "no"})
    with pytest.raises(ValueError, match="timezone"):
        rulings.status(ruling(), POSTED, [], datetime(2026, 11, 10), ROSTER)
