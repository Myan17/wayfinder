#!/usr/bin/env python3
"""Print a map of the whole codebase, sized to read in one sitting instead of exploring the tree.

Modules come from docs/team/OWNERSHIP.md and card status from docs/context/INDEX.md, with each
module's real footprint counted from `git ls-files`, so a module whose code does not exist yet
says so. Then come the scripts with their header lines, the migrations, the ADRs, the CI jobs
and the size of the big documents, so a reader knows what a full read would cost.

Like orient.py it **writes nothing**, so the map cannot go stale. It is not part of the
SessionStart brief. Run it when a task needs the shape of the whole repository, instead of
listing directories or reading code you do not own (AGENTS.md §3.2).

usage: scripts/codemap.py
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from orient import parse_cards  # noqa: E402 — one parser for INDEX's card status, not two

ROOT = Path(__file__).resolve().parents[1]
LOCKS = ("go.sum", "uv.lock", "package-lock.json")


def modules(ownership: str) -> list[dict]:
    """Each `name: {owner: x, paths: [...]}` line of OWNERSHIP.md's yaml block."""
    out = []
    for m in re.finditer(r"^  ([a-z-]+):\s+\{owner: (\w+),\s+paths: \[(.*?)\]\}", ownership, re.M):
        out.append({"name": m.group(1), "owner": m.group(2),
                    "paths": re.findall(r'"([^"]+)"', m.group(3))})
    return out


def matches(path: str, glob: str) -> bool:
    """OWNERSHIP's globs: `**` spans directories, `*` stays inside one, anything else is literal."""
    pattern = "".join(".*" if part == "**" else "[^/]*" if part == "*" else re.escape(part)
                      for part in re.split(r"(\*\*|\*)", glob))
    return re.fullmatch(pattern, path) is not None


def footprint(module: dict, files: dict[str, int]) -> tuple[int, int]:
    """(files, lines) under a module's paths, not counting its contract card or lock files."""
    own = [f for f in files
           if any(matches(f, g) for g in module["paths"])
           and not f.startswith("docs/context/modules/") and not f.endswith(LOCKS)]
    return len(own), sum(files[f] for f in own)


def unowned(mods: list[dict], files: dict[str, int]) -> list[str]:
    """Tracked files that no module claims. CODEOWNERS routes these to nobody."""
    return sorted(f for f in files if not any(matches(f, g) for m in mods for g in m["paths"]))


def purpose(text: str) -> str:
    """A script's first header line: its docstring's first line, or its first comment."""
    doc = re.search(r'^"""(.+)$', text, re.M)
    if doc:
        return doc.group(1).strip()
    comment = re.search(r"^# (?!!)(.+)$", text, re.M)
    return comment.group(1).strip() if comment else ""


def ci_jobs(yml: str) -> list[str]:
    """The job ids of a workflow: two-space keys after `jobs:`."""
    _, _, body = yml.partition("\njobs:\n")
    return re.findall(r"^  ([A-Za-z0-9_-]+):", body, re.M)


def tracked() -> dict[str, int]:
    """Every tracked file and its line count. Binary or unreadable files count as zero lines."""
    names = subprocess.run(["git", "ls-files"], capture_output=True, text=True, cwd=ROOT,
                           check=False).stdout.splitlines()
    out = {}
    for name in names:
        try:
            out[name] = (ROOT / name).read_text().count("\n")
        except (OSError, UnicodeDecodeError):
            out[name] = 0
    return out


def read(rel: str) -> str:
    path = ROOT / rel
    return path.read_text() if path.exists() else ""


def main() -> int:
    files = tracked()
    mods = modules(read("docs/team/OWNERSHIP.md"))
    cards = parse_cards(read("docs/context/INDEX.md"))
    status = {n: s for s in ("written", "placeholder") for n in cards[s]}
    add = print

    add(f"WAYFINDER CODE MAP — {len(files)} tracked files, {sum(files.values()):,} lines"
        " (from git ls-files; OWNERSHIP.md for modules, INDEX.md for cards)")
    add("")
    add("MODULES  owner · card · files/lines in its paths (no card, no lock files) · paths")
    for m in mods:
        n, lines = footprint(m, files)
        size = (f"{n:>3} files {lines:>6,} lines" if lines else
                "   stub (empty files)" if n else "   no code yet       ")
        paths = " ".join(p for p in m["paths"] if not p.startswith("docs/context/modules/"))
        paths = paths if len(paths) <= 70 else paths[:69] + "…"
        add(f"  {m['name']:<13} {m['owner']:<5} {status.get(m['name'], '-'):<11} {size}  {paths}")
    stray = unowned(mods, files)
    add(f"  unowned: {' '.join(stray) if stray else 'none'}")

    add("")
    add("SCRIPTS")
    for f in sorted(f for f in files if re.fullmatch(r"scripts/[^/]+\.(py|sh)", f)):
        add(f"  {Path(f).name:<27} {purpose(read(f))[:90]}")

    add("")
    add("MIGRATIONS  (immutable once on main)")
    for f in sorted(f for f in files if re.fullmatch(r"db/migrations/[^/]+\.sql", f)):
        add(f"  {Path(f).name}")

    add("")
    add("ADRS")
    for f in sorted(f for f in files if re.fullmatch(r"docs/adr/ADR-\d+[^/]*\.md", f)):
        add(f"  {read(f).splitlines()[0].lstrip('# ')[:95]}")

    add("")
    add("CI")
    for f in sorted(f for f in files if re.fullmatch(r"\.github/workflows/[^/]+\.ya?ml", f)):
        add(f"  {Path(f).name:<16} jobs: {' '.join(ci_jobs(read(f)))}")

    add("")
    add("DOCS  lines — read by section, not whole")
    for f in ("docs/DESIGN.md", "AGENTS.md", "docs/team/WORKING-AGREEMENT.md", "docs/context/INDEX.md"):
        if f in files:
            add(f"  {f:<34} {files[f]:>5}")
    card_lines = sum(v for k, v in files.items() if k.startswith("docs/context/modules/"))
    add(f"  {'docs/context/modules/*.md':<34} {card_lines:>5}  (one card per module)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
