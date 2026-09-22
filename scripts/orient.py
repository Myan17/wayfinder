#!/usr/bin/env python3
"""Print the session orientation brief: where the project is, and what is in flight.

Reads DESIGN §19 for the plan and docs/context/INDEX.md for card status. **Writes nothing**, so
the brief cannot go stale, cannot land in a diff and cannot conflict on a rebase.

This is the plan half: which phase we are in, what it contains, and which contract cards are real.
The in-flight half — open worktrees, their last HANDOFF and their review state — is its own pull
request, and the brief is useful without it.

No done column for the phase's tasks: nothing in the repository records completion, so it would be
a guess, and a guessed "done" is worse than none. Nothing from CLAUDE.md either — a Claude Code
session already loads it, and printing it again would be paying twice.

usage: scripts/orient.py
"""
from __future__ import annotations

import datetime as dt
import re
import subprocess
from pathlib import Path

MONTHS = {m: i for i, m in enumerate(
    ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"], start=1)}

# Anchored to the repository, not to the caller's directory: run from scripts/ with relative paths
# and every read misses, which the brief reports as "no phase table found" rather than as an error.
ROOT = Path(__file__).resolve().parents[1]
DESIGN = ROOT / "docs/DESIGN.md"
INDEX = ROOT / "docs/context/INDEX.md"


def run(*args: str, timeout: int = 10) -> str:
    """Run a command in the repository root and return stdout, or "" if it fails.

    Never raises: a missing `gh`, a timeout or a non-zero exit degrades the brief instead of
    killing it. `cwd` is pinned for the same reason the paths above are.
    """
    try:
        out = subprocess.run(args, capture_output=True, text=True, timeout=timeout,
                             check=False, cwd=ROOT)
    except (OSError, subprocess.SubprocessError):
        return ""
    return out.stdout if out.returncode == 0 else ""


# --- plan

def build_window_year(design: str) -> int | None:
    """The year the schedule starts, from DESIGN's `Planned build window` row.

    §19.1's table writes months and days with no year. Taking the year from today's date is wrong
    the moment the calendar rolls over: every phase shifts a year, the current phase reads as past,
    and nothing in the output says so. The window is the design's own statement of when this is
    built, so it is the source. No window, no phase dates — better silent than confidently wrong.
    """
    m = re.search(r"^\| Planned build window \|[^|]*?(\d{4})-\d{2}-\d{2}", design, re.M)
    return int(m.group(1)) if m else None


def parse_phases(design: str, base_year: int) -> list[dict]:
    """Rows of the §19.1 phase table, with dates resolved to real years.

    A span reads "Sep 21 <en dash> 27", or "Sep 28 <en dash> Oct 11" across a month, and carries no
    year: it comes from base_year and rolls forward when the month sequence goes backwards. The
    dash is U+2013, matched by escape so this file stays ASCII.
    """
    phases: list[dict] = []
    year = base_year
    prev_month = 0
    for row in re.finditer(r"^\| (P\d) \| ([^|]+?) \| ([^|]+?) \| ([^|]+?) \| ([^|]+?) \|$",
                           design, re.M):
        pid, weeks, dates, theme, gate = (g.strip() for g in row.groups())
        span = re.match(r"([A-Z][a-z]{2}) (\d{1,2})\s*[\u2013-]\s*(?:([A-Z][a-z]{2}) )?(\d{1,2})",
                        dates)
        if not span:
            continue
        m1, d1, m2, d2 = span.group(1), int(span.group(2)), span.group(3) or span.group(1), int(span.group(4))
        if MONTHS[m1] < prev_month:
            year += 1
        prev_month = MONTHS[m2]
        start = dt.date(year, MONTHS[m1], d1)
        end = dt.date(year + (1 if MONTHS[m2] < MONTHS[m1] else 0), MONTHS[m2], d2)
        phases.append({"id": pid, "weeks": weeks, "start": start, "end": end,
                       "theme": theme, "gate": gate})
    return phases


def current_phase(phases: list[dict], today: dt.date) -> tuple[dict | None, str]:
    """The phase today falls in, plus a note when it falls outside the plan."""
    for p in phases:
        if p["start"] <= today <= p["end"]:
            return p, ""
    if phases and today < phases[0]["start"]:
        return phases[0], f"not started yet — {phases[0]['id']} opens {phases[0]['start']}"
    if phases and today > phases[-1]["end"]:
        return phases[-1], f"past the plan — {phases[-1]['id']} closed {phases[-1]['end']}"
    return None, "no phase table found in DESIGN §19.1"


def phase_tasks(design: str, phase_id: str) -> list[tuple[str, str]]:
    """The task/hours rows of the §19.x table for one phase."""
    section = re.search(rf"^### 19\.\d+ Phase {phase_id[1:]} — .*?(?=^### |^## )", design, re.M | re.S)
    if not section:
        return []
    tasks = []
    for row in re.finditer(r"^\| ([^|]+?) \| (\d+) \|", section.group(0), re.M):
        label = re.sub(r"[`*]", "", row.group(1)).strip()
        if label.lower() != "task":
            tasks.append((label, row.group(2)))
    return tasks


def parse_cards(index: str) -> dict[str, list[str]]:
    """Module names from docs/context/INDEX.md, split by whether the card is real or a placeholder."""
    out: dict[str, list[str]] = {"written": [], "placeholder": []}
    for row in re.finditer(r"^\| `([a-z-]+)` \| [^|]+ \| (✅|🟡)", index, re.M):
        out["written" if row.group(2) == "✅" else "placeholder"].append(row.group(1))
    return out


def render(head: str, phase: dict | None, note: str, tasks: list[tuple[str, str]],
           cards: dict[str, list[str]], merges: list[str]) -> str:
    lines: list[str] = []
    add = lines.append

    add(f"WAYFINDER — main {head or '(unknown)'}")
    if phase:
        add(f"  {phase['id']} {phase['theme']} · {phase['start']} to {phase['end']}"
            + (f" · {note}" if note else ""))
        add(f"  gate {re.sub(r'[*]', '', phase['gate'])}")
    else:
        add(f"  {note}")

    if merges:
        add("")
        add("LAST MERGES")
        for m in merges:
            add(f"  {m}")

    if tasks:
        add("")
        add(f"{phase['id']} TASKS (DESIGN §19; no done column — nothing in the repo records completion)")
        for label, hours in tasks:
            add(f"  {hours:>2}h  {label}")

    if cards["written"] or cards["placeholder"]:
        add("")
        add("CARDS  read these, not other modules' code (AGENTS.md §3.2)")
        add(f"  written      {' '.join(cards['written'])}")
        add(f"  placeholder  {' '.join(cards['placeholder'])}  — build against one and you open a BCR first")

    add("")
    add("Durable half of orientation is CLAUDE.md, already loaded. Rules: AGENTS.md.")
    return "\n".join(lines)


def main() -> int:
    design = DESIGN.read_text() if DESIGN.exists() else ""
    index = INDEX.read_text() if INDEX.exists() else ""

    today = dt.date.today()
    base = build_window_year(design)
    phases = parse_phases(design, base) if base else []
    phase, note = current_phase(phases, today)
    if base is None:
        note = "DESIGN has no 'Planned build window' row, so §19.1's dates carry no year"

    print(render(
        head=run("git", "rev-parse", "--short", "main").strip(),
        phase=phase,
        note=note,
        tasks=phase_tasks(design, phase["id"]) if phase else [],
        cards=parse_cards(index),
        merges=[m for m in run("git", "log", "main", "--oneline", "-5").splitlines() if m],
    ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
