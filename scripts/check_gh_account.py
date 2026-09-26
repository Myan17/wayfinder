#!/usr/bin/env python3
"""Guardrail: push and post only as the operator's own GitHub account.

`gh` can hold several github.com logins, and whichever is active is the one that pushes (through
its git credential helper), opens pull requests and comments. Commit identity comes from git's own
config, so it looks right even when the active login is wrong. On 2026-09-26 the reviewer's login
was active in the implementer's session: four pull requests were opened as the reviewer, who
therefore could not approve them, and every brief @-mentioned its own author and notified no one.

Run by `.githooks/pre-push` and by `review_handoff.py` before any verb that posts. It fails closed
on an unknown operator or login. With no `gh` installed it passes with a warning, because then `gh`
is not the one pushing.

usage: scripts/check_gh_account.py
"""
from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def expected_login(roster: str, operator: str) -> str | None:
    """The `github:` of the ROSTER engineer whose `handle:` is the operator."""
    m = re.search(rf"^\s*- handle: {re.escape(operator)}\s*$(?:\n(?!\s*- handle:).*)*?\n\s*github: (\S+)",
                  roster, re.M)
    return m.group(1) if m and operator else None


def problem(operator: str, login: str, roster: str) -> str | None:
    """None when the active login is the operator's, otherwise what is wrong and how to fix it."""
    if not operator:
        return "no operator: set it once with  git config wayfinder.operator <handle>"
    want = expected_login(roster, operator)
    if not want:
        return f"operator '{operator}' is not in docs/team/ROSTER.md"
    if not login:
        return "could not read the active GitHub login (gh api user); refusing rather than guessing"
    if login.lower() != want.lower():
        return (f"gh is acting as '{login}', but operator '{operator}' is '{want}'. "
                f"Fix: gh auth switch --hostname github.com --user {want}")
    return None


def out(*args: str) -> str:
    try:
        return subprocess.run(args, capture_output=True, text=True, check=False, cwd=ROOT,
                              timeout=20).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return ""


def main() -> int:
    if not shutil.which("gh"):
        print("warning: gh not installed; account not checked", file=sys.stderr)
        return 0
    roster = (ROOT / "docs/team/ROSTER.md").read_text()
    msg = problem(out("git", "config", "wayfinder.operator"), out("gh", "api", "user", "--jq", ".login"),
                  roster)
    if msg:
        print(f"::error::wrong GitHub account — {msg}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
