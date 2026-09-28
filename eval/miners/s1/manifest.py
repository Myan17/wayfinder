"""Checks on the dataset manifest that JSON Schema cannot express."""

from __future__ import annotations

COUNTS = ("strong_count", "weak_count", "total_count")


def count_problem(pairs_file: dict) -> str | None:
    """None when the explicit counts are present, non-negative and total = strong + weak."""
    for key in COUNTS:
        if key not in pairs_file:
            return f"{key} missing"
        value = pairs_file[key]
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            return f"{key} is not a non-negative integer"
    total, strong, weak = (pairs_file[k] for k in ("total_count", "strong_count", "weak_count"))
    if total != strong + weak:
        return f"total_count {total} != strong_count {strong} + weak_count {weak}"
    return None
