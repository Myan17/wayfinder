#!/usr/bin/env python3
"""Guardrail: a pull request stays small enough to review in one sitting.

usage: scripts/check_pr_size.py <base-ref> <head-ref> [--branch <name>] [--limit 400]

The limit counts added plus deleted lines across the whole diff, with exactly one exception, agreed
with the reviewer on 2026-09-20: the task's own mandatory log, `docs/agent-log/<task>.md`. That file
is process output which grows with every commit, and counting it pushed authors to trim code comments
to make room for it -- the rule pressuring the wrong thing.

Everything else counts: source, tests, ordinary documentation, configuration, and generated files.
A generated file that is large enough to matter belongs in its own pull request (see #3), which is a
review decision rather than an accounting trick.
"""

from __future__ import annotations

import os
import subprocess
import sys


def git(*args: str) -> str:
    return subprocess.run(["git", *args], check=True, capture_output=True, text=True).stdout


def main() -> int:
    base, head = sys.argv[1], sys.argv[2]
    argv = sys.argv

    limit = 400
    if "--limit" in argv:
        limit = int(argv[argv.index("--limit") + 1])

    branch = ""
    if "--branch" in argv:
        branch = argv[argv.index("--branch") + 1]
    branch = branch or os.environ.get("GITHUB_HEAD_REF", "") or git("rev-parse", "--abbrev-ref", head).strip()
    exempt = f"docs/agent-log/{branch.replace('/', '-')}.md"

    counted = 0
    exempted = 0
    rows: list[tuple[int, str]] = []
    for line in git("diff", "--numstat", f"{base}...{head}").splitlines():
        parts = line.split("\t")
        if len(parts) != 3 or parts[0] == "-":      # binary files report "-"
            continue
        added, deleted, path = int(parts[0]), int(parts[1]), parts[2]
        changed = added + deleted
        if path == exempt:
            exempted += changed
            continue
        counted += changed
        rows.append((changed, path))

    if counted > limit:
        for changed, path in sorted(rows, reverse=True)[:8]:
            print(f"::notice::{changed:>5}  {path}")
        print(
            f"::error::{counted} changed lines, limit {limit} "
            f"(excluding {exempted} in {exempt}). Split this pull request: a review that cannot be "
            "held in one sitting is not a review (AGENTS.md §2.2)."
        )
        return 1

    print(f"size OK: {counted} changed lines (limit {limit}; {exempted} exempt in the task log)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
