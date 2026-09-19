#!/usr/bin/env python3
"""Turn the week's task logs into the gate report.

usage: scripts/weekly_digest.py [--week YYYY-Www] [--since YYYY-MM-DD] [--until YYYY-MM-DD]

Writes docs/agent-log/DIGEST-<year>-W<week>.md: work by operator and module, decisions taken,
blockers, tests run, commits. This is the artifact DESIGN §19.9 asks for at each phase gate — built
from what actually happened rather than from memory.
"""
from __future__ import annotations
import argparse
import datetime as dt
import pathlib
import re
import subprocess
from collections import defaultdict

LOGS = pathlib.Path("docs/agent-log")
ENTRY = re.compile(r"^### (?P<ts>\S+) · (?P<type>[A-Z]+) · (?P<op>\S+) · (?P<agent>\S+) · (?P<sha>\S+)$")


def parse(path: pathlib.Path):
    text = path.read_text()
    meta = dict(re.findall(r"^\| (\w[\w ]*) \| (.+) \|$", text, re.M))
    lines = text.splitlines()
    for i, line in enumerate(lines):
        m = ENTRY.match(line)
        if not m:
            continue
        body: list[str] = []
        for nxt in lines[i + 1 :]:
            if ENTRY.match(nxt):
                break
            if nxt.strip():
                body.append(nxt.strip())
        yield {**m.groupdict(), "body": " ".join(body)[:300], "task": path.stem,
               "module": meta.get("Module", "?"), "status": meta.get("Status", "?")}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--week")
    ap.add_argument("--since")
    ap.add_argument("--until")
    a = ap.parse_args()

    today = dt.date.today()
    if a.week:
        year, wk = a.week.split("-W")
        monday = dt.date.fromisocalendar(int(year), int(wk), 1)
    else:
        monday = today - dt.timedelta(days=today.weekday())
    since = dt.date.fromisoformat(a.since) if a.since else monday
    until = dt.date.fromisoformat(a.until) if a.until else since + dt.timedelta(days=6)
    year, week, _ = since.isocalendar()

    entries = []
    for f in sorted(LOGS.glob("*.md")):
        if f.name in {"README.md", "TEMPLATE.md"} or f.name.startswith("DIGEST-"):
            continue
        for e in parse(f):
            try:
                day = dt.datetime.strptime(e["ts"], "%Y-%m-%dT%H:%M:%SZ").date()
            except ValueError:
                continue
            if since <= day <= until:
                entries.append({**e, "day": day})

    by_op: dict[str, list] = defaultdict(list)
    for e in entries:
        by_op[e["op"]].append(e)

    out = [
        f"# Digest {year}-W{week:02d} ({since} → {until})",
        "",
        f"Generated {dt.datetime.utcnow().strftime('%Y-%m-%dT%H:%MZ')} from {len(entries)} log entries "
        f"across {len({e['task'] for e in entries})} tasks.",
        "",
        "## Work by operator",
        "",
        "| Operator | Agent(s) | Tasks | Edits | Tests | Decisions | Blockers | Commits |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for op, es in sorted(by_op.items()):
        count = lambda t: sum(1 for e in es if e["type"] == t)  # noqa: E731
        agents = ", ".join(sorted({e["agent"] for e in es}))
        out.append(
            f"| {op} | {agents} | {len({e['task'] for e in es})} | {count('EDIT')} | "
            f"{count('TEST')} | {count('DECIDE')} | {count('BLOCKED')} | {count('COMMIT')} |"
        )

    for title, kind in (("Decisions", "DECIDE"), ("Blockers", "BLOCKED"), ("Handoffs still open", "HANDOFF")):
        rows = [e for e in entries if e["type"] == kind]
        out += ["", f"## {title}", ""]
        if not rows:
            out.append("_none_")
            continue
        for e in rows:
            out.append(f"- **{e['day']} · {e['op']} · {e['module']}** — {e['body']} (`{e['task']}`)")

    tests = [e for e in entries if e["type"] == "TEST"]
    out += ["", "## Test runs recorded", ""]
    out += [f"- {e['day']} · {e['op']} · {e['body']}" for e in tests] if tests else ["_none_"]

    try:
        log = subprocess.run(
            ["git", "log", f"--since={since}", f"--until={until + dt.timedelta(days=1)}", "--format=%h %an %s"],
            check=True, capture_output=True, text=True).stdout.strip().splitlines()
    except subprocess.CalledProcessError:
        log = []
    commit_lines = [f"- `{line}`" for line in log] if log else ["_none_"]
    out += ["", "## Commits on this branch", "", *commit_lines]
    out += ["", "## Open questions for the gate review", "", "- (fill in before the gate meeting)", ""]

    path = LOGS / f"DIGEST-{year}-W{week:02d}.md"
    path.write_text("\n".join(out) + "\n")
    print(f"wrote {path} ({len(entries)} entries)")


if __name__ == "__main__":
    main()
