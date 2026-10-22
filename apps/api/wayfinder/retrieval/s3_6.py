"""Spike S3-6 (ADR-0007 Amendments 1 and 2, step 4): the plans of the canonical two-leg query.

    WAYFINDER_TEST_DSN=... uv run python -m wayfinder.retrieval.s3_6 [report.json]

The statement is `hybrid_sql.build`'s, imported and never copied; this module may not change it. Each
case PREPAREs that one parameterized statement and captures EXPLAIN (ANALYZE, BUFFERS) EXECUTE under
force_custom_plan and force_generic_plan, in JSON for the checks and in TEXT for the release manifest
(S3-6e). The checks read the plan as a tree. A failing plan is recorded and raised at G0; it is not an
automatic fallback.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import uuid
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path

import psycopg
from psycopg import sql

from wayfinder.authz.interface import AuthorizedScope, Principal, PrincipalKind
from wayfinder.retrieval import hybrid_sql as h

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "db"))
import s6_identity  # noqa: E402  ADR-0005's stand-in embedder, shared with spike S6

COMPOSE = ROOT / "infra" / "spikes" / "s3" / "compose.yml"
MIGRATIONS = sorted((ROOT / "db" / "migrations").glob("*.sql"))
REPORT = ROOT / "db" / "evidence" / "s3-6-plans.json"

REPOS = 100                      # all private: only the granted array admits rows
SIZES = (7_175, 60_000)          # ADR-0019's two sizes, live representations
SELECTIVITIES = (1, 10, 100)     # repositories the granted array admits
MODES = ("force_custom_plan", "force_generic_plan")
MATCHES_PER_REPO = 5
TERM = "wayfinderprobe"          # the query text; matches exactly 5 representations per repository
QUERY_ROW = 0                    # the query vector is this row's stand-in vector
K = 2 * h.LEG_LIMIT              # every fused candidate is returned (one representation per path)
SPEC = s6_identity.Spec(0, "s3-6", "sha256:s3-6-stand-in", "{body}")
SESSION = ("SET LOCAL max_parallel_workers_per_gather = 0",)  # ADR-0019: the plan S2 times


def vector(row: int) -> list[float]:
    return s6_identity.stand_in(SPEC, str(row))


def texts(row: int, repo: int) -> tuple[str, str, str]:
    """(header, body_text, path). Of each repository's rows, the first five carry TERM, through the
    body, the header or a path segment; no other row contains it."""
    path, header, body = f"src/r{repo}/m{row}.py", f"src/r{repo}/m{row}.py def filler_{row}", f"return {row}"
    match row // REPOS:
        case 0 | 3:
            body = f"def {TERM}_{row}(): return {row}"
        case 1:
            header = f"src/r{repo}/m{row}.py def {TERM}"
        case 2:
            path = f"src/r{repo}/{TERM}_{row}.py"
        case 4:
            body = f"{TERM}.call({row})"
    return header, body, path


@dataclass
class Fixture:
    size: int
    spec_id: int
    repo_ids: list[int]
    query_vector: list[float] = field(repr=False)


def build_fixture(conn, size: int) -> Fixture:
    """One connection, REPOS private repositories with an active generation, and `size` live
    representations spread evenly across them, each with a vector and an occurrence. ANALYZE last."""
    one = lambda q, p=(): conn.execute(q, p).fetchone()[0]  # noqa: E731
    conn_id = one("INSERT INTO connection (mode, account_login, state, state_observed_at, state_valid_until,"
                  " egress_policy, config) VALUES ('public_readonly', 'acme', 'active', now(),"
                  " now() + interval '1 day', '{}', '{}') RETURNING id")
    spec_id = one("INSERT INTO embedding_spec (model_ref, model_digest, runtime, doc_template,"
                  " query_template, pooling, normalize, dimension, truncation, tokenizer_ref)"
                  " VALUES (%s, %s, 'stand-in', %s, 'q: {query}', 'mean', true, 768, 'end', 't')"
                  " RETURNING id",
                  (SPEC.model_ref, SPEC.model_digest, SPEC.doc_template))
    repos, gens = [], []
    for i in range(REPOS):
        repo = one("INSERT INTO repository (connection_id, github_repo_id, full_name, default_branch,"
                   " visibility, visibility_observed_at, visibility_valid_until, serving_state, data_class)"
                   " VALUES (%s, %s, %s, 'main', 'private', now(), now() + interval '1 day', 'active',"
                   " 'private') RETURNING id", (conn_id, 1_000_000 + i, f"acme/r{i}"))
        gen = one("INSERT INTO generation (repo_id, desired_generation, commit_sha, spec_id, chunker_version,"
                  " status) VALUES (%s, 1, 'c1', %s, 'v1', 'active') RETURNING id", (repo, spec_id))
        conn.execute("UPDATE repository SET active_generation_id = %s WHERE id = %s", (gen, repo))
        repos.append(repo)
        gens.append(gen)
    with conn.transaction():
        with conn.cursor().copy("COPY content (content_hash, body, token_count) FROM STDIN") as cp:
            for row in range(size):
                body = texts(row, row % REPOS)[1]
                cp.write_row((hashlib.sha256(body.encode()).digest(), body, 1))
        with conn.cursor().copy("COPY representation (repo_id, spec_id, input_hash, content_hash, header,"
                                " body_text, path, live) FROM STDIN") as cp:
            for row in range(size):
                header, body, path = texts(row, row % REPOS)
                digest = hashlib.sha256(body.encode()).digest()
                cp.write_row((repos[row % REPOS], spec_id, digest, digest, header, body, path, True))
        ids = dict(conn.execute("SELECT input_hash, id FROM representation").fetchall())
        with conn.cursor().copy("COPY vector_d768 (representation_id, repo_id, spec_id, live, embedding)"
                                " FROM STDIN") as cp:
            for row in range(size):
                body = texts(row, row % REPOS)[1]
                rep = ids[hashlib.sha256(body.encode()).digest()]
                cp.write_row((rep, repos[row % REPOS], spec_id, True, h._vector(vector(row))))
        with conn.cursor().copy("COPY occurrence (repo_id, generation_id, representation_id, path, blob_sha,"
                                " start_line, end_line) FROM STDIN") as cp:
            for row in range(size):
                header, body, path = texts(row, row % REPOS)
                rep = ids[hashlib.sha256(body.encode()).digest()]
                cp.write_row((repos[row % REPOS], gens[row % REPOS], rep, path, "b", 1, 2))
    conn.execute("ANALYZE")
    return Fixture(size, spec_id, repos, vector(QUERY_ROW))


def scope(repo_ids) -> AuthorizedScope:
    return AuthorizedScope(Principal(1, PrincipalKind.USER), frozenset(repo_ids), frozenset(repo_ids),
                           datetime.now(UTC) + timedelta(hours=1))


def prepared(query: h.HybridQuery) -> tuple[str, list]:
    """The statement with each named parameter as $n, and the values in $n order."""
    names: list[str] = []

    def number(m: re.Match) -> str:
        if m[1] not in names:
            names.append(m[1])
        return f"${names.index(m[1]) + 1}"

    return re.sub(r"%\((\w+)\)s", number, query.sql), [query.params[n] for n in names]


def walk(node: dict) -> Iterator[dict]:
    yield node
    for child in node.get("Plans", []):
        yield from walk(child)


def scans(nodes: list[dict], relation: str, served) -> dict:
    """Whether some node on `relation` satisfies `served`, and the aliases of every Seq Scan on it."""
    nodes = [n for n in nodes if n.get("Relation Name") == relation]
    seq = sorted(n.get("Alias", relation) for n in nodes if n["Node Type"] == "Seq Scan")
    served_by = any(served(n) for n in nodes)
    return {"passed": served_by and not seq, "served": served_by, "seq_scans": seq}


def lexical_leg(plan: dict) -> list[dict]:
    """Amendment 2: every node under the scan of the `lexical` CTE, inlined (a Subquery Scan aliased
    `lexical`) or materialized (the `CTE lexical` subplan). Empty when the plan has neither."""
    return [n for root in walk(plan)
            if root.get("Alias") == "lexical" or root.get("Subplan Name") == "CTE lexical"
            for n in walk(root)]


def check_lexical(plan: dict) -> dict:
    """S3-6a, on the lexical leg's subtree only (Amendment 2): a ParadeDB Custom Scan on
    representation, and no Seq Scan on it. A plan with no lexical subtree fails."""
    return scans(lexical_leg(plan), "representation", lambda n: n["Node Type"] == "Custom Scan"
                 and "ParadeDB" in n.get("Custom Plan Provider", ""))


def check_dense(plan: dict) -> dict:
    """S3-6b: an Index Scan using vec768_hnsw on vector_d768, and no Seq Scan on it."""
    return scans(list(walk(plan)), "vector_d768", lambda n: n["Node Type"] == "Index Scan"
                 and n.get("Index Name") == "vec768_hnsw")


def check_rows(rows: list[dict], counted: set[int]) -> dict:
    """S3-6d, read from the rows and not from the SQL: each leg returned a candidate, and every row
    (so every candidate, as K exceeds both legs and no path holds two) is in a counted repository."""
    lexical = sum(r["lexical_rank"] is not None for r in rows)
    dense = sum(r["dense_rank"] is not None for r in rows)
    outside = sorted({r["repo_id"] for r in rows} - counted)
    return {"passed": lexical > 0 and dense > 0 and not outside,
            "lexical": lexical, "dense": dense, "rows": len(rows), "outside": outside}


def case(conn, fx: Fixture, granted: int, mode: str, *, text: str = TERM, extra: int | None = None) -> dict:
    """One prepared statement, one plan_cache_mode. `extra` is granted to the SQL but not counted by
    the harness: S3-6d's mutation check."""
    counted = set(fx.repo_ids[:granted])
    sc = scope(counted | ({extra} if extra is not None else set()))
    statement, values = prepared(h.build(text, {fx.spec_id: fx.query_vector}, sc, k=K))
    args = sql.SQL(", ").join(sql.Literal(v) for v in values)
    out: dict = {"size": fx.size, "granted": granted, "mode": mode}
    if conn.execute("SELECT 1 FROM pg_prepared_statements WHERE name = 's3_6'").fetchone():
        conn.execute("DEALLOCATE s3_6")  # PREPARE is not transactional; a failed case may leave it
    try:
        with conn.transaction():
            for s in (h.SESSION, *SESSION, f"SET LOCAL plan_cache_mode = {mode}"):
                conn.execute(s)
            conn.execute(sql.SQL("PREPARE s3_6 AS {}").format(sql.SQL(statement)))
            run = sql.SQL("EXECUTE s3_6({})").format(args)
            explain = lambda fmt: conn.execute(sql.SQL(  # noqa: E731
                "EXPLAIN (ANALYZE, BUFFERS, FORMAT {}) {}").format(sql.SQL(fmt), run)).fetchall()
            plan = explain("JSON")[0][0][0]["Plan"]
            out["plan_text"] = "\n".join(r[0] for r in explain("TEXT"))
            cur = conn.execute(run)
            rows = [dict(zip([c.name for c in cur.description], r, strict=True)) for r in cur.fetchall()]
    except psycopg.Error as e:
        return {**out, "error": f"{type(e).__name__}: {str(e).splitlines()[0]}",
                "S3-6a": {"passed": False}, "S3-6b": {"passed": False}, "S3-6d": {"passed": False}}
    return {**out, "S3-6a": check_lexical(plan), "S3-6b": check_dense(plan),
            "S3-6d": check_rows(rows, counted)}


def verdict(cases: list[dict]) -> dict:
    generic = [c for c in cases if c["mode"] == "force_generic_plan"]
    checks = {
        "S3-6a": all(c["S3-6a"]["passed"] for c in cases),
        "S3-6b": all(c["S3-6b"]["passed"] for c in cases),
        "S3-6c": bool(generic) and all(c["S3-6a"]["passed"] and c["S3-6b"]["passed"] for c in generic),
        "S3-6d": all(c["S3-6d"]["passed"] for c in cases),
        "S3-6e": all(c.get("plan_text") for c in cases),
    }
    return {"checks": checks, "passed": all(checks.values())}


def cases_at(conn, size: int) -> list[dict]:
    fx = build_fixture(conn, size)
    return [case(conn, fx, g, m) for g in SELECTIVITIES for m in MODES]


def on_temporary_database(dsn: str, size: int) -> list[dict]:
    name = f"wf_s3_6_{uuid.uuid4().hex[:12]}"
    with psycopg.connect(dsn, autocommit=True) as admin:
        admin.execute(f'CREATE DATABASE "{name}"')
    try:
        with psycopg.connect(psycopg.conninfo.make_conninfo(dsn, dbname=name), autocommit=True) as conn:
            for m in MIGRATIONS:
                conn.execute(m.read_text().split("-- migrate:up", 1)[1].split("-- migrate:down")[0])
            return cases_at(conn, size)
    finally:
        with psycopg.connect(dsn, autocommit=True) as admin:
            admin.execute(f'DROP DATABASE "{name}" WITH (FORCE)')


def main(argv: list[str]) -> int:
    dsn = os.environ.get("WAYFINDER_TEST_DSN")
    if not dsn:
        sys.exit("WAYFINDER_TEST_DSN is not set (make db-up prints it in the Makefile)")
    git = ["git", "-C", str(ROOT)]
    if subprocess.run([*git, "status", "--porcelain"], capture_output=True, text=True).stdout:
        sys.exit("the tree has uncommitted changes; the report must name the commit that produced it")
    cases = [c for size in SIZES for c in on_temporary_database(dsn, size)]
    with psycopg.connect(dsn) as conn:
        server = conn.execute("SELECT version(), (SELECT extversion FROM pg_extension"
                              " WHERE extname = 'pg_search')").fetchone()
    report = {
        **verdict(cases),
        "image": re.search(r"image:\s*(\S+)", COMPOSE.read_text())[1],
        "server": {"version": server[0], "pg_search": server[1]},
        "commit": subprocess.run([*git, "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip(),
        "cases": cases,
    }
    out = Path(argv[0]) if argv else REPORT
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, sort_keys=True, default=str) + "\n")
    print(json.dumps({"passed": report["passed"], **report["checks"]}, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
