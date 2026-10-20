"""Retrieval's SQL tests run against the pinned database, through the schema module's fixtures (a fresh
database per test with every migration). CI's unit job has no database, so they skip there; `make
db-test` runs them in the pinned job, where any skip fails the target."""

import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import psycopg
import pytest

from wayfinder.authz.interface import AuthorizedScope, Principal, PrincipalKind
from wayfinder.retrieval import hybrid_sql as h

sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "db" / "tests"))
from conftest import DSN, db, empty_db  # noqa: F401  the schema module's database fixtures


@pytest.fixture
def pinned():
    """Skip, before `db` tries to create a database, when the pinned database is not reachable."""
    try:
        psycopg.connect(DSN or "", connect_timeout=2).close()
    except psycopg.OperationalError:
        pytest.skip("the pinned database is not reachable; make db-test runs these")


# Helpers shared by the retrieval SQL tests.

DIM = h.DIMENSION


def axis(i: int) -> list[float]:
    return [1.0 if d == i else 0.0 for d in range(DIM)]


def scope(granted=(), public=(), *, expires_in=timedelta(hours=1)) -> AuthorizedScope:
    return AuthorizedScope(
        principal=Principal(1, PrincipalKind.USER),
        repo_ids=frozenset(granted) | frozenset(public),
        granted_repo_ids=frozenset(granted),
        expires_at=datetime.now(UTC) + expires_in,
    )


class World:
    """Repositories with an active generation, and helpers to add indexed passages to them."""

    def __init__(self, conn):
        self.db = conn
        self.conn_id = conn.execute(
            "INSERT INTO connection (mode, account_login, state, state_observed_at, state_valid_until,"
            " egress_policy, config) VALUES ('public_readonly', 'acme', 'active', now(),"
            " now() + interval '1 hour', '{}', '{}') RETURNING id").fetchone()[0]
        self.n = 0

    def spec(self, digest: str) -> int:
        return self.db.execute(
            "INSERT INTO embedding_spec (model_ref, model_digest, runtime, doc_template, query_template,"
            " pooling, normalize, dimension, truncation, tokenizer_ref) VALUES ('m', %s, 'ollama/0',"
            " 'd: {body}', 'q: {query}', 'mean', true, 768, 'end', 't') RETURNING id",
            (digest,)).fetchone()[0]

    def repo(self, spec: int, *, public: bool = False) -> tuple[int, int]:
        vis = "public" if public else "private"
        repo = self.db.execute(
            "INSERT INTO repository (connection_id, github_repo_id, full_name, default_branch, visibility,"
            " visibility_observed_at, visibility_valid_until, serving_state, data_class) VALUES"
            " (%s, (random() * 1e12)::bigint, 'acme/r', 'main', %s, now(), now() + interval '1 hour',"
            " 'active', %s) RETURNING id", (self.conn_id, vis, vis)).fetchone()[0]
        gen = self.generation(repo, spec, "active")
        self.db.execute("UPDATE repository SET active_generation_id = %s WHERE id = %s", (gen, repo))
        return repo, gen

    def generation(self, repo: int, spec: int, status: str) -> int:
        return self.db.execute(
            "INSERT INTO generation (repo_id, desired_generation, commit_sha, spec_id, chunker_version,"
            " status) VALUES (%s, 1, 'c' || nextval('generation_id_seq'), %s, 'v1', %s) RETURNING id",
            (repo, spec, status)).fetchone()[0]

    def add(self, repo, gen, spec, body, path, *, vec=1, start_line=1, live=True) -> int:
        """`vec` is an axis index, or a whole vector."""
        self.n += 1
        key = f"{self.n}".encode()
        self.db.execute("INSERT INTO content (content_hash, body, token_count) VALUES (%s, %s, 1)"
                        " ON CONFLICT DO NOTHING", (body.encode(), body))
        rep = self.db.execute(
            "INSERT INTO representation (repo_id, spec_id, input_hash, content_hash, header, body_text, path,"
            " live) VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING id",
            (repo, spec, key, body.encode(), path, body, path, live)).fetchone()[0]
        self.db.execute("INSERT INTO vector_d768 (representation_id, repo_id, spec_id, live, embedding)"
                        " VALUES (%s, %s, %s, %s, %s::halfvec)",
                        (rep, repo, spec, live, h._vector(axis(vec) if isinstance(vec, int) else vec)))
        self.db.execute("INSERT INTO occurrence (repo_id, generation_id, representation_id, path, blob_sha,"
                        " start_line, end_line) VALUES (%s, %s, %s, %s, 'b', %s, %s)",
                        (repo, gen, rep, path, start_line, start_line + 1))
        return rep


@pytest.fixture
def world(pinned, db):  # noqa: F811  `db` is the schema module's fixture, imported above
    return World(db)


def run(conn, sc, text="widget", vectors=None, k=50):
    query = h.build(text, vectors or {}, sc, k=k)
    return h.execute(conn, query, sc)
