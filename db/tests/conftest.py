"""Schema tests run against a real Postgres with the pinned extensions, never a mock.

Set WAYFINDER_TEST_DSN to a server where the role may CREATE DATABASE, e.g. the S3 spike's container
(infra/spikes/s3/compose.yml, pinned by digest). Each test gets a fresh database with every migration
applied. Without the variable the tests skip rather than pass: a schema test that touched no
database proved nothing.
"""

from __future__ import annotations

import os
import re
import uuid
from collections.abc import Iterator
from pathlib import Path

import psycopg
import pytest

ROOT = Path(__file__).resolve().parents[2]
MIGRATIONS = sorted((ROOT / "db" / "migrations").glob("*.sql"))
DSN = os.environ.get("WAYFINDER_TEST_DSN")


def sections(path: Path) -> tuple[str, str]:
    """Split a dbmate migration into its up and down SQL."""
    up, down = re.split(r"^-- migrate:down\s*$", path.read_text(), flags=re.M)
    return up.split("-- migrate:up", 1)[1], down


@pytest.fixture
def empty_db() -> Iterator[psycopg.Connection]:
    if not DSN:
        pytest.skip("WAYFINDER_TEST_DSN not set: schema tests need a real database (see conftest)")
    name = f"wf_test_{uuid.uuid4().hex[:12]}"
    with psycopg.connect(DSN, autocommit=True) as admin:
        admin.execute(f'CREATE DATABASE "{name}"')
    try:
        with psycopg.connect(psycopg.conninfo.make_conninfo(DSN, dbname=name), autocommit=True) as conn:
            yield conn
    finally:
        with psycopg.connect(DSN, autocommit=True) as admin:
            admin.execute(f'DROP DATABASE "{name}" WITH (FORCE)')


@pytest.fixture
def db(empty_db: psycopg.Connection) -> psycopg.Connection:
    for m in MIGRATIONS:
        empty_db.execute(sections(m)[0])
    return empty_db


# Seed helpers: the minimum rows a test needs, and nothing it does not.

def one(conn, sql: str, params=()) -> int:
    return conn.execute(sql, params).fetchone()[0]


def seed_connection(conn, *, valid: str = "1 hour") -> int:
    return one(conn, "INSERT INTO connection (mode, account_login, state, state_observed_at,"
               " state_valid_until, egress_policy, config)"
               " VALUES ('public_readonly', 'acme', 'active', now(), now() + %s::interval, '{}', '{}')"
               " RETURNING id", (valid,))


def seed_repo(conn, connection_id: int, *, visibility="public", valid="1 hour",
              serving_state="active") -> int:
    return one(conn, "INSERT INTO repository (connection_id, github_repo_id, full_name, default_branch,"
               " visibility, visibility_observed_at, visibility_valid_until, serving_state, data_class)"
               " VALUES (%s, (random() * 1e12)::bigint, 'acme/r', 'main', %s, now(), now() + %s::interval,"
               " %s, %s) RETURNING id",
               (connection_id, visibility, valid, serving_state,
                "public" if visibility == "public" else "private"))


def seed_spec(conn, *, digest: str = "sha256:x") -> int:
    return one(conn, "INSERT INTO embedding_spec (model_ref, model_digest, runtime, doc_template,"
               " query_template, pooling, normalize, dimension, truncation, tokenizer_ref)"
               " VALUES ('m', %s, 'ollama/0', 'd: {body}', 'q: {query}', 'mean', true, 768,"
               " 'end', 't') RETURNING id", (digest,))


def seed_generation(conn, repo_id: int, spec_id: int, *, status: str, n: int = 1, base=None) -> int:
    return one(conn, "INSERT INTO generation (repo_id, desired_generation, commit_sha, spec_id,"
               " chunker_version, status, base_generation_id) VALUES (%s, %s, 'c' || %s, %s, 'v1', %s, %s)"
               " RETURNING id", (repo_id, n, n, spec_id, status, base))


def seed_representation(conn, repo_id: int, spec_id: int, text: str, *, live: bool = False) -> int:
    h = text.encode()
    conn.execute("INSERT INTO content (content_hash, body, token_count) VALUES (%s, %s, 1)"
                 " ON CONFLICT DO NOTHING", (h, text))
    return one(conn, "INSERT INTO representation (repo_id, spec_id, input_hash, content_hash, header,"
               " body_text, live) VALUES (%s, %s, %s, %s, 'h', %s, %s) RETURNING id",
               (repo_id, spec_id, h + str(repo_id).encode(), h, text, live))


def seed_occurrence(conn, repo_id: int, generation_id: int, rep_id: int) -> None:
    conn.execute("INSERT INTO occurrence (repo_id, generation_id, representation_id, path, blob_sha,"
                 " start_line, end_line) VALUES (%s, %s, %s, 'a.py', 'b', 1, 2)",
                 (repo_id, generation_id, rep_id))
