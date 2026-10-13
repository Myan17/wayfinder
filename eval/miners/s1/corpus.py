"""S1's corpus from measured candidates: D-6 survivors, ADR-0016's selection rounds, and the dataset.

Pure: the input is what `s1.run.measure` returns per candidate (its manifest entry and its linked
pairs with base, exclusion reason, gold and strength), so selection and the file format are tested
without a live run. `build` refuses to return a dataset that fails its landing checks.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
from collections import Counter

from jsonschema import Draft202012Validator

from . import dataset, pairs, repo, select, split, universe

AS_OF = dt.datetime(2026, 9, 28, tzinfo=dt.UTC)
A3_BAR = 300
PAIRS_PATH = "eval/datasets/s1/pairs.jsonl"
MANIFEST = Draft202012Validator(
    json.loads(dataset.SCHEMA.read_text()), format_checker=Draft202012Validator.FORMAT_CHECKER
)


def survivors(cand: dict, max_files: int) -> tuple[list[dict], Counter]:
    """The candidate's pairs that pass D-1, Amendment 1 and D-2, and the D-6 count of the rest."""
    kept, excluded = [], Counter()
    for p in cand["pairs"]:
        if p["reason"] is not None:
            excluded[p["reason"] if p["reason"] == repo.MERGE_IN_HISTORY else f"D-1: {p['reason']}"] += 1
            continue
        ok, why = pairs.keep(p["gold"], max_files)
        if ok:
            kept.append(p)
        else:
            excluded[f"D-2: {why}"] += 1
    return kept, excluded


def _qualified(cand: dict) -> bool:
    return all(r["pass"] for r in cand["entry"]["rules"].values())


def _round(measured: list[dict], max_files: int) -> dict:
    cands = [
        {
            "repo_id": m["entry"]["github_repo_id"],
            "lang": m["entry"]["lang"],
            "chunks": m["entry"]["chunk_estimate"],
            "qualified": _qualified(m),
            "pairs": sum(p["strong"] for p in survivors(m, max_files)[0]),
        }
        for m in measured
    ]
    winner, rest = select.best(cands)
    strong = sum(c["pairs"] for c in cands if winner and c["repo_id"] in winner)
    return {
        "candidates": sorted(c["repo_id"] for c in cands),
        "max_files": max_files,
        "feasible": [list(s) for s in rest] if winner else [],
        "winner": list(winner) if winner else None,
        "no_feasible_reason": None if winner else rest,
        "strong": strong,
    }


def rounds(measured: list[dict], widened: bool = False) -> list[dict]:
    """ADR-0016's selection at D-2's 10 files, then R-03 step 2 (15 files) only after step 1.

    R-03 runs in DESIGN's order (review of #65). A short winner on the original candidates stops
    here, because step 1 comes first: a pull request names new candidates before they are measured.
    Only a run over that widened list (`widened`) that is still short relaxes D-2. Relaxing cannot
    help when no subset is feasible, since it changes neither qualification nor size.
    """
    first = _round(measured, 10)
    if not widened or first["winner"] is None or first["strong"] >= A3_BAR:
        return [first]
    return [first, _round(measured, 15)]


def _utc(t: dt.datetime) -> str:
    return t.astimezone(dt.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def build(
    measured: list[dict], miner_commit: str, calls: dict, widened: bool = False, as_of: dt.datetime = AS_OF
) -> tuple[bytes, dict]:
    """The pairs file and manifest; raises if either fails its landing checks."""
    done = rounds(measured, widened)
    final = done[-1]
    winner = set(final["winner"] or [])
    kept, excluded = [], Counter()
    for m in measured:  # D-6 counts every measured candidate's exclusions (review of #65)
        k, e = survivors(m, final["max_files"])
        excluded += e
        if m["entry"]["github_repo_id"] in winner:
            kept += k
    assigned = split.assign(kept)
    rows = sorted(assigned["pairs"], key=lambda p: (p["repo_id"], p["pr"], p["issue"]))
    lines = [
        {
            "github_repo_id": p["repo_id"],
            "issue": p["issue"],
            "pr": p["pr"],
            "base_commit": p["base"],
            "gold": p["gold"],
            "strong": p["strong"],
            "group_id": p["group_id"],
            "t_g": _utc(p["t_g"]),
            "split": p["split"],
        }
        for p in rows
    ]
    data = b"".join(json.dumps(row, sort_keys=True).encode() + b"\n" for row in lines)
    strong = sum(row["strong"] for row in lines)
    splits = {
        str(r): {
            **assigned["achieved"][r],
            **{k: _utc(v) if v else None for k, v in assigned["boundaries"][r].items()},
        }
        for r in assigned["achieved"]
    }
    manifest = {
        "schema_version": 1,
        "as_of": _utc(as_of),
        "miner_commit": miner_commit,
        "rules": {
            "adrs": ["ADR-0013", "ADR-0016"],
            "max_files": final["max_files"],
            "gold_extensions": list(pairs.SOURCE),
            "chunk_lines": universe.CHUNK_LINES,
        },
        "candidates": [m["entry"] for m in measured],
        "selection_rounds": [{k: v for k, v in r.items() if k != "strong"} for r in done],
        "selected": final["winner"] or [],
        "pairs_file": {
            "path": PAIRS_PATH,
            "sha256": hashlib.sha256(data).hexdigest(),
            "total_count": len(lines),
            "strong_count": strong,
            "weak_count": len(lines) - strong,
        },
        "exclusions": dict(sorted(excluded.items())),
        "splits": splits,
        "api_calls": dict(calls),
    }
    found = [f"manifest: {e.message}" for e in MANIFEST.iter_errors(manifest)] + dataset.problems(
        data, manifest
    )
    if found:
        raise ValueError("refusing to write the dataset: " + "; ".join(found))
    return data, manifest
