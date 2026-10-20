"""The canonical two-leg query's ordering (ADR-0007 Amendment 1, step 3b). Every component of every
pinned key is exercised so that dropping, reordering or reversing it fails a test:

    lexical cut and ranks   score desc, repo_id, path, representation id
    dense ranks             exact distance asc, repo_id, path, representation id
    per-file cap            fused desc, start_line, representation_id
    final order             fused desc, repo_id, path, start_line, representation_id

Texts have equal length and differ only in how often the query term occurs, so BM25 order is
deliberate. Representation ids are explicit and inserted in reverse, so a sort that lost its id key
cannot pass on insertion order. Equal fused scores come from pairs whose lexical and dense ranks are
swapped (1 and 2, 2 and 1). No plan is captured or inspected here: plans are step 4's."""

import math
import random

import pytest

from wayfinder.retrieval import hybrid_sql as h

from .conftest import DIM, axis, run, scope


def text(hits: int) -> str:
    """Four tokens, `hits` of them the query term."""
    return " ".join(["widget"] * hits + ["filler"] * (4 - hits))


def toward(c: float) -> list[float]:
    """A unit vector at cosine `c` from axis 0, so its distance to the query is 1 - c."""
    v = [0.0] * DIM
    v[0], v[1] = c, math.sqrt(1 - c * c)
    return v


def put(world, repo, gen, spec, rep_id, path, *, hits=1, c=0.5, lines=(1,)):
    db = world.db
    body = f"{text(hits)} #{rep_id}"   # distinct content; the suffix is one more equal-length token
    db.execute("INSERT INTO content (content_hash, body, token_count) VALUES (%s, %s, 1)",
               (body.encode(), body))
    db.execute("INSERT INTO representation (id, repo_id, spec_id, input_hash, content_hash, header,"
               " body_text, path, live) VALUES (%s, %s, %s, %s, %s, 'h', %s, %s, true)",
               (rep_id, repo, spec, body.encode(), body.encode(), body, path))
    db.execute("INSERT INTO vector_d768 (representation_id, repo_id, spec_id, live, embedding)"
               " VALUES (%s, %s, %s, true, %s::halfvec)", (rep_id, repo, spec, h._vector(toward(c))))
    for line in lines:
        db.execute("INSERT INTO occurrence (repo_id, generation_id, representation_id, path, blob_sha,"
                   " start_line, end_line) VALUES (%s, %s, %s, %s, 'b', %s, %s)",
                   (repo, gen, rep_id, path, line, line + 1))
    return rep_id


@pytest.fixture
def two_repos(world):
    s = world.spec("sha256:a")
    (r1, g1), (r2, g2) = world.repo(s), world.repo(s)
    assert r1 < r2
    return world, s, (r1, g1), (r2, g2)


def test_each_leg_ranks_by_its_key_before_rrf(two_repos):
    """Score or distance first, then repo_id, then path, then id. The best row is in the later
    repository and the last path, and the ids disagree with every other component."""
    world, s, (r1, g1), (r2, g2) = two_repos
    for rep_id, (repo, gen), path, hits, c in [
        (1002, (r1, g1), "a.py", 1, 0.5),       # inserted before 1001
        (1001, (r1, g1), "a.py", 1, 0.5),
        (999, (r1, g1), "b.py", 1, 0.5),        # lowest id, second path
        (1000, (r2, g2), "a.py", 1, 0.5),
        (5000, (r2, g2), "z.py", 3, 0.9),       # best score and nearest vector
    ]:
        put(world, repo, gen, s, rep_id, path, hits=hits, c=c)
    rows = run(world.db, scope(granted=[r1, r2]), vectors={s: axis(0)})
    expected = {5000: 1, 1001: 2, 1002: 3, 999: 4, 1000: 5}
    assert {r["representation_id"]: r["lexical_rank"] for r in rows} == expected
    assert {r["representation_id"]: r["dense_rank"] for r in rows} == expected
    assert rows[0]["representation_id"] == 5000        # the final order leads with fused


def test_the_lexical_cut_keeps_the_first_hundred_by_its_key(two_repos):
    """103 lexical matches, so the leg's LIMIT drops 3. Kept: the best row (scored above the rest
    though it sorts last by repo and path), then r1's 99 tied rows by path, and of the two rows that
    share r1's last kept path, the lower id. Dropped: the other one of that pair, and r2's tied rows."""
    world, s, (r1, g1), (r2, g2) = two_repos
    paths = [f"p{n:03}.py" for n in range(98)] + ["p098.py", "p098.py"]
    ids = random.Random(5).sample(range(2000, 3000), 100)
    low, high = sorted(ids[98:])
    ids[98:] = [high, low]                                   # the higher id of the pair goes in first
    for rep_id, path in zip(ids, paths, strict=True):
        put(world, r1, g1, s, rep_id, path)
    put(world, r2, g2, s, 1, "p000.py")
    put(world, r2, g2, s, 2, "p001.py")
    best = put(world, r2, g2, s, 9000, "z.py", hits=3)
    rows = run(world.db, scope(granted=[r1, r2]), vectors={s: axis(0)}, k=500)
    kept = {r["representation_id"] for r in rows if r["lexical_rank"] is not None}
    assert kept == {best, *ids[:98], low}


def swapped_pair(world, s, first, second):
    """`first` sorts before `second` on the lexical tie key and `second` is nearer, so their ranks
    are (1, 2) and (2, 1) and their fused scores are equal. Each is (rep_id, (repo, gen), path, lines);
    `second` is inserted first."""
    (b_id, (b_repo, b_gen), b_path, b_lines), (a_id, (a_repo, a_gen), a_path, a_lines) = second, first
    put(world, b_repo, b_gen, s, b_id, b_path, c=0.9, lines=b_lines)
    put(world, a_repo, a_gen, s, a_id, a_path, c=0.5, lines=a_lines)


@pytest.mark.parametrize("decides", ["repo_id", "path", "start_line", "representation_id"])
def test_equal_fused_scores_follow_the_final_key(two_repos, decides):
    """Each case ties every earlier component of the final key and makes the named one decide,
    against the order of every later component."""
    world, s, one, two = two_repos
    first, second = {
        "repo_id": ((2000, one, "z.py", (9,)), (1999, two, "a.py", (1,))),
        "path": ((2001, one, "a.py", (9,)), (2000, one, "b.py", (1,))),
        "start_line": ((2000, one, "a.py", (2,)), (2001, one, "a.py", (1,))),
        "representation_id": ((2000, one, "a.py", (1,)), (2001, one, "a.py", (1,))),
    }[decides]
    if decides == "start_line":       # 2000 is lexically first by id; 2001 has the earlier line
        first, second = second, first
        put(world, *first[1], s, first[0], first[2], c=0.9, lines=first[3])
        put(world, *second[1], s, second[0], second[2], c=0.5, lines=second[3])
    else:
        swapped_pair(world, s, first, second)
    rows = run(world.db, scope(granted=[one[0], two[0]]), vectors={s: axis(0)})
    assert rows[0]["fused"] == rows[1]["fused"]
    assert [r["representation_id"] for r in rows] == [first[0], second[0]]


@pytest.mark.parametrize("decides", ["start_line", "representation_id"])
def test_the_per_file_cap_keeps_the_first_three_by_its_key(two_repos, decides):
    """Four passages in one file. Two lead on fused score but sit on the last lines; the other two
    tie on fused score at the cap's boundary, and the named component chooses which one is kept. A
    passage in another path, and one at the same path in another repository, are not capped."""
    world, s, (r1, g1), (r2, g2) = two_repos
    elsewhere = {put(world, r1, g1, s, 10, "b.py", c=0.1), put(world, r2, g2, s, 11, "a.py", c=0.1)}
    put(world, r1, g1, s, 3000, "a.py", hits=3, c=0.99, lines=(90,))
    put(world, r1, g1, s, 3001, "a.py", hits=2, c=0.95, lines=(80,))
    if decides == "start_line":       # the later line has the lower id
        put(world, r1, g1, s, 3002, "a.py", c=0.8, lines=(2,))
        keep = put(world, r1, g1, s, 3003, "a.py", c=0.9, lines=(1,))
    else:                             # same line; the higher id goes in first
        put(world, r1, g1, s, 3003, "a.py", c=0.9, lines=(1,))
        keep = put(world, r1, g1, s, 3002, "a.py", c=0.8, lines=(1,))
    rows = run(world.db, scope(granted=[r1, r2]), vectors={s: axis(0)})
    capped = {r["representation_id"] for r in rows if (r["repo_id"], r["path"]) == (r1, "a.py")}
    assert capped == {3000, 3001, keep} and len(capped) == h.PER_FILE_CAP
    assert elsewhere <= {r["representation_id"] for r in rows}  # the cap is per repository and path


def test_every_order_by_carries_its_pinned_key():
    """Three mutants that drop a trailing id cannot be told apart by results alone: an earlier sort
    over the same id (the cut, under the ranks; the per-file window, under the final order; and
    pg_search's own tie order, under the cut) already puts tied rows in id order. The key lists are
    therefore also pinned on the statement itself."""
    sql = " ".join(h.build("x", {1: axis(0)}, scope(granted=[1]), k=5).sql.split())
    for key in [
        "ORDER BY score DESC, rep.repo_id, rep.path, rep.id LIMIT",                     # lexical cut
        "OVER (ORDER BY score DESC, repo_id, path, id) AS r FROM lexical",              # lexical ranks
        "OVER (ORDER BY d.distance, d.repo_id, rep.path, d.id) AS r",                   # dense ranks
        "PARTITION BY rr.repo_id, rr.path ORDER BY f.fused DESC, rr.start_line, rr.representation_id)",  # cap
        "ORDER BY fused DESC, repo_id, path, start_line, representation_id LIMIT",      # final order
    ]:
        assert sql.count(key) == 1, key
