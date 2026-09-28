"""ADR-0016's corpus selection: feasible 3- and 4-subsets under a total order."""

from __future__ import annotations

from itertools import combinations

MAX_CHUNKS = 60_000


def _key(subset: tuple[dict, ...]):
    # More surviving strong pairs, more repositories, fewer chunks, then the sorted id tuple.
    return (
        -sum(c["pairs"] for c in subset),
        -len(subset),
        sum(c["chunks"] for c in subset),
        tuple(sorted(c["repo_id"] for c in subset)),
    )


def best(cands: list[dict], max_chunks: int = MAX_CHUNKS):
    """(winner id tuple, all feasible id tuples), or (None, the constraint that failed)."""
    ok = [c for c in cands if c["qualified"]]
    if len(ok) < 3:
        return None, "qualification count"
    subsets = [s for k in (3, 4) for s in combinations(ok, k)]
    mixed = [s for s in subsets if {"py", "go"} <= {c["lang"] for c in s}]
    if not mixed:
        return None, "language mix"
    feasible = [s for s in mixed if sum(c["chunks"] for c in s) <= max_chunks]
    if not feasible:
        return None, "chunk bound"
    win = min(feasible, key=_key)
    # Sorted, so neither the winner nor the feasible list depends on candidate input order (review of #51).
    ids = sorted(tuple(sorted(c["repo_id"] for c in s)) for s in feasible)
    return tuple(sorted(c["repo_id"] for c in win)), ids
