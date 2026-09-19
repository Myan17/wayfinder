#!/usr/bin/env python3
"""Guardrail: every branch has an append-only task log that matches its commits.

usage: scripts/check_agent_log.py <base-ref> <head-ref>

Checks, in order:
  1. A log exists for this branch (docs/agent-log/<operator>-<module>-<slug>.md).
  2. Every log file touched in this range was appended to, never rewritten
     (the old content must be a prefix of the new content).
  3. There is one COMMIT entry per commit in the range and the last one carries the head subject,
     so the log cannot fall behind the branch.
  4. The log contains at least one PLAN and one TEST entry — evidence that the work was
     thought about and actually run.
"""
from __future__ import annotations
import re
import subprocess
import sys


def git(*args: str) -> str:
    return subprocess.run(["git", *args], check=True, capture_output=True, text=True).stdout


def file_at(ref: str, path: str) -> str | None:
    r = subprocess.run(["git", "show", f"{ref}:{path}"], capture_output=True, text=True)
    return r.stdout if r.returncode == 0 else None


def fail(msg: str) -> None:
    print(f"::error::{msg}")
    sys.exit(1)


def main() -> None:
    base, head = sys.argv[1], sys.argv[2]
    branch = git("rev-parse", "--abbrev-ref", head).strip()
    if branch in {"HEAD", "main"}:
        branch = (
            subprocess.run(["git", "symbolic-ref", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
            or branch
        )

    expected = "docs/agent-log/" + branch.replace("/", "-") + ".md"
    changed = [p for p in git("diff", "--name-only", f"{base}...{head}").splitlines() if p.startswith("docs/agent-log/")]

    if expected not in changed and file_at(head, expected) is None:
        fail(
            f"no task log for branch '{branch}'. Expected {expected}. "
            "Start work with scripts/new-task.sh so the log exists from the first commit."
        )

    # 2. append-only, checked commit by commit — a rewrite *inside* the branch must fail too,
    #    which a base..head comparison misses when the log was created on the branch.
    for path in changed:
        if path.endswith(("README.md", "TEMPLATE.md")) or "/DIGEST-" in path:
            continue
        if file_at(head, path) is None:
            fail(f"{path} was deleted; task logs are append-only and permanent.")
        revs = git("rev-list", "--reverse", f"{base}..{head}", "--", path).split()
        for rev in revs:
            before = file_at(f"{rev}^", path)
            after = file_at(rev, path)
            if before is None or after is None:
                continue
            if not after.startswith(before):
                fail(
                    f"{path} was rewritten in {rev[:7]}, not appended to. "
                    "Corrections are new entries (AGENTS.md §5.1)."
                )

    log = file_at(head, expected) or ""
    entries = re.findall(r"^### (\S+) · ([A-Z]+) · (\S+) · (\S+) · (\S+)$", log, re.M)
    if not entries:
        fail(f"{expected} has no entries. Log as you work, not afterwards.")

    types = [e[1] for e in entries]
    for required in ("PLAN", "TEST"):
        if required not in types:
            fail(
                f"{expected} has no {required} entry. "
                + ("Record the approach before editing." if required == "PLAN" else "Record the command and its real output.")
            )

    head_subject = git("show", "-s", "--format=%s", head).strip()
    commit_entries = [e for e in entries if e[1] == "COMMIT"]
    if not commit_entries:
        fail(f"{expected} has no COMMIT entries — install hooks: git config core.hooksPath .githooks")

    n_commits = len([c for c in git("rev-list", f"{base}..{head}").splitlines() if c])
    bodies = re.split(r"^### .*$", log, flags=re.M)[1:]
    commit_bodies = [b.strip().splitlines()[0] for e, b in zip(entries, bodies) if e[1] == "COMMIT" and b.strip()]
    if n_commits and len(commit_bodies) < n_commits:
        fail(
            f"{expected} has {len(commit_bodies)} COMMIT entries for {n_commits} commits. "
            "Every commit logs itself through the commit-msg hook; a missing entry means the hook was bypassed."
        )
    if commit_bodies and commit_bodies[-1] != head_subject:
        fail(
            f"{expected} last COMMIT entry is {commit_bodies[-1]!r} but the head commit is {head_subject!r}. "
            "The log must cover every commit in the pull request."
        )

    print(f"agent-log OK: {expected} — {len(entries)} entries, {len(commit_bodies)} commits logged")


if __name__ == "__main__":
    main()
