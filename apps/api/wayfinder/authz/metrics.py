"""Counters that must survive sampling -- DESIGN 17.1.

Security-relevant counts are never sampled away: a telemetry budget can drop a trace, but it must
never drop the fact that a denial, a violation or a caller defect happened. This module is the seam
those counters live behind. Exporting them to the collector arrives with the observability module;
until then the values are readable in-process and in tests, and nothing here pretends otherwise.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field


@dataclass
class Counter:
    """A monotonic counter. Cheap, thread-safe, and reset only by tests."""

    name: str
    description: str
    _value: int = 0
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    @property
    def value(self) -> int:
        return self._value

    def increment(self, amount: int = 1) -> int:
        with self._lock:
            self._value += amount
            return self._value

    def reset_for_test(self) -> None:
        with self._lock:
            self._value = 0


authorization_violation_total = Counter(
    name="authorization_violation_total",
    description=(
        "Rows that reached the caller from outside the authorized scope. Must stay at zero; any "
        "increment is stop-the-line (DESIGN 13.2)."
    ),
)

anonymous_grants_rejected_total = Counter(
    name="anonymous_grants_rejected_total",
    description=(
        "Calls that offered grants for an anonymous principal. A resolver defect, refused by the "
        "kernel rather than normalised away; counted where it is raised so the signal exists before "
        "a handler does."
    ),
)
