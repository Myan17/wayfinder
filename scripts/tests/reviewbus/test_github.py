import json
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # scripts/, for the reviewbus package
from reviewbus import github, protocol

ROSTER = (protocol.ROOT / "docs/team/ROSTER.md").read_text()
SHA = "a" * 40


class FakeGh:
    """Records every call; answers `gh api user` with `login` and anything else from `replies`."""

    def __init__(self, login, replies=None, fail=()):
        self.login, self.replies, self.fail, self.calls = login, replies or {}, set(fail), []

    def __call__(self, argv, env, stdin):
        self.calls.append((argv, env, stdin))
        key = argv[1]
        if key in self.fail:
            raise subprocess.CalledProcessError(1, argv)
        if argv[1:3] == ["api", "user"]:
            return self.login + "\n"
        reply = self.replies.get(key, "")
        if argv[1:3] == ["pr", "view"] and reply:  # answer only the fields asked for, as gh does
            wanted = argv[argv.index("--json") + 1].split(",")
            return json.dumps({k: v for k, v in json.loads(reply).items() if k in wanted})
        return reply


def reviewer(fake, tmp_path):
    return github.GitHub(protocol.REVIEWER, ROSTER, tmp_path, run=fake)


def writes(fake):
    return [argv for argv, _, _ in fake.calls if argv[1:3] != ["api", "user"]]


def test_each_role_runs_under_its_own_login_and_never_inherits_a_token(monkeypatch, tmp_path):
    for var in github.INHERITED:
        monkeypatch.setenv(var, "leaked")
    fake = FakeGh("gupta958")
    reviewer(fake, tmp_path).login()
    env = fake.calls[0][1]
    assert env["GH_CONFIG_DIR"] == str(tmp_path) and env["GH_PROMPT_DISABLED"] == "1"
    assert not any(env.get(v) == "leaked" for v in github.INHERITED)
    author = FakeGh("Myan17")
    github.GitHub(protocol.AUTHOR, ROSTER, run=author).login()
    assert "GH_CONFIG_DIR" not in author.calls[0][1] and "GH_TOKEN" not in author.calls[0][1]


def test_the_reviewer_needs_its_own_config_directory():
    with pytest.raises(ValueError, match="own gh config directory"):
        github.GitHub(protocol.REVIEWER, ROSTER)
    with pytest.raises(ValueError, match="unknown role"):
        github.GitHub("admin", ROSTER)
    with pytest.raises(ValueError, match="never another login"):
        github.GitHub(protocol.AUTHOR, ROSTER, Path("/tmp/gh-reviewer"))


def test_there_is_no_public_raw_gh_call():  # Codex f1: every write goes through a checked method
    public = {n for n in vars(github.GitHub) if not n.startswith("_")}
    assert public - {"visibility"} == {
        "env",
        "login",
        "open_pulls",
        "pull",
        "comments",
        "variable",
        "check_account",
        "comment",
        "approve",
        "merge",
    }


def test_a_role_logged_in_as_the_other_account_writes_nothing(tmp_path):
    fake = FakeGh("Myan17")
    gh = reviewer(fake, tmp_path)
    for write in (lambda: gh.comment(1, "x"), lambda: gh.approve(1, SHA, "ok"), lambda: gh.merge(1, SHA)):
        with pytest.raises(github.WrongAccount, match="logged in as 'Myan17'"):
            write()
    author = FakeGh("Gupta958")
    with pytest.raises(github.WrongAccount):
        github.GitHub(protocol.AUTHOR, ROSTER, run=author).comment(1, "x")
    assert writes(fake) == [] and writes(author) == []


def test_the_author_may_never_approve_or_merge_even_when_logged_in_correctly():
    fake = FakeGh("Myan17")
    gh = github.GitHub(protocol.AUTHOR, ROSTER, run=fake)
    for write in (lambda: gh.approve(1, SHA, "ok"), lambda: gh.merge(1, SHA)):
        with pytest.raises(github.WrongAccount, match="may never"):
            write()
    assert fake.calls == []


def test_approve_and_merge_are_pinned_to_the_reviewed_commit(tmp_path):
    fake = FakeGh("gupta958")
    gh = reviewer(fake, tmp_path)
    gh.approve(7, SHA, "Approved by the bus.")
    gh.merge(7, SHA)
    (review, _, stdin), (merge, _, _) = [c for c in fake.calls if c[0][1:3] != ["api", "user"]]
    assert review[-3:] == ["repos/Myan17/wayfinder/pulls/7/reviews", "--input", "-"]
    assert json.loads(stdin) == {"commit_id": SHA, "event": "APPROVE", "body": "Approved by the bus."}
    assert merge == [
        "gh",
        "pr",
        "merge",
        "7",
        "-R",
        "Myan17/wayfinder",
        "--squash",
        "--match-head-commit",
        SHA,
    ]


@pytest.mark.parametrize("n, sha", [(0, SHA), (True, SHA), ("7", SHA), (7, SHA[:7]), (7, "A" * 40)])
def test_a_bad_number_or_sha_is_refused_before_any_call(n, sha, tmp_path):
    fake = FakeGh("gupta958")
    with pytest.raises(ValueError):
        reviewer(fake, tmp_path).merge(n, sha)
    assert fake.calls == []


def test_a_comment_goes_as_json_on_stdin_never_as_an_argument(tmp_path):
    fake = FakeGh("gupta958")
    reviewer(fake, tmp_path).comment(3, "--body-file=/etc/passwd\n<!-- x -->")
    argv, _, stdin = fake.calls[-1]
    assert "--body-file=/etc/passwd" not in " ".join(argv) and json.loads(stdin)["body"].startswith("--body")


def test_reads_are_parsed_into_plain_data(tmp_path):
    pr = {
        "headRefOid": SHA,
        "baseRefOid": "b" * 40,
        "files": [{"path": "a.py"}, {"path": "db/x.sql"}],
        "body": None,
        "statusCheckRollup": [
            {"name": "unit", "conclusion": "SUCCESS"},
            {"name": "unit", "conclusion": "FAILURE"},
            {"name": "go", "conclusion": None, "status": "IN_PROGRESS"},
            {"context": "legacy", "state": "SUCCESS"},
        ],
    }
    comments = '{"author":"Myan17","body":"a"}\n{"author":"mallory","body":"b"}\n'
    gh = reviewer(FakeGh("gupta958", {"pr": json.dumps(pr), "api": comments}), tmp_path)
    assert gh.pull(5) == {
        "head": SHA,
        "base": "b" * 40,
        "files": ["a.py", "db/x.sql"],
        "body": "",
        "checks": {"unit": "failure", "go": "pending", "legacy": "success"},
    }
    assert gh.comments(5) == [{"author": "Myan17", "body": "a"}, {"author": "mallory", "body": "b"}]


def test_an_unreadable_variable_is_none_so_callers_treat_it_as_off(tmp_path):
    assert (
        reviewer(FakeGh("gupta958", fail={"variable"}), tmp_path).variable("WAYFINDER_AGENT_APPROVAL") is None
    )
    gh = reviewer(FakeGh("gupta958", {"variable": "shadow\n"}), tmp_path)
    assert gh.variable("WAYFINDER_AGENT_RULINGS") == "shadow"
    for name in ("--help", "X", "WAYFINDER_AGENT_APPROVAL --repo evil/x"):  # Codex f2
        with pytest.raises(ValueError, match="not one of the bus's variables"):
            gh.variable(name)


def test_visibility_is_read_from_the_repository_and_lowercased(tmp_path):
    gh = reviewer(FakeGh("gupta958", {"repo": '{"visibility": "PUBLIC"}'}), tmp_path)
    assert gh.visibility() == "public"
