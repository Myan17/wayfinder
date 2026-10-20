"""Retrieval's SQL tests run against the pinned database, through the schema module's fixtures (a fresh
database per test with every migration). CI's unit job has no database, so they skip there; `make
db-test` runs them in the pinned job, where any skip fails the target."""

import sys
from pathlib import Path

import psycopg
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "db" / "tests"))
from conftest import DSN, db, empty_db  # noqa: F401  the schema module's database fixtures


@pytest.fixture
def pinned():
    """Skip, before `db` tries to create a database, when the pinned database is not reachable."""
    try:
        psycopg.connect(DSN or "", connect_timeout=2).close()
    except psycopg.OperationalError:
        pytest.skip("the pinned database is not reachable; make db-test runs these")
