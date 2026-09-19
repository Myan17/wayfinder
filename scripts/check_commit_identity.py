#!/usr/bin/env python3
"""Guardrail: every commit names its human, its agent and its session.

usage: scripts/check_commit_identity.py <base-ref> <head-ref>

Rules (AGENTS.md §6):
  - author email is in docs/team/ROSTER.md (an engineer's email, or their machine account's)
  - trailers Agent:, Operator:, Session:, Task: are present
  - Operator is a known handle, and Task matches the branch
  - subject follows Conventional Commits with a scope that is a known module
"""
from __future__ import annotations
import re
import subprocess
import sys
import pathlib

SUBJECT = re.compile(r"^(feat|fix|docs|test|refactor|perf|build|ci|chore|revert)\(([a-z0-9-]+)\)!?: .{3,}$")
REQUIRED = ("Agent", "Operator", "Session", "Task")


def git(*args: str) -> str:
    return subprocess.run(["git", *args], check=True, capture_output=True, text=True).stdout


def roster() -> tuple[dict[str, str], set[str]]:
    """Returns (email -> handle, handles)."""
    text = pathlib.Path("docs/team/ROSTER.md").read_text()
    block = re.search(r"```yaml\n(.*?)```", text, re.S).group(1)
    emails: dict[str, str] = {}
    handles: set[str] = set()
    handle = None
    for line in block.splitlines():
        m = re.match(r"\s*-\s*handle:\s*(\S+)", line)
        if m:
            handle = m.group(1)
            handles.add(handle)
            continue
        m = re.match(r"\s*-\s*(\S+@\S+)", line)
        if m and handle:
            emails[m.group(1)] = handle
    return emails, handles


def modules() -> set[str]:
    text = pathlib.Path("docs/team/OWNERSHIP.md").read_text()
    block = re.search(r"```yaml\n(.*?)```", text, re.S).group(1)
    return set(re.findall(r"^\s{2}([a-z0-9-]+):\s*\{", block, re.M))


def main() -> int:
    base, head = sys.argv[1], sys.argv[2]
    emails, handles = roster()
    mods = modules() | {"deps", "release", "agents"}
    shas = git("rev-list", f"{base}..{head}").split()
    if not shas:
        print("identity OK: no commits in range")
        return 0

    errors: list[str] = []
    for sha in shas:
        author = git("show", "-s", "--format=%ae", sha).strip()
        subject = git("show", "-s", "--format=%s", sha).strip()
        body = git("show", "-s", "--format=%B", sha)
        short = sha[:7]

        if author not in emails:
            errors.append(f"{short}: author '{author}' is not in docs/team/ROSTER.md")
        if subject.startswith("Merge "):
            errors.append(f"{short}: merge commit on a task branch — rebase instead (AGENTS.md §2.2)")
            continue
        if not SUBJECT.match(subject):
            errors.append(f"{short}: subject is not Conventional Commits with a module scope: {subject!r}")
        else:
            scope = SUBJECT.match(subject).group(2)
            if scope not in mods:
                errors.append(f"{short}: scope '{scope}' is not a module in docs/team/OWNERSHIP.md")

        trailers = dict(re.findall(r"^([A-Za-z-]+):\s*(.+)$", body, re.M))
        for key in REQUIRED:
            if key not in trailers:
                errors.append(f"{short}: missing '{key}:' trailer — install hooks: git config core.hooksPath .githooks")
        op = trailers.get("Operator", "")
        if op and op not in handles:
            errors.append(f"{short}: Operator '{op}' is not a roster handle")
        if author in emails and op and emails[author] != op:
            errors.append(f"{short}: Operator '{op}' does not match author '{author}' ({emails[author]})")

    if errors:
        for e in errors:
            print(f"::error::{e}")
        return 1
    print(f"identity OK: {len(shas)} commits")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
