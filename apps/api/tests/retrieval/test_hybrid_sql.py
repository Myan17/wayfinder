"""The canonical two-leg query's results, authorization and determinism (ADR-0007 Amendment 1, step 3).

No plan is captured or inspected here: plans are step 4's, after this query is merged and frozen."""

import random
from datetime import UTC, datetime, timedelta

import pytest

from wayfinder.authz.interface import AuthorizedScope, Principal, PrincipalKind
from wayfinder.retrieval import hybrid_sql as h

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

    def __init__(self, db):
        self.db = db
        self.conn_id = db.execute(
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
def world(pinned, db):
    return World(db)


def run(db, sc, text="widget", vectors=None, k=50):
    query = h.build(text, vectors or {}, sc, k=k)
    return h.execute(db, query, sc)


def test_only_authorized_repositories_are_returned(world):
    s = world.spec("sha256:a")
    granted, ungranted, public = world.repo(s), world.repo(s), world.repo(s, public=True)
    for repo, gen in (granted, ungranted, public):
        world.add(repo, gen, s, "def parse_widget(): pass", f"src/w{repo}.py", vec=0)
    rows = run(world.db, scope(granted=[granted[0]], public=[public[0]]), vectors={s: axis(0)})
    assert {r["repo_id"] for r in rows} == {granted[0], public[0]}


def test_an_expired_scope_returns_nothing(world):
    s = world.spec("sha256:a")
    repo, gen = world.repo(s)
    world.add(repo, gen, s, "def parse_widget(): pass", "src/w.py", vec=0)
    assert run(world.db, scope(granted=[repo], expires_in=timedelta(seconds=-1)), vectors={s: axis(0)}) == []


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


def test_ties_break_on_the_pinned_keys_whatever_the_insertion_order(world):
    """Identical text and identical vectors tie on score and on distance, so every rank comes from
    (repo_id, path, representation_id) and the final order adds start_line."""
    s = world.spec("sha256:a")
    repos = [world.repo(s) for _ in range(3)]
    placements = [(repo, gen, path) for repo, gen in repos for path in ("src/b.py", "src/a.py")]
    random.Random(7).shuffle(placements)
    for repo, gen, path in placements:
        world.add(repo, gen, s, "def parse_widget(): pass", path, vec=0)
    rows = run(world.db, scope(granted=[r for r, _ in repos]), vectors={s: axis(0)})
    keys = [(r["repo_id"], r["path"]) for r in rows]
    assert keys == sorted(keys) and len(keys) == 6
    assert [r["lexical_rank"] for r in rows] == [1, 2, 3, 4, 5, 6]
    assert [r["dense_rank"] for r in rows] == [1, 2, 3, 4, 5, 6]
    assert rows == run(world.db, scope(granted=[r for r, _ in repos]), vectors={s: axis(0)})


def test_at_most_three_passages_per_file(world):
    s = world.spec("sha256:a")
    repo, gen = world.repo(s)
    for line in (50, 10, 40, 20, 30):
        world.add(repo, gen, s, f"def parse_widget_{line}(): pass", "src/a.py", vec=0, start_line=line)
    world.add(repo, gen, s, "def parse_widget(): pass", "src/b.py", vec=0)
    rows = run(world.db, scope(granted=[repo]), vectors={s: axis(0)})
    assert sum(r["path"] == "src/a.py" for r in rows) == h.PER_FILE_CAP
    assert sum(r["path"] == "src/b.py" for r in rows) == 1


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


def test_the_lexical_cut_keeps_the_first_hundred_by_the_tie_key(world):
    """102 identical passages tie on score, so the leg's LIMIT keeps the first 100 by (repo_id, path, id)."""
    s = world.spec("sha256:a")
    repo, gen = world.repo(s)
    reps = {world.add(repo, gen, s, "def parse_widget(): pass", f"src/f{n:03}.py", vec=1): f"src/f{n:03}.py"
            for n in random.Random(3).sample(range(102), 102)}
    rows = run(world.db, scope(granted=[repo]), vectors={s: axis(0)}, k=500)
    kept = {r["representation_id"] for r in rows if r["lexical_rank"] is not None}
    assert kept == {rep for rep, path in reps.items() if path < "src/f100.py"}


@pytest.mark.parametrize("a_first", [True, False])
def test_equal_fused_scores_order_by_repo_path_and_line(world, a_first):
    """A ranks first lexically and second densely, B the reverse, so their fused scores are equal and
    only the final key orders them: same repository, so path decides, whichever was inserted first."""
    s = world.spec("sha256:a")
    repo, gen = world.repo(s)
    tilted = [0.0] * DIM
    tilted[0], tilted[1] = 0.6, 0.8

    def add_a():
        return world.add(repo, gen, s, "def parse_widget(): pass", "src/a.py", vec=tilted)

    def add_b():
        return world.add(repo, gen, s, "def parse_widget(): pass", "src/b.py", vec=0)

    if a_first:
        a, b = add_a(), add_b()
    else:
        b, a = add_b(), add_a()
    rows = run(world.db, scope(granted=[repo]), vectors={s: axis(0)})
    by = {r["representation_id"]: r for r in rows}
    assert (by[a]["lexical_rank"], by[a]["dense_rank"]) == (1, 2)
    assert (by[b]["lexical_rank"], by[b]["dense_rank"]) == (2, 1)
    assert by[a]["fused"] == by[b]["fused"]
    assert [r["representation_id"] for r in rows] == [a, b]


def test_a_path_alone_is_enough_for_the_lexical_leg(world):
    s = world.spec("sha256:a")
    repo, gen = world.repo(s)
    hit = world.add(repo, gen, s, "x = 1", "src/widget_parser.py", vec=1)
    world.add(repo, gen, s, "y = 2", "src/other.py", vec=1)
    world.db.execute("UPDATE representation SET header = 'h'")      # the path is not in the header here
    rows = run(world.db, scope(granted=[repo]), text="widget_parser", vectors={s: axis(0)})
    assert [r["representation_id"] for r in rows if r["lexical_rank"] is not None] == [hit]


def test_the_relaxed_scan_is_set_inside_the_querys_transaction(world):
    s = world.spec("sha256:a")
    repo, _ = world.repo(s)
    seen = []

    class Spy:
        def __init__(self, conn):
            self.conn = conn

        def transaction(self):
            seen.append("BEGIN")
            return self.conn.transaction()

        def execute(self, sql, params=None):
            seen.append(sql if sql == h.SESSION else "query")
            return self.conn.execute(sql, params)

    h.execute(Spy(world.db), h.build("x", {s: axis(0)}, scope(granted=[repo]), k=5), scope(granted=[repo]))
    assert seen == ["BEGIN", h.SESSION, "query"]
