"""Spike S6, rules S6-1 to S6-3 and the v0.2 negative control (ADR-0005), on the stand-in embedder.

Every rule runs for both pairs: B differs from A only in model_digest, or only in doc_template.
"""

import pytest
import s6_identity as s6
from conftest import one, seed_connection, seed_repo

PAIRS = {
    "digest": ({"model_digest": "sha256:aaaa"}, {"model_digest": "sha256:bbbb"}),
    "template": (
        {"doc_template": "search_document: {header}\n{body}"},
        {"doc_template": "passage: {header}\n\n{body}"},
    ),
}
BASE = {
    "model_ref": "nomic-embed-text",
    "model_digest": "sha256:aaaa",
    "runtime": "ollama/0.34.2",
    "doc_template": "search_document: {header}\n{body}",
}


class Counting:
    """The stand-in, counting calls: S6-3 is stated in embedder calls."""

    def __init__(self):
        self.calls = 0

    def __call__(self, spec, text):
        self.calls += 1
        return s6.stand_in(spec, text)


@pytest.fixture(params=sorted(PAIRS))
def world(request, db):
    """A's generation built with T, then B's generation built with T. Activation is the next PR's."""
    a_fields, b_fields = PAIRS[request.param]
    repo = seed_repo(db, seed_connection(db))
    a = s6.capture_spec(db, **{**BASE, **a_fields})
    b = s6.capture_spec(db, **{**BASE, **b_fields})
    embed = Counting()
    gen_a = s6.new_generation(db, repo, a, desired=1, base=None)
    rep_a = s6.index_chunk(db, embed, repo_id=repo, generation_id=gen_a, spec=a)
    w = dict(pair=request.param, db=db, repo=repo, a=a, b=b, embed=embed, gen_a=gen_a, rep_a=rep_a)
    w["snapshot"] = _rows(db, rep_a)
    w["gen_b"] = s6.new_generation(db, repo, b, desired=2, base=gen_a)
    w["calls_before_b"] = embed.calls
    w["rep_b"] = s6.index_chunk(db, embed, repo_id=repo, generation_id=w["gen_b"], spec=b)
    return w


def _rows(db, rep):
    """A's representation and vector rows, every column, as text."""
    return (
        db.execute("SELECT row_to_json(r)::text FROM representation r WHERE id = %s", (rep,)).fetchone(),
        db.execute(
            "SELECT row_to_json(v)::text, embedding::text FROM vector_d768 v WHERE representation_id = %s",
            (rep,),
        ).fetchone(),
    )


def test_s6_1_a_second_specification_creates_new_rows(world):
    db, repo = world["db"], world["repo"]
    assert one(db, "SELECT count(*) FROM content") == 1
    reps = db.execute(
        "SELECT spec_id, input_hash FROM representation WHERE repo_id = %s ORDER BY spec_id", (repo,)
    ).fetchall()
    assert [r[0] for r in reps] == sorted([world["a"].id, world["b"].id])
    assert one(db, "SELECT count(*) FROM vector_d768 WHERE repo_id = %s", (repo,)) == 2
    assert (reps[0][1] == reps[1][1]) is (world["pair"] == "digest")


def test_s6_2_the_first_specifications_rows_are_untouched_before_activation(world):
    assert _rows(world["db"], world["rep_a"]) == world["snapshot"]


def test_s6_3_reuse_never_crosses_specifications(world):
    db, repo, embed, a = world["db"], world["repo"], world["embed"], world["a"]
    assert world["embed"].calls - world["calls_before_b"] == 1  # B's first build of T
    reps = one(db, "SELECT count(*) FROM representation")
    occurrences = one(db, "SELECT count(*) FROM occurrence")
    again = s6.new_generation(db, repo, a, desired=99, base=world["gen_a"])
    before = embed.calls
    assert s6.index_chunk(db, embed, repo_id=repo, generation_id=again, spec=a) == world["rep_a"]
    assert embed.calls == before
    assert one(db, "SELECT count(*) FROM representation") == reps
    assert one(db, "SELECT count(*) FROM occurrence") == occurrences + 1
    s6.index_chunk(
        db,
        embed,
        repo_id=repo,
        generation_id=again,
        spec=a,
        header=s6.T_HEADER + " (moved)",
        path="wayfinder/moved.py",
    )
    assert embed.calls == before + 1


@pytest.mark.parametrize("pair", sorted(PAIRS))
def test_the_v02_control_fails_s6_1(db, pair):
    """v0.2's (repo_id, content_hash) key with ON CONFLICT DO NOTHING keeps A's vector and loses B's.
    If this ever passed S6-1, the prototype could not tell the designs apart (ADR-0005: an error)."""
    db.execute(
        "CREATE TABLE v02_representation (repo_id bigint, content_hash bytea, spec text,"
        " embedding halfvec(768), PRIMARY KEY (repo_id, content_hash))"
    )
    a_fields, b_fields = PAIRS[pair]
    for fields in (a_fields, b_fields):
        spec = s6.Spec(
            0,
            BASE["model_ref"],
            **{k: v for k, v in {**BASE, **fields}.items() if k in ("model_digest", "doc_template")},
        )
        text = s6.embedded_input(spec.doc_template, s6.T_HEADER, s6.T_BODY)
        db.execute(
            "INSERT INTO v02_representation VALUES (1, sha256(%s::bytea), %s, %s::halfvec)"
            " ON CONFLICT DO NOTHING",
            (s6.T_BODY.encode(), repr(fields), s6.vector_text(s6.stand_in(spec, text))),
        )
    assert db.execute("SELECT spec FROM v02_representation").fetchall() == [(repr(a_fields),)]


def test_a_specification_is_captured_once_per_identity_key(db):
    a = s6.capture_spec(db, **BASE)
    assert s6.capture_spec(db, **BASE) == a
    assert s6.capture_spec(db, **{**BASE, "model_digest": "sha256:cccc"}).id != a.id
    assert one(db, "SELECT count(*) FROM embedding_spec") == 2


def test_the_embedded_input_substitutes_once_and_hashes_its_utf8_bytes():
    assert s6.embedded_input("d: {header}|{body}", "h {body}", "x{header}y") == "d: h {body}|x{header}y"
    # SHA-256 of "é" as UTF-8 (c3 a9); its Latin-1 byte (e9) would give de2e331d…
    assert s6.input_hash("é").hex() == "4a99557e4033c3539de2eb65472017cad5f9557f7a0625a09f1c3f6e2ba69c4c"
