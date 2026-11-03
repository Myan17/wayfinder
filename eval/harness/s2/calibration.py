"""Spike S2's calibration cross-check (ADR-0019, "The calibration cross-check").

The reference is the machine's executed CPU from `/proc/stat` (`counters.executed_ticks`), a
different accounting from the scheduler sums behind the three per-call counters. For each path:

1. background before: 60 s with the services up and no calls gives `b_before`;
2. block: that path's real calls back to back until their summed per-call CPU reaches 30 s;
3. background after: another 60 s gives `b_after`;
4. noise gate: `|b_after - b_before|` x the block's elapsed time must not exceed 1% of the reference;
5. reference: executed CPU during the block, minus the mean background over the block, minus the
   harness process's own CPU, except on the rerank path, where the harness's CPU is the work;
6. the summed per-call values must be within 5% of the reference.

A failed gate or check raises `CounterError`: S2 is an error, not a result. The machine is reached
through `Machine`'s callables, so every rule is tested off Linux; `Machine.linux()` is the real one.
"""

from __future__ import annotations

import gzip
import os
import platform
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from s2.counters import PROC, CounterError, Executed, executed_ticks

PATHS = ("embedding", "sql", "rerank")
BACKGROUND_S = 60
BLOCK_CPU_NS = 30 * 10**9
NOISE_LIMIT = 0.01
AGREEMENT_LIMIT = 0.05
NS = 10**9


@dataclass(frozen=True)
class Machine:
    read_stat: Callable[[], Executed]  # the aggregate cpu line now
    monotonic_ns: Callable[[], int]
    harness_cpu_ns: Callable[[], int]  # CLOCK_PROCESS_CPUTIME_ID of the harness
    sleep: Callable[[float], None]
    user_hz: int

    @staticmethod
    def linux(proc: Path = PROC) -> Machine:
        return Machine(
            read_stat=lambda: executed_ticks((proc / "stat").read_text()),
            monotonic_ns=time.monotonic_ns,
            harness_cpu_ns=time.process_time_ns,
            sleep=time.sleep,
            user_hz=os.sysconf("SC_CLK_TCK"),
        )


@dataclass(frozen=True)
class Window:
    """Executed CPU, iowait and steal over one interval, in seconds, and its elapsed time."""

    executed_s: float
    iowait_s: float
    steal_s: float
    elapsed_s: float

    @property
    def rate(self) -> float:
        """Core-seconds per second."""
        return self.executed_s / self.elapsed_s


def _window(m: Machine, before: Executed, after: Executed, elapsed_ns: int) -> Window:
    def s(ticks: int) -> float:
        if ticks < 0:
            raise CounterError("/proc/stat went backwards")
        return ticks / m.user_hz

    return Window(
        s(after.executed - before.executed),
        s(after.iowait - before.iowait),
        s(after.steal - before.steal),
        elapsed_ns / NS,
    )


def background(m: Machine, seconds: float = BACKGROUND_S) -> Window:
    """Executed CPU with the services up and no calls."""
    t0, s0 = m.monotonic_ns(), m.read_stat()
    m.sleep(seconds)
    s1, t1 = m.read_stat(), m.monotonic_ns()
    return _window(m, s0, s1, t1 - t0)


@dataclass(frozen=True)
class Block:
    window: Window
    harness_cpu_s: float
    per_call_ns: list[int]

    @property
    def summed_s(self) -> float:
        return sum(self.per_call_ns) / NS


def block(m: Machine, call: Callable[[], int], cpu_ns: int = BLOCK_CPU_NS) -> Block:
    """Run `call` back to back until the summed per-call CPU reaches `cpu_ns`. `call` makes one real
    call and returns its CPU through the path's own counter, in ns."""
    per_call: list[int] = []
    h0, t0, s0 = m.harness_cpu_ns(), m.monotonic_ns(), m.read_stat()
    while sum(per_call) < cpu_ns:
        v = call()
        if v <= 0:
            raise CounterError(f"a call returned {v} ns of CPU; the path's counter is not counting")
        per_call.append(v)
    s1, t1, h1 = m.read_stat(), m.monotonic_ns(), m.harness_cpu_ns()
    return Block(_window(m, s0, s1, t1 - t0), (h1 - h0) / NS, per_call)


@dataclass(frozen=True)
class Calibration:
    path: str
    before: Window
    block: Block
    after: Window
    noise_s: float
    reference_s: float

    @property
    def ratio(self) -> float:
        """Summed per-call CPU over the reference: 1.0 is perfect agreement."""
        return self.block.summed_s / self.reference_s


def check(path: str, before: Window, blk: Block, after: Window) -> Calibration:
    """Steps 4 to 6 on measured windows. Raises `CounterError` if the noise gate or agreement fails."""
    if path not in PATHS:
        raise ValueError(f"unknown path {path!r}")
    elapsed = blk.window.elapsed_s
    harness = 0.0 if path == "rerank" else blk.harness_cpu_s
    reference = blk.window.executed_s - (before.rate + after.rate) / 2 * elapsed - harness
    if reference <= 0:
        raise CounterError(f"{path}: reference is {reference:.3f} s, the block did no measurable work")
    noise = abs(after.rate - before.rate) * elapsed
    if noise > NOISE_LIMIT * reference:
        raise CounterError(
            f"{path}: background moved by {noise:.3f} s over the block, "
            f"above 1% of the {reference:.3f} s reference"
        )
    result = Calibration(path, before, blk, after, noise, reference)
    if abs(result.ratio - 1) > AGREEMENT_LIMIT:
        raise CounterError(
            f"{path}: per-call sum {blk.summed_s:.3f} s is {result.ratio:.2%} of the "
            f"{reference:.3f} s reference, outside 5%"
        )
    return result


def calibrate(m: Machine, path: str, call: Callable[[], int]) -> Calibration:
    """Steps 1 to 6 for one path, in order."""
    before = background(m)
    blk = block(m, call)
    after = background(m)
    return check(path, before, blk, after)


# --- provenance (S2-8): which CPU-time accounting the kernel uses ---------------------------------

ACCOUNTING = ("CONFIG_TICK_CPU_ACCOUNTING", "CONFIG_VIRT_CPU_ACCOUNTING_GEN")


def accounting(kernel_config: str) -> str:
    """The one CPU-time accounting option set to `y` in a kernel config."""
    on = [opt for opt in ACCOUNTING if f"{opt}=y" in kernel_config.splitlines()]
    if len(on) != 1:
        raise CounterError(f"kernel config sets {on or 'none'} of {list(ACCOUNTING)}, need exactly one")
    return on[0]


def kernel_config(proc: Path = PROC, boot: Path = Path("/boot")) -> str:
    """The running kernel's config, from `/proc/config.gz` or `/boot/config-<release>`."""
    gz = proc / "config.gz"
    if gz.exists():
        return gzip.decompress(gz.read_bytes()).decode()
    f = boot / f"config-{platform.release()}"
    if f.exists():
        return f.read_text()
    raise CounterError(f"no kernel config at {gz} or {f}")
