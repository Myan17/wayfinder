import psycopg
import pytest
from conftest import one


def test_cached_from_set_null(db):
    """DESIGN 9.3.6 step 3: expiring a cached-from parent must not block on its children."""
    p = one(db, "INSERT INTO principal (kind) VALUES ('anonymous') RETURNING id")
    ins = ("INSERT INTO answer (id, principal_id, status, mode, query, evidence_manifest, classification,"
           " pipeline_config, cached_from) VALUES (gen_random_uuid(), %s, 'completed', 'locate', 'q', '{}',"
           " 'public', 'c', %s) RETURNING id")
    parent = db.execute(ins, (p, None)).fetchone()[0]
    child = db.execute(ins, (p, parent)).fetchone()[0]
    db.execute("DELETE FROM answer WHERE id = %s", (parent,))
    assert db.execute("SELECT cached_from FROM answer WHERE id = %s", (child,)).fetchone()[0] is None


def test_answer_needs_a_principal(db):
    """An anonymous request still has a principal (DESIGN 9.2): answers are never ownerless."""
    with pytest.raises(psycopg.errors.NotNullViolation):
        db.execute("INSERT INTO answer (id, principal_id, status, mode, query, evidence_manifest,"
                   " classification, pipeline_config) VALUES (gen_random_uuid(), NULL, 'completed',"
                   " 'locate', 'q', '{}', 'public', 'c')")
