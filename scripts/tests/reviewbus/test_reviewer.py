import contextlib
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # scripts/, for the reviewbus package
from reviewbus import agents, gates, protocol, reviewer, state

ROSTER = (protocol.ROOT / "docs/team/ROSTER.md").read_text()
HEAD, BASE = "a" * 40, "b" * 40
CLEAN = {"verdict": "approve", "findings": [], "summary": "Looks right."}
CFG = reviewer.Config(Path("/repo"), ["unit", "guardrails"], "gpt-test", Path(tempfile.mkdtemp()) / "locks")


def request(round_=1):
    body = protocol.build("review_request", {"pr": 9, "head": HEAD[:7], "round": round_}, "Review.", ROSTER)
    return {"author": "Myan17", "body": body}


class FakeGh:
    def __init__(
        self,
        mode="shadow",
        comments=None,
        files=("eval/harness/x.py",),
        heads=(HEAD,),
        modes=(),
        unit=("success",),
    ):
        self.mode, self.vis, self.calls, self.modes, self.unit = mode, "public", [], list(modes), list(unit)
        self._comments = comments if comments is not None else [request()]
        self.files, self.heads = list(files), list(heads)

    def variable(self, name):
        return self.modes.pop(0) if self.modes else self.mode

    def pull(self, n):
        head = self.heads.pop(0) if len(self.heads) > 1 else self.heads[0]
        unit = self.unit.pop(0) if len(self.unit) > 1 else self.unit[0]
        checks = {"unit": unit, "guardrails": "success"}
        return {
            "head": head,
            "base": BASE,
            "files": self.files,
            "body": f"head `{HEAD[:7]}`",
            "checks": checks,
        }

    def comments(self, n):
        return list(self._comments)

    def visibility(self):
        return self.vis

    def comment(self, n, body):
        self.calls.append(("comment", body))
        self._comments.append({"author": "Gupta958", "body": body})

    def approve(self, n, sha, body):
        self.calls.append(("approve", sha))

    def merge(self, n, sha):
        self.calls.append(("merge", sha))


def fake_ask(answer=CLEAN, error=None):
    seen = []

    def ask(wt, pr, head, base, data, *, visibility, model):
        seen.append((wt, pr, head, base, data, visibility, model))
        if error:
            raise error
        return answer

    ask.seen = seen
    return ask


@contextlib.contextmanager
def fake_checkout(repo_dir, pr, head):
    yield Path(f"/wt/{pr}/{head[:7]}")


def run(gh, ask=None, **kw):
    return reviewer.review_pr(9, gh, CFG, ROSTER, ask=ask or fake_ask(), open_checkout=fake_checkout, **kw)


def posted(gh):
    return [protocol.parse(b, "Gupta958", ROSTER) for kind, b in gh.calls if kind == "comment"]


def test_shadow_posts_would_approve_and_never_approves_or_merges():
    gh = FakeGh(mode="shadow")
    log = run(gh)
    assert [k for k, _ in gh.calls] == ["comment"] and "would_approve" in log[-1]
    (m,) = posted(gh)
    assert m.fields["verdict"] == "approve" and m.fields["round"] == 1 and m.text.startswith("@Gupta958")
    assert state.state(gh.comments(9), HEAD, ROSTER).status == "reviewed"  # the next pass does nothing


def test_on_mode_approves_and_merges_pinned_to_the_reviewed_head_only_when_every_gate_holds():
    gh = FakeGh(mode="on")
    run(gh)
    assert gh.calls[1:] == [("approve", HEAD), ("merge", HEAD)]
    tier_pr = FakeGh(mode="on", files=["scripts/reviewbus/gates.py"])
    run(tier_pr)
    assert [k for k, _ in tier_pr.calls] == ["comment"] and posted(tier_pr)[0].fields[
        "verdict"
    ] == "needs_human"


@pytest.mark.parametrize("mode", [None, "off", "ON", "maybe"])
def test_off_unset_or_unknown_mode_does_nothing_at_all(mode):
    gh, ask = FakeGh(mode=mode), fake_ask()
    assert "is off" in run(gh, ask)[-1] and gh.calls == [] and ask.seen == []


def test_nothing_happens_unless_the_current_head_is_requested():
    gh, ask = FakeGh(comments=[]), fake_ask()
    assert "state idle" in run(gh, ask)[-1] and ask.seen == [] and gh.calls == []


def test_codex_gets_the_checkout_heads_visibility_and_the_pr_text_as_data():
    gh, ask = FakeGh(), fake_ask()
    run(gh, ask)
    wt, pr, head, base, data, vis, model = ask.seen[0]
    assert (str(wt), pr, head, base, vis, model) == (f"/wt/9/{HEAD[:7]}", 9, HEAD, BASE, "public", "gpt-test")
    assert data.startswith("Description:") and "--- Myan17:" in data


def test_changes_are_requested_in_shadow_with_the_findings_listed():
    finding = {"id": "f1", "file": "a.py", "line": 3, "severity": "high", "blocking": True, "text": "bug"}
    gh = FakeGh()
    run(gh, fake_ask({"verdict": "changes", "findings": [finding], "summary": "One bug."}))
    (m,) = posted(gh)
    assert m.fields["verdict"] == "changes" and "1. [blocking] a.py:3 — bug" in m.text


@pytest.mark.parametrize("error", [agents.AgentError("no usable review"), OSError("git failed")])
def test_a_failed_review_posts_needs_human_and_never_approves(error):
    gh = FakeGh(mode="on")
    log = run(gh, fake_ask(error=error))
    assert [k for k, _ in gh.calls] == ["comment"] and posted(gh)[0].fields["verdict"] == "needs_human"
    assert "review failed" in log[0]


def test_a_head_that_moves_during_the_review_posts_nothing():
    gh = FakeGh(mode="on", heads=[HEAD, "c" * 40])
    assert "changed during the review" in run(gh)[-1] and gh.calls == []


def test_a_check_that_fails_during_the_review_blocks_the_approval():  # Codex f3
    gh = FakeGh(mode="on", unit=["success", "failure"])
    run(gh)
    assert [k for k, _ in gh.calls] == ["comment"] and posted(gh)[0].fields["verdict"] == "needs_human"


def test_the_switch_turned_off_during_the_review_posts_nothing():  # Codex f3
    gh = FakeGh(mode="on", modes=["on", "off"])
    run(gh)
    assert gh.calls == []


def test_an_escalation_during_the_review_posts_nothing():  # Codex f4
    gh = FakeGh(mode="on")
    esc = protocol.build("escalate", {"pr": 9, "reason": "r", "question": "q"}, "Stop.", ROSTER)

    def ask(*a, **k):
        gh._comments.append({"author": "Myan17", "body": esc})
        return CLEAN

    assert "changed during the review" in run(gh, ask)[-1] and gh.calls == []


def test_a_second_pass_on_the_same_pr_skips_while_the_first_holds_it():  # Codex f4
    with reviewer.one_at_a_time(CFG.lock_dir, 9) as first:
        gh = FakeGh()
        assert first and "another pass holds" in run(gh)[-1] and gh.calls == []
    with reviewer.one_at_a_time(CFG.lock_dir, 9) as again:
        assert again


def git(*args, cwd):
    env = {**os.environ, "GIT_CONFIG_GLOBAL": os.devnull}
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, env=env)


def test_the_checkout_never_runs_a_hook_the_pr_adds(tmp_path):  # Codex f2
    origin, clone, marker = tmp_path / "origin", tmp_path / "clone", tmp_path / "hook-ran"
    ident = ["-c", "user.email=a@b", "-c", "user.name=a"]
    git("init", "-q", "-b", "main", str(origin), cwd=tmp_path)
    git(*ident, "commit", "-q", "--allow-empty", "-m", "base", cwd=origin)
    hook = origin / ".githooks" / "post-checkout"
    hook.parent.mkdir()
    hook.write_text(f"#!/bin/sh\ntouch {marker}\n")
    hook.chmod(0o755)
    git("checkout", "-q", "-b", "pr", cwd=origin)
    git("add", ".", cwd=origin)
    git(*ident, "commit", "-q", "-m", "hook", cwd=origin)
    git("update-ref", "refs/pull/1/head", "pr", cwd=origin)
    head = subprocess.run(
        ["git", "rev-parse", "pr"], cwd=origin, capture_output=True, text=True
    ).stdout.strip()
    git("clone", "-q", str(origin), str(clone), cwd=tmp_path)
    git("config", "core.hooksPath", ".githooks", cwd=clone)  # as this repository is configured
    with reviewer.checkout(clone, 1, head) as wt:
        assert (wt / ".githooks" / "post-checkout").exists() and not marker.exists()
    git("worktree", "add", "-q", "--detach", str(tmp_path / "plain"), head, cwd=clone)
    assert marker.exists()  # the same checkout without the guards runs it, so this test can fail


def test_a_dry_run_reviews_but_posts_nothing():
    gh, ask = FakeGh(mode="on"), fake_ask()
    log = run(gh, ask, dry_run=True)
    assert len(ask.seen) == 1 and gh.calls == [] and "dry run" in log[-1]


def test_every_action_maps_to_a_verdict_the_state_machine_accepts():
    assert set(reviewer.POSTED) == {gates.APPROVE, gates.WOULD_APPROVE, gates.REQUEST_CHANGES,
                                    gates.NEEDS_HUMAN, gates.ESCALATE}  # fmt: skip
    assert set(reviewer.POSTED.values()) <= set(gates.VERDICTS)
