#!/usr/bin/env python3
"""Guardrail: a contract card is never more than one merged pull request behind its interface.

Each card in docs/context/modules/*.md declares its interface files and the commit it was last
verified at. If any interface file's content at HEAD differs from its content at that commit, the
card is stale and the build fails — which is what forces the card to be updated in the same pull
request as the interface change (AGENTS.md §3.3).

usage: scripts/check_context_freshness.py [--fix]
       --fix rewrites verified_at/verified_on to HEAD (use only when you have actually re-read the card)
"""
from __future__ import annotations
import datetime as dt
import pathlib
import re
import subprocess
import sys

CARDS = pathlib.Path("docs/context/modules")


def blob(ref: str, path: str) -> str | None:
    r = subprocess.run(["git", "show", f"{ref}:{path}"], capture_output=True, text=True)
    return r.stdout if r.returncode == 0 else None


def front_matter(text: str) -> str:
    m = re.match(r"^---\n(.*?)\n---", text, re.S)
    return m.group(1) if m else ""


def listed(fm: str, key: str) -> list[str]:
    m = re.search(rf"^{key}:\n((?:\s*-\s*.+\n)+)", fm, re.M)
    return [ln.strip().lstrip("- ").strip() for ln in m.group(1).strip().splitlines()] if m else []


def scalar(fm: str, key: str) -> str:
    m = re.search(rf"^{key}:\s*(.+)$", fm, re.M)
    return m.group(1).strip() if m else ""


def main() -> int:
    fix = "--fix" in sys.argv
    head = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    stale: list[str] = []
    to_fix: list[pathlib.Path] = []
    checked = 0

    for card in sorted(CARDS.glob("*.md")):
        text = card.read_text()
        fm = front_matter(text)
        if not fm:
            print(f"::error file={card}::card has no front matter (copy TEMPLATE-module-card.md)")
            return 1
        interfaces = listed(fm, "interface_files")
        verified = scalar(fm, "verified_at")
        if not interfaces:
            continue
        placeholder = "PLACEHOLDER — not yet a contract" in text
        existing = [p for p in interfaces if pathlib.Path(p).exists()]
        if placeholder and existing:
            stale.append(
                f"{card}: still a PLACEHOLDER, but {existing[0]} exists — write the contract in the "
                "pull request that lands the interface (AGENTS.md §3.1)"
            )
            continue
        if not verified or set(verified) <= {"0"}:
            if existing:
                stale.append(
                    f"{card}: interface {existing[0]} exists but verified_at is unset — read the card "
                    "against the code and bump it (scripts/check_context_freshness.py --fix)"
                )
                to_fix.append(card)
            continue  # card written before the interface exists; unverified is fine until then

        for path in interfaces:
            if not pathlib.Path(path).exists():
                continue  # not implemented yet
            checked += 1
            then, now = blob(verified, path), blob("HEAD", path)
            if then is None:
                stale.append(f"{card}: interface {path} did not exist at verified_at {verified[:7]}")
                if card not in to_fix:
                    to_fix.append(card)
            elif then != now:
                stale.append(f"{card}: {path} changed since verified_at {verified[:7]}")
                if card not in to_fix:
                    to_fix.append(card)

    # --fix bumps verification stamps only. A PLACEHOLDER card is never auto-fixed: the whole point is
    # that a human writes the contract before anything depends on it.
    if fix:
        for card in to_fix:
            text = card.read_text()
            text = re.sub(r"^verified_at:.*$", f"verified_at: {head[:7]}", text, flags=re.M)
            text = re.sub(r"^verified_on:.*$", f"verified_on: {dt.date.today().isoformat()}", text, flags=re.M)
            card.write_text(text)
        print(f"bumped verified_at on {len(to_fix)} card(s) — re-read each one before committing")
        return 0

    if stale and not fix:
        for s in stale:
            print(f"::error::{s}")
        print(
            "::error::A contract card is stale. Re-read the card against the new interface, update it, "
            "then bump verified_at (scripts/check_context_freshness.py --fix) in this same pull request."
        )
        return 1

    print(f"context-freshness OK: {checked} interface files checked across {len(list(CARDS.glob('*.md')))} cards")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
