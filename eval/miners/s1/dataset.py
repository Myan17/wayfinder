"""The four checks the pairs file must pass before it lands (gupta958 on #50, 2026-09-28).

Canonical order by (github_repo_id, pr, issue), every line valid JSON and a valid `$defs/pair`, the
file's SHA-256 equal to the manifest's, and the counts equal to the manifest's. A dataset with any
problem is refused (card: "the manifest's SHA-256 does not match the file").
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import re
import sys
from pathlib import Path

from .manifest import count_problem

# `$defs/pair` of eval/datasets/manifest.schema.json; a test keeps the two in step.
INT, STR, BOOL = "integer", "string", "boolean"
PAIR = {
    "github_repo_id": INT,
    "issue": INT,
    "pr": INT,
    "base_commit": STR,
    "gold": "array",
    "strong": BOOL,
    "group_id": STR,
    "t_g": STR,
    "split": STR,
}
SPLITS = ("dev", "test", "held_out")
SHA1 = re.compile(r"[0-9a-f]{40}")


def _is(value: object, kind: str) -> bool:
    if kind == INT:
        return isinstance(value, int) and not isinstance(value, bool)
    return isinstance(value, {STR: str, BOOL: bool, "array": list}[kind])


def _date_time(value: str) -> bool:
    try:
        return dt.datetime.fromisoformat(value).tzinfo is not None
    except ValueError:
        return False


def pair_problem(pair: object) -> str | None:
    """None when `pair` is a valid `$defs/pair`, else the first violation."""
    if not isinstance(pair, dict):
        return "not an object"
    for key, kind in PAIR.items():
        if key not in pair:
            return f"{key} missing"
        if not _is(pair[key], kind):
            return f"{key} is not of type {kind}"
    if not SHA1.fullmatch(pair["base_commit"]):
        return "base_commit is not 40 lowercase hex characters"
    if not pair["gold"] or not all(isinstance(g, str) for g in pair["gold"]):
        return "gold is not a non-empty list of strings"
    if not _date_time(pair["t_g"]):
        return "t_g is not a date-time with an offset"
    if pair["split"] not in SPLITS:
        return f"split {pair['split']!r} is not one of {', '.join(SPLITS)}"
    return None


def problems(data: bytes, manifest: dict) -> list[str]:
    """Every failure of the four checks; an empty list means the file may land."""
    found = []
    pairs_file = manifest.get("pairs_file", {})
    if (bad := count_problem(pairs_file)) is not None:
        found.append(f"manifest: {bad}")
    if hashlib.sha256(data).hexdigest() != pairs_file.get("sha256"):
        found.append("sha256 does not match the manifest")
    if data and not data.endswith(b"\n"):
        found.append("the file does not end with a newline")
    strong = weak = 0
    previous = None
    for n, line in enumerate(data.splitlines(), start=1):
        try:
            pair = json.loads(line)
        except ValueError:
            found.append(f"line {n}: not JSON")
            continue
        if (bad := pair_problem(pair)) is not None:
            found.append(f"line {n}: {bad}")
            continue
        key = (pair["github_repo_id"], pair["pr"], pair["issue"])
        if previous is not None and key <= previous:
            found.append(f"line {n}: {key} is not after {previous} (github_repo_id, pr, issue)")
        previous = key
        strong, weak = strong + pair["strong"], weak + (not pair["strong"])
    for name, got in (("total_count", strong + weak), ("strong_count", strong), ("weak_count", weak)):
        if got != pairs_file.get(name):
            found.append(f"{name}: file has {got}, manifest says {pairs_file.get(name)}")
    return found


def main(argv: list[str]) -> int:
    """usage: dataset.py <pairs.jsonl> <manifest.json>; exits 1 and lists the problems if any."""
    pairs_path, manifest_path = map(Path, argv)
    found = problems(pairs_path.read_bytes(), json.loads(manifest_path.read_text()))
    for p in found:
        print(f"{pairs_path}: {p}", file=sys.stderr)
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
