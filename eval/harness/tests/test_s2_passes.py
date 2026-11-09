import pytest
from s2 import inputs, passes
from s2.passes import Measured


def recorder(cpu):
    """A stage call whose CPU is `cpu(query, n)`, n counting every call, warm-up included."""
    seen = []

    def measure(q):
        seen.append(q)
        return Measured(cpu(q, len(seen)), 1)

    measure.seen = seen
    return measure


def test_three_warmup_passes_then_five_timed_and_only_the_timed_calls_are_kept():
    m = recorder(lambda q, n: n)
    got = passes.warm(["a", "b"], m)
    assert m.seen == ["a", "b"] * 8
    assert [[c.cpu_ns for c in p] for p in got.passes] == [[7, 8], [9, 10], [11, 12], [13, 14], [15, 16]]


def test_the_cost_is_the_median_of_the_per_pass_means_not_the_mean_of_all_calls():
    per_pass = iter([[1, 1], [1, 3], [100, 100], [2, 2], [3, 3]])
    got = passes.Warm(tuple(tuple(Measured(c, 0) for c in p) for p in per_pass))
    assert got.pass_means_ns == [1, 2, 100, 2, 3]
    assert got.cost_ns == 2


def test_per_call_p50_and_p95_are_nearest_rank_over_every_timed_call():
    got = passes.warm(list(range(20)), recorder(lambda q, n: q + 1), warmup=0, timed=5)
    assert got.stats == passes.Stats(10, 19, 100)
    assert passes.percentile(list(range(1, 101)), 0.95) == 95
    assert passes.percentile([4], 0.5) == 4
    with pytest.raises(ValueError):
        passes.percentile([], 0.5)


def test_a_warm_pass_needs_queries():
    with pytest.raises(ValueError, match="full query set"):
        passes.warm([], recorder(lambda q, n: n))


SAMPLE = list(range(inputs.COLD_SAMPLE))


def test_each_cold_pass_resets_then_loads_the_model_then_makes_one_call_per_stage():
    events = []

    def load():
        events.append("load")
        return {"embedding-model": Measured(500, 9)}

    def measure(q):
        events.append(("call", q))
        return {"embedding": Measured(q + 1, 0), "sql": Measured(2 * (q + 1), 0)}

    got = passes.cold(SAMPLE, lambda: events.append("reset"), load, measure)
    assert events == [e for q in SAMPLE for e in ("reset", "load", ("call", q))]
    assert got.stats("embedding") == passes.Stats(25, 48, 50)
    assert got.stats("sql") == passes.Stats(50, 96, 50)
    assert got.model_load("embedding-model") == passes.Stats(500, 500, 50)


def test_the_cold_sample_must_be_exactly_fifty_queries():
    with pytest.raises(ValueError, match="50 queries, not 49"):
        passes.cold(SAMPLE[:49], lambda: None, dict, lambda q: {})


def test_every_cold_pass_must_measure_the_same_stages():
    calls = iter([{"sql": Measured(1, 0)}] * 49 + [{"embedding": Measured(1, 0)}])
    with pytest.raises(ValueError, match="different stages"):
        passes.cold(SAMPLE, lambda: None, dict, lambda q: next(calls))
