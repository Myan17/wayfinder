"""The manifest's mechanical checks before it lands (gupta958, 2026-10-17, AGENTS.md §2.2).

The manifest is exempt from the line limit because these checks review it instead of a reader:

- it is valid against the committed schema, and its bytes are the miner's canonical encoding;
- each selection round's candidate set and feasible subsets are rebuilt from the candidates' recorded
  qualification, language and chunk estimate, independently of `s1.select`, and must equal the
  recorded ones (or the recorded `no_feasible_reason` must be the constraint that fails);
- the selected corpus equals the final round's winner, and the winner is feasible;
- the pairs file passes `s1.dataset`'s four checks (SHA-256 and counts included), holds only selected
  repositories, and its per-repository split counts equal the manifest's `splits`.

The winner itself is not recomputed: the total order's first key, surviving strong pairs, is not in
the manifest for candidates that were not selected. The reviewer reads `s1.select` at the pinned
`miner_commit` for that.
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from itertools import combinations
from pathlib import Path

from . import corpus, dataset, select


def encoded(manifest: object) -> str:
    """The miner's canonical encoding of a manifest (`s1.run.main`)."""
    return json.dumps(manifest, indent=2, sort_keys=True) + "\n"


def _feasible(candidates: list[dict]) -> tuple[list[list[int]], str | None]:
    """ADR-0016's feasible subsets as sorted id lists, sorted; or ([], the constraint that fails)."""
    ok = [c for c in candidates if all(r["pass"] for r in c["rules"].values())]
    if len(ok) < 3:
        return [], "qualification count"
    subsets = [s for k in (3, 4) for s in combinations(ok, k)]
    mixed = [s for s in subsets if {c["lang"] for c in s} >= {"py", "go"}]
    if not mixed:
        return [], "language mix"
    fit = [s for s in mixed if sum(c["chunk_estimate"] for c in s) <= select.MAX_CHUNKS]
    if not fit:
        return [], "chunk bound"
    return sorted(sorted(c["github_repo_id"] for c in s) for s in fit), None


def round_problems(manifest: dict) -> list[str]:
    """Every selection round against the candidates, and `selected` against the final round."""
    found = []
    candidates = manifest["candidates"]
    ids = [c["github_repo_id"] for c in candidates]
    if len(set(ids)) != len(ids):
        found.append("candidates: a github_repo_id appears twice")
    rounds = manifest["selection_rounds"]
    steps = [r["max_files"] for r in rounds]
    if steps not in ([10], [10, 15]):
        found.append(f"selection_rounds: max_files {steps}, expected [10] or [10, 15] (R-03)")
    elif manifest["rules"]["max_files"] != steps[-1]:
        found.append(f"rules.max_files {manifest['rules']['max_files']} is not the final round's {steps[-1]}")
    feasible, reason = _feasible(candidates)
    for n, r in enumerate(rounds, start=1):
        if r["candidates"] != sorted(ids):
            found.append(f"round {n}: candidates are not the measured candidates' ids, sorted")
        if r.get("feasible") != feasible:
            found.append(
                f"round {n}: feasible subsets differ from the {len(feasible)} rebuilt from the candidates"
            )
        if r.get("no_feasible_reason") != reason:
            found.append(f"round {n}: no_feasible_reason {r.get('no_feasible_reason')!r}, rebuilt {reason!r}")
        winner = r["winner"]
        if reason is None and (winner is None or winner not in feasible):
            found.append(f"round {n}: winner {winner} is not a feasible subset")
        if reason is not None and winner is not None:
            found.append(f"round {n}: a winner is recorded but no subset is feasible ({reason})")
    if rounds and manifest["selected"] != (rounds[-1]["winner"] or []):
        found.append(
            f"selected {manifest['selected']} is not the final round's winner {rounds[-1]['winner']}"
        )
    return found


def pairs_problems(rows: list[dict], manifest: dict) -> list[str]:
    """The pairs file against `selected` and `splits`."""
    found = []
    selected = set(manifest["selected"])
    if stray := sorted({p["github_repo_id"] for p in rows} - selected):
        found.append(f"pairs from repositories that were not selected: {stray}")
    if sorted(manifest["splits"]) != sorted(str(r) for r in selected):
        found.append(f"splits are keyed by {sorted(manifest['splits'])}, not the selected ids")
    got = Counter((str(p["github_repo_id"]), p["split"]) for p in rows)
    for repo, s in sorted(manifest["splits"].items()):
        for name in ("dev", "test", "held_out"):
            if s[name] != got[repo, name]:
                found.append(f"splits.{repo}.{name}: manifest says {s[name]}, file has {got[repo, name]}")
    return found


def problems(data: bytes, text: str) -> list[str]:
    """Every failure; an empty list means the pairs file and manifest may land together."""
    try:
        manifest = json.loads(text, parse_constant=dataset._no_constant)
    except ValueError:
        return ["manifest: not JSON"]
    if schema := [f"manifest: {e.message}" for e in corpus.MANIFEST.iter_errors(manifest)]:
        return schema  # the checks below index fields the schema requires
    found = []
    if text != encoded(manifest):
        found.append("manifest: not the miner's canonical encoding (indent 2, sorted keys, final newline)")
    found += round_problems(manifest)
    if pairs := dataset.problems(data, manifest):
        return found + pairs
    rows = [json.loads(line) for line in data.splitlines()]
    return found + pairs_problems(rows, manifest)


def main(argv: list[str]) -> int:
    """usage: landing.py <pairs.jsonl> <manifest.json>; exits 1 and lists the problems if any."""
    pairs_path, manifest_path = map(Path, argv)
    found = problems(pairs_path.read_bytes(), manifest_path.read_text())
    for p in found:
        print(f"{manifest_path}: {p}", file=sys.stderr)
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
