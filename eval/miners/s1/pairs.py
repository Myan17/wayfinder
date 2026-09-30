"""ADR-0013 D-2 (gold files) and D-3 (the weak set)."""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from pathlib import PurePosixPath

from . import universe

SOURCE = (".py", ".pyi", ".go")  # D-2's "source files" (reviewer ruling on #50, 2026-09-28)


@dataclass(frozen=True)
class Changed:
    """One file the pull request touched, as it was at the pair's pre-fix base commit (D-1).

    `previous_path` is the path before a rename. `base_mode` and `base_bytes` are the base path's Git
    mode and content, or None when the path does not exist at the base commit (an added file).
    """

    path: str
    previous_path: str | None
    base_mode: str | None
    base_bytes: bytes | None


def gold_files(changed: list[Changed]) -> list[str]:
    """D-2's gold labels: base-snapshot paths that are source files in ADR-0016's universe, sorted.

    Every label is verified against the base snapshot (review of #50). A file added by the PR does not
    exist there and is not a label; a renamed file is labelled by its base path; the mode and bytes at
    the base decide the symlink, generated and UTF-8 steps. Unread base bytes are never assumed clean.
    """
    gold = set()
    for c in changed:
        base = c.previous_path or c.path
        if c.base_mode is None or c.base_bytes is None or PurePosixPath(base).suffix not in SOURCE:
            continue
        if universe.excluded(base, c.base_mode, c.base_bytes) is None:
            gold.add(base)
    return sorted(gold)


def keep(gold: list[str], max_files: int = 10) -> tuple[bool, str | None]:
    """D-2: drop pairs with 0 or more than max_files source files (10; 15 under R-03 step 2)."""
    if not gold:
        return False, "no source files"
    if len(gold) > max_files:
        return False, f"more than {max_files} source files"
    return True, None


def weak(issue_updated_at: dt.datetime, pr_merged_at: dt.datetime) -> bool:
    """D-3: an issue updated after the merge may name its answer."""
    return issue_updated_at > pr_merged_at
