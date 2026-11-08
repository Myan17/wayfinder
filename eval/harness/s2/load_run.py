"""Spike S2's corpus load, part 3: load the corpus into a new database and write the load report.

    PYTHONPATH=eval/harness:eval/miners uv run --extra dev python -m s2.load_run \\
        --mirrors ~/wayfinder-s1/mirrors --size real --out ~/wayfinder-s2/load-real.json

ADR-0019 Amendments 1-3. `--mirrors` holds S1's bare mirror clones, named `<owner>__<name>.git` as
`eval/miners/s1/run.py` names them. Each selected repository is read at its manifest `as_of_commit`,
and the run refuses unless every repository's window count equals its `chunk_estimate`. The embedder
is the ingestion Ollama container's `nomic-embed-text`, refused unless the runtime reports ADR-0019's
version and digest. The load goes into a database this command creates on the S2 Postgres and keeps
for the passes; it refuses a name that exists, and drops the database again only if the load fails.
`--size 60k` pads to exactly 60,000 live representations and is labelled scale evidence.

The windows are ADR-0016's 60-line estimate rule, not DESIGN §9.4's chunker, and the report says so.
A run on any host but the A1 is S2-dev, and its numbers are never evidence.
"""

from __future__ import annotations

import argparse
import json
import math
import platform
import subprocess
import sys
from collections.abc import Callable, Mapping
from dataclasses import asdict
from pathlib import Path

from s2 import inputs, load, load_plan, services

ROOT = Path(__file__).resolve().parents[3]
MANIFEST = ROOT / "eval/datasets/s1/manifest.json"
SIZES = {"real": None, "60k": load_plan.PADDED_TOTAL}
CHUNKER = "ADR-0016's 60-line estimate windows, not DESIGN §9.4's chunker (ADR-0019 Amendment 1 §1)"


class Refused(RuntimeError):
    """An input or the runtime is not the one ADR-0019 pins; nothing was loaded."""


def mirror(mirrors: Path, full_name: str) -> Path:
    owner, name = full_name.split("/")
    return mirrors / f"{owner}__{name}.git"


def corpus(
    manifest: Mapping, mirrors: Path, snapshot: Callable = inputs.snapshot
) -> tuple[list[inputs.Window], dict[int, str]]:
    """Every selected repository's windows at its as-of commit, and `owner/name` by id."""
    rows = {c["github_repo_id"]: c for c in manifest["candidates"]}
    names = {r: rows[r]["repo"] for r in manifest["selected"]}
    windows, counts = [], {}
    for r in sorted(names):
        ws = snapshot(mirror(mirrors, names[r]), rows[r]["as_of_commit"], r)
        counts[r] = len(ws)
        windows.extend(ws)
    if problems := inputs.count_problems(counts, manifest):
        raise Refused("window counts differ from the manifest: " + "; ".join(problems))
    return windows, names


def check_runtime(http: services.Http, service: str = "ollama-ingest") -> str:
    """The runtime string for the specification, once version and digest are ADR-0019's."""
    status, body = http(f"{services.OLLAMA[service]}/api/version", None)
    version = body.get("version") if status == 200 else None
    if version != services.OLLAMA_VERSION:
        raise Refused(f"{service}: Ollama {version}, pinned {services.OLLAMA_VERSION}")
    try:
        services.check_model(http, service)
    except services.ServiceError as e:
        raise Refused(str(e)) from e
    return f"ollama/{version}"


def distribution(xs: list[int]) -> dict:
    """Nearest-rank p50 and p95, and the maximum."""
    s = sorted(xs)
    rank = lambda q: s[max(math.ceil(q * len(s)), 1) - 1] if s else None  # noqa: E731
    return {"count": len(s), "p50": rank(0.50), "p95": rank(0.95), "max": s[-1] if s else None}


def report(got: load.Loaded, size: str, meta: Mapping) -> dict:
    distinct = sum(got.real.values())
    copies = sum(got.padded.values())
    return {
        "adr": "ADR-0019 Amendments 1-3",
        "size": size,
        "label": "scale evidence, never retrieval-quality evidence" if size == "60k" else "real corpus",
        "chunker": CHUNKER,
        "lease_seconds": got.lease.total_seconds(),
        "build_seconds": {f"{p:02d}": d.total_seconds() for p, d in sorted(got.durations.items())},
        "windows": got.windows,
        "distinct_representations": distinct,
        "live_representations": distinct + copies,
        "padding_fraction": copies / (distinct + copies),
        "per_pseudo_repository": {
            f"{p:02d}": {"real": got.real[p], "padded": got.padded[p]} for p in sorted(got.real)
        },
        "truncated": {
            "count": len(got.truncated),
            "fraction": len(got.truncated) / got.windows,
            "rejected_length": f"exceeds {load_plan.CONTEXT_TOKENS:,}",
            "windows": [asdict(t) for t in got.truncated],
        },
        "accepted_tokens": distribution(got.accepted_tokens),
        **meta,
    }


def provenance(runtime: str, database: str) -> dict:
    git = ["git", "-C", str(ROOT)]
    if subprocess.run([*git, "status", "--porcelain", "db", "eval"], capture_output=True, text=True).stdout:
        raise Refused("db/ or eval/ has uncommitted changes; the report must name its commit")
    return {
        "commit": subprocess.run([*git, "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip(),
        "host": " ".join(platform.uname()),
        "ollama": runtime,
        "model": services.MODEL,
        "model_digest": services.MODEL_DIGEST,
        "database": database,
    }


def run(dsn: str, database: str, windows, names, pad_to: int | None, runtime: str) -> load.Loaded:
    """Create `database`, migrate it and load into it. It is dropped again only if the load fails."""
    import psycopg
    import s6_ollama  # here, so the pure parts above never load the schema tests' setup

    with psycopg.connect(dsn, autocommit=True) as admin:
        admin.execute(f'CREATE DATABASE "{database}"')  # an existing name fails here, before any load
    try:
        with psycopg.connect(psycopg.conninfo.make_conninfo(dsn, dbname=database), autocommit=True) as conn:
            for m in s6_ollama.MIGRATIONS:
                conn.execute(s6_ollama.sections(m)[0])
            spec = load.s6.capture_spec(
                conn,
                model_ref=services.MODEL,
                model_digest=services.MODEL_DIGEST,
                runtime=runtime,
                doc_template=s6_ollama.TEMPLATE,
            )
            calls: list = []
            client = s6_ollama.Ollama(services.OLLAMA["ollama-ingest"])
            embed = s6_ollama.embedder(client, {"calls": 0}, record=calls, truncate_rejected=True)
            return load.load(
                conn, embed, windows, names, spec,
                calls=calls, context_exceeded=s6_ollama.ContextExceeded, pad_to=pad_to,
            )  # fmt: skip
    except BaseException:
        with psycopg.connect(dsn, autocommit=True) as admin:
            admin.execute(f'DROP DATABASE "{database}" WITH (FORCE)')
        raise


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--mirrors", type=Path, required=True, help="S1's <owner>__<name>.git mirrors")
    ap.add_argument("--size", choices=sorted(SIZES), required=True)
    ap.add_argument("--out", type=Path, required=True, help="the report, JSON")
    ap.add_argument("--dsn", default=services.DSN, help="the S2 Postgres (default: compose.yml's)")
    ap.add_argument("--dbname", help="the database to create (default: s2_<size>)")
    args = ap.parse_args(argv)
    database = args.dbname or f"s2_{args.size}"
    try:
        windows, names = corpus(json.loads(MANIFEST.read_text()), args.mirrors.expanduser())
        runtime = check_runtime(services.urllib_http)
        meta = provenance(runtime, database)
        got = run(args.dsn, database, windows, names, SIZES[args.size], runtime)
    except (Refused, load_plan.LoadFailed) as e:
        print(f"refused: {e}" if isinstance(e, Refused) else f"load failed: {e}", file=sys.stderr)
        return 1
    out = args.out.expanduser()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report(got, args.size, meta), indent=2, sort_keys=True) + "\n")
    print(f"{got.windows} windows, {len(got.truncated)} truncated; report at {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
