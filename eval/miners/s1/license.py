"""ADR-0016 S1-1: the clone's license file as an SPDX id, cross-checked against the GitHub API's.

GitHub's `licenseInfo` comes from its own detector run over the same file, so it is only a
cross-check if this side is independent. Each license is recognised by phrases from its SPDX
standard text, written before any candidate's file was read, so the rule cannot be tuned to them.
"""

from __future__ import annotations

import re
from pathlib import Path

from .repo import _git

ALLOWED = ("MIT", "BSD-2-Clause", "BSD-3-Clause", "Apache-2.0", "ISC")
NAME = re.compile(r"(licen[cs]e|copying)(\.[a-z0-9]+)?", re.IGNORECASE)

_BSD = "redistribution and use in source and binary forms, with or without modification, are permitted"
_ENDORSE = "to endorse or promote products derived from this software"
_ADVERTISING = "all advertising materials mentioning features or use of this software"
# Each id: phrases that must all appear, and phrases that must not.
RULES: dict[str, tuple[tuple[str, ...], tuple[str, ...]]] = {
    "MIT": (
        (
            "permission is hereby granted, free of charge, to any person obtaining a copy",
            "the above copyright notice and this permission notice shall be included",
        ),
        (),
    ),
    "ISC": (("distribute this software for any purpose with or without fee is hereby granted",), ()),
    "Apache-2.0": (("apache license", "version 2.0"), ()),
    "BSD-3-Clause": ((_BSD, _ENDORSE), (_ADVERTISING,)),
    "BSD-2-Clause": ((_BSD,), (_ENDORSE, _ADVERTISING)),
}


def spdx(text: str) -> str | None:
    """The one allowed license whose phrases match `text`; None if none or several match."""
    norm = " ".join(text.lower().split())
    hits = [
        sid
        for sid, (need, forbid) in RULES.items()
        if all(p in norm for p in need) and not any(p in norm for p in forbid)
    ]
    return hits[0] if len(hits) == 1 else None


def file_spdx(git_dir: Path, commit: str) -> tuple[str | None, str | None]:
    """(SPDX id, None), or (None, reason): the root-level LICENSE, LICENCE or COPYING file at `commit`."""
    out = _git(git_dir, "ls-tree", "-z", commit).stdout.split(b"\0")
    files = []
    for rec in filter(None, out):
        meta, name = rec.split(b"\t", 1)
        mode, _, oid = meta.decode().split(" ")
        if mode in ("100644", "100755") and NAME.fullmatch(name.decode(errors="replace")):
            files.append((name.decode(), oid))
    if len(files) != 1:
        return None, f"{len(files)} license files at the root"
    blob = _git(git_dir, "cat-file", "blob", files[0][1]).stdout
    try:
        sid = spdx(blob.decode("utf-8"))
    except UnicodeDecodeError:
        return None, f"{files[0][0]} is not UTF-8"
    return (sid, None) if sid else (None, f"{files[0][0]} matches no single allowed license")


def s1_1(file_id: str | None, api_id: str | None) -> dict:
    """S1-1's manifest entry: both sources agree on one allowed id, else it fails."""
    ok = file_id is not None and file_id == api_id and file_id in ALLOWED
    return {"value": {"file": file_id, "api": api_id}, "pass": ok}
