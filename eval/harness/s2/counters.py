"""Spike S2's CPU counters, exactly as ADR-0019's "How CPU is accounted" pins them.

| Stage           | Charged to                                  | Counter here                      |
|-----------------|---------------------------------------------|-----------------------------------|
| Query embedding | every thread of the query Ollama container  | `cgroup_usage_usec` (cgroup v2)   |
| Hybrid SQL      | every thread of the Postgres backend        | `process_cpu_ns` (process clock)  |
| Rerank          | the calling harness thread                  | `thread_cpu_ns`                   |

The calibration's reference is `executed_ticks` over `/proc/stat`. Tick counters such as
`/proc/<pid>/stat`'s `utime` are never used for a per-call value. Everything that reads the machine
is Linux-only and is passed paths or pids, so the parsers are tested anywhere with fixtures.
Any failed check raises `CounterError`, which S2 reports as an error, never as a result.
"""

from __future__ import annotations

import ctypes
import ctypes.util
import os
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

CGROUP_ROOT = Path("/sys/fs/cgroup")
PROC = Path("/proc")
RESOLUTION_LIMIT_NS = 10_000  # "a nonzero difference below 10 µs"


class CounterError(RuntimeError):
    """A counter is missing, unreadable or too coarse. S2 stops as an error."""


# --- cgroup v2: query embedding ---------------------------------------------------------------


def cgroup_of(pid: int, proc: Path = PROC, root: Path = CGROUP_ROOT) -> Path:
    """The cgroup v2 directory of a host pid, from its unified `0::` line."""
    for line in (proc / str(pid) / "cgroup").read_text().splitlines():
        if line.startswith("0::"):
            return root / line[3:].lstrip("/")
    raise CounterError(f"pid {pid} has no cgroup v2 entry; the host must run the unified hierarchy")


def cgroup_usage_usec(cgroup: Path) -> int:
    """`usage_usec` from the cgroup's `cpu.stat`: all CPU of every thread of every process in it."""
    for line in (cgroup / "cpu.stat").read_text().splitlines():
        key, _, value = line.partition(" ")
        if key == "usage_usec":
            return int(value)
    raise CounterError(f"{cgroup}/cpu.stat has no usage_usec")


# --- the Postgres backend: hybrid SQL ---------------------------------------------------------


def nspid(pid: int, proc: Path = PROC) -> list[int]:
    """The pid's `NSpid` chain, outermost (host) first, innermost (the container's view) last."""
    for line in (proc / str(pid) / "status").read_text().splitlines():
        if line.startswith("NSpid:"):
            return [int(x) for x in line.split()[1:]]
    raise CounterError(f"pid {pid} has no NSpid line")


def backend_host_pid(backend_pid: int, postgres_cgroup: Path, proc: Path = PROC) -> int:
    """The host pid of the backend whose `pg_backend_pid()` is `backend_pid`.

    Only processes in the Postgres container's cgroup are candidates, so a process in another
    namespace with the same inner pid can never match. Exactly one match is required.
    """
    pids = [int(p) for p in (postgres_cgroup / "cgroup.procs").read_text().split()]
    hits = [p for p in pids if nspid(p, proc)[-1] == backend_pid]
    if len(hits) != 1:
        raise CounterError(f"backend pid {backend_pid}: {len(hits)} host pids match, need exactly 1")
    return hits[0]


def _libc() -> ctypes.CDLL:
    return ctypes.CDLL(ctypes.util.find_library("c") or None, use_errno=True)


def process_clock(host_pid: int) -> int:
    """`clock_getcpuclockid(host_pid)`: the scheduler's runtime summed over the whole thread group,
    live and exited threads alike."""
    clock = ctypes.c_int()
    rc = _libc().clock_getcpuclockid(ctypes.c_int(host_pid), ctypes.byref(clock))
    if rc != 0:
        raise CounterError(f"clock_getcpuclockid({host_pid}) failed: {os.strerror(rc)}")
    return clock.value


def process_cpu_ns(clock: int) -> int:
    return time.clock_gettime_ns(clock)


def schedstat_ns(host_pid: int, proc: Path = PROC) -> int:
    """The main thread's run time from its `schedstat`. One task only: used by the preflight's
    agreement check, never as the SQL counter."""
    return int((proc / str(host_pid) / "task" / str(host_pid) / "schedstat").read_text().split()[0])


# --- the harness thread: rerank ---------------------------------------------------------------


def thread_cpu_ns() -> int:
    return time.thread_time_ns()


# --- the calibration reference ----------------------------------------------------------------


@dataclass(frozen=True)
class Executed:
    executed: int  # user + nice + system + irq + softirq, in USER_HZ ticks
    iowait: int
    steal: int


def executed_ticks(proc_stat: str) -> Executed:
    """The aggregate `cpu` line of `/proc/stat`. `idle`, `iowait` and `steal` are not execution, and
    `guest` and `guest_nice` are already inside `user` and `nice`, so neither is added."""
    for line in proc_stat.splitlines():
        f = line.split()
        if f and f[0] == "cpu":
            user, nice, system, _idle, iowait, irq, softirq, steal = (int(x) for x in f[1:9])
            return Executed(user + nice + system + irq + softirq, iowait, steal)
    raise CounterError("/proc/stat has no aggregate cpu line")


# --- counter checks ---------------------------------------------------------------------------


def check_cgroup_v2(root: Path = CGROUP_ROOT) -> None:
    if not (root / "cgroup.controllers").exists():
        raise CounterError(f"{root} is not a cgroup v2 mount")


def check_resolution(read_ns: Callable[[], int], name: str) -> int:
    """Two back-to-back reads, taken while the caller keeps the target busy, must differ by more
    than nothing and less than 10 µs. A coarser or frozen counter fails. Returns the difference."""
    first = read_ns()
    diff = read_ns() - first
    if not 0 < diff < RESOLUTION_LIMIT_NS:
        raise CounterError(f"{name}: two reads differ by {diff} ns, need 0 < diff < 10 µs")
    return diff
