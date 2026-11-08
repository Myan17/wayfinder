"""S2's load plan (ADR-0019 Amendments 1-3): grouping, distinct representations, padding, the lease and
the truncation report. Pure: no database, no Ollama."""

from collections import namedtuple
from datetime import timedelta

import pytest
from s2 import load_plan as lp
from s2.inputs import Window

TEMPLATE = "search_document: {header}\n{body}"
NAMES = {7: "o/a", 8: "o/b"}
Call = namedtuple("Call", "input_hash prompt_eval_count truncated error")  # s6_ollama.Call's shape


def w(path, first, text, pr=0, repo=7):
    return Window(repo, path, (first - 1) // 60, first, text, pr)


def test_header_is_owner_name_dot_path():
    assert lp.header("psf/black", "a/b.py") == "psf/black · a/b.py"


def test_group_holds_all_100_ids_ascending_with_windows_in_path_then_line_order():
    g = lp.group([w("b.py", 1, "x", 3), w("a.py", 61, "y", 3), w("a.py", 1, "z", 3), w("c.py", 1, "q", 99)])
    assert list(g) == list(range(100))
    assert [(x.path, x.first_line) for x in g[3]] == [("a.py", 1), ("a.py", 61), ("b.py", 1)]
    assert len(g[99]) == 1 and g[0] == []


def test_identical_windows_share_a_source_only_within_one_file_header():
    ws = [w("a.py", 1, "same\n"), w("a.py", 61, "same\n"), w("b.py", 1, "same\n"), w("a.py", 121, "other\n")]
    got = lp.sources(sorted(ws, key=lambda x: (x.path, x.first_line)), NAMES, TEMPLATE)
    assert [(x.path, x.first_line) for x in got] == [("a.py", 1), ("a.py", 121), ("b.py", 1)]


def test_the_same_window_in_another_repository_is_another_source():
    ws = [w("a.py", 1, "same\n", repo=7), w("a.py", 1, "same\n", repo=8)]
    assert len(lp.sources(ws, NAMES, TEMPLATE)) == 2


def test_allocate_is_proportional_by_largest_remainder_with_ties_to_the_lower_id():
    # need = 10 - 3 = 7 over weights 1,1,1: quotas 7/3 each, floors 2,2,2, one left; equal remainders -> id 0
    assert lp.allocate({0: 1, 1: 1, 2: 1}, total=10) == {0: 3, 1: 2, 2: 2}
    # need = 20 - 4 = 16 over 3,1: quotas 12 and 4, no remainder
    assert lp.allocate({5: 3, 9: 1}, total=20) == {5: 12, 9: 4}
    # need = 8 over 2,1: quotas 16/3 and 8/3, floors 5 and 2; the larger remainder (id 1) beats the lower id
    assert lp.allocate({0: 2, 1: 1}, total=11) == {0: 5, 1: 3}


def test_allocate_reaches_exactly_60000_on_a_skewed_corpus():
    real = {p: (724 if p == 0 else 14 + p) for p in range(100)}
    shares = lp.allocate(real)
    assert sum(real.values()) + sum(shares.values()) == 60_000
    assert shares[0] == max(shares.values())


@pytest.mark.parametrize("real", [{0: 0}, {0: 60_001}])
def test_allocate_refuses_nothing_to_copy_or_too_much_already(real):
    with pytest.raises(lp.LoadFailed):
        lp.allocate(real)


def test_pads_go_in_ascending_id_cycle_sources_and_number_rows_once_from_zero():
    s0, s1 = [w("a.py", 1, "a"), w("b.py", 1, "b")], [w("c.py", 1, "c", 4)]
    got = lp.pads({4: s1, 0: s0}, {4: 2, 0: 3})
    assert [(p.pseudo_repo, p.source.path, p.row) for p in got] == [
        (0, "a.py", 0), (0, "b.py", 1), (0, "a.py", 2), (4, "c.py", 3), (4, "c.py", 4),
    ]  # fmt: skip


def test_pads_refuse_a_share_with_no_source():
    with pytest.raises(lp.LoadFailed, match="pseudo-repository 2"):
        lp.pads({2: []}, {2: 1})


def test_the_lease_is_exactly_60_minutes_and_a_longer_build_fails():
    assert timedelta(minutes=60) == lp.LEASE
    lp.check_lease(5, timedelta(minutes=60))
    with pytest.raises(lp.LoadFailed, match="pseudo-repository 5"):
        lp.check_lease(5, timedelta(minutes=60, microseconds=1))


def _hash(x):
    return lp.input_hash(x, NAMES[x.github_repo_id], TEMPLATE)


def test_embed_report_lists_every_truncated_window_and_keeps_them_out_of_the_distribution():
    a, b1, b2 = w("a.py", 1, "a\nb\n", 3), w("big.py", 61, "x\n" * 60, 3), w("big.py", 121, "x\n" * 60, 3)
    a2 = w("a.py", 61, "a\nb\n", 3)  # same file and text as a: one representation, two windows
    by_hash = {_hash(a): [a, a2], _hash(b1): [b1, b2]}  # b1 and b2 share one representation too
    calls = [
        Call(_hash(a), 600, False, None),
        Call(_hash(b1), 2048, True, "the input length exceeds the context length"),
    ]
    accepted, truncated = lp.embed_report(calls, by_hash)
    assert accepted == [600, 600]  # one count per window, not per call
    assert [(t.path, t.start_line, t.end_line, t.prompt_eval_count) for t in truncated] == [
        ("big.py", 61, 120, 2048), ("big.py", 121, 180, 2048),
    ]  # fmt: skip
    assert (
        truncated[0].error == "the input length exceeds the context length" and truncated[0].pseudo_repo == 3
    )


def test_a_retry_above_the_context_fails_naming_the_window():
    b = w("big.py", 61, "x\n", repo=8)
    with pytest.raises(
        lp.LoadFailed, match=r"8 big.py:61 exceeds 2,048: retry counted 2049 tokens after: raw"
    ):
        lp.embed_report([Call(_hash(b), 2049, True, "raw")], {_hash(b): [b]})


def test_a_call_for_an_input_no_window_has_is_an_error():
    with pytest.raises(AssertionError):
        lp.embed_report([Call(b"\0" * 32, 5, False, None)], {})


def test_retry_failed_names_repository_path_start_line_context_and_raw_error():
    assert str(lp.retry_failed(w("d/x.md", 61, "x"), "boom")) == "7 d/x.md:61 exceeds 2,048: boom"
