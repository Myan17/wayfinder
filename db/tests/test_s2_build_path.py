"""BCR-1's additions to the S2/S6 build path: `start_line`, the repository seeds and `pad_copy`.

The first two tests need no database. The rest run against the pinned image (CI's `db` job).
"""

import psycopg
import pytest
import s6_identity as s6
from conftest import one

SPEC = {
    "model_ref": "nomic-embed-text:latest",
    "model_digest": "sha256:" + "0a" * 32,
    "runtime": "ollama 0.34.2",
    "doc_template": "search_document: {header}\n{body}",
}
BLANK = "\n" * 3  # a window that repeats inside one file


def test_line_count_is_universe_lines_rule():
    assert [s6.line_count(b) for b in ("", "a", "a\n", "a\nb", "a\nb\n", "\n\n")] == [0, 1, 1, 2, 2, 2]


def test_a_start_line_below_1_is_refused_before_any_write():
    with pytest.raises(ValueError, match="start_line must be at least 1, not 0"):
        s6.index_chunk(None, s6.stand_in, repo_id=1, generation_id=1, spec=None, start_line=0)


def build(db, repo, spec, windows):
    """One generation of `windows` [(path, start_line, body)], ready but not activated."""
    desired, claim = s6.push_and_claim(db, repo)
    gen = s6.new_generation(db, repo, spec, desired=desired, base=None)
    reps = [
        s6.index_chunk(
            db,
            s6.stand_in,
            repo_id=repo,
            generation_id=gen,
            spec=spec,
            header=f"o/n · {p}",
            body=b,
            path=p,
            start_line=s,
        )
        for p, s, b in windows
    ]
    return gen, desired, claim, reps


def lines(db, gen):
    return db.execute(
        "SELECT representation_id, path, start_line, end_line FROM occurrence WHERE generation_id = %s"
        " ORDER BY path, start_line",
        (gen,),
    ).fetchall()


@pytest.fixture
def world(db):
    conn_id = s6.seed_connection(db)
    repo = s6.seed_repository(db, connection_id=conn_id, github_repo_id=7, full_name="s2/pseudo-07")
    return db, repo, s6.capture_spec(db, **SPEC)


def test_identical_windows_of_one_file_share_a_representation_at_their_own_lines(world):
    db, repo, spec = world
    gen, *_, reps = build(db, repo, spec, [("a.py", 1, BLANK), ("a.py", 4, BLANK), ("a.py", 7, "x\ny")])
    assert reps[0] == reps[1] != reps[2]
    assert lines(db, gen) == [(reps[0], "a.py", 1, 3), (reps[0], "a.py", 4, 6), (reps[2], "a.py", 7, 8)]


def test_one_connection_holds_the_100_pseudo_repositories(db):
    conn_id = s6.seed_connection(db)
    ids = [
        s6.seed_repository(db, connection_id=conn_id, github_repo_id=n, full_name=f"s2/pseudo-{n:02d}")
        for n in range(100)
    ]
    assert one(db, "SELECT count(*) FROM connection") == 1
    rows = db.execute(
        "SELECT DISTINCT connection_id, visibility, data_class, serving_state FROM repository"
        " WHERE id = ANY(%s)",
        (ids,),
    ).fetchall()
    assert rows == [(conn_id, "private", "private", "active")]
    eligible = "SELECT count(*) FROM eligible_repo WHERE repo_id = ANY(%s) AND NOT verified_public"
    assert one(db, eligible, (ids,)) == 100  # eligible, and admitted only by a grant


def test_a_pad_copy_is_its_stored_input_at_its_sources_location(world):
    db, repo, spec = world
    gen, *_, (src, _, _) = build(db, repo, spec, [("a.py", 4, BLANK), ("a.py", 1, BLANK), ("c.py", 1, "z")])
    pad = s6.pad_copy(db, repo_id=repo, generation_id=gen, spec=spec, source=src, row=41)
    header, body, ihash, path = db.execute(
        "SELECT header, body_text, input_hash, path FROM representation WHERE id = %s", (pad,)
    ).fetchone()
    assert (header, body) == ("o/n · a.py · s2-pad:41", BLANK)
    text = s6.embedded_input(spec.doc_template, header, body)
    assert bytes(ihash) == s6.input_hash(text)  # the hash is of exactly what is stored
    vec = one(db, "SELECT embedding::text FROM vector_d768 WHERE representation_id = %s", (pad,))
    assert vec == one(db, "SELECT %s::halfvec::text", (s6.vector_text(s6.stand_in(spec, text)),))
    assert [r for r in lines(db, gen) if r[0] == pad] == [(pad, "a.py", 1, 3)]  # its first, not line 4
    assert path == "a.py"
    with pytest.raises(psycopg.errors.UniqueViolation):
        s6.pad_copy(db, repo_id=repo, generation_id=gen, spec=spec, source=src, row=41)  # a row is used once
    other = s6.new_generation(db, repo, spec, desired=99, base=None)
    with pytest.raises(ValueError, match="no occurrence in generation"):
        s6.pad_copy(db, repo_id=repo, generation_id=other, spec=spec, source=src, row=42)


def test_60000_means_60000_live_representations_after_activation(world):
    db, repo, spec = world
    gen, desired, claim, reps = build(
        db, repo, spec, [("a.py", 1, BLANK), ("a.py", 4, BLANK), ("a.py", 7, "x")]
    )
    real = len(set(reps))  # 2: the identical windows share one
    for row in range(60_000 - real):
        s6.pad_copy(db, repo_id=repo, generation_id=gen, spec=spec, source=reps[row % 3], row=row)
    s6.finish_build(db, gen)
    s6.activate(db, repo_id=repo, new=gen, base=None, desired=desired, claim=claim)
    live = "SELECT count(*) FROM {} WHERE live AND repo_id = %s AND spec_id = %s"
    assert one(db, live.format("representation"), (repo, spec.id)) == 60_000
    assert one(db, live.format("vector_d768"), (repo, spec.id)) == 60_000
    assert one(db, "SELECT chunk_count FROM generation WHERE id = %s", (gen,)) == 60_001  # 3 windows + copies
