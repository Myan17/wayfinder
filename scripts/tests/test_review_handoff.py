"""The two things that must not drift in the review handoff tooling.

1. Webhook payloads carry metadata, never content. Slack and Discord are third parties, and the
   egress discipline the design demands of the product applies to the tooling as well.
2. The tool exposes no way to approve or merge. AGENTS.md reserves both for a human reviewer, and a
   verb added "just for convenience" is how that rule would quietly stop being true.
"""

import importlib.util
import pathlib
import shutil
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


@pytest.fixture
def no_env_file(tmp_path, monkeypatch):
    """Point the lookup at empty directories.

    Without this, "no webhook is configured" is only true on a machine where nobody has configured
    one -- so these tests passed for as long as .env did not exist and began failing the moment a
    real webhook was set up. A test that depends on the developer's machine being unconfigured is
    not testing anything.
    """
    monkeypatch.delenv(handoff.WEBHOOK_VAR, raising=False)
    monkeypatch.setattr(handoff, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(handoff, "main_checkout", lambda: None)
    return tmp_path


def test_notify_is_a_no_op_without_a_configured_webhook(no_env_file):
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
    monkeypatch.setattr(handoff, "main_checkout", lambda: None)
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


def test_a_worktree_falls_back_to_the_env_in_the_main_checkout(tmp_path, monkeypatch):
    """Every pull request is authored from a linked worktree, and .env is not in one.

    A worktree has its own root but shares .git with the main clone. The author configures .env once,
    beside .env.example, in the checkout they cloned. Anchoring only on the script's own root made
    the tool silently unconfigured in exactly the place it is always run from -- and the alternative,
    a copy of the same secret in every worktree, is worse than the bug.
    """
    checkout = tmp_path / "wayfinder"
    worktree = tmp_path / "wayfinder-wt" / "myan-authz-thing"
    worktree.mkdir(parents=True)
    checkout.mkdir()
    (checkout / ".env").write_text(f"{handoff.WEBHOOK_VAR}=https://example.invalid/from-checkout\n")
    monkeypatch.delenv(handoff.WEBHOOK_VAR, raising=False)
    monkeypatch.setattr(handoff, "REPO_ROOT", worktree)
    monkeypatch.setattr(handoff, "main_checkout", lambda: checkout)

    assert handoff.webhook_url() == "https://example.invalid/from-checkout"


def test_a_worktrees_own_env_wins_over_the_main_checkout(tmp_path, monkeypatch):
    """A worktree may point somewhere else on purpose -- a scratch channel, say."""
    checkout = tmp_path / "wayfinder"
    worktree = tmp_path / "wayfinder-wt" / "myan-authz-thing"
    worktree.mkdir(parents=True)
    checkout.mkdir()
    (checkout / ".env").write_text(f"{handoff.WEBHOOK_VAR}=https://example.invalid/from-checkout\n")
    (worktree / ".env").write_text(f"{handoff.WEBHOOK_VAR}=https://example.invalid/from-worktree\n")
    monkeypatch.delenv(handoff.WEBHOOK_VAR, raising=False)
    monkeypatch.setattr(handoff, "REPO_ROOT", worktree)
    monkeypatch.setattr(handoff, "main_checkout", lambda: checkout)

    assert handoff.webhook_url() == "https://example.invalid/from-worktree"


def git(*args, cwd):
    """Run git with identity supplied, so the test does not depend on the machine's git config."""
    return subprocess.run(
        ["git", "-c", "user.email=test@example.invalid", "-c", "user.name=test", *args],
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


@pytest.mark.skipif(shutil.which("git") is None, reason="git is required to build a worktree")
def test_main_checkout_resolves_through_a_real_linked_worktree(tmp_path, monkeypatch):
    """Build an actual repository and an actual linked worktree, and resolve one from the other.

    The two tests above monkeypatch `main_checkout`, so they pin how `webhook_url` uses the answer,
    not whether the answer is right. This one exercises the `git rev-parse --git-common-dir` call
    itself against the real thing: a worktree's `.git` is a file pointing into the primary
    checkout's `.git/worktrees/<name>`, and the whole fix depends on that indirection resolving.
    """
    checkout = tmp_path / "wayfinder"
    checkout.mkdir()
    git("init", "-b", "main", cwd=checkout)
    (checkout / "README.md").write_text("probe\n")
    git("add", "README.md", cwd=checkout)
    git("commit", "-m", "initial", cwd=checkout)

    worktree = tmp_path / "wayfinder-wt" / "myan-authz-thing"
    git("worktree", "add", "-b", "myan/authz/thing", str(worktree), cwd=checkout)
    assert (worktree / ".git").is_file(), "a linked worktree's .git is a file, not a directory"

    monkeypatch.setattr(handoff, "REPO_ROOT", worktree)

    resolved = handoff.main_checkout()

    assert resolved is not None
    assert resolved.resolve() == checkout.resolve()
    assert resolved.resolve() != worktree.resolve()


@pytest.mark.skipif(shutil.which("git") is None, reason="git is required to build a repository")
def test_the_primary_checkout_resolves_to_itself(tmp_path, monkeypatch):
    """Run from the clone rather than a worktree: the answer is the clone, and env_files has one entry."""
    checkout = tmp_path / "wayfinder"
    checkout.mkdir()
    git("init", "-b", "main", cwd=checkout)
    monkeypatch.setattr(handoff, "REPO_ROOT", checkout)

    assert handoff.main_checkout().resolve() == checkout.resolve()
    assert handoff.env_files() == [checkout / ".env"]


def test_outside_a_repository_there_is_no_main_checkout(tmp_path, monkeypatch):
    """`git rev-parse` fails outside a repository; the lookup degrades instead of raising."""
    monkeypatch.setattr(handoff, "REPO_ROOT", tmp_path)

    assert handoff.main_checkout() is None
    assert handoff.env_files() == [tmp_path / ".env"]


def test_the_request_identifies_itself_with_a_user_agent(monkeypatch):
    """Discord's edge answers 403 Forbidden to urllib's default User-Agent.

    Verified against a real webhook: the same request with a User-Agent header returns 204. Slack
    accepts the default, which is why every test so far passed against a fake urlopen and the
    tooling still could not post to Discord.

    The value names the tool and the repository rather than imitating a browser -- a channel admin
    deciding whether this traffic is legitimate should be able to see what it is.
    """
    seen = {}

    def fake_urlopen(req, timeout=0):
        seen["agent"] = req.get_header("User-agent")

        class R:
            status = 204

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

        return R()

    monkeypatch.setenv(handoff.WEBHOOK_VAR, "https://example.invalid/hook")
    monkeypatch.setattr(handoff.urllib.request, "urlopen", fake_urlopen)

    handoff.notify("anything")

    agent = seen["agent"] or ""
    assert agent, "urllib's default User-Agent is rejected by Discord; send an explicit one"
    assert "python-urllib" not in agent.lower()
    assert "wayfinder" in agent.lower()
    for imitation in ("Mozilla", "Chrome", "Safari"):
        assert imitation not in agent, "identify the tool; do not imitate a browser"


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


def test_a_missing_dotenv_is_not_an_error(no_env_file):
    assert handoff.webhook_url() == ""


@pytest.fixture
def captured(monkeypatch, tmp_path):
    """Fake gh and the webhook; point CODEOWNERS at a known reviewer."""
    (tmp_path / ".github").mkdir()
    (tmp_path / ".github" / "CODEOWNERS").write_text("*  @Gupta958\n")
    monkeypatch.setattr(handoff, "REPO_ROOT", tmp_path)
    calls = {"gh": [], "notify": []}

    def fake_gh(*args):
        calls["gh"].append(args)
        return "https://github.com/o/r/pull/34#issuecomment-1\n"

    monkeypatch.setattr(handoff, "gh", fake_gh)
    monkeypatch.setattr(handoff, "notify", lambda text: calls["notify"].append(text) or "webhook: 204")
    return calls, tmp_path


def test_brief_is_posted_on_the_pull_request_with_a_mention(captured):
    calls, tmp = captured
    (brief := tmp / "b.md").write_text("Approve and squash-merge after checking ADR-0004 line 40.")
    assert handoff.cmd_brief("34", brief) == 0
    args = calls["gh"][0]
    assert args[:3] == ("pr", "comment", "34")
    body = args[args.index("--body") + 1]
    assert body.startswith("@Gupta958") and "ADR-0004 line 40" in body


def test_brief_webhook_carries_the_link_not_the_brief(captured):
    calls, tmp = captured
    (brief := tmp / "b.md").write_text("secret-ish detail that belongs on GitHub only")
    handoff.cmd_brief("34", brief)
    assert calls["notify"] == [
        "Brief for #34 posted on the pull request: https://github.com/o/r/pull/34#issuecomment-1"
    ]


def test_brief_does_not_double_an_existing_mention(captured):
    calls, tmp = captured
    (brief := tmp / "b.md").write_text("@gupta958 please look at the table.")
    handoff.cmd_brief("34", brief)
    body = calls["gh"][0][calls["gh"][0].index("--body") + 1]
    assert body.lower().count("@gupta958") == 1


def test_an_empty_brief_posts_nothing(captured):
    calls, tmp = captured
    (brief := tmp / "b.md").write_text("  \n")
    assert handoff.cmd_brief("34", brief) == 1
    assert calls["gh"] == [] and calls["notify"] == []


def test_reviewers_are_read_from_the_repository_not_the_callers_directory(captured, monkeypatch, tmp_path):
    _, _ = captured
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)
    assert handoff.reviewers() == ["@Gupta958"]


def test_a_posting_verb_refuses_under_the_wrong_account(monkeypatch, tmp_path):
    # 2026-09-26: briefs posted as the reviewer's own login @-mentioned their author and
    # notified no one. The guard runs before the verb, and a refusal posts nothing.
    posted = []
    monkeypatch.setattr(handoff, "account_guard", lambda: 1)
    monkeypatch.setattr(handoff, "cmd_brief", lambda *a: posted.append(a) or 0)
    brief = tmp_path / "b.md"
    brief.write_text("x")
    monkeypatch.setattr(sys, "argv", ["review_handoff.py", "brief", "40", "--file", str(brief)])
    assert handoff.main() == 1 and posted == []
    monkeypatch.setattr(handoff, "account_guard", lambda: 0)
    assert handoff.main() == 0 and len(posted) == 1
