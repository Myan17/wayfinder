import gzip

import pytest
from s2 import calibration as cal
from s2.calibration import Block, Machine, Window
from s2.counters import CounterError, Executed

HZ = 100


class FakeHost:
    """A simulated machine: background CPU accrues with time, each call adds its real work, and the
    harness adds its own overhead. Ticks are kept as floats and floored when read, like the kernel."""

    def __init__(self, rate=0.2, after_rate=None, overhead_ns=0, iowait_rate=0.01, steal_rate=0.02):
        self.t_ns = 0
        self.cpu_s = 0.0
        self.harness_ns = 0
        self.rate, self.after_rate = rate, after_rate
        self.overhead_ns = overhead_ns
        self.iowait_rate, self.steal_rate = iowait_rate, steal_rate

    def _advance(self, ns):
        self.t_ns += ns
        self.cpu_s += self.rate * ns / 1e9

    def sleep(self, seconds):
        self._advance(int(seconds * 1e9))

    def stat(self):
        t = self.t_ns / 1e9
        return Executed(int(self.cpu_s * HZ), int(self.iowait_rate * t * HZ), int(self.steal_rate * t * HZ))

    def call(self, work_ns, reported_ns=None):
        def one():
            self._advance(work_ns)  # wall time: one core busy for the call
            self.cpu_s += work_ns / 1e9 + self.overhead_ns / 1e9
            self.harness_ns += self.overhead_ns
            return work_ns if reported_ns is None else reported_ns

        return one

    def machine(self):
        return Machine(self.stat, lambda: self.t_ns, lambda: self.harness_ns, self.sleep, HZ)

    def run(self, path, work_ns=100_000_000, reported_ns=None):
        m = self.machine()
        before = cal.background(m)
        blk = cal.block(m, self.call(work_ns, reported_ns))
        if self.after_rate is not None:
            self.rate = self.after_rate
        after = cal.background(m)
        return cal.check(path, before, blk, after)


def test_an_exact_path_agrees_and_the_block_reaches_30_s_of_cpu():
    got = FakeHost(overhead_ns=2_000_000).run("sql")
    assert got.block.summed_s >= 30 and len(got.block.per_call_ns) == 300
    assert got.block.harness_cpu_s == pytest.approx(0.6)
    assert got.ratio == pytest.approx(1, abs=0.002)  # boundary ticks only
    assert got.before.elapsed_s == 60 and got.before.rate == pytest.approx(0.2)


def test_harness_cpu_is_subtracted_except_on_the_rerank_path():
    # with 10% overhead not subtracted, a non-rerank path would read 0.91 of its reference
    host = FakeHost(overhead_ns=10_000_000)
    assert host.run("embedding").ratio == pytest.approx(1, abs=0.002)
    with pytest.raises(CounterError, match="outside 95% to 105%"):
        FakeHost(overhead_ns=10_000_000).run("rerank")  # the same 10% left out of the reference
    # rerank: the harness's CPU is the work, so the thread clock reports it and it stays in
    got = FakeHost(overhead_ns=10_000_000).run("rerank", reported_ns=110_000_000)
    assert got.ratio == pytest.approx(1, abs=0.002)


def test_a_path_that_misses_cpu_is_an_error_and_one_inside_5_percent_is_not():
    FakeHost().run("sql", reported_ns=96_000_000)
    with pytest.raises(CounterError, match="outside 95% to 105%"):
        FakeHost().run("sql", reported_ns=94_000_000)
    with pytest.raises(CounterError, match="outside 95% to 105%"):
        FakeHost().run("sql", reported_ns=106_000_000)


def test_the_agreement_bounds_are_inclusive_at_exactly_95_and_105_percent():
    # no background and the rerank path, so the reference is exactly the block's 100 s
    idle = Window(executed_s=0, iowait_s=0, steal_s=0, elapsed_s=60)
    block_window = Window(executed_s=100, iowait_s=0, steal_s=0, elapsed_s=100)

    def ratio(summed_ns):
        return cal.check("rerank", idle, Block(block_window, 0.0, [summed_ns]), idle).ratio

    assert ratio(95 * 10**9) == 0.95
    assert ratio(105 * 10**9) == 1.05
    for just_outside in (95 * 10**9 - 1_000_000, 105 * 10**9 + 1_000_000):
        with pytest.raises(CounterError, match="outside 95% to 105%"):
            ratio(just_outside)


def test_background_that_moves_during_the_block_fails_the_noise_gate():
    # 30 s block: 0.011 core-s/s drift x 30 s = 0.33 s, above 1% of the 30 s reference
    with pytest.raises(CounterError, match="background moved"):
        FakeHost(rate=0.2, after_rate=0.211).run("sql")
    assert FakeHost(rate=0.2, after_rate=0.209).run("sql").noise_s == pytest.approx(0.27, abs=0.01)


def test_iowait_and_steal_are_reported_not_added():
    got = FakeHost(iowait_rate=0.5, steal_rate=0.5).run("sql")
    assert got.ratio == pytest.approx(1, abs=0.002)
    assert got.block.window.iowait_s == pytest.approx(15, abs=0.02)
    assert got.block.window.steal_s == pytest.approx(15, abs=0.02)


def test_a_counter_that_does_not_count_and_a_block_with_no_work_are_errors():
    host = FakeHost()
    with pytest.raises(CounterError, match="not counting"):
        cal.block(host.machine(), host.call(1, reported_ns=0))
    w = Window(executed_s=6, iowait_s=0, steal_s=0, elapsed_s=30)
    bg = Window(executed_s=12, iowait_s=0, steal_s=0, elapsed_s=60)
    with pytest.raises(CounterError, match="no measurable work"):
        cal.check("sql", bg, Block(w, 0.0, [1]), bg)
    with pytest.raises(ValueError, match="unknown path"):
        cal.check("api", bg, Block(w, 0.0, [1]), bg)


def test_stat_going_backwards_is_an_error():
    seq = iter([Executed(500, 0, 0), Executed(400, 0, 0)])
    m = Machine(lambda: next(seq), iter([0, 60 * 10**9]).__next__, lambda: 0, lambda s: None, HZ)
    with pytest.raises(CounterError, match="backwards"):
        cal.background(m)


def test_calibrate_runs_background_block_background_in_order():
    host = FakeHost()
    got = cal.calibrate(host.machine(), "embedding", host.call(100_000_000))
    assert host.t_ns == pytest.approx(150 * 10**9, rel=0.01)  # 60 + 30 + 60 s
    assert got.ratio == pytest.approx(1, abs=0.002)


def test_kernel_accounting_needs_exactly_one_option(tmp_path):
    tick = "# comment\nCONFIG_TICK_CPU_ACCOUNTING=y\n# CONFIG_VIRT_CPU_ACCOUNTING_GEN is not set\n"
    assert cal.accounting(tick) == "CONFIG_TICK_CPU_ACCOUNTING"
    assert cal.accounting("CONFIG_VIRT_CPU_ACCOUNTING_GEN=y\n") == "CONFIG_VIRT_CPU_ACCOUNTING_GEN"
    for bad in ("", "CONFIG_TICK_CPU_ACCOUNTING=y\nCONFIG_VIRT_CPU_ACCOUNTING_GEN=y\n"):
        with pytest.raises(CounterError, match="need exactly one"):
            cal.accounting(bad)
    (tmp_path / "proc").mkdir()
    (tmp_path / "proc/config.gz").write_bytes(gzip.compress(tick.encode()))
    assert cal.kernel_config(tmp_path / "proc", tmp_path / "boot") == tick
    with pytest.raises(CounterError, match="no kernel config"):
        cal.kernel_config(tmp_path / "none", tmp_path / "boot")
