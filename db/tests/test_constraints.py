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


def test_cross_repo_occurrence_rejected(db):
    c = seed_connection(db)
    a, b = seed_repo(db, c), seed_repo(db, c)
    s = seed_spec(db)
    gen_a = seed_generation(db, a, s, status="building")
    rep_b = seed_representation(db, b, s, "x")
    with pytest.raises(psycopg.errors.ForeignKeyViolation):
        seed_occurrence(db, a, gen_a, rep_b)


def test_cross_repo_vector_rejected(db):
    c = seed_connection(db)
    a, b = seed_repo(db, c), seed_repo(db, c)
    s = seed_spec(db)
    rep_a = seed_representation(db, a, s, "x")
    with pytest.raises(psycopg.errors.ForeignKeyViolation):
        db.execute(
            "INSERT INTO vector_d768 (representation_id, repo_id, spec_id, embedding) "
            "VALUES (%s, %s, %s, array_fill(0.1, ARRAY[768])::halfvec(768))",
            (rep_a, b, s),
        )


def test_vector_spec_must_match_representation(db):
    """The dense leg filters on vector_d768.spec_id; a mislabelled row would be searched in the
    wrong embedding space."""
    c = seed_connection(db)
    r = seed_repo(db, c)
    s1, s2 = seed_spec(db), seed_spec(db, digest="sha256:y")
    rep = seed_representation(db, r, s1, "x")
    with pytest.raises(psycopg.errors.ForeignKeyViolation):
        db.execute(
            "INSERT INTO vector_d768 (representation_id, repo_id, spec_id, embedding) "
            "VALUES (%s, %s, %s, array_fill(0.1, ARRAY[768])::halfvec(768))",
            (rep, r, s2),
        )


def test_one_active_generation(db):
    c = seed_connection(db)
    r = seed_repo(db, c)
    s = seed_spec(db)
    seed_generation(db, r, s, status="active", n=1)
    with pytest.raises(psycopg.errors.UniqueViolation):
        seed_generation(db, r, s, status="active", n=2)


def test_active_pointer_cannot_name_another_repos_generation(db):
    c = seed_connection(db)
    a, b = seed_repo(db, c), seed_repo(db, c)
    s = seed_spec(db)
    gen_b = seed_generation(db, b, s, status="active")
    with pytest.raises(psycopg.errors.ForeignKeyViolation):
        db.execute("UPDATE repository SET active_generation_id = %s WHERE id = %s", (gen_b, a))
