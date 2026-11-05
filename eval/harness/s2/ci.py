"""Spike S2's CI job (ADR-0019 Amendment 1 §5): whether it runs in full, its cache keys, and the model.

    PYTHONPATH=eval/harness python3 -m s2.ci changed <base> <head>   # mode=full or mode=no-op
    PYTHONPATH=eval/harness python3 -m s2.ci keys                    # cache keys, by pinned digest
    PYTHONPATH=eval/harness uv run --no-sync python -m s2.ci model --restored | --pulled

`changed` and `keys` use only the standard library, so they run before any sync. Each command writes
`name=value` lines to `$GITHUB_OUTPUT` when it is set. The job runs in full whenever the diff cannot
be computed: the no-op is only for a diff that touches none of S2's inputs.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from collections.abc import Callable, Iterable

WORKFLOW = ".github/workflows/ci.yml"  # the job's own workflow file
# Amendment 1 §5's trigger list, with rulings 4 and 5. A path is S2's input when it is under one of
# DIRS or is one of FILES. The model pins live in the harness, so `eval/harness/s2/` covers them.
DIRS = (
    "eval/harness/s2/",
    "eval/harness/tests/",  # the harness's tests, so a change to a real test runs it
    "apps/api/wayfinder/retrieval/",
    "apps/api/wayfinder/authz/",
    "db/views/",
    "db/migrations/",
    "eval/datasets/s1/",
    "infra/spikes/s3/",
)
FILES = (
    "db/s6_identity.py",
    "db/tests/test_s2_build_path.py",  # its 60,000-row test runs only in this job (gupta958's #108 ruling)
    "db/tests/conftest.py",
    "eval/miners/s1/universe.py",
    "pyproject.toml",
    "uv.lock",
    "Makefile",  # make s2-scale-test
    WORKFLOW,
)

Run = Callable[[list[str]], str]


def git(argv: list[str]) -> str:
    return subprocess.run(argv, check=True, capture_output=True, text=True).stdout


def triggers(paths: Iterable[str]) -> list[str]:
    return sorted(p for p in set(paths) if p in FILES or p.startswith(DIRS))


def changed(base: str, head: str, run: Run = git) -> tuple[str, list[str]]:
    """`("full", reasons)` or `("no-op", [])`. Renames count as both paths, so moving a file out of
    S2's inputs is a change to them."""
    if not base.strip("0") or not head:
        return "full", ["no base to compare against"]
    try:
        out = run(["git", "diff", "--no-renames", "--name-only", f"{base}...{head}"])
    except (subprocess.CalledProcessError, OSError):
        return "full", [f"git diff {base[:12]}...{head[:12]} failed"]
    hits = triggers(out.splitlines())
    return ("full", hits) if hits else ("no-op", [])


def keys() -> dict[str, str]:
    """Cache keys made from the pins themselves, so a new pin can never restore an old file."""
    from s2 import reranker, services

    pins = [reranker.REPO, reranker.REVISION, reranker.PINS, reranker.SIZES]
    digest = hashlib.sha256(json.dumps(pins, sort_keys=True).encode()).hexdigest()
    return {"model": f"s2-ollama-{services.MODEL_DIGEST}", "reranker": f"s2-reranker-{digest}"}


def model(restored: bool, run=None, http=None) -> None:
    """Start the query Ollama. A restored model is only checked against its pinned digest, so a bad
    cache fails the job; a missing one is pulled, then checked."""
    from s2 import services

    run, http = run or services.subprocess_run, http or services.urllib_http
    services.up(run, http, ("ollama-query",))
    (services.check_model if restored else services.pull_model)(http, "ollama-query")


def output(values: dict[str, str]) -> None:
    for k, v in values.items():
        print(f"{k}={v}")
    if path := os.environ.get("GITHUB_OUTPUT"):
        with open(path, "a") as f:
            f.writelines(f"{k}={v}\n" for k, v in values.items())


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("changed")
    c.add_argument("base")
    c.add_argument("head")
    sub.add_parser("keys")
    m = sub.add_parser("model").add_mutually_exclusive_group(required=True)
    m.add_argument("--restored", action="store_true")
    m.add_argument("--pulled", action="store_true")
    args = ap.parse_args(argv)
    if args.cmd == "changed":
        mode, why = changed(args.base, args.head)
        print("S2 inputs changed: " + ", ".join(why) if why else "No S2 input changed: the job is a no-op.")
        output({"mode": mode})
    elif args.cmd == "keys":
        output(keys())
    else:
        model(args.restored)
        print("ollama-query: nomic-embed-text at its pinned digest")
    return 0


if __name__ == "__main__":
    sys.exit(main())
