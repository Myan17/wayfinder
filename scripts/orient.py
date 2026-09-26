#!/usr/bin/env python3
"""Print the session orientation brief: where the project is, and what is in flight.

Reads DESIGN §19 for the plan and docs/context/INDEX.md for card status. **Writes nothing**, so
the brief cannot go stale, cannot land in a diff and cannot conflict on a rebase.

Also reads `git worktree list` for what is open, each task log's last HANDOFF for where it stopped,
and GitHub for review state.

Also reads ORIENT.md's item table for the NEXT item, its owner actions and the phase's budget.
Status comes from ORIENT only, where a merged pull request records it; the brief never guesses one.
Nothing from CLAUDE.md — a Claude Code session already loads it, and printing it twice costs twice.

usage: scripts/orient.py [--no-network]
"""
from __future__ import annotations

import datetime as dt
import json
import re
import subprocess
import sys
import textwrap
from pathlib import Path

MONTHS = {m: i for i, m in enumerate(
    ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"], start=1)}

# Anchored to the repository, not to the caller's directory: run from scripts/ with relative paths
# and every read misses, which the brief reports as "no phase table found" rather than as an error.
ROOT = Path(__file__).resolve().parents[1]
DESIGN = ROOT / "docs/DESIGN.md"
INDEX = ROOT / "docs/context/INDEX.md"
ORIENT = ROOT / "ORIENT.md"
LOG_DIR = Path("docs/agent-log")  # relative: joined onto each worktree's own path


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


def orient_items(orient: str) -> list[dict]:
    """The rows of ORIENT's item table, in order. An em dash in the hours column is unsized."""
    items = []
    for line in orient.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) == 5 and re.fullmatch(r"\d+[a-z]?", cells[0]):
            items.append({"id": cells[0], "item": cells[1],
                          "hours": int(cells[2]) if cells[2].isdigit() else None,
                          "status": cells[4]})
    return items


def next_item(items: list[dict]) -> dict | None:
    """ORIENT rule 1: the first item that is neither done nor blocked."""
    return next((i for i in items if not i["status"].startswith(("done", "blocked"))), None)


def owner_actions(orient: str) -> list[str]:
    """The bullets of ORIENT's `## Owner actions` section: things only an owner can do."""
    section = re.search(r"^## Owner actions\n(.*?)(?=^## |\Z)", orient, re.M | re.S)
    # a bullet runs on over indented continuation lines, as Markdown wraps them
    bullets = re.findall(r"^- (.+(?:\n  +\S.*)*)", section.group(1), re.M) if section else []
    return [" ".join(b.split()) for b in bullets]


def budget(orient: str, items: list[dict], phase: dict | None, today: dt.date) -> list[str]:
    """Open hours against the days the phase has left, at the pace the phase was planned at.

    The warning is ORIENT rule 5's trigger, and it has to be computed: nobody reads "Sep 21 - 27"
    and the item table together at the top of a session and does the sum.
    """
    if not phase:
        return []
    open_ = [i for i in items if not i["status"].startswith(("done", "blocked"))]
    sized = [i for i in open_ if i["hours"] is not None]
    hours = sum(i["hours"] for i in sized)
    days = (phase["end"] - today).days + 1
    gate = (re.search(r"G\d+", phase["gate"]) or re.search(r"P\d+", phase["id"])).group(0)
    plan = re.search(r"(\d+) h planned, (\d+) h of contingency", orient)
    unsized = [i["id"] for i in open_ if i["hours"] is None]
    line = (f"BUDGET  {gate} closes {phase['end']}, {days} days left · {hours} h open "
            f"({' '.join(i['id'] for i in sized)}{'; unsized ' + ' '.join(unsized) if unsized else ''})")
    if not plan:
        return [line]
    lines = [line + f" · {plan.group(2)} h contingency"]
    pace = int(plan.group(1)) / ((phase["end"] - phase["start"]).days + 1)
    if 0 < days and hours > pace * days:
        lines.append(f"  !! at the planned pace ({pace:.1f} h/day) {days} days hold {pace * days:.0f} h:"
                     f" apply ORIENT rule 5 (DESIGN §19.8) today, and rule 6 (the next phase's list)"
                     f" before {gate} closes")
    return lines


def parse_cards(index: str) -> dict[str, list[str]]:
    """Module names from docs/context/INDEX.md, split by whether the card is real or a placeholder."""
    out: dict[str, list[str]] = {"written": [], "placeholder": []}
    for row in re.finditer(r"^\| `([a-z-]+)` \| [^|]+ \| (✅|🟡)", index, re.M):
        out["written" if row.group(2) == "✅" else "placeholder"].append(row.group(1))
    return out


# --- what is in flight

def timeline(log: str) -> str:
    """Just the entries: the template's header explains the closing marker in prose, so a whole-file
    search finds that sentence in every log that was never closed."""
    _, _, rest = log.partition("\n## Timeline")
    return rest


def is_closed(log: str) -> bool:
    """`end-task.sh` opens the closing entry's body with "TASK CLOSED. ", so the marker is only a
    marker at the start of a line. Anywhere else it is an entry talking about closing a task."""
    return re.search(r"^TASK CLOSED\b", timeline(log), re.M) is not None


def entries(log: str) -> list[tuple[str, str, str]]:
    """(kind, date, body) for every timeline entry, oldest first, body on one line."""
    heads = list(re.finditer(r"^### (\d{4}-\d{2}-\d{2})\S* · ([A-Z]+) ·.*$", timeline(log), re.M))
    text = timeline(log)
    return [(h.group(2), h.group(1),
             " ".join(text[h.end():heads[n + 1].start() if n + 1 < len(heads) else None].split()))
            for n, h in enumerate(heads)]


def clip(text: str, limit: int) -> str:
    """Clipped at a sentence boundary when there is one before the limit."""
    if len(text) <= limit:
        return text
    cut = text.rfind(". ", 0, limit)
    return text[: cut + 1] + " […]" if cut > 0 else text[:limit].rstrip() + " […]"


def last_handoff(log: str, limit: int = 220) -> str:
    """The last HANDOFF entry, clipped: the brief shows it for work that is not the next item."""
    handoff, _ = handoff_and_after(log)
    return clip(handoff, limit)


def handoff_and_after(log: str) -> tuple[str, list[str]]:
    """The last HANDOFF whole, and one clipped line per entry written after it.

    Whole because this is the worktree the session is about to resume: the clip used to cut
    "Next, in order: ..." off the S5 handoff, so the brief said where work stopped but not what
    came next. The later entries are there because a TEST after the handoff can overturn it.
    """
    es = entries(log)
    last = max((n for n, e in enumerate(es) if e[0] == "HANDOFF"), default=None)
    if last is None:
        return "", []
    # a TEST, DECIDE or BLOCKED can overturn the handoff, so those stay whole; the rest is a record
    return es[last][2], [f"{k} {d}: {b if k in ('TEST', 'DECIDE', 'BLOCKED') else clip(b, 160)}"
                         for k, d, b in es[last + 1:]]


def orient_item_of(log: str) -> str | None:
    """The ORIENT item a task log says it works on, from its header's Task field."""
    m = re.search(r"^\| Task \| .*?ORIENT item (\w+)", log, re.M)
    return m.group(1) if m else None


def mark_merged(text: str, merged: set[int]) -> str:
    """Handoffs are written before merges happen; say so where they name a merged pull request."""
    return re.sub(r"#(\d+)\b", lambda m: m.group(0) + (" [merged]" if int(m.group(1)) in merged
                                                        else ""), text)


def worktrees(here: Path, merged: set[int] = frozenset()) -> list[dict]:
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
        full, later = handoff_and_after(text)
        task = re.search(r"^\| Task \| (.+?) \|$", text, re.M)
        out.append({"path": path.group(1), "branch": branch.group(1), "log": str(log),
                    "handoff": mark_merged(last_handoff(text), merged),
                    "full": mark_merged(full, merged), "later": later,
                    "item": orient_item_of(text), "task": task.group(1) if task else "",
                    "closed": is_closed(text),
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
        # REVIEW_REQUIRED is GitHub's wording for "nobody has reviewed it yet".
        decision = (pr.get("reviewDecision") or "REVIEW_REQUIRED").replace("_", " ")
        decision = "awaiting review" if decision == "REVIEW REQUIRED" else decision
        states[pr["headRefName"]] = f"PR #{pr['number']} {'DRAFT' if pr.get('isDraft') else decision}"
    return states


def merged_prs() -> set[int]:
    """Numbers of recently merged pull requests, to mark stale mentions in handoffs."""
    raw = run("gh", "pr", "list", "--state", "merged", "--limit", "100", "--json", "number",
              timeout=20)
    try:
        return {pr["number"] for pr in json.loads(raw)} if raw else set()
    except json.JSONDecodeError:
        return set()


def render(head: str, phase: dict | None, note: str, cards: dict[str, list[str]],
           trees: list[dict], prs: dict[str, str], merges: list[str], network: bool,
           items: list[dict] | None = None, actions: list[str] | None = None,
           budget_lines: list[str] | None = None) -> str:
    lines: list[str] = []
    add = lines.append

    def state(t_: dict) -> str:
        return prs.get(t_["branch"], "no pull request" if network else "pull request state unknown")

    add(f"WAYFINDER — main {head or '(unknown)'}")
    if phase:
        add(f"  {phase['id']} {phase['theme']} · {phase['start']} to {phase['end']}"
            + (f" · {note}" if note else ""))
        add(f"  gate {re.sub(r'[*]', '', phase['gate'])}")
    else:
        add(f"  {note}")
    lines.extend(budget_lines or [])

    nxt = next_item(items or [])
    resumed = next((t_ for t_ in trees if nxt and t_.get("item") == nxt["id"] and not t_["closed"]),
                   None)
    if nxt:
        add("")
        add(f"NEXT  item {nxt['id']} · {nxt['item']}  (ORIENT rule 1)")
        if resumed:
            add(f"  resume  {resumed['branch']}  [{state(resumed)}] — do not run new-task.sh")
            add(f"    worktree {resumed['path']}")
            if resumed.get("task"):
                add(f"    task     {resumed['task']}")
            add(textwrap.fill(resumed.get("full") or f"none yet — read {resumed['log']}", width=100,
                              initial_indent="    handoff  ", subsequent_indent=" " * 13))
            for n, entry in enumerate(resumed.get("later", [])):
                add(textwrap.fill(entry, width=100, subsequent_indent=" " * 13,
                                  initial_indent="    since    " if n == 0 else " " * 13))
        else:
            add(f'  start   scripts/new-task.sh <module> <slug> "<description> (ORIENT item {nxt["id"]})"')

    if actions:
        add("")
        add("OWNER ACTIONS  myan's, not an agent's; remind, do not do")
        for a in actions:
            add(f"  - {a}")

    others = [t_ for t_ in trees if t_ is not resumed]
    add("")
    if resumed:
        add("OTHER IN FLIGHT" if others else "OTHER IN FLIGHT  nothing")
    else:
        add("IN FLIGHT" if others else "IN FLIGHT  nothing — start with scripts/new-task.sh")
    for t_ in others:
        marks = "  <- you are here" if t_["here"] else ""
        marks += "  CLOSED" if t_["closed"] else ""
        add(f"  {t_['branch']}  [{state(t_)}]{marks}")
        add(f"    worktree {t_['path']}")
        add(f"    handoff  {t_['handoff'] or 'none yet — read ' + t_['log']}")

    if merges:
        add("")
        add("LAST MERGES")
        for m in merges:
            add(f"  {m}")

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
    base = build_window_year(design)
    phases = parse_phases(design, base) if base else []
    phase, note = current_phase(phases, today)
    if base is None:
        note = "DESIGN has no 'Planned build window' row, so §19.1's dates carry no year"

    orient = ORIENT.read_text() if ORIENT.exists() else ""
    items = orient_items(orient)
    print(render(
        head=run("git", "rev-parse", "--short", "main").strip(),
        phase=phase,
        note=note,
        cards=parse_cards(index),
        trees=worktrees(here, merged_prs() if network else set()),
        prs=open_prs() if network else {},
        network=network,
        merges=[m for m in run("git", "log", "main", "--oneline", "-3").splitlines() if m],
        items=items,
        actions=owner_actions(orient),
        budget_lines=budget(orient, items, phase, today),
    ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
