import psycopg
import pytest
from conftest import (
    seed_connection,
    seed_generation,
    seed_occurrence,
    seed_repo,
    seed_representation,
    seed_spec,
)


def test_gc_order_and_set_null(db):
    """DESIGN 9.3.6: out-of-order deletes fail loudly; the documented order succeeds."""
    c = seed_connection(db)
    r = seed_repo(db, c)
    s = seed_spec(db)
    old = seed_generation(db, r, s, status="retired", n=1)
    new = seed_generation(db, r, s, status="active", n=2, base=old)
    rep = seed_representation(db, r, s, "gone")
    db.execute(
        "INSERT INTO vector_d768 (representation_id, repo_id, spec_id, embedding) "
        "VALUES (%s, %s, %s, array_fill(0.1, ARRAY[768])::halfvec(768))",
        (rep, r, s),
    )
    seed_occurrence(db, r, old, rep)

    with pytest.raises(psycopg.errors.RestrictViolation):     # representation before occurrence
        db.execute("DELETE FROM representation WHERE id = %s", (rep,))
    with pytest.raises(psycopg.errors.RestrictViolation):     # generation before its occurrences
        db.execute("DELETE FROM generation WHERE id = %s", (old,))

    db.execute("DELETE FROM occurrence WHERE generation_id = %s", (old,))          # step 1
    db.execute("DELETE FROM generation WHERE id = %s", (old,))                     # step 3
    assert db.execute("SELECT base_generation_id FROM generation WHERE id = %s", (new,)).fetchone()[0] is None
    db.execute("DELETE FROM representation WHERE id = %s", (rep,))                # step 4
    assert db.execute("SELECT count(*) FROM vector_d768").fetchone()[0] == 0       # 1:1 cascade
    db.execute("DELETE FROM content WHERE content_hash = %s", (b"gone",))          # step 5

