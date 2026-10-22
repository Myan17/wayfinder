"""The S3-6 plan harness (ADR-0007 Amendment 1, step 4): its checks, and the mutation checks that show
each can fail. The 7,175 fixture is built once for the module; each mutation runs inside a transaction
that is rolled back, so the next test sees the fixture unchanged."""

import uuid

import psycopg
import pytest

from wayfinder.retrieval import s3_6

from .conftest import DSN


def node(kind, relation=None, **extra):
    return {"Node Type": kind, **({"Relation Name": relation} if relation else {}), **extra}


def tree(*children):
    return {"Node Type": "Limit", "Plans": [{"Node Type": "Hash Join", "Plans": list(children)}]}


BM25 = node("Custom Scan", "representation", **{"Custom Plan Provider": "ParadeDB Base Scan"})
HNSW = node("Index Scan", "vector_d768", **{"Index Name": "vec768_hnsw"})


def test_lexical_check_reads_the_whole_tree():
    assert s3_6.check_lexical(tree(BM25, HNSW))["passed"]
    assert not s3_6.check_lexical(tree(HNSW))["served"]
    seq = s3_6.check_lexical(tree(BM25, node("Seq Scan", "representation", Alias="rep_2")))
    assert seq == {"passed": False, "served": True, "seq_scans": ["rep_2"]}
    other = node("Custom Scan", "representation", **{"Custom Plan Provider": "Other"})
    assert not s3_6.check_lexical(tree(other))["served"]


def test_dense_check_needs_the_hnsw_index_and_no_seq_scan():
    assert s3_6.check_dense(tree(BM25, HNSW))["passed"]
    btree = node("Index Scan", "vector_d768", **{"Index Name": "vec768_repo"})
    assert not s3_6.check_dense(tree(btree))["served"]
    assert not s3_6.check_dense(tree(HNSW, node("Seq Scan", "vector_d768")))["passed"]


def test_rows_check_counts_each_leg_and_every_repository():
    rows = [{"repo_id": 1, "lexical_rank": 1, "dense_rank": None},
            {"repo_id": 2, "lexical_rank": None, "dense_rank": 1}]
    assert s3_6.check_rows(rows, {1, 2})["passed"]
    assert s3_6.check_rows(rows, {1}) == {"passed": False, "lexical": 1, "dense": 1, "rows": 2,
                                          "outside": [2]}
    assert not s3_6.check_rows(rows[:1], {1, 2})["passed"]
    assert not s3_6.check_rows(rows[1:], {1, 2})["passed"]


def test_the_fixture_text_matches_five_rows_per_repository():
    hits = [r for r in range(1_000) if any(s3_6.TERM in t for t in s3_6.texts(r, r % s3_6.REPOS))]
    assert len(hits) == s3_6.MATCHES_PER_REPO * s3_6.REPOS
    for field in range(3):  # header, body and path each carry it for some row
        assert any(s3_6.TERM in s3_6.texts(r, 0)[field] for r in hits)


def test_the_statement_is_prepared_with_numbered_parameters():
    sc = s3_6.scope({7})
    statement, values = s3_6.prepared(s3_6.h.build("x", {3: [0.0] * s3_6.h.DIMENSION}, sc, k=5))
    assert "%(" not in statement and "$1" in statement
    assert "x" in values and 3 in values and 5 in values


@pytest.fixture(scope="module")
def plans():
    try:
        psycopg.connect(DSN or "", connect_timeout=2).close()
    except psycopg.OperationalError:
        pytest.skip("the pinned database is not reachable; make db-test runs these")
    name = f"wf_s3_6_{uuid.uuid4().hex[:12]}"
    with psycopg.connect(DSN, autocommit=True) as admin:
        admin.execute(f'CREATE DATABASE "{name}"')
    try:
        with psycopg.connect(psycopg.conninfo.make_conninfo(DSN, dbname=name), autocommit=True) as conn:
            for m in s3_6.MIGRATIONS:
                conn.execute(m.read_text().split("-- migrate:up", 1)[1].split("-- migrate:down")[0])
            yield conn, s3_6.build_fixture(conn, s3_6.SIZES[0])
    finally:
        with psycopg.connect(DSN, autocommit=True) as admin:
            admin.execute(f'DROP DATABASE "{name}" WITH (FORCE)')


def under(conn, ddl, *args, **kw):
    """One case with `ddl` applied, in a transaction that is always rolled back."""
    with conn.transaction(force_rollback=True):
        conn.execute(ddl)
        return s3_6.case(conn, *args, **kw)


def test_dropping_rep_bm25_fails_s3_6a(plans):
    conn, fx = plans
    assert s3_6.case(conn, fx, 100, "force_custom_plan")["S3-6a"]["served"]
    out = under(conn, "DROP INDEX rep_bm25", fx, 100, "force_custom_plan")
    assert not out["S3-6a"]["passed"] and not out["S3-6a"].get("served")


def test_dropping_vec768_hnsw_fails_s3_6b(plans):
    conn, fx = plans
    assert s3_6.case(conn, fx, 100, "force_custom_plan")["S3-6b"]["served"]
    out = under(conn, "DROP INDEX vec768_hnsw", fx, 100, "force_custom_plan")
    assert not out["S3-6b"]["passed"] and not out["S3-6b"].get("served")


def test_a_query_text_that_matches_nothing_fails_s3_6d(plans):
    conn, fx = plans
    assert s3_6.case(conn, fx, 10, "force_generic_plan")["S3-6d"]["passed"]
    out = s3_6.case(conn, fx, 10, "force_generic_plan", text="nothingmatchesthis")
    assert out["S3-6d"]["lexical"] == 0 and not out["S3-6d"]["passed"]


def test_a_grant_the_harness_does_not_count_fails_s3_6d(plans):
    conn, fx = plans
    extra = fx.repo_ids[-1]
    out = s3_6.case(conn, fx, 10, "force_generic_plan", extra=extra)
    assert out["S3-6d"]["outside"] == [extra] and not out["S3-6d"]["passed"]


def test_every_case_is_captured_with_its_text_plan(plans):
    conn, fx = plans
    cases = [s3_6.case(conn, fx, g, m) for g in s3_6.SELECTIVITIES for m in s3_6.MODES]
    assert len(cases) == 6 and all("error" not in c and c["plan_text"] for c in cases)
    assert s3_6.verdict(cases)["checks"]["S3-6e"] and s3_6.verdict(cases)["checks"]["S3-6d"]
