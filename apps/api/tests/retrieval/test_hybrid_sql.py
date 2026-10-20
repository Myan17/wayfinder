"""The canonical two-leg query's results and authorization (ADR-0007 Amendment 1, step 3).

No plan is captured or inspected here: plans are step 4's, after this query is merged and frozen."""

from datetime import timedelta

import pytest

from wayfinder.retrieval import hybrid_sql as h

from .conftest import DIM, axis, run, scope


def test_only_authorized_repositories_are_returned(world):
    s = world.spec("sha256:a")
    granted, ungranted, public = world.repo(s), world.repo(s), world.repo(s, public=True)
    for repo, gen in (granted, ungranted, public):
        world.add(repo, gen, s, "def parse_widget(): pass", f"src/w{repo}.py", vec=0)
    rows = run(world.db, scope(granted=[granted[0]], public=[public[0]]), vectors={s: axis(0)})
    assert {r["repo_id"] for r in rows} == {granted[0], public[0]}


def test_rows_not_live_or_not_in_the_active_generation_are_excluded(world):
    s = world.spec("sha256:a")
    repo, gen = world.repo(s)
    retired = world.generation(repo, s, "retired")
    keep = world.add(repo, gen, s, "def parse_widget(): pass", "src/a.py", vec=0)
    world.add(repo, gen, s, "def parse_widget_old(): pass", "src/b.py", vec=0, live=False)
    world.add(repo, retired, s, "def parse_widget_gone(): pass", "src/c.py", vec=0)
    rows = run(world.db, scope(granted=[repo]), vectors={s: axis(0)})
    assert [r["representation_id"] for r in rows] == [keep]


def test_fused_score_is_rrf_over_both_legs(world):
    s = world.spec("sha256:a")
    repo, gen = world.repo(s)
    both = world.add(repo, gen, s, "def parse_widget(): pass", "src/a.py", vec=0)
    world.add(repo, gen, s, "def unrelated(): pass", "src/b.py", vec=1)
    rows = run(world.db, scope(granted=[repo]), vectors={s: axis(0)})
    top = rows[0]
    assert top["representation_id"] == both and (top["lexical_rank"], top["dense_rank"]) == (1, 1)
    for r in rows:
        ranks = [x for x in (r["lexical_rank"], r["dense_rank"]) if x is not None]
        assert float(r["fused"]) == pytest.approx(sum(1 / (h.RRF_K + x) for x in ranks))
    other = next(r for r in rows if r["representation_id"] != both)
    assert other["lexical_rank"] is None and other["dense_rank"] == 2


def test_query_grammar_in_the_text_is_only_text(world):
    s = world.spec("sha256:a")
    repo, gen = world.repo(s)
    world.add(repo, gen, s, "def parse_widget(): pass", "src/a.py", vec=0)
    rows = run(world.db, scope(granted=[repo]), text='widget OR body_text:* AND "unterminated ~2 ^9',
               vectors={s: axis(0)})
    assert rows and rows[0]["lexical_rank"] == 1


def test_one_dense_leg_per_specification(world):
    s1, s2 = world.spec("sha256:a"), world.spec("sha256:b")
    (r1, g1), (r2, g2) = world.repo(s1), world.repo(s2)
    a = world.add(r1, g1, s1, "def alpha(): pass", "src/a.py", vec=0)
    b = world.add(r2, g2, s2, "def beta(): pass", "src/b.py", vec=0)
    query = h.build("nothing", {s2: axis(0), s1: axis(0)}, scope(granted=[r1, r2]), k=10)
    assert "dense_0" in query.sql and "dense_1" in query.sql
    assert (query.params["spec_0"], query.params["spec_1"]) == tuple(sorted((s1, s2)))
    rows = h.execute(world.db, query, scope(granted=[r1, r2]))
    assert {r["representation_id"]: r["dense_rank"] for r in rows} == {a: 1, b: 1}


def test_no_caller_value_reaches_the_sql_text():
    vector = [0.123456] * DIM
    query = h.build("xyzzy_secret_term", {7: vector}, scope(granted=[98765]), k=5)
    assert "xyzzy" not in query.sql and "98765" not in query.sql and "0.123456" not in query.sql
    assert query.params["q"] == "xyzzy_secret_term" and query.params["spec_0"] == 7


def test_a_vector_of_the_wrong_dimension_is_refused():
    with pytest.raises(ValueError, match="dimensions"):
        h.build("x", {1: [0.0] * 3}, scope(granted=[1]), k=5)


def test_rows_are_asserted_again_if_the_sql_filter_were_bypassed(world, monkeypatch):
    """9.1.5's second layer: with the predicate replaced by `true`, execute must raise, not serve."""
    from wayfinder.authz.predicate import AuthorizationViolation

    s = world.spec("sha256:a")
    granted, other = world.repo(s), world.repo(s)
    for repo, gen in (granted, other):
        world.add(repo, gen, s, "def parse_widget(): pass", f"src/w{repo}.py", vec=0)
    monkeypatch.setattr(h, "sql_predicate", lambda *a, **kw: ("true", {}))
    with pytest.raises(AuthorizationViolation):
        run(world.db, scope(granted=[granted[0]]), vectors={s: axis(0)})


def test_a_path_alone_is_enough_for_the_lexical_leg(world):
    s = world.spec("sha256:a")
    repo, gen = world.repo(s)
    hit = world.add(repo, gen, s, "x = 1", "src/widget_parser.py", vec=1)
    world.add(repo, gen, s, "y = 2", "src/other.py", vec=1)
    world.db.execute("UPDATE representation SET header = 'h'")      # the path is not in the header here
    rows = run(world.db, scope(granted=[repo]), text="widget_parser", vectors={s: axis(0)})
    assert [r["representation_id"] for r in rows if r["lexical_rank"] is not None] == [hit]


class Recorder:
    """A connection that records the transaction and each statement, by kind."""

    def __init__(self, conn):
        self.conn, self.seen = conn, []

    def transaction(self):
        self.seen.append("BEGIN")
        return self.conn.transaction()

    def execute(self, sql, params=None):
        self.seen.append(sql if sql == h.SESSION else "query")
        return self.conn.execute(sql, params)


def test_the_relaxed_scan_is_set_inside_the_querys_transaction(world):
    s = world.spec("sha256:a")
    repo, _ = world.repo(s)
    conn = Recorder(world.db)
    h.execute(conn, h.build("x", {s: axis(0)}, scope(granted=[repo]), k=5), scope(granted=[repo]))
    assert conn.seen == ["BEGIN", h.SESSION, "query"]


@pytest.mark.parametrize("when", ["at build", "before the statement", "during the statement"])
def test_an_expired_lease_returns_nothing(world, when):
    """Fail closed at every check: when building, just before the statement runs, and after its rows
    are fetched. A statement built before expiry must not serve rows after it."""
    s = world.spec("sha256:a")
    repo, gen = world.repo(s)
    world.add(repo, gen, s, "def parse_widget(): pass", "src/w.py", vec=0)
    sc = scope(granted=[repo], expires_in=timedelta(minutes=5))
    held, expired = sc.expires_at - timedelta(seconds=1), sc.expires_at
    query = h.build("widget", {s: axis(0)}, sc, k=5, now=expired if when == "at build" else held)
    assert when == "at build" or h.execute(world.db, query, sc, clock=lambda: held)  # rows while it holds
    ticks = {"at build": [held, held], "before the statement": [expired],
             "during the statement": [held, expired]}
    conn = Recorder(world.db)
    assert h.execute(conn, query, sc, clock=iter(ticks[when]).__next__) == []
    assert ("query" in conn.seen) == (when != "before the statement")
