"""ADR-0013 D-2 (gold files) and D-3 (the weak set)."""

from __future__ import annotations

import datetime as dt
from pathlib import PurePosixPath

from . import universe

SOURCE = (".py", ".pyi", ".go")


def gold_files(changed: dict[str, bytes | None]) -> list[str]:
    """The pull request's modified files that are source in ADR-0016's universe, sorted.

    Tests, docs, changelogs, lockfiles and generated paths fall out through the universe steps;
    Markdown is in the universe but is not source.
    """
    return sorted(path for path, content in changed.items()
                  if PurePosixPath(path).suffix in SOURCE and universe.excluded(path, "100644", content) is None)


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
