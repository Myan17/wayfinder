"""S1 acquisition, git side: everything ADR-0016 reads from a read-only clone (S1-5).

A mirror clone carries `refs/pull/*/head`, so fork PRs' commits resolve (S1-3). Every function reads
the clone and writes nothing to it. The GitHub API side (pairs, licenses, the call tally) is separate.
"""

from __future__ import annotations

import datetime as dt
import subprocess
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from . import universe
from .pairs import Changed


def _git(git_dir: Path, *args: str, ok: tuple[int, ...] = (0,), input_: bytes | None = None):
    out = subprocess.run(["git", "--git-dir", str(git_dir), *args], capture_output=True, input=input_)
    if out.returncode not in ok:
        raise RuntimeError(f"git {args[0]} failed: {out.stderr.decode(errors='replace').strip()}")
    return out


def mirror(url: str, dest: Path) -> Path:
    """A bare mirror clone, which fetches every ref GitHub serves, `refs/pull/*/head` included."""
    subprocess.run(["git", "clone", "--quiet", "--mirror", url, str(dest)], check=True, capture_output=True)
    return dest


def as_of_commit(git_dir: Path, branch: str, as_of: dt.datetime) -> str | None:
    """The default branch's last first-parent commit committed before `as_of`, or None."""
    out = _git(git_dir, "rev-list", "-1", "--first-parent", f"--before={as_of.isoformat()}", branch)
    return out.stdout.decode().strip() or None


def _exists(git_dir: Path, rev: str) -> bool:
    return _git(git_dir, "cat-file", "-e", f"{rev}^{{commit}}", ok=(0, 1, 128)).returncode == 0


def base_commit(git_dir: Path, first_commit: str) -> tuple[str | None, str | None]:
    """ADR-0013 D-1: the parent of the PR's first commit, or None and the reason it did not resolve."""
    if not _exists(git_dir, first_commit):
        return None, "first commit not in the clone"
    parent = _git(git_dir, "rev-parse", "--verify", "--quiet", f"{first_commit}^", ok=(0, 1)).stdout
    if not parent.strip():
        return None, "first commit has no parent"
    return parent.decode().strip(), None


def has_merges(git_dir: Path, base: str, head: str) -> bool:
    """Whether the PR's range contains a merge commit, so base..head may hold others' changes."""
    return bool(_git(git_dir, "rev-list", "--merges", "-1", f"{base}..{head}").stdout.strip())


MERGE_IN_HISTORY = "merge_commit_in_pr_history"  # ADR-0016 Amendment 1


def resolve(git_dir: Path, first_commit: str, head: str) -> tuple[str | None, str | None]:
    """D-1, then ADR-0016 Amendment 1: (base, None) for a usable pair, else (base or None, reason).

    An unresolved base keeps its S1-3 reason. A resolved base whose PR history (base..head) holds any
    multi-parent commit is excluded as merge_commit_in_pr_history; the pair still counts for S1-2
    and S1-3, but never reaches gold, the split or the strong and weak counts.
    """
    base, reason = base_commit(git_dir, first_commit)
    if base is None:
        return None, reason
    if has_merges(git_dir, base, head):
        return base, MERGE_IN_HISTORY
    return base, None


def _tree(git_dir: Path, commit: str, paths: list[str] | None = None) -> dict[str, tuple[str, str]]:
    """path -> (mode, object id) for the regular, symlink and submodule entries at `commit`."""
    args = ["ls-tree", "-r", "-z", commit] + (["--", *paths] if paths else [])
    entries = {}
    for rec in _git(git_dir, *args).stdout.split(b"\0"):
        if rec:
            meta, path = rec.split(b"\t", 1)
            mode, _, oid = meta.decode().split(" ")
            entries[path.decode()] = (mode, oid)
    return entries


def _blobs(git_dir: Path, oids: list[str]) -> dict[str, bytes]:
    """The contents of many blobs in one `git cat-file --batch` process."""
    if not oids:
        return {}
    out = _git(git_dir, "cat-file", "--batch", input_=("\n".join(oids) + "\n").encode()).stdout
    blobs, i = {}, 0
    for oid in oids:
        header_end = out.index(b"\n", i)
        size = int(out[i:header_end].split(b" ")[2])
        blobs[oid] = out[header_end + 1 : header_end + 1 + size]
        i = header_end + 1 + size + 1
    return blobs


@dataclass(frozen=True)
class Measure:
    """The universe at one commit: ADR-0016's chunk estimate and S1-4's Markdown counts."""

    file_count: int
    chunk_estimate: int
    md_files: int
    md_words: int


def measure(git_dir: Path, commit: str) -> Measure:
    """ADR-0016's seven-step universe at `commit`, its chunk estimate, and S1-4's inputs."""
    tree = _tree(git_dir, commit)
    wanted = {p: oid for p, (mode, oid) in tree.items() if universe.excluded(p, mode, None) is None}
    blobs = _blobs(git_dir, sorted(set(wanted.values())))
    files = chunks = md_files = md_words = 0
    for path, oid in wanted.items():
        content = blobs[oid]
        if universe.excluded(path, tree[path][0], content) is not None:
            continue
        files, chunks = files + 1, chunks + universe.chunks(content)
        if PurePosixPath(path).suffix == ".md":
            md_files, md_words = md_files + 1, md_words + len(content.decode("utf-8").split())
    return Measure(files, chunks, md_files, md_words)


def changed(git_dir: Path, base: str, head: str) -> list[Changed]:
    """The files `base..head` touched, each with its base path's mode and bytes (None if absent).

    Renames are detected (`-M`), so a renamed file carries its base path as `previous_path`.
    """
    out = _git(git_dir, "diff", "--name-status", "-M", "-z", base, head).stdout.decode().split("\0")
    rows, i = [], 0
    while i < len(out) - 1:
        status = out[i]
        if status.startswith(("R", "C")):
            rows.append((out[i + 2], out[i + 1] if status[0] == "R" else None))
            i += 3
        else:
            rows.append((out[i + 1], None))
            i += 2
    base_paths = sorted({prev or path for path, prev in rows})
    tree = _tree(git_dir, base, base_paths)
    blobs = _blobs(git_dir, sorted({oid for mode, oid in tree.values() if mode != "160000"}))
    result = []
    for path, prev in rows:
        mode, oid = tree.get(prev or path, (None, None))
        result.append(Changed(path, prev, mode, blobs.get(oid) if oid else None))
    return result
