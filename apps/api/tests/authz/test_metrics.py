"""Counters that survive sampling -- DESIGN 17.1.

A telemetry budget may drop a trace. It must never drop the fact that authorization denied something
or that a caller defect was refused, so these counts live in-process and unsampled.
"""

from wayfinder.authz.metrics import Counter


def test_a_counter_starts_at_zero_and_increments():
    c = Counter(name="test_total", description="counts things")

    assert c.value == 0
    assert c.increment() == 1
    assert c.increment(3) == 4


def test_counters_are_independent():
    a = Counter(name="a_total", description="a")
    b = Counter(name="b_total", description="b")

    a.increment()

    assert (a.value, b.value) == (1, 0)


def test_reset_is_test_only_and_explicit():
    c = Counter(name="c_total", description="c")
    c.increment()

    c.reset_for_test()

    assert c.value == 0
