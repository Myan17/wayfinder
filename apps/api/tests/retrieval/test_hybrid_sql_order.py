"""The canonical two-leg query's ordering (ADR-0007 Amendment 1, step 3b): the per-leg tie keys before
RRF ranks, the lexical leg's top-100 cut, the final key on equal fused scores, and the per-file cap.

No plan is captured or inspected here: plans are step 4's."""

import random

import pytest

from wayfinder.retrieval import hybrid_sql as h

from .conftest import DIM, axis, run, scope


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
