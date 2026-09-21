#!/usr/bin/env python3
"""Guardrail: a contract card is never more than one merged pull request behind its interface.

Each card in docs/context/modules/*.md lists its interface files and records a sha256 of each one as
it was when the card was last read against the code. If a hash no longer matches, the card is stale
and the build fails -- which is what forces the card to be updated in the same pull request as the
interface change (AGENTS.md 3.3).

**Why content hashes and not a commit sha.** The card used to record `verified_at: <commit>`, and
that value cannot survive this repository's own merge policy: squash merges discard branch commits,
so a card verified against one becomes unresolvable the moment it lands, and every later pull request
fails on `main`. Rebases orphan it the same way. A hash of the file has no such problem -- it needs no
object from any history, only the bytes in front of it.

usage: scripts/check_context_freshness.py [--fix <module>]
       --fix <module> records the current hashes on that one module's card and touches no other
       card. Run it only once you have actually re-read that card against its interface -- the
       hash is the attestation that you did, and a reviewer reads it that way.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import pathlib
import re
import sys

CARDS = pathlib.Path("docs/context/modules")


def file_hash(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]


def front_matter(text: str) -> str:
    m = re.match(r"^---\n(.*?)\n---", text, re.S)
    return m.group(1) if m else ""


def listed(fm: str, key: str) -> list[str]:
    m = re.search(rf"^{key}:\n((?:\s*-\s*.+\n)+)", fm, re.M)
    if not m:
        return []
    out = []
    for line in m.group(1).strip().splitlines():
        name = line.split("#", 1)[0].strip().lstrip("-").strip()
        if name:
            out.append(name)
    return out


def recorded_hashes(text: str) -> dict[str, str]:
    """Parse the verified_hashes block: two-space-indented `"path": "hash"` lines."""
    fm = front_matter(text)
    m = re.search(r"^verified_hashes:\n((?:\s+\".+\n)+)", fm, re.M)
    if not m:
        return {}
    pairs = re.findall(r'"([^"]+)":\s*"([^"]+)"', m.group(1))
    return dict(pairs)


def write_hashes(card: pathlib.Path, hashes: dict[str, str]) -> None:
    text = card.read_text()
    block = "verified_hashes:\n" + "".join(f'  "{p}": "{h}"\n' for p, h in sorted(hashes.items()))
    today = f"verified_on: {dt.date.today().isoformat()}"
    if re.search(r"^verified_hashes:\n(?:\s+\".+\n)+", text, re.M):
        text = re.sub(r"^verified_hashes:\n(?:\s+\".+\n)+", block, text, flags=re.M)
    else:
        text = re.sub(r"^verified_on:.*$", block + today, text, count=1, flags=re.M)
    text = re.sub(r"^verified_on:.*$", today, text, count=1, flags=re.M)
    text = re.sub(r"^verified_at:.*\n", "", text, count=1, flags=re.M)  # the old, unusable field
    card.write_text(text)


def main_with(cards_dir: pathlib.Path = CARDS, fix: str | None = None) -> int:
    """Check every card. With `fix` set to a module name, record hashes on that card only.

    `fix` is deliberately not a bare flag. Recording a hash asserts that a human re-read that card
    against its interface, so a `--fix` that swept every implemented card would write that assertion
    onto cards nobody opened -- forging exactly the claim this guardrail exists to make unforgeable.
    Naming the module is the smallest thing that keeps the assertion true.
    """
    if fix is not None:
        target = cards_dir / f"{fix}.md"
        if not fix or not target.is_file():
            known = ", ".join(sorted(p.stem for p in cards_dir.glob("*.md"))) or "(none)"
            print(f"::error::--fix needs the module whose card you just re-read. Known cards: {known}")
            return 2

    stale: list[str] = []
    to_fix: dict[pathlib.Path, dict[str, str]] = {}
    checked = 0

    for card in sorted(cards_dir.glob("*.md")):
        text = card.read_text()
        fm = front_matter(text)
        if not fm:
            print(f"::error file={card}::card has no front matter (copy TEMPLATE-module-card.md)")
            return 1

        interfaces = listed(fm, "interface_files")
        if not interfaces:
            continue
        placeholder = "PLACEHOLDER - not yet a contract" in text or "PLACEHOLDER — not yet a contract" in text
        existing = {p: pathlib.Path(p) for p in interfaces if pathlib.Path(p).exists()}
        if placeholder and existing:
            stale.append(
                f"{card}: still a PLACEHOLDER, but {next(iter(existing))} exists -- write the "
                "contract in the pull request that lands the interface (AGENTS.md 3.1)"
            )
            continue
        if not existing:
            continue  # nothing implemented yet; a card may describe what is still planned

        recorded = recorded_hashes(text)
        current = {path: file_hash(p) for path, p in existing.items()}
        to_fix[card] = current
        for path, now in current.items():
            checked += 1
            then = recorded.get(path)
            if then is None:
                stale.append(f"{card}: no recorded hash for {path}; record one with --fix {card.stem}")
            elif then != now:
                stale.append(f"{card}: {path} changed since the card was last verified")

    if fix is not None:
        hashes = to_fix.get(target)
        if hashes is None:
            print(f"::error::{target} lists no interface file that exists; nothing to record")
            return 2
        write_hashes(target, hashes)
        print(f"recorded {len(hashes)} hash(es) on {target}; no other card was touched")
        return 0

    if stale:
        for s in stale:
            print(f"::error::{s}")
        print(
            "::error::A contract card is stale. Re-read it against the interface, update it, then "
            "record the new hashes (scripts/check_context_freshness.py --fix <module>, one card at a "
            "time) in this same pull request."
        )
        return 1

    cards = len(list(cards_dir.glob("*.md")))
    print(f"context-freshness OK: {checked} interface files checked across {cards} cards")
    return 0


def parse_fix(argv: list[str]) -> str | None:
    """`--fix <module>` -> "module"; `--fix` with nothing after it -> "", which main_with refuses."""
    if "--fix" not in argv:
        return None
    after = argv[argv.index("--fix") + 1 :]
    return after[0] if after and not after[0].startswith("-") else ""


if __name__ == "__main__":
    raise SystemExit(main_with(fix=parse_fix(sys.argv[1:])))
