"""The two things that must not drift in the review handoff tooling.

1. Webhook payloads carry metadata, never content. Slack and Discord are third parties, and the
   egress discipline the design demands of the product applies to the tooling as well.
2. The tool exposes no way to approve or merge. AGENTS.md reserves both for a human reviewer, and a
   verb added "just for convenience" is how that rule would quietly stop being true.
"""

import importlib.util
import pathlib
import subprocess
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


def test_the_env_file_is_read_from_the_repository_root_not_the_callers_directory(tmp_path, monkeypatch):
    """`.env` lives beside `.env.example` at the repository root, and the tool is run from anywhere.

    Resolving it as `Path(".env")` made the webhook work or not work depending on which directory
    the caller happened to be in -- and the common case, running from a worktree subdirectory, was
    the failing one.
    """
    (tmp_path / ".env").write_text(f"{handoff.WEBHOOK_VAR}=https://example.invalid/from-root\n")
    elsewhere = tmp_path / "apps" / "api"
    elsewhere.mkdir(parents=True)
    monkeypatch.delenv(handoff.WEBHOOK_VAR, raising=False)
    monkeypatch.setattr(handoff, "REPO_ROOT", tmp_path)
    monkeypatch.chdir(elsewhere)

    assert handoff.webhook_url() == "https://example.invalid/from-root"


def test_a_dot_env_in_the_current_directory_is_not_read(tmp_path, monkeypatch):
    """The repository root is the only place the tool looks; a stray .env elsewhere is not config."""
    root = tmp_path / "repo"
    root.mkdir()
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    (elsewhere / ".env").write_text(f"{handoff.WEBHOOK_VAR}=https://example.invalid/stray\n")
    monkeypatch.delenv(handoff.WEBHOOK_VAR, raising=False)
    monkeypatch.setattr(handoff, "REPO_ROOT", root)
    monkeypatch.chdir(elsewhere)

    assert handoff.webhook_url() == ""


def test_an_exported_value_still_beats_the_env_file(tmp_path, monkeypatch):
    (tmp_path / ".env").write_text(f"{handoff.WEBHOOK_VAR}=https://example.invalid/from-file\n")
    monkeypatch.setenv(handoff.WEBHOOK_VAR, "https://example.invalid/exported")
    monkeypatch.setattr(handoff, "REPO_ROOT", tmp_path)
    monkeypatch.chdir(tmp_path)

    assert handoff.webhook_url() == "https://example.invalid/exported"


def test_repo_root_is_derived_from_the_script_when_imported_from_another_directory(tmp_path):
    """Run the module from a directory that is not the repository, in a separate interpreter.

    The monkeypatched tests above prove the lookup uses REPO_ROOT; this one proves REPO_ROOT itself
    is the repository the script lives in, whatever the caller's working directory is.
    """
    probe = (
        "import importlib.util, pathlib, sys;"
        f"spec = importlib.util.spec_from_file_location('rh', r'{MODULE_PATH}');"
        "m = importlib.util.module_from_spec(spec);"
        "spec.loader.exec_module(m);"
        "print(m.REPO_ROOT)"
    )
    out = subprocess.run(
        [sys.executable, "-c", probe], cwd=tmp_path, capture_output=True, text=True, check=True
    ).stdout.strip()

    assert pathlib.Path(out) == MODULE_PATH.parent.parent
    assert (pathlib.Path(out) / ".env.example").is_file()


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


def test_a_webhook_timeout_degrades_instead_of_raising(monkeypatch):
    """TimeoutError is not a URLError subclass, so it escaped the handler that promised to degrade.

    A notification is a courtesy; GitHub already holds the request. Failing the caller because a
    chat webhook was slow would make the tooling less reliable than doing nothing.
    """

    def timeout(req, timeout=0):
        raise TimeoutError("timed out")

    monkeypatch.setenv("WAYFINDER_REVIEW_WEBHOOK_URL", "https://example.invalid/hook")
    monkeypatch.setattr(handoff.urllib.request, "urlopen", timeout)

    result = handoff.notify("anything")

    assert "FAILED" in result
    assert "GitHub still has the request" in result


def test_a_refused_connection_also_degrades(monkeypatch):
    def refused(req, timeout=0):
        raise OSError(61, "Connection refused")

    monkeypatch.setenv("WAYFINDER_REVIEW_WEBHOOK_URL", "https://example.invalid/hook")
    monkeypatch.setattr(handoff.urllib.request, "urlopen", refused)

    assert "FAILED" in handoff.notify("anything")


def test_a_commented_line_in_the_env_file_is_not_config(monkeypatch, tmp_path):
    """.env.example ships with commented lines, so a copied file is mostly comments."""
    monkeypatch.delenv(handoff.WEBHOOK_VAR, raising=False)
    (tmp_path / ".env").write_text(
        f"# {handoff.WEBHOOK_VAR}=https://example.invalid/commented-out\n"
        f"{handoff.WEBHOOK_VAR}=https://example.invalid/real\n"
    )
    monkeypatch.setattr(handoff, "REPO_ROOT", tmp_path)

    assert handoff.webhook_url() == "https://example.invalid/real"


def test_a_missing_dotenv_is_not_an_error(monkeypatch, tmp_path):
    monkeypatch.delenv("WAYFINDER_REVIEW_WEBHOOK_URL", raising=False)
    monkeypatch.chdir(tmp_path)

    assert handoff.webhook_url() == ""
