"""Fetch the S2 query set's issue text once, into a local file outside git (ADR-0019 Amendment 1 §4).

    PYTHONPATH=eval/harness:eval/miners uv run python -m s2.fetch_issues --out ~/wayfinder-s2/issues.jsonl

Issue text is not ours to redistribute, and it can be edited later, so it is never committed. The dev
run and the A1 run read the same file. Each line holds `github_repo_id`, `issue`, `title` and `body`
exactly as GitHub's REST API returned them; joining and normalization happen in `s2.inputs.query`.
A meta file beside it records the fetch time, the count and the file's SHA-256 for the report.

`GITHUB_TOKEN` is read from the environment and is never written anywhere. Set it: the 874 issues
exceed the unauthenticated limit of 60 requests an hour. Any response that
is not a 200 for an issue (deleted, transferred, or a pull request) stops the fetch: a partial set
would silently change what S2 measures.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from collections.abc import Callable
from pathlib import Path

from s2 import inputs

ROOT = Path(__file__).resolve().parents[3]
PAIRS = ROOT / "eval/datasets/s1/pairs.jsonl"
MANIFEST = ROOT / "eval/datasets/s1/manifest.json"
API = "https://api.github.com"

Transport = Callable[[str], tuple[int, dict]]  # url -> (status, decoded JSON body)


def urllib_transport(token: str | None) -> Transport:
    def get(url: str) -> tuple[int, dict]:
        req = urllib.request.Request(
            url, headers={"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
        )
        if token:
            req.add_header("Authorization", f"Bearer {token}")
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                return resp.status, json.load(resp)
        except urllib.error.HTTPError as e:
            return e.code, {}

    return get


def repo_names(manifest: dict) -> dict[int, str]:
    """`owner/name` for each selected repository, from the manifest's candidate rows."""
    names = {c["github_repo_id"]: c["repo"] for c in manifest["candidates"]}
    return {r: names[r] for r in manifest["selected"]}


def fetch(issues: list[inputs.Issue], names: dict[int, str], get: Transport) -> list[dict]:
    rows = []
    for q in issues:
        status, data = get(f"{API}/repos/{names[q.github_repo_id]}/issues/{q.issue}")
        if status != 200:
            raise RuntimeError(f"{names[q.github_repo_id]}#{q.issue}: HTTP {status}")
        if "pull_request" in data:
            raise RuntimeError(f"{names[q.github_repo_id]}#{q.issue} is a pull request, not an issue")
        rows.append(
            {
                "github_repo_id": q.github_repo_id,
                "issue": q.issue,
                "title": data["title"],
                "body": data.get("body"),
            }
        )
    return rows


def inside_git(path: Path) -> bool:
    """True when the destination is inside a git checkout. The probe is the destination's nearest
    existing ancestor, never the caller's cwd, so a path under a repository is caught from anywhere.
    """
    path = path.expanduser().resolve()
    probe = next(p for p in path.parents if p.exists())
    r = subprocess.run(
        ["git", "-C", str(probe), "rev-parse", "--show-toplevel"], capture_output=True, text=True
    )
    return r.returncode == 0 and path.is_relative_to(Path(r.stdout.strip()).resolve())


def write(rows: list[dict], out: Path, fetched_at: str) -> dict:
    data = "".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in rows).encode()
    out.write_bytes(data)
    meta = {"count": len(rows), "fetched_at": fetched_at, "sha256": hashlib.sha256(data).hexdigest()}
    out.with_suffix(".meta.json").write_text(json.dumps(meta, indent=2, sort_keys=True) + "\n")
    return meta


def main(argv: list[str] | None = None, get: Transport | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", type=Path, required=True, help="JSONL path outside any git checkout")
    args = ap.parse_args(argv)
    out = args.out.expanduser()
    if inside_git(out):
        print(
            f"refusing {out}: it is inside a git checkout, and issue text is never committed", file=sys.stderr
        )
        return 2
    pairs = [json.loads(line) for line in PAIRS.read_text().splitlines()]
    issues = inputs.strong_dev_issues(pairs)
    names = repo_names(json.loads(MANIFEST.read_text()))
    fetched_at = dt.datetime.now(dt.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    rows = fetch(issues, names, get or urllib_transport(os.environ.get("GITHUB_TOKEN")))
    out.parent.mkdir(parents=True, exist_ok=True)
    print(json.dumps(write(rows, out, fetched_at), sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
