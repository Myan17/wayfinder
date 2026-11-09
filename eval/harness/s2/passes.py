"""Spike S2's passes: ADR-0019, "Warm and cold measurements are separate passes".

This is the protocol only. Each stage's call is injected as `measure`, which makes one real call and
returns its CPU through that stage's own counter; the stage wiring lives elsewhere.

- Warm (ADR-0013's protocol, gupta958's ruling 4): three warm-up passes over the full query set, then
  five timed passes. Only timed calls are kept. A stage's cost is the median of the five per-pass
  means, and per-call p50 and p95 come from all the timed calls.
- Cold: one query per pass, because only the first call after a reset is cold. The sample is the 50
  queries `inputs.cold_sample` fixes. Before each, the reset runs, then the model load, whose CPU is
  reported separately; then one call through each stage. Cold numbers never enter the warm ones.

Percentiles are nearest-rank. CPU is judged; wall time is recorded and never judged.
"""

from __future__ import annotations

import math
import statistics
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass

from s2 import inputs

WARMUP_PASSES = 3
TIMED_PASSES = 5


@dataclass(frozen=True)
class Measured:
    cpu_ns: int
    wall_ns: int
    tokens: int | None = None  # the embedder's count, for S2-3's cost against query length


def percentile(xs: Sequence[float], q: float) -> float:
    """Nearest-rank: the smallest value with at least `q` of the values at or below it."""
    if not xs:
        raise ValueError("no values")
    s = sorted(xs)
    return s[max(math.ceil(q * len(s)), 1) - 1]


@dataclass(frozen=True)
class Stats:
    p50_ns: float
    p95_ns: float
    calls: int

    @classmethod
    def of(cls, calls: Sequence[Measured]) -> Stats:
        cpu = [c.cpu_ns for c in calls]
        return cls(percentile(cpu, 0.50), percentile(cpu, 0.95), len(cpu))


@dataclass(frozen=True)
class Warm:
    passes: tuple[tuple[Measured, ...], ...]  # the timed passes, each in query order

    @property
    def pass_means_ns(self) -> list[float]:
        return [statistics.fmean(c.cpu_ns for c in p) for p in self.passes]

    @property
    def cost_ns(self) -> float:
        """The stage's cost: the median of the per-pass means."""
        return statistics.median(self.pass_means_ns)

    @property
    def stats(self) -> Stats:
        return Stats.of([c for p in self.passes for c in p])


def warm[Q](
    queries: Sequence[Q],
    measure: Callable[[Q], Measured],
    *,
    warmup: int = WARMUP_PASSES,
    timed: int = TIMED_PASSES,
) -> Warm:
    if not queries:
        raise ValueError("a warm pass needs the full query set, not none")
    for _ in range(warmup):
        for q in queries:
            measure(q)
    return Warm(tuple(tuple(measure(q) for q in queries) for _ in range(timed)))


@dataclass(frozen=True)
class ColdPass:
    query: object
    model_load: Mapping[str, Measured]  # e.g. the embedding model and the ONNX session
    calls: Mapping[str, Measured]  # one call through each stage


@dataclass(frozen=True)
class Cold:
    passes: tuple[ColdPass, ...]

    def stats(self, stage: str) -> Stats:
        return Stats.of([p.calls[stage] for p in self.passes])

    def model_load(self, what: str) -> Stats:
        return Stats.of([p.model_load[what] for p in self.passes])


def cold[Q](
    sample: Sequence[Q],
    reset: Callable[[], None],
    load: Callable[[], Mapping[str, Measured]],
    measure: Callable[[Q], Mapping[str, Measured]],
) -> Cold:
    """Each query: reset, then the model load, then one call through each stage, in that order."""
    if len(sample) != inputs.COLD_SAMPLE:
        raise ValueError(f"the cold sample is {inputs.COLD_SAMPLE} queries, not {len(sample)}")
    out = []
    for q in sample:
        reset()
        loaded = load()
        out.append(ColdPass(q, loaded, measure(q)))
    stages = {frozenset(p.calls) for p in out}
    if len(stages) != 1:
        raise ValueError(f"cold passes measured different stages: {sorted(map(sorted, stages))}")
    return Cold(tuple(out))
