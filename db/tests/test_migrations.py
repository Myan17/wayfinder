from conftest import MIGRATIONS, sections


def test_up_from_empty_and_from_previous_release(empty_db):
    """Every migration up from empty, all down in reverse, then up again. There is no previous release
    yet; the down-up cycle stands in for it, and proves each down removes what its up created."""
    before = _relations(empty_db)   # the ParadeDB template already carries postgis's tables and views
    for m in MIGRATIONS:
        empty_db.execute(sections(m)[0])
    assert _relations(empty_db) > before
    for m in reversed(MIGRATIONS):
        empty_db.execute(sections(m)[1])
    assert _relations(empty_db) == before
    for m in MIGRATIONS:
        empty_db.execute(sections(m)[0])


def test_pinned_extensions_present(db):
    names = {r[0] for r in db.execute("SELECT extname FROM pg_extension")}
    assert {"vector", "pg_search"} <= names


def _relations(conn) -> set[str]:
    return {r[0] for r in conn.execute(
        "SELECT c.relname FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace "
        "WHERE n.nspname = 'public' AND c.relkind IN ('r','v')"
    )}
