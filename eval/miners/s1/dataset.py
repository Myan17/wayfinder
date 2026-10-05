"""The four checks the pairs file must pass before it lands (gupta958 on #50, 2026-09-28).

Canonical order by (github_repo_id, pr, issue), every line valid JSON and a valid `$defs/pair`, the
file's SHA-256 equal to the manifest's, and the counts equal to the manifest's. A dataset with any
problem is refused (card: "the manifest's SHA-256 does not match the file").
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

from jsonschema import Draft202012Validator

from .manifest import count_problem

SCHEMA = Path(__file__).parents[2] / "datasets" / "manifest.schema.json"
# Format checks are off unless a FormatChecker is passed; date-time needs rfc3339-validator (#57).
PAIR = Draft202012Validator(
    json.loads(SCHEMA.read_text())["$defs"]["pair"], format_checker=Draft202012Validator.FORMAT_CHECKER
)


def _no_constant(name: str) -> None:
    raise ValueError(f"{name} is not JSON")


def parse(line: bytes) -> object:
    """One JSONL line; NaN, Infinity and -Infinity are refused, not read as floats."""
    return json.loads(line, parse_constant=_no_constant)


def pair_problem(pair: object) -> str | None:
    """None when `pair` is a valid `$defs/pair`, else its first violation, with the field's path."""
    error = next(iter(sorted(PAIR.iter_errors(pair), key=lambda e: list(map(str, e.path)))), None)
    if error is None:
        return None
    where = ".".join(map(str, error.path))
    return f"{where}: {error.message}" if where else error.message


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
            pair = parse(line)
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
