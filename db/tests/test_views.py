from conftest import (
    MIGRATIONS,
    ROOT,
    seed_connection,
    seed_generation,
    seed_occurrence,
    seed_repo,
    seed_representation,
    seed_spec,
)


def _block(text: str, name: str) -> str:
    return text.split(f"-- view:{name}:begin\n", 1)[1].split(f"-- view:{name}:end", 1)[0]


def test_view_files_match_migration():
    migration = MIGRATIONS[-1].read_text()
    for name in ("eligible_repo", "retrieval_rows"):
        body = "".join(
            line for line in (ROOT / "db" / "views" / f"{name}.sql").read_text().splitlines(keepends=True)
            if not line.startswith("-- ")
        )
        assert body == _block(migration, name), f"db/views/{name}.sql drifted from the migration"


def test_eligible_repo_expiry(db):
    live_conn = seed_connection(db)
    ok = seed_repo(db, live_conn)
    lapsed = seed_repo(db, live_conn, valid="-1 second")
    denied = seed_repo(db, live_conn, serving_state="denied")
    private = seed_repo(db, live_conn, visibility="private")
    dead_conn = seed_connection(db, valid="-1 second")
    under_dead = seed_repo(db, dead_conn)

    rows = dict(db.execute("SELECT repo_id, verified_public FROM eligible_repo").fetchall())
    assert rows == {ok: True, private: False}
    assert lapsed not in rows and denied not in rows and under_dead not in rows


def test_retrieval_rows_active_generation_only_and_predicate_applies(db):
    c = seed_connection(db)
    pub, priv = seed_repo(db, c), seed_repo(db, c, visibility="private")
    s = seed_spec(db)
    rows = {}
    for repo in (pub, priv):
        old = seed_generation(db, repo, s, status="retired", n=1)
        new = seed_generation(db, repo, s, status="active", n=2)
        stale = seed_representation(db, repo, s, f"stale{repo}", live=False)
        cur = seed_representation(db, repo, s, f"cur{repo}", live=True)
        seed_occurrence(db, repo, old, stale)
        seed_occurrence(db, repo, new, cur)
        # The live representation also occurs in the retired generation, at a path it no longer has.
        # `live` alone cannot hide that row; only the active-generation join can.
        db.execute("INSERT INTO occurrence (repo_id, generation_id, representation_id, path, blob_sha,"
                   " start_line, end_line) VALUES (%s, %s, %s, 'moved-away.py', 'b', 1, 2)", (repo, old, cur))
        db.execute("UPDATE repository SET active_generation_id = %s WHERE id = %s", (new, repo))
        rows[repo] = cur

    visible = set(db.execute("SELECT representation_id, path FROM retrieval_rows").fetchall())
    assert visible == {(rep, "a.py") for rep in rows.values()}

    # authz's row predicate (apps/api/wayfinder/authz/predicate.py) applied unchanged to the view.
    q = ("SELECT rr.representation_id FROM retrieval_rows rr JOIN eligible_repo eligible "
         "ON eligible.repo_id = rr.repo_id "
         "WHERE (rr.live AND (eligible.verified_public OR rr.repo_id = ANY(%(granted_repo_ids)s)))")
    assert {r[0] for r in db.execute(q, {"granted_repo_ids": []})} == {rows[pub]}
    assert {r[0] for r in db.execute(q, {"granted_repo_ids": [priv]})} == set(rows.values())
