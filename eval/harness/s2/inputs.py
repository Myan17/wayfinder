"""Spike S2's inputs, exactly as ADR-0019 Amendment 1 pins them.

- Section 1: the corpus is 60-line windows over ADR-0016's file universe at each repository's
  as-of commit. The universe comes from `s1.universe`, imported and not rewritten, and each
  repository's window count must equal its `chunk_estimate` in the S1 manifest.
- Section 3: every file belongs to one of 100 pseudo-repositories, and S2-4's three levels grant
  0, 0-9 and 0-99.
- Section 4, the query set, lands in the next part of the harness.

Everything here is a pure function except `snapshot`, which reads a local git directory. Nothing
here touches the network.
"""

from __future__ import annotations

import hashlib
import subprocess
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path

from s1 import universe

PSEUDO_REPOS = 100
GRANTS: dict[int, range] = {1: range(1), 10: range(10), 100: range(100)}  # percent -> granted ids


@dataclass(frozen=True)
class Window:
    github_repo_id: int
    path: str
    index: int  # 0-based window number within the file
    first_line: int  # 1-based line number of the window's first line
    text: str
    pseudo_repo: int


def split_lines(content: bytes) -> list[bytes]:
    """The file's lines with their newlines, counted exactly as `universe.lines` counts them."""
    parts = content.split(b"\n")
    out = [p + b"\n" for p in parts[:-1]]
    if parts[-1]:
        out.append(parts[-1])
    if len(out) != universe.lines(content):
        raise AssertionError("line split disagrees with universe.lines")
    return out


def pseudo_repo(github_repo_id: int, path: str) -> int:
    """Amendment 1 section 3: decimal id, a slash and the git path, UTF-8, SHA-256 mod 100."""
    digest = hashlib.sha256(f"{github_repo_id}/{path}".encode()).hexdigest()
    return int(digest, 16) % PSEUDO_REPOS


def windows(github_repo_id: int, path: str, content: bytes) -> list[Window]:
    """Consecutive `universe.CHUNK_LINES`-line windows; the last one may be shorter."""
    lines, n, pr = split_lines(content), universe.CHUNK_LINES, pseudo_repo(github_repo_id, path)
    out = [
        Window(github_repo_id, path, i, start + 1, b"".join(lines[start : start + n]).decode("utf-8"), pr)
        for i, start in enumerate(range(0, len(lines), n))
    ]
    if len(out) != universe.chunks(content):
        raise AssertionError("window count disagrees with universe.chunks")
    return out


def _git(git_dir: Path, *args: str, input_: bytes | None = None) -> bytes:
    return subprocess.run(
        ["git", f"--git-dir={git_dir}", *args], input=input_, check=True, capture_output=True
    ).stdout


def snapshot(git_dir: Path, commit: str, github_repo_id: int) -> list[Window]:
    """Every universe file at `commit`, cut into windows, in path order.

    The universe test runs twice, as `s1.repo.measure` runs it: on the path and mode first, then
    with the bytes, for the two content steps (Go's generated header and UTF-8).
    """
    entries = []
    for row in _git(git_dir, "ls-tree", "-r", "-z", "--full-tree", commit).split(b"\0"):
        if not row:
            continue
        meta, path = row.split(b"\t", 1)
        mode, _type, oid = meta.decode().split(" ")
        entries.append((path.decode("utf-8"), mode, oid))
    wanted = sorted((p, m, o) for p, m, o in entries if universe.excluded(p, m, None) is None)
    blobs = _blobs(git_dir, sorted({o for _, _, o in wanted}))
    out: list[Window] = []
    for path, mode, oid in wanted:
        if universe.excluded(path, mode, blobs[oid]) is None:
            out.extend(windows(github_repo_id, path, blobs[oid]))
    return out


def _blobs(git_dir: Path, oids: list[str]) -> dict[str, bytes]:
    raw = _git(git_dir, "cat-file", "--batch", input_="".join(f"{o}\n" for o in oids).encode())
    out, pos = {}, 0
    for oid in oids:
        header_end = raw.index(b"\n", pos)
        got, _type, size = raw[pos:header_end].decode().split(" ")
        if got != oid:
            raise AssertionError(f"cat-file returned {got} for {oid}")
        start = header_end + 1
        out[oid] = raw[start : start + int(size)]
        pos = start + int(size) + 1
    return out


def count_problems(counts: Mapping[int, int], manifest: Mapping) -> list[str]:
    """Section 1's refusal: each selected repository's window count must equal its estimate."""
    estimates = {c["github_repo_id"]: c["chunk_estimate"] for c in manifest["candidates"]}
    selected = set(manifest["selected"])
    problems = [f"{r}: not a selected repository" for r in sorted(set(counts) - selected)]
    for r in sorted(selected):
        if counts.get(r) != estimates[r]:
            problems.append(f"{r}: {counts.get(r)} windows, manifest chunk_estimate {estimates[r]}")
    return problems


def admitted_fraction(ws: Iterable[Window], percent: int) -> float:
    """The fraction of representations a grant level actually admits (files differ in size)."""
    ws = list(ws)
    granted = GRANTS[percent]
    return sum(w.pseudo_repo in granted for w in ws) / len(ws)
