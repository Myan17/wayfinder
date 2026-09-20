#!/usr/bin/env python3
"""Guardrail: a pull request stays inside its task's module, and inside its operator's modules.

usage: scripts/check_ownership.py <base-ref> <head-ref> [--operator <handle>] [--module <module>]

Two boundaries, checked in order:

1. **Task scope.** A branch is `<operator>/<module>/<slug>`. Its changes belong to that module. This
   is the boundary that does the day-to-day work while one person implements everything: it keeps
   parallel agent sessions from colliding, and it keeps each pull request small enough for a reviewer
   who did not write it. Widen it deliberately with `Scope: a, b` in the pull request body.

2. **Ownership.** A module has an implementation owner. Editing someone else's module needs a linked
   BCR. Today every module is owned by `myan`, so this fires only once the roster changes — the rule
   is here so that transition needs no new machinery.

Always-writable regardless of scope: the task log, boundary requests, and the module's own card.
"""
from __future__ import annotations
import fnmatch
import os
import pathlib
import re
import subprocess
import sys


def git(*args: str) -> str:
    return subprocess.run(["git", *args], check=True, capture_output=True, text=True).stdout


def ownership() -> dict[str, tuple[str, list[str]]]:
    text = pathlib.Path("docs/team/OWNERSHIP.md").read_text()
    block = re.search(r"```yaml\n(.*?)```", text, re.S).group(1)
    out: dict[str, tuple[str, list[str]]] = {}
    for name, owner, paths in re.findall(
        r"^\s{2}([a-z0-9-]+):\s*\{owner:\s*([^,]+),\s*paths:\s*\[(.*?)\]\}", block, re.M
    ):
        out[name] = (owner.strip(), [p.strip().strip('"') for p in paths.split(",")])
    return out


def matches(path: str, globs: list[str]) -> bool:
    for g in globs:
        if path == g or fnmatch.fnmatch(path, g) or (g.endswith("/**") and path.startswith(g[:-3])):
            return True
    return False


def main() -> int:
    base, head = sys.argv[1], sys.argv[2]
    argv = sys.argv
    branch = os.environ.get("GITHUB_HEAD_REF", "") or git("rev-parse", "--abbrev-ref", head).strip()
    parts = branch.split("/")
    operator = argv[argv.index("--operator") + 1] if "--operator" in argv else (parts[0] if parts else "")
    task_module = argv[argv.index("--module") + 1] if "--module" in argv else (parts[1] if len(parts) > 2 else "")

    owners = ownership()
    body = os.environ.get("PR_BODY", "")
    has_bcr = bool(re.search(r"BCR-\d+", body))
    declared = set()
    m = re.search(r"^\s*Scope:\s*(.+)$", body, re.M | re.I)
    if m:
        declared = {x.strip() for x in re.split(r"[,\s]+", m.group(1)) if x.strip()}

    in_scope = {task_module} | declared
    unknown = in_scope - set(owners) - {""}
    if unknown:
        print(f"::error::unknown module(s) in branch name or Scope: line: {', '.join(sorted(unknown))}")
        return 1

    changed = [p for p in git("diff", "--name-only", f"{base}...{head}").splitlines() if p]
    free_globs = [g for name, (owner, globs) in owners.items() if owner == "any" for g in globs]
    free_globs += [f"docs/context/modules/{m}.md" for m in in_scope if m]

    out_of_scope: list[str] = []
    foreign: list[str] = []
    joint: list[str] = []
    unowned: list[str] = []

    for path in changed:
        if matches(path, free_globs):
            continue
        hit = next(((n, o, g) for n, (o, g) in owners.items() if matches(path, g)), None)
        if hit is None:
            unowned.append(path)
            continue
        module, owner, _ = hit
        if owner == "any":
            continue
        if owner == "joint":
            joint.append(f"{path} ({module})")
        elif operator and owner != operator:
            foreign.append(f"{path} — owned by {owner} via {module}")
        if module not in in_scope:
            out_of_scope.append(f"{path} — module '{module}', not this task's scope ('{task_module}')")

    for p in unowned:
        print(f"::warning::{p} matches no module in docs/team/OWNERSHIP.md — add it or move the file")
    for j in joint:
        print(f"::notice::joint path changed, review the design and not just the diff: {j}")

    failed = False
    if out_of_scope and not (has_bcr or declared):
        for o in out_of_scope:
            print(f"::error::{o}")
        print(
            "::error::This pull request reaches outside its task's module. Either split it into one "
            "branch per module, or declare the widening in the pull request body with a line "
            "'Scope: <module>, <module>' and say why in the work record (AGENTS.md §2.5)."
        )
        failed = True

    if foreign and not has_bcr:
        for f in foreign:
            print(f"::error::{f}")
        print("::error::Edits to a module this operator does not own need a linked BCR-<n> (AGENTS.md §4).")
        failed = True

    if failed:
        return 1
    if out_of_scope:
        print(f"::notice::scope widened deliberately to: {', '.join(sorted(in_scope - {''}))}")
    print(f"scope/ownership OK: {len(changed)} files, task '{task_module or '—'}', operator '{operator or '—'}'")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
