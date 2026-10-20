"""representation.path and the code-aware rep_bm25 (ADR-0007 Amendment 1, DESIGN §9.5 step 2).

Each field's example from the migration's table must match through that field and no other way, so a
tokenizer that silently fell back to the default would fail here."""

import psycopg
import pytest
from conftest import (
    MIGRATIONS,
    sections,
    seed_connection,
    seed_generation,
    seed_occurrence,
    seed_repo,
    seed_representation,
    seed_spec,
)

HEADER = "src/app/widget_parser.py parseWidget_value"
BODY = "def parseWidget_value(x): return foo.Bar_baz(x)"
PATH = "src/app/widget_parser.py"


@pytest.fixture
def rows(db):
    repo = seed_repo(db, seed_connection(db))
    spec = seed_spec(db)
    hit = seed_representation(db, repo, spec, BODY, path=PATH)
    db.execute("UPDATE representation SET header = %s WHERE id = %s", (HEADER, hit))
    seed_representation(db, repo, spec, "nothing here", path="lib/z.go")
    return db, hit


def matches(db, field: str, text: str) -> list[int]:
    return [r[0] for r in db.execute(
        "SELECT id FROM representation WHERE id @@@ paradedb.match(%s, %s) ORDER BY id", (field, text))]


@pytest.mark.parametrize("field, text", [
    ("header", "widget"),                       # source_code splits parseWidget_value
    ("header_ident", "parseWidget_value"),      # the original token, lowercased on both sides
    ("body_text", "Widget"),
    ("body_ident", "foo.Bar_baz"),              # a dotted identifier stays whole
    ("path", "widget_parser.py"),               # a whole path segment
    ("path", "app"),
    ("path_code", "parser"),                    # a part of a path segment
])
def test_each_field_matches_its_example(rows, field, text):
    db, hit = rows
    assert matches(db, field, text) == [hit]


@pytest.mark.parametrize("field, text", [
    ("body_ident", "widget"),                   # the ident field does not split
    ("path", "parser"),                         # the segment field does not split
])
def test_unsplit_fields_do_not_match_parts(rows, field, text):
    db, _ = rows
    assert matches(db, field, text) == []


def test_occurrence_path_must_equal_its_representations(db):
    repo = seed_repo(db, seed_connection(db))
    spec = seed_spec(db)
    gen = seed_generation(db, repo, spec, status="building")
    rep = seed_representation(db, repo, spec, "x", path="a.py")
    seed_occurrence(db, repo, gen, rep, path="a.py")
    with pytest.raises(psycopg.errors.ForeignKeyViolation, match="occurrence_path_matches_representation"):
        seed_occurrence(db, repo, gen, rep, path="b.py")


def test_path_is_required(db):
    repo = seed_repo(db, seed_connection(db))
    spec = seed_spec(db)
    db.execute("INSERT INTO content (content_hash, body, token_count) VALUES ('\\x01', 'x', 1)")
    with pytest.raises(psycopg.errors.NotNullViolation):
        db.execute("INSERT INTO representation (repo_id, spec_id, input_hash, content_hash, header,"
                   " body_text) VALUES (%s, %s, '\\x01', '\\x01', 'h', 'x')", (repo, spec))


def test_the_migration_refuses_a_table_with_rows(empty_db):
    """No path can be derived for a row written before the column existed, so the migration stops."""
    i = next(i for i, m in enumerate(MIGRATIONS) if m.name.endswith("_representation_path_bm25.sql"))
    this = MIGRATIONS[i]
    for m in MIGRATIONS[:i]:
        empty_db.execute(sections(m)[0])
    repo = seed_repo(empty_db, seed_connection(empty_db))
    spec = seed_spec(empty_db)
    empty_db.execute("INSERT INTO content (content_hash, body, token_count) VALUES ('\\x01', 'x', 1)")
    empty_db.execute("INSERT INTO representation (repo_id, spec_id, input_hash, content_hash, header,"
                     " body_text) VALUES (%s, %s, '\\x01', '\\x01', 'h', 'x')", (repo, spec))
    with pytest.raises(psycopg.errors.RaiseException, match="representation has rows"):
        empty_db.execute(sections(this)[0])


UNICODE_BODY = "def größe_berechnen(x): return café.naïve_ä + 変数 + Ünïcode.Ström"


@pytest.fixture
def unicode_rows(db):
    repo = seed_repo(db, seed_connection(db))
    spec = seed_spec(db)
    hit = seed_representation(db, repo, spec, UNICODE_BODY, path="src/u.py")
    seed_representation(db, repo, spec, "def other(): pass", path="src/o.py")
    return db, hit


@pytest.mark.parametrize("ident", ["größe_berechnen", "café.naïve_ä", "変数", "Ünïcode.Ström"])
def test_unicode_identifiers_match_whole(unicode_rows, ident):
    """Python and Go allow Unicode identifiers (XID), so the ident fields must keep them whole."""
    db, hit = unicode_rows
    assert matches(db, "body_ident", ident) == [hit]


@pytest.mark.parametrize("fragment", ["gr", "e_berechnen", "caf", "ve_"])
def test_ascii_fragments_of_unicode_identifiers_do_not_match(unicode_rows, fragment):
    """What an ASCII-only pattern would leave of those identifiers. Matching the whole identifier is
    not enough on its own: an ASCII pattern splits the query the same way and still matches."""
    db, _ = unicode_rows
    assert matches(db, "body_ident", fragment) == []


def test_rollback_refuses_once_representations_exist(db):
    """Rollback is pre-ingestion only: dropping path would lose it, and the up section would then refuse."""
    this = next(m for m in MIGRATIONS if m.name.endswith("_representation_path_bm25.sql"))
    repo = seed_repo(db, seed_connection(db))
    rep = seed_representation(db, repo, seed_spec(db), "x", path="a.py")
    with pytest.raises(psycopg.errors.RaiseException, match="rolling back would drop their path"):
        db.execute(sections(this)[1])
    assert db.execute("SELECT path FROM representation WHERE id = %s", (rep,)).fetchone() == ("a.py",)
