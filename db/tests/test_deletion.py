import psycopg
import pytest
from conftest import seed_spec


def test_tombstone_retained_at_least_90_days(db):
    ins = "INSERT INTO tombstone (scope, ref, expires_at) VALUES ('repository', '1', now() + %s::interval)"
    with pytest.raises(psycopg.errors.CheckViolation):
        db.execute(ins, ("89 days",))
    db.execute(ins, ("90 days",))


def test_embedding_cache_data_class_is_closed(db):
    """GC step 6 deletes private entries only; a value outside the two classes would escape it."""
    s = seed_spec(db)
    ins = ("INSERT INTO embedding_cache (input_hash, spec_id, embedding, data_class)"
           " VALUES (%s, %s, array_fill(0.1, ARRAY[768])::halfvec, %s)")
    with pytest.raises(psycopg.errors.CheckViolation):
        db.execute(ins, (b"a", s, "secret"))
    db.execute(ins, (b"a", s, "private"))
