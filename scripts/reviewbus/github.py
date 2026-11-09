"""Every `gh` call the review bus makes, in one place (REVIEW-BUS.md §7), each under its role's login.

The reviewer's calls carry its own `GH_CONFIG_DIR`; the author's use gh's default directory. Both drop
any `GH_TOKEN`, `GITHUB_TOKEN` or `GH_CONFIG_DIR` inherited from the environment, so neither role can
act on the other's credentials. Before every write the role's live login is checked against ROSTER.md
(rule 8), the author may never approve or merge, and approvals and merges are pinned to the reviewed
commit (rule 5). Deciding *whether* to approve is `gates.decide`'s job, not this file's.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
from collections.abc import Callable
from pathlib import Path

from reviewbus import protocol

Run = Callable[[list[str], dict[str, str], str | None], str]  # argv, env, stdin -> stdout
REPO = "Myan17/wayfinder"
INHERITED = ("GH_TOKEN", "GITHUB_TOKEN", "GH_ENTERPRISE_TOKEN", "GITHUB_ENTERPRISE_TOKEN", "GH_CONFIG_DIR")
_SHA = re.compile(r"[0-9a-f]{40}")
VARIABLES = ("WAYFINDER_AGENT_APPROVAL", "WAYFINDER_AGENT_RULINGS")  # the only ones the bus reads


class WrongAccount(RuntimeError):
    """The role's gh login is not its ROSTER account; nothing was written."""


def subprocess_run(argv: list[str], env: dict[str, str], stdin: str | None) -> str:
    return subprocess.run(
        argv, env=env, input=stdin, capture_output=True, text=True, check=True, timeout=120
    ).stdout


def _number(n: object) -> int:
    if type(n) is not int or n < 1:
        raise ValueError(f"pull request number {n!r} is not a positive integer")
    return n


def _sha(sha: object) -> str:
    if type(sha) is not str or not _SHA.fullmatch(sha):
        raise ValueError(f"{sha!r} is not a full commit sha")
    return sha


def conclusions(rollup: list[dict]) -> dict[str, str]:
    """`statusCheckRollup` as name -> lowercase conclusion; unfinished is `pending`. A name reported
    twice keeps its worse result, so a passing duplicate cannot hide a failing run."""
    out: dict[str, str] = {}
    for c in rollup:
        name = c.get("name") or c.get("context")
        value = (c.get("conclusion") or c.get("state") or "pending").lower()
        if not isinstance(name, str) or not name:
            continue
        if out.get(name, "success") == "success":
            out[name] = value
    return out


class GitHub:
    def __init__(self, role: str, roster: str, config_dir: Path | None = None, run: Run = subprocess_run):
        if role not in (protocol.AUTHOR, protocol.REVIEWER):
            raise ValueError(f"unknown role {role!r}")
        if role == protocol.REVIEWER and config_dir is None:
            raise ValueError("the reviewer needs its own gh config directory (REVIEW-BUS.md §6)")
        if role == protocol.AUTHOR and config_dir is not None:
            raise ValueError("the author uses gh's default directory, never another login's")
        self.role, self.account = role, protocol.logins(roster)[role]
        self.config_dir, self.run = config_dir, run

    def env(self) -> dict[str, str]:
        env = {k: v for k, v in os.environ.items() if k not in INHERITED}
        env.update(GH_PROMPT_DISABLED="1", NO_COLOR="1")
        if self.config_dir is not None:
            env["GH_CONFIG_DIR"] = str(Path(self.config_dir).expanduser())
        return env

    def _gh(self, *args: str, stdin: str | None = None) -> str:
        """Private: callers use the typed methods, which carry the account, role and commit checks."""
        return self.run(["gh", *args], self.env(), stdin)

    # reads

    def login(self) -> str:
        return self._gh("api", "user", "--jq", ".login").strip()

    def open_pulls(self) -> list[dict]:
        return json.loads(self._gh("pr", "list", "-R", REPO, "--state", "open", "--limit", "100",
                                  "--json", "number,headRefOid"))  # fmt: skip

    def pull(self, n: int) -> dict:
        raw = json.loads(self._gh("pr", "view", str(_number(n)), "-R", REPO, "--json",
                                 "headRefOid,baseRefOid,files,body,statusCheckRollup"))  # fmt: skip
        return {
            "head": raw["headRefOid"],
            "base": raw["baseRefOid"],
            "files": [f["path"] for f in raw.get("files") or []],
            "body": raw.get("body") or "",
            "checks": conclusions(raw.get("statusCheckRollup") or []),
        }

    def comments(self, n: int) -> list[dict]:
        out = self._gh("api", "--paginate", f"repos/{REPO}/issues/{_number(n)}/comments",
                      "--jq", ".[] | {author: (.user.login // \"\"), body: (.body // \"\")}")  # fmt: skip
        return [json.loads(line) for line in out.splitlines() if line.strip()]

    def visibility(self) -> str:
        """`public`, `private` or `internal`, lowercased; agents.review sends only public ones."""
        return json.loads(self._gh("repo", "view", REPO, "--json", "visibility"))["visibility"].lower()

    def variable(self, name: str) -> str | None:
        """A repository variable, or None when unset or unreadable: callers treat None as `off`."""
        if name not in VARIABLES:
            raise ValueError(f"{name!r} is not one of the bus's variables {VARIABLES}")
        try:
            return self._gh("variable", "get", name, "-R", REPO).strip()
        except subprocess.CalledProcessError:
            return None

    # writes

    def check_account(self) -> None:
        login = self.login()
        if login.lower() != self.account.lower():
            raise WrongAccount(f"the {self.role} role is logged in as {login!r}, not {self.account!r}")

    def comment(self, n: int, body: str) -> None:
        _number(n)
        self.check_account()
        self._gh("api", "-X", "POST", f"repos/{REPO}/issues/{n}/comments", "--input", "-",
                stdin=json.dumps({"body": body}))  # fmt: skip

    def _reviewer_only(self, what: str) -> None:
        if self.role != protocol.REVIEWER:
            raise WrongAccount(f"the {self.role} role may never {what} (AGENTS.md §1)")

    def approve(self, n: int, sha: str, body: str) -> None:
        """An approval of exactly `sha`: if the PR moved, GitHub does not apply it to the new head."""
        _number(n)
        _sha(sha)
        self._reviewer_only("approve")
        self.check_account()
        self._gh("api", "-X", "POST", f"repos/{REPO}/pulls/{n}/reviews", "--input", "-",
                stdin=json.dumps({"commit_id": sha, "event": "APPROVE", "body": body}))  # fmt: skip

    def merge(self, n: int, sha: str) -> None:
        """Squash-merge only while the head is still `sha` (rule 5)."""
        _number(n)
        _sha(sha)
        self._reviewer_only("merge")
        self.check_account()
        self._gh("pr", "merge", str(n), "-R", REPO, "--squash", "--match-head-commit", sha)
