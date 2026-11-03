"""Spike S2's backend thread preflight (ADR-0019, "The backend thread preflight").

strace logs every creation as it happens, so a thread that starts and ends inside a call is still
seen. Every creation the backend made is classified:

- none: the backend is one thread, so its process clock must agree with the main thread's
  `schedstat` within 10 µs per call;
- threads only (`clone`/`clone3` with `CLONE_THREAD`): the process clock already counts them, and it
  must be at least `schedstat` on every call;
- any child process (`fork`, `vfork`, or `clone` without `CLONE_THREAD`): its CPU leaves the thread
  group, so S2 stops as an error.

The case runner takes the attach, query and reset steps as callables. The Docker and Postgres wiring
arrives with the passes. Timings taken under ptrace are never measurements.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Iterable
from dataclasses import dataclass

from s2.counters import RESOLUTION_LIMIT_NS, CounterError

SIZES = ("real", "60k")
LEVELS = (1, 10, 100)  # percent of pseudo-repositories granted (Amendment 1 §3)
CREATORS = ("clone3", "clone", "vfork", "fork")

_PID = re.compile(r"^\[pid\s+(\d+)\]\s*")
_CALL = re.compile(r"^(clone3|clone|vfork|fork)\((.*)\)\s+=\s+(-?\d+)")
_UNFINISHED = " <unfinished ...>"
_RESUMED = re.compile(r"^<\.\.\. (\w+) resumed>\s*")


def strace_command(host_pid: int) -> list[str]:
    return ["strace", "-f", "-qq", "-e", "trace=clone,clone3,fork,vfork", "-p", str(host_pid)]


@dataclass(frozen=True)
class Creations:
    threads: tuple[int, ...]
    children: tuple[int, ...]

    @property
    def kind(self) -> str:
        return "child" if self.children else "threads" if self.threads else "none"


def classify(strace_output: str) -> Creations:
    """Every successful creation in strace's output. A line naming a creator that cannot be parsed
    raises: an unread line could be a child process."""
    threads: list[int] = []
    children: list[int] = []
    pending: dict[str, str] = {}
    for raw in strace_output.splitlines():
        m = _PID.match(raw)
        who, line = (m.group(1), raw[m.end() :]) if m else ("main", raw)
        if line.endswith(_UNFINISHED):
            pending[who] = line[: -len(_UNFINISHED)]
            continue
        r = _RESUMED.match(line)
        if r:
            if who not in pending:
                raise ValueError(f"resumed call with no start: {raw!r}")
            line = pending.pop(who) + line[r.end() :]
        call = _CALL.match(line)
        if not call:
            if any(line.startswith(c + "(") for c in CREATORS):
                raise ValueError(f"cannot parse creation: {raw!r}")
            continue  # signals, exits and other noise
        name, args, result = call.group(1), call.group(2), int(call.group(3))
        if result <= 0:
            continue  # failed, so nothing was created
        if name in ("clone", "clone3") and "CLONE_THREAD" in args:
            threads.append(result)
        else:
            children.append(result)
    if pending:
        raise ValueError(f"unfinished calls never resumed: {sorted(pending)}")
    return Creations(tuple(threads), tuple(children))


def check_clock(found: Creations, process_ns: Iterable[int], schedstat_ns: Iterable[int]) -> list[int]:
    """Apply the agreement rule for what the backend did, per call. Returns process - schedstat."""
    if found.kind == "child":
        raise CounterError(f"the backend created child processes {list(found.children)}")
    diffs = [p - s for p, s in zip(process_ns, schedstat_ns, strict=True)]
    if found.kind == "none" and any(abs(d) > RESOLUTION_LIMIT_NS for d in diffs):
        raise CounterError(
            f"single-threaded backend, but the clocks disagree by up to {max(map(abs, diffs))} ns"
        )
    if found.kind == "threads" and any(d < 0 for d in diffs):
        raise CounterError(f"process clock below schedstat by {-min(diffs)} ns with threads present")
    return diffs


@dataclass(frozen=True)
class Case:
    size: str
    level: int
    cold: bool


def cases() -> list[Case]:
    """Two sizes by three levels, once warm and once cold: 12 cases."""
    return [Case(s, lv, cold) for cold in (False, True) for s in SIZES for lv in LEVELS]


@dataclass(frozen=True)
class Result:
    case: Case
    found: Creations
    diffs: list[int]


def run_case(
    case: Case,
    reset: Callable[[], None],
    connect: Callable[[], int],
    traced_query: Callable[[int, Case], tuple[str, int, int]],
) -> Result:
    """One case. A cold case resets first, so the connection, its backend pid and the attachment are
    all new after the reset: nothing crosses it. `connect` opens a fresh connection and returns its
    host backend pid; `traced_query` attaches strace to that pid, runs the canonical query once,
    detaches, and returns strace's output with the process clock and schedstat deltas."""
    if case.cold:
        reset()
    pid = connect()
    output, process_ns, sched_ns = traced_query(pid, case)
    found = classify(output)
    return Result(case, found, check_clock(found, [process_ns], [sched_ns]))
