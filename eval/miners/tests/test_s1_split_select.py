"""S1's D-5 split (ADR-0013) and corpus selection (ADR-0016)."""

import datetime as dt

import pytest

from s1 import select, split


def _pair(pr, issue, day, repo=1):
    return {"repo_id": repo, "issue": issue, "pr": pr, "merged_at": dt.datetime(2026, 1, day, tzinfo=dt.UTC)}


def test_d5_reproduces_adr_0013s_worked_example():
    # Groups of 3, 2, 1, 3, 1 pairs in time order: g1 shares issue 1, g2 issue 2, g4 PR 40.
    ps = ([_pair(10, 1, 1), _pair(11, 1, 1), _pair(12, 1, 1)] + [_pair(20, 2, 2), _pair(21, 2, 2)]
          + [_pair(30, 3, 3)] + [_pair(40, 4, 4), _pair(40, 5, 4), _pair(40, 6, 4)] + [_pair(50, 7, 5)])
    out = split.assign(ps)
    by_pr = {}
    for p in out["pairs"]:
        by_pr.setdefault(p["pr"], set()).add(p["split"])
    assert by_pr == {10: {"dev"}, 11: {"dev"}, 12: {"dev"}, 20: {"dev"}, 21: {"dev"},
                     30: {"test"}, 40: {"test"}, 50: {"held_out"}}
    assert out["achieved"] == {1: {"dev": 5, "test": 4, "held_out": 1}}   # 5/4/1, not 5/3/2
    assert len({p["group_id"] for p in out["pairs"]}) == 5


def test_d5_a_group_is_placed_by_its_latest_merge():
    # Group {1, 2} shares issue 9 and merges on days 1 and 9, so t(g) = 9 and it sorts after the
    # singletons of days 5 and 6. N = 4: c = 0, 1 -> dev; c = 2 is not < 2 -> test. By its first
    # merge (day 1) it would have sorted first and gone to dev.
    ps = [_pair(1, 9, 1), _pair(2, 9, 9), _pair(3, 8, 5), _pair(4, 7, 6)]
    out = split.assign(ps)
    assert {p["pr"]: p["t_g"].day for p in out["pairs"]} == {1: 9, 2: 9, 3: 5, 4: 6}
    assert {p["pr"]: p["split"] for p in out["pairs"]} == {1: "test", 2: "test", 3: "dev", 4: "dev"}


def test_d5_issue_numbers_are_per_repository():
    # Issue 9 in repository 7 and issue 9 in repository 3 are different issues, so different groups.
    out = split.assign([_pair(1, 9, 1, repo=7), _pair(2, 9, 2, repo=3)])
    assert len({p["group_id"] for p in out["pairs"]}) == 2 and set(out["achieved"]) == {3, 7}


def _c(rid, lang, n, ch, ok=True):
    return {"repo_id": rid, "lang": lang, "qualified": ok, "pairs": n, "chunks": ch}


def test_selection_is_the_total_order_of_adr_0016():
    cands = [_c(1, "py", 100, 10_000), _c(2, "py", 90, 5_000), _c(3, "go", 90, 5_000),
             _c(4, "go", 60, 50_000), _c(5, "go", 10, 1_000, ok=False)]
    win, feasible = select.best(cands)
    assert win == (1, 2, 3) or win == (1, 2, 3, 4)
    assert win == (1, 2, 3)                                             # (1,2,3,4) breaks 60k
    assert (1, 2, 3, 4) not in feasible and all(5 not in s for s in feasible)


def test_the_last_key_is_the_sorted_id_tuple_not_a_sum():
    # Only {1,5,6} and {2,3,4} survive every earlier key (21 pairs, 3 repositories, 18 chunks).
    # The tuple order picks (1,5,6); a sum of ids would pick (2,3,4), since 9 < 12.
    cands = [_c(1, "py", 1, 2), _c(2, "py", 13, 10), _c(3, "go", 4, 4), _c(4, "go", 4, 4),
             _c(5, "go", 10, 8), _c(6, "go", 10, 8)]
    win, feasible = select.best(cands, max_chunks=18)
    assert win == (1, 5, 6) and (2, 3, 4) in feasible


@pytest.mark.parametrize("cands,why", [
    ([_c(1, "py", 1, 1), _c(2, "go", 1, 1)], "qualification count"),
    ([_c(1, "py", 1, 1), _c(2, "py", 1, 1), _c(3, "py", 1, 1)], "language mix"),
    ([_c(1, "py", 1, 40_000), _c(2, "go", 1, 40_000), _c(3, "go", 1, 40_000)], "chunk bound"),
])
def test_no_feasible_corpus_names_the_constraint_that_failed(cands, why):
    assert select.best(cands) == (None, why)
