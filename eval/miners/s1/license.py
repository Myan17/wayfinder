"""ADR-0016 S1-1: the clone's license file as an SPDX id, cross-checked against the GitHub API's.

GitHub's `licenseInfo` comes from its own detector run over the same file, so it is only a
cross-check if this side is independent. A file is an allowed license only if its **whole text**
matches that license's SPDX template (review of #63): a phrase test, or a list of other licenses'
names, cannot rule out a dual-license offer, while a whole-text match leaves nothing outside the
license except a leading block of copyright lines and a plain title. The templates are SPDX's own,
pinned by release and SHA-256 and committed under `spdx/`, and were fixed before any candidate's
file was read.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

from .repo import _git

ALLOWED = ("MIT", "BSD-2-Clause", "BSD-3-Clause", "Apache-2.0", "ISC")
NAME = re.compile(r"(licen[cs]e|copying)(\.[a-z0-9]+)?", re.IGNORECASE)

# github.com/spdx/license-list-data, tag v3.29.0 (2026-09-16), template/<id>.template.txt, byte for byte
# (whitespace included; see spdx/.gitattributes), so each hash is upstream's file's hash.
SPDX_TEMPLATES = Path(__file__).parent / "spdx"
SHA256 = {
    "MIT": "9b91e12dfe57d42e91ea96d2acb7624040bffc54182bd164d39d0fae33e77794",
    "ISC": "a382ee687364e5fa6361f299be089d79ded228a7ccbf1d4352a30fa22bfddb8f",
    "BSD-2-Clause": "922ac644c79e7c2aa31bacac531a5d4d5b9d183853a3dc44a253fd9267c3c890",
    "BSD-3-Clause": "c42368b683ceef1ad41b6f17999adf3b7534e3c47fbdd51449ed6690edb1fc5f",
    "Apache-2.0": "5567209d3a634ebd6ed122a7302563b9668ab141941149a4e30d9c7b887f41b9",
}
_MARK = re.compile(r'<<beginOptional>>|<<endOptional>>|<<var;name="[^"]*";original="(.*?)";match="(.*?)">>')
# The leading block a license file may carry outside its template (review of #63): blank lines,
# copyright lines, and at most one title, which must name the license being tested. A copyright line
# is "copyright" or "(c)" and then at most 120 characters of years and holders; one that makes an
# offer (or, and/or, licen*, dual*, under, terms, alternativ*, spdx) is not a copyright line, stays
# in the text, and fails the template. Apache-2.0's template carries its own title block.
_COPYRIGHT = re.compile(r"(?:copyright\b|\(c\))(?:\s*\(c\))?(?P<rest>.{0,120})|all rights reserved\.?")
_OFFER = re.compile(r"\b(or|licen\w*|dual\w*|under|terms|alternativ\w*|spdx)\b")
_TITLES = {
    "MIT": r"(the )?mit licen[cs]e( \(mit\))?",
    "ISC": r"(the )?isc licen[cs]e( \(iscl?\))?",
    "BSD-2-Clause": r"(the )?(simplified |freebsd )?bsd( 2-clause)? licen[cs]e( \(bsd-2-clause\))?",
    "BSD-3-Clause": r"(the )?(new |modified |revised )?bsd( 3-clause)? licen[cs]e( \(bsd-3-clause\))?",
}
_TITLE = {sid: re.compile(rf"\(?{title}\)?:?") for sid, title in _TITLES.items()}
_QUOTES = str.maketrans(
    {c: '"' for c in "'`\u201c\u201d\u201e\u201f\u2033\u2018\u2019\u201a\u201b"}
    | {c: "-" for c in "\u2010\u2011\u2012\u2013\u2014\u2015"}
)


def _norm(text: str) -> str:
    """Lower case; one form for all quotes and apostrophes, and one for all dashes; (c) for the
    copyright sign; http for https; one space for any whitespace run (SPDX matching guidelines)."""
    text = text.lower().translate(_QUOTES).replace("\u00a9", "(c)").replace("https://", "http://")
    return " ".join(text.split())


def _literal(text: str) -> str:
    return r"\s+".join(re.escape(word) for word in _norm(text).split())


def _var(match: str) -> str:
    """A template variable's pattern. Unbounded wildcards are capped, so none can absorb a second
    license; the leading copyright variable (`.{0,5000}`) matches nothing, because `_lead` strips
    that block line by line under the stricter rule above."""
    if match == ".{0,5000}":
        return ""
    if match == ".{0,20}":  # a list bullet such as "1." or "(a)": no spaces, so a failed match ends fast
        return "([^ ]{0,20})"
    return "(" + match.replace(".+", ".{1,200}?").replace(".*", ".{0,200}?") + ")"


def _compile(template: str) -> re.Pattern:
    parts: list[list[str]] = [[]]
    pos = 0
    for m in _MARK.finditer(template):
        parts[-1].append(_literal(template[pos : m.start()]))
        pos = m.end()
        if m.group(0) == "<<beginOptional>>":
            parts.append([])
        elif m.group(0) == "<<endOptional>>":
            inner = r"\s*".join(filter(None, parts.pop()))
            parts[-1].append(f"(?:{inner})?")
        else:
            parts[-1].append(_var(m.group(2)))
    parts[-1].append(_literal(template[pos:]))
    return re.compile(r"\s*".join(filter(None, parts[0])), re.IGNORECASE | re.DOTALL)


def _load() -> dict[str, re.Pattern]:
    found = {}
    for sid in ALLOWED:
        raw = (SPDX_TEMPLATES / f"{sid}.template.txt").read_bytes()
        if hashlib.sha256(raw).hexdigest() != SHA256[sid]:
            raise RuntimeError(f"SPDX template for {sid} does not match its pinned SHA-256")
        found[sid] = _compile(raw.decode())
    return found


TEMPLATES = _load()


def _copyright(line: str) -> bool:
    m = _COPYRIGHT.fullmatch(line)
    return m is not None and not _OFFER.search(m.group("rest") or "")


def _lead(text: str, sid: str) -> str:
    """The text after its leading blank and copyright lines and at most one title naming `sid`."""
    lines, titled = text.splitlines(), False
    while lines:
        line = _norm(lines[0])
        if not titled and sid in _TITLE and _TITLE[sid].fullmatch(line):
            titled = True
        elif line and not _copyright(line):
            break
        lines.pop(0)
    return "\n".join(lines)


def spdx(text: str) -> str | None:
    """The one allowed license whose SPDX template matches the whole text; else None.

    No variable may hold the word "licen[cs]e", so a template's wildcard cannot carry another one.
    """
    hits = []
    for sid, pattern in TEMPLATES.items():
        m = pattern.fullmatch(_norm(_lead(text, sid)))
        if m and not any(g and "licen" in g for g in m.groups()):
            hits.append(sid)
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
