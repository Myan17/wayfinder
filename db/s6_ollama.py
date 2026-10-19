"""Spike S6: rule S6-5 and the repeatability measurement (ADR-0005), against a real Ollama.

usage, from the repository root, with `make db-up` and `ollama serve` running and both models pulled
(`ollama pull nomic-embed-text`, `ollama pull snowflake-arctic-embed:110m`):

    WAYFINDER_TEST_DSN=... uv run --extra dev python db/s6_ollama.py [report.json]

It builds and activates through db/s6_identity.py, the code CI tests with the stand-in. Only the embedder
differs (gupta958's ruling on #80). It writes a JSON report that the results pull request commits
unchanged, and exits 1 unless every S6-5 check passed.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import struct
import subprocess
import sys
import urllib.request
import uuid
from pathlib import Path

import psycopg
import s6_identity as s6

sys.path.insert(0, str(Path(__file__).resolve().parent / "tests"))
from conftest import MIGRATIONS, sections, seed_connection, seed_repo  # the CI tests' setup

FIRST = "nomic-embed-text"
SECOND = "snowflake-arctic-embed:110m"  # also 768-d, so the re-pointed alias still fits vector_d768
ALIAS = "wayfinder-s6-embed"
TEMPLATE = "search_document: {header}\n{body}"
OPTIONS: dict = {}  # identical for every call, including both repeatability calls
REPORT = Path(__file__).resolve().parent / "evidence" / "s6-ollama.json"


class Ollama:
    """The five Ollama API calls S6-5 needs."""

    def __init__(self, base: str = "http://localhost:11434"):
        self.base = base

    def _call(self, method: str, path: str, body: dict | None = None) -> dict:
        data = None if body is None else json.dumps(body).encode()
        req = urllib.request.Request(self.base + path, data=data, method=method)
        req.add_header("Content-Type", "application/json")
        with urllib.request.urlopen(req, timeout=120) as resp:
            raw = resp.read()
        return json.loads(raw) if raw else {}

    def version(self) -> str:
        return self._call("GET", "/api/version")["version"]

    def digest(self, name: str) -> str:
        """The digest the runtime reports for a local model name, never derived from the name."""
        full = name if ":" in name else f"{name}:latest"
        for model in self._call("GET", "/api/tags")["models"]:
            if model["name"] == full:
                return model["digest"]
        raise LookupError(f"{name} is not pulled")

    def copy(self, source: str, destination: str) -> None:
        self._call("POST", "/api/copy", {"source": source, "destination": destination})

    def delete(self, name: str) -> None:
        self._call("DELETE", "/api/delete", {"model": name, "name": name})

    def embed(self, model: str, text: str) -> list[float]:
        body = {"model": model, "input": text, "options": OPTIONS, "truncate": False}
        return self._call("POST", "/api/embed", body)["embeddings"][0]


def embedder(client, counter: dict) -> s6.Embedder:
    """The real embedder for s6.index_chunk. It refuses to embed unless the alias still names the
    captured digest, so a vector can never be stored under a specification that did not produce it."""

    def embed(spec: s6.Spec, text: str) -> list[float]:
        if client.digest(spec.model_ref) != spec.model_digest:
            raise RuntimeError(f"{spec.model_ref} no longer names {spec.model_digest}")
        counter["calls"] += 1
        vector = client.embed(spec.model_ref, text)
        if len(vector) != s6.DIMENSION:
            raise RuntimeError(f"{spec.model_ref} returned {len(vector)} dimensions")
        return vector

    return embed


def repeatability(client, model: str, text: str) -> dict:
    """Two direct calls, bypassing reuse, with the same digest, input and options (gupta958's ruling 2)."""
    v1, v2 = client.embed(model, text), client.embed(model, text)
    pack = struct.Struct(f"<{len(v1)}d").pack
    dot = sum(a * b for a, b in zip(v1, v2, strict=True))
    norms = math.sqrt(sum(a * a for a in v1)) * math.sqrt(sum(b * b for b in v2))
    return {
        "byte_identical": len(v1) == len(v2) and pack(*v1) == pack(*v2),
        "max_abs_difference": max(abs(a - b) for a, b in zip(v1, v2, strict=True)),
        "cosine_distance": 1 - dot / norms,
    }


def count(conn, table: str) -> int:
    return conn.execute(f"SELECT count(*) FROM {table}").fetchone()[0]


def run(client, conn) -> dict:
    """S6-5's sequence on a fresh database. Returns the report; `passed` is every check."""
    runtime = f"ollama/{client.version()}"
    capture = {"model_ref": ALIAS, "runtime": runtime, "doc_template": TEMPLATE}
    calls = {"calls": 0}
    embed = embedder(client, calls)
    checks = {}

    client.copy(FIRST, ALIAS)
    d1 = client.digest(ALIAS)
    checks["digest_is_the_runtimes"] = d1 == client.digest(FIRST) and d1 not in (ALIAS, FIRST)
    a = s6.capture_spec(conn, model_digest=d1, **capture)
    checks["unchanged_alias_recaptures_the_existing_row"] = (
        s6.capture_spec(conn, model_digest=d1, **capture) == a and count(conn, "embedding_spec") == 1
    )
    repo = seed_repo(conn, seed_connection(conn))
    desired, claim = s6.push_and_claim(conn, repo)
    gen_a = s6.new_generation(conn, repo, a, desired=desired, base=None)
    rep_a = s6.index_chunk(conn, embed, repo_id=repo, generation_id=gen_a, spec=a)
    s6.finish_build(conn, gen_a)
    s6.activate(conn, repo_id=repo, new=gen_a, base=None, desired=desired, claim=claim)
    calls_a = calls["calls"]

    client.copy(SECOND, ALIAS)
    d2 = client.digest(ALIAS)
    checks["alias_now_names_another_digest"] = d2 != d1 and d2 == client.digest(SECOND)
    b = s6.capture_spec(conn, model_digest=d2, **capture)
    checks["repointed_alias_is_a_new_spec"] = b.id != a.id and count(conn, "embedding_spec") == 2
    desired, claim = s6.push_and_claim(conn, repo)
    gen_b = s6.new_generation(conn, repo, b, desired=desired, base=gen_a)
    rep_b = s6.index_chunk(conn, embed, repo_id=repo, generation_id=gen_b, spec=b)
    checks["s6_1_new_representation"] = (
        rep_b != rep_a and count(conn, "representation") == 2 and count(conn, "vector_d768") == 2
    )
    checks["s6_3_one_embedder_call_each"] = calls_a == 1 and calls["calls"] == 2
    s6.finish_build(conn, gen_b)
    s6.activate(conn, repo_id=repo, new=gen_b, base=gen_a, desired=desired, claim=claim)
    checks["serving_follows_activation"] = (
        s6.serving_rows(conn, repo, b) == [rep_b] and s6.serving_rows(conn, repo, a) == []
    )

    text = s6.embedded_input(TEMPLATE, s6.T_HEADER, s6.T_BODY)
    return {
        "adr": "ADR-0005",
        "rule": "S6-5",
        "passed": all(checks.values()),
        "checks": checks,
        "ollama": runtime,
        "models": {FIRST: d1, SECOND: d2},
        "alias": ALIAS,
        "template": TEMPLATE,
        "options": OPTIONS,
        "dimension": s6.DIMENSION,
        "t_body_sha256": hashlib.sha256(s6.T_BODY.encode()).hexdigest(),
        "repeatability": {"model": FIRST, "digest": d1, **repeatability(client, FIRST, text)},
    }


def main(argv: list[str]) -> int:
    dsn = os.environ.get("WAYFINDER_TEST_DSN")
    if not dsn:
        sys.exit("WAYFINDER_TEST_DSN is not set (make db-up prints it in the Makefile)")
    root = Path(__file__).resolve().parents[1]
    git = ["git", "-C", str(root)]
    if subprocess.run([*git, "status", "--porcelain", "db"], capture_output=True, text=True).stdout:
        sys.exit("db/ has uncommitted changes; the report must name the commit that produced it")
    out = Path(argv[0]) if argv else REPORT
    client = Ollama()
    name = f"wf_s6_{uuid.uuid4().hex[:12]}"
    with psycopg.connect(dsn, autocommit=True) as admin:
        admin.execute(f'CREATE DATABASE "{name}"')
    try:
        with psycopg.connect(psycopg.conninfo.make_conninfo(dsn, dbname=name), autocommit=True) as conn:
            for m in MIGRATIONS:
                conn.execute(sections(m)[0])
            report = run(client, conn)
    finally:
        client.delete(ALIAS)
        with psycopg.connect(dsn, autocommit=True) as admin:
            admin.execute(f'DROP DATABASE "{name}" WITH (FORCE)')
    report["commit"] = subprocess.run(
        [*git, "rev-parse", "HEAD"], capture_output=True, text=True
    ).stdout.strip()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"passed": report["passed"], **report["checks"], **report["repeatability"]}, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
