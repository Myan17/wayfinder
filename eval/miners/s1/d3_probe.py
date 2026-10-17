"""A bounded, read-only diagnostic of D-3 on S1 run 3 (gupta958's ruling, 2026-10-17). Not an S1 re-run.

Run 3's strong pairs are 613 dev, 64 test, 22 held-out. Hypothesis: the closure the merge triggers
moves `updatedAt` past `mergedAt`, so D-3 calls a merge-closed issue weak. Per repository x split
cell, the 3 weak pairs and 1 strong pair with the lowest SHA-256 of `github_repo_id:issue:pr`; only
PR `mergedAt` and issue `closedAt` and `updatedAt` are read. It changes no rule and no dataset.

usage: WAYFINDER_S1_TOKEN=<classic token with no scopes> python -m s1.d3_probe [pairs.jsonl] [out.json]
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import sys
from collections import defaultdict
from pathlib import Path

from . import github

WEAK_PER_CELL, STRONG_PER_CELL = 3, 1
SPLITS = ("dev", "test", "held_out")
BUCKETS = ("<=5s", "<=60s", "<=1h", ">1h", "not closed")
EVAL = Path(__file__).parents[2]


def key(p: dict) -> str:
    return hashlib.sha256(f"{p['github_repo_id']}:{p['issue']}:{p['pr']}".encode()).hexdigest()


def sample(rows: list[dict]) -> list[dict]:
    """The ruling's sample, in (github_repo_id, split, weak first, key) order."""
    cells = defaultdict(list)
    for p in rows:
        cells[p["github_repo_id"], p["split"], p["strong"]].append(p)
    picked = []
    for repo in sorted({p["github_repo_id"] for p in rows}):
        for split in SPLITS:
            for strong, n in ((False, WEAK_PER_CELL), (True, STRONG_PER_CELL)):
                cell = sorted(cells[repo, split, strong], key=key)
                if len(cell) < n:
                    raise ValueError(
                        f"cell {repo} {split} {'strong' if strong else 'weak'} has {len(cell)} pairs"
                    )
                picked += cell[:n]
    return picked


def query(pairs: list[dict]) -> str:
    """One repository's query. Numbers are ints from the pairs file, so they are safe as literals."""
    fields = []
    for p in pairs:
        issue, pr = int(p["issue"]), int(p["pr"])
        fields.append(f"i{issue}: issue(number: {issue}) {{ closedAt updatedAt }}")
        fields.append(f"p{pr}: pullRequest(number: {pr}) {{ mergedAt }}")
    body = "\n    ".join(dict.fromkeys(fields))  # a PR or issue shared by two sampled pairs is read once
    head = "query($owner: String!, $name: String!) {\n  repository(owner: $owner, name: $name) {"
    return f"{head}\n    {body}\n  }}\n}}"


def _time(s: str | None) -> dt.datetime | None:
    return dt.datetime.fromisoformat(s.replace("Z", "+00:00")) if s else None


def _seconds(later: dt.datetime | None, merged: dt.datetime) -> int | None:
    return None if later is None else int((later - merged).total_seconds())


def bucket(seconds: int | None) -> str:
    """Disjoint buckets; a negative delta (closed or updated before the merge) falls in <=5s."""
    if seconds is None:
        return "not closed"
    if seconds <= 5:
        return "<=5s"
    if seconds <= 60:
        return "<=60s"
    return "<=1h" if seconds <= 3600 else ">1h"


def measure(pair: dict, repository: dict) -> dict:
    """One sampled pair's times and deltas from its repository's query result."""
    issue, pr = repository[f"i{pair['issue']}"], repository[f"p{pair['pr']}"]
    if issue is None or pr is None or pr["mergedAt"] is None:
        raise RuntimeError(f"{pair['github_repo_id']}: issue {pair['issue']} or PR {pair['pr']} not readable")
    merged = _time(pr["mergedAt"])
    closed, updated = _time(issue["closedAt"]), _time(issue["updatedAt"])
    return {
        "github_repo_id": pair["github_repo_id"],
        "split": pair["split"],
        "strong_in_run_3": pair["strong"],
        "issue": pair["issue"],
        "pr": pair["pr"],
        "merged_at": pr["mergedAt"],
        "closed_at": issue["closedAt"],
        "updated_at": issue["updatedAt"],
        "closed_minus_merged_s": _seconds(closed, merged),
        "updated_minus_merged_s": _seconds(updated, merged),
        "weak_now": updated > merged,  # D-3 as written, on today's updatedAt
    }


def summary(measured: list[dict]) -> dict:
    """Bucket counts for both deltas, overall and by repository, split and run 3's class."""
    groups = {
        "all": lambda m: "all",
        "by_repository": lambda m: str(m["github_repo_id"]),
        "by_split": lambda m: m["split"],
        "by_run_3_class": lambda m: "strong" if m["strong_in_run_3"] else "weak",
    }
    out = {}
    for delta in ("closed_minus_merged_s", "updated_minus_merged_s"):
        out[delta] = {}
        for name, of in groups.items():
            counts = defaultdict(lambda: dict.fromkeys(BUCKETS, 0))
            for m in measured:
                counts[of(m)][bucket(m[delta])] += 1
            out[delta][name] = dict(sorted(counts.items())) if name != "all" else counts["all"]
        out[delta]["negative"] = sum(1 for m in measured if (m[delta] or 0) < 0)
    controls = [m for m in measured if m["strong_in_run_3"]]
    out["strong_controls"] = len(controls)
    out["strong_controls_now_weak"] = [
        [m["github_repo_id"], m["issue"], m["pr"]] for m in controls if m["weak_now"]
    ]
    return out


def encoded(value, indent: int = 0) -> str:
    """JSON with sorted keys, one line per row and per bucket count, so the file stays reviewable.

    A dict holding a dict or list, or a list holding a dict, is spread over lines; anything flatter
    (a row, a bucket count, an id list) stays on one line.
    """
    pad, inner = " " * indent, " " * (indent + 2)
    if isinstance(value, dict) and any(isinstance(v, (dict, list)) for v in value.values()):
        items = [f"{inner}{json.dumps(k)}: {encoded(v, indent + 2)}" for k, v in sorted(value.items())]
        return "{\n" + ",\n".join(items) + f"\n{pad}}}"
    if isinstance(value, list) and any(isinstance(v, dict) for v in value):
        return "[\n" + ",\n".join(f"{inner}{encoded(v, indent + 2)}" for v in value) + f"\n{pad}]"
    return json.dumps(value, sort_keys=True)


def main(argv: list[str]) -> int:
    pairs_path = Path(argv[0]) if argv else EVAL / "datasets" / "s1" / "pairs.jsonl"
    out = Path(argv[1]) if len(argv) > 1 else EVAL / "datasets" / "s1-d3-probe.json"
    token = os.environ.get("WAYFINDER_S1_TOKEN")
    if not token:
        print(
            "WAYFINDER_S1_TOKEN is not set (a classic token with no scopes, ADR-0016 S1-5)", file=sys.stderr
        )
        return 2
    data = pairs_path.read_bytes()
    manifest = json.loads((pairs_path.parent / "manifest.json").read_text())
    slugs = {c["github_repo_id"]: c["repo"] for c in manifest["candidates"]}
    picked = sample([json.loads(line) for line in data.splitlines()])
    client = github.Client(github.urllib_transport(token))
    started = dt.datetime.now(dt.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    measured = []
    for repo in sorted({p["github_repo_id"] for p in picked}):
        mine = [p for p in picked if p["github_repo_id"] == repo]
        owner, name = slugs[repo].split("/")
        repository = client.query(query(mine), owner=owner, name=name)["repository"]
        measured += [measure(p, repository) for p in mine]
    result = {
        "ruling": "gupta958, 2026-10-17: bounded read-only D-3 diagnostic, not an S1 re-run",
        "pairs_sha256": hashlib.sha256(data).hexdigest(),
        "queried_at": started,
        "api_calls": client.calls,
        "sample": {
            "weak_per_cell": WEAK_PER_CELL,
            "strong_per_cell": STRONG_PER_CELL,
            "key": "sha256(id:issue:pr)",
        },
        "rows": measured,
        "summary": summary(measured),
    }
    out.write_text(encoded(result) + "\n")
    print(f"wrote {out}: {len(measured)} pairs, calls {client.calls}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
