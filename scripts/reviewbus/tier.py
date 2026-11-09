"""ADR-0021 rule 6: the human-only tier. For these paths the reviewer agent may review, but Myan clicks.

The security modules' paths are read from `docs/team/OWNERSHIP.md`, never copied, so a path added to
`schema` or `authz` there joins the tier at once. A security module missing from that file is an error:
an empty tier would let the agent approve anything.
"""

from __future__ import annotations

import fnmatch
import re
from collections.abc import Iterable
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SECURITY = ("authz", "egress", "webhooks", "schema")
RULES = (
    "AGENTS.md",
    "CLAUDE.md",
    "ORIENT.md",
    "docs/team/**",
    "docs/adr/**",
    ".github/**",
    ".githooks/**",
    "scripts/check_*",
    "scripts/gen_codeowners.py",
)
BUS = ("scripts/reviewbus/**", "scripts/tests/reviewbus/**")

_MODULE = re.compile(r"^\s{2}([a-z0-9-]+):\s*\{owner:\s*[^,]+,\s*paths:\s*\[(.*?)\]\}", re.M)


def module_paths(ownership: str) -> dict[str, list[str]]:
    """Each module's path globs from OWNERSHIP.md's yaml block, as `check_ownership.py` reads it."""
    block = re.search(r"```yaml\n(.*?)```", ownership, re.S)
    if not block:
        raise ValueError("OWNERSHIP.md has no yaml block")
    out = {}
    for module, raw in _MODULE.findall(block.group(1)):
        paths = [p.strip() for p in raw.split(",") if p.strip()]
        if any(len(p) < 3 or p[0] not in "\"'" or p[-1] != p[0] for p in paths):
            raise ValueError(f"OWNERSHIP.md: {module} has a path that is not a quoted string: {raw!r}")
        out[module] = [p[1:-1] for p in paths]
    return out


def globs(ownership: str | None = None) -> tuple[str, ...]:
    text = ownership if ownership is not None else (ROOT / "docs/team/OWNERSHIP.md").read_text()
    modules = module_paths(text)
    if missing := [m for m in SECURITY if not modules.get(m)]:
        raise ValueError(f"OWNERSHIP.md has no paths for security module(s) {missing}")
    return tuple(p for m in SECURITY for p in modules[m]) + RULES + BUS


def matches(path: str, pattern: str) -> bool:
    return (
        path == pattern
        or fnmatch.fnmatch(path, pattern)
        or (pattern.endswith("/**") and path.startswith(pattern[:-2]))
    )


def human_only(paths: Iterable[str], tier: Iterable[str]) -> list[str]:
    """The changed paths that are in the tier, in input order."""
    tier = tuple(tier)
    return [p for p in paths if any(matches(p, g) for g in tier)]
