#!/usr/bin/env python3
"""Print the session orientation brief: where the project is, and what is in flight.

Reads DESIGN §19 for the plan, `git worktree list` for what is open, each task log's last HANDOFF
for where it stopped, docs/context/INDEX.md for card status, and GitHub for review state. **Writes
nothing**, so the brief cannot go stale, cannot land in a diff and cannot conflict on a rebase.

No done column for the phase's tasks: nothing in the repository records completion, so it would be
a guess, and a guessed "done" is worse than none. Nothing from CLAUDE.md either — a Claude Code
session already loads it, and printing it again would be paying twice.

usage: scripts/orient.py [--no-network]
"""
from __future__ import annotations

import datetime as dt
import json
import re
import subprocess
import sys
from pathlib import Path

MONTHS = {m: i for i, m in enumerate(
    ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"], start=1)}

DESIGN = Path("docs/DESIGN.md")
INDEX = Path("docs/context/INDEX.md")
LOG_DIR = Path("docs/agent-log")


def run(*args: str, timeout: int = 10) -> str:
    """Run a command and return stdout, or "" if it fails. Never raises: the brief degrades."""
    try:
        out = subprocess.run(args, capture_output=True, text=True, timeout=timeout, check=False)
    except (OSError, subprocess.SubprocessError):
        return ""
    return out.stdout if out.returncode == 0 else ""


# --- plan

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


# --- what is in flight

HANDOFF_CHARS = 220


def timeline(log: str) -> str:
    """Just the entries: the template's header explains the closing marker in prose, so a whole-file
    search finds that sentence in every log that was never closed."""
    _, _, rest = log.partition("\n## Timeline")
    return rest


def last_handoff(log: str, limit: int = HANDOFF_CHARS) -> str:
    """The last HANDOFF entry, clipped at a sentence boundary.

    Clipped because a full handoff runs to a paragraph and this is read at the top of every
    session. The first sentences say where the work stopped; the log is one `cat` away.
    """
    entries = re.split(r"^### .*?· ([A-Z]+) ·.*$", timeline(log), flags=re.M)
    # split() yields [preamble, kind, body, kind, body, ...]
    for kind, body in reversed(list(zip(entries[1::2], entries[2::2], strict=False))):
        if kind != "HANDOFF":
            continue
        text = " ".join(body.split())
        if len(text) <= limit:
            return text
        cut = text.rfind(". ", 0, limit)
        return text[: cut + 1] + " […]" if cut > 0 else text[:limit].rstrip() + " […]"
    return ""


def worktrees(here: Path) -> list[dict]:
    """Every task worktree, with its branch and the state its own log was left in.

    `--porcelain` puts the main worktree first; it is the checkout of `main`, not a task, so it is
    dropped. A task log lives only on its own branch, so each is read from inside its worktree.
    """
    out = []
    blocks = run("git", "worktree", "list", "--porcelain").split("\n\n")
    for block in blocks[1:]:
        path = re.search(r"^worktree (.+)$", block, re.M)
        branch = re.search(r"^branch refs/heads/(.+)$", block, re.M)
        if not path or not branch:
            continue
        log = LOG_DIR / f"{branch.group(1).replace('/', '-')}.md"
        on_disk = Path(path.group(1)) / log
        text = on_disk.read_text() if on_disk.exists() else ""
        out.append({"path": path.group(1), "branch": branch.group(1), "log": str(log),
                    "handoff": last_handoff(text),
                    "closed": "TASK CLOSED" in timeline(text),
                    "here": Path(path.group(1)) == here})
    return out


def open_prs() -> dict[str, str]:
    """branch → review state, from GitHub. Empty when gh is missing or offline."""
    raw = run("gh", "pr", "list", "--state", "open", "--limit", "30",
              "--json", "number,headRefName,isDraft,reviewDecision", timeout=20)
    if not raw:
        return {}
    try:
        prs = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    states = {}
    for pr in prs:
        decision = {"": "awaiting review", "REVIEW_REQUIRED": "awaiting review",
                    "APPROVED": "APPROVED", "CHANGES_REQUESTED": "CHANGES REQUESTED"}.get(
            pr.get("reviewDecision") or "", (pr.get("reviewDecision") or "").lower())
        flag = "DRAFT" if pr.get("isDraft") else decision
        states[pr["headRefName"]] = f"PR #{pr['number']} {flag}"
    return states


# --- render

def render(head: str, phase: dict | None, note: str, tasks: list[tuple[str, str]],
           cards: dict[str, list[str]], trees: list[dict], prs: dict[str, str],
           merges: list[str], network: bool) -> str:
    lines: list[str] = []
    add = lines.append

    add(f"WAYFINDER — main {head or '(unknown)'}")
    if phase:
        add(f"  {phase['id']} {phase['theme']} · {phase['start']} to {phase['end']}"
            + (f" · {note}" if note else ""))
        add(f"  gate {re.sub(r'[*]', '', phase['gate'])}")
    else:
        add(f"  {note}")

    add("")
    add("IN FLIGHT" if trees else "IN FLIGHT  nothing — start with scripts/new-task.sh")
    for t in trees:
        state = prs.get(t["branch"], "no pull request" if network else "pull request state unknown")
        marks = "  <- you are here" if t["here"] else ""
        marks += "  CLOSED" if t["closed"] else ""
        add(f"  {t['branch']}  [{state}]{marks}")
        add(f"    worktree {t['path']}")
        if t["handoff"]:
            add(f"    handoff  {t['handoff']}")
        else:
            add(f"    handoff  none yet — read {t['log']}")

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
    if not network:
        add("Review state not fetched (--no-network).")
    return "\n".join(lines)


def main(argv: list[str]) -> int:
    network = "--no-network" not in argv
    here = Path(run("git", "rev-parse", "--show-toplevel").strip() or ".")
    design = DESIGN.read_text() if DESIGN.exists() else ""
    index = INDEX.read_text() if INDEX.exists() else ""

    today = dt.date.today()
    phases = parse_phases(design, today.year)
    phase, note = current_phase(phases, today)

    print(render(
        head=run("git", "rev-parse", "--short", "main").strip(),
        phase=phase,
        note=note,
        tasks=phase_tasks(design, phase["id"]) if phase else [],
        cards=parse_cards(index),
        trees=worktrees(here),
        prs=open_prs() if network else {},
        merges=[m for m in run("git", "log", "main", "--oneline", "-5").splitlines() if m],
        network=network,
    ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
