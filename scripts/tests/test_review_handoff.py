"""The two things that must not drift in the review handoff tooling.

1. Webhook payloads carry metadata, never content. Slack and Discord are third parties, and the
   egress discipline the design demands of the product applies to the tooling as well.
2. The tool exposes no way to approve or merge. AGENTS.md reserves both for a human reviewer, and a
   verb added "just for convenience" is how that rule would quietly stop being true.
"""

import importlib.util
import pathlib
import sys

import pytest

MODULE_PATH = pathlib.Path(__file__).resolve().parents[1] / "review_handoff.py"
spec = importlib.util.spec_from_file_location("review_handoff", MODULE_PATH)
handoff = importlib.util.module_from_spec(spec)
sys.modules["review_handoff"] = handoff
spec.loader.exec_module(handoff)


def test_no_verb_can_approve_or_merge():
    source = MODULE_PATH.read_text()
    for forbidden in ('"pr", "merge"', '"pr", "review"', "--approve", "--squash"):
        assert forbidden not in source, (
            f"tooling must never {forbidden}: approval and merge belong to the reviewer"
        )


def test_notify_is_a_no_op_without_a_configured_webhook(monkeypatch):
    monkeypatch.delenv("WAYFINDER_REVIEW_WEBHOOK_URL", raising=False)

    result = handoff.notify("anything")

    assert "not configured" in result


def test_notification_text_is_metadata_only(monkeypatch):
    """A request notification names the pull request; it never carries the diff or file contents."""
    sent = {}

    def fake_urlopen(req, timeout=0):
        sent["body"] = req.data.decode()

        class R:
            status = 200

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

        return R()

    monkeypatch.setenv("WAYFINDER_REVIEW_WEBHOOK_URL", "https://example.invalid/hook")
    monkeypatch.setattr(handoff.urllib.request, "urlopen", fake_urlopen)

    handoff.notify("Review requested: #12 feat(authz): thing (+10/-2, 3 files) https://example/pr/12")

    assert "#12" in sent["body"]
    for leak in ("diff --git", "+++", "def ", "class "):
        assert leak not in sent["body"]


def test_security_modules_are_detected_from_paths():
    files = ["apps/api/wayfinder/egress/interface.py", "README.md"]

    assert handoff.touches_security(files) == ["egress"]
    assert handoff.touches_security(["README.md"]) == []


def test_packet_diff_budget_is_bounded():
    """An unbounded packet is unreviewable; the budget is the point, not an implementation detail."""
    assert 10_000 <= handoff.PACKET_DIFF_BUDGET <= 200_000


def test_record_rejects_an_unknown_verdict():
    with pytest.raises(KeyError):
        handoff.cmd_record("1", "rubber-stamp", "someone", "")
