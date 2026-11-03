import os
import sys
import time
from pathlib import Path

import pytest
from s2 import counters
from s2.counters import CounterError

linux = pytest.mark.skipif(sys.platform != "linux", reason="the real counters exist only on Linux")


def proc_entry(proc, pid, cgroup="0::/system.slice/docker-pg.scope\n", nspid=(4100, 77)):
    d = proc / str(pid)
    d.mkdir(parents=True)
    (d / "cgroup").write_text(cgroup)
    (d / "status").write_text(f"Name:\tpostgres\nNSpid:\t{' '.join(map(str, nspid))}\n")
    return d


def test_a_pids_cgroup_is_its_unified_line_under_the_v2_root(tmp_path):
    proc_entry(tmp_path / "proc", 4100, cgroup="12:cpu:/legacy\n0::/system.slice/docker-pg.scope\n")
    got = counters.cgroup_of(4100, tmp_path / "proc", tmp_path / "cg")
    assert got == tmp_path / "cg/system.slice/docker-pg.scope"
    proc_entry(tmp_path / "proc", 4101, cgroup="12:cpu:/legacy\n")
    with pytest.raises(CounterError, match="no cgroup v2"):
        counters.cgroup_of(4101, tmp_path / "proc", tmp_path / "cg")


def test_cgroup_usage_is_usage_usec_and_a_missing_key_is_an_error(tmp_path):
    (tmp_path / "cpu.stat").write_text("usage_usec 123456\nuser_usec 100000\nsystem_usec 23456\n")
    assert counters.cgroup_usage_usec(tmp_path) == 123456
    (tmp_path / "cpu.stat").write_text("user_usec 1\n")
    with pytest.raises(CounterError, match="usage_usec"):
        counters.cgroup_usage_usec(tmp_path)


def test_the_backend_host_pid_matches_nspid_only_inside_the_postgres_cgroup(tmp_path):
    proc, cg = tmp_path / "proc", tmp_path / "cg"
    proc_entry(proc, 4100, nspid=(4100, 77))  # the backend
    proc_entry(proc, 4200, nspid=(4200, 78))  # another backend
    proc_entry(proc, 5100, nspid=(5100, 77))  # same inner pid, another container: not listed
    cg.mkdir()
    (cg / "cgroup.procs").write_text("4100\n4200\n")
    assert counters.backend_host_pid(77, cg, proc) == 4100
    with pytest.raises(CounterError, match="0 host pids"):
        counters.backend_host_pid(99, cg, proc)
    (cg / "cgroup.procs").write_text("4100\n5100\n")
    with pytest.raises(CounterError, match="2 host pids"):
        counters.backend_host_pid(77, cg, proc)


def test_schedstat_is_the_main_threads_first_field(tmp_path):
    task = tmp_path / "4100/task/4100"
    task.mkdir(parents=True)
    (task / "schedstat").write_text("987654321 1234 56\n")
    assert counters.schedstat_ns(4100, tmp_path) == 987654321


def test_executed_cpu_excludes_idle_iowait_and_steal_and_never_adds_guest():
    #           user nice system idle iowait irq softirq steal guest guest_nice
    stat = "cpu  100 20 30 5000 40 5 6 70 80 9\ncpu0 50 10 15 2500 20 2 3 35 40 4\nintr 1\n"
    assert counters.executed_ticks(stat) == counters.Executed(executed=161, iowait=40, steal=70)
    with pytest.raises(CounterError, match="aggregate cpu"):
        counters.executed_ticks("cpu0 1 2 3 4 5 6 7 8\n")


def test_resolution_needs_a_nonzero_difference_below_10_microseconds():
    def reads(*values):
        it = iter(values)
        return lambda: next(it)

    assert counters.check_resolution(reads(1_000, 1_900), "x") == 900
    for frozen_or_coarse in ((5, 5), (0, 10_000), (0, 10_000_000)):
        with pytest.raises(CounterError, match="need 0 < diff"):
            counters.check_resolution(reads(*frozen_or_coarse), "x")


def test_cgroup_v2_check_needs_cgroup_controllers(tmp_path):
    with pytest.raises(CounterError, match="not a cgroup v2"):
        counters.check_cgroup_v2(tmp_path)
    (tmp_path / "cgroup.controllers").write_text("cpu memory\n")
    counters.check_cgroup_v2(tmp_path)


@linux
def test_this_process_clock_counts_a_thread_that_has_already_exited():
    import threading

    clock = counters.process_clock(os.getpid())
    before = counters.process_cpu_ns(clock)

    def spin():
        end = time.thread_time_ns() + 50_000_000
        while time.thread_time_ns() < end:
            pass

    t = threading.Thread(target=spin)
    t.start()
    t.join()  # the thread is gone before the second read
    assert counters.process_cpu_ns(clock) - before >= 50_000_000


@linux
def test_the_real_thread_and_process_clocks_pass_the_resolution_check():
    clock = counters.process_clock(os.getpid())
    assert counters.check_resolution(counters.thread_cpu_ns, "thread clock") > 0
    assert counters.check_resolution(lambda: counters.process_cpu_ns(clock), "process clock") > 0
    main = counters.schedstat_ns(os.getpid())
    assert main > 0 and counters.executed_ticks(Path("/proc/stat").read_text()).executed > 0


@linux
def test_an_unknown_pid_has_no_process_clock():
    with pytest.raises(CounterError, match="clock_getcpuclockid"):
        counters.process_clock(2**22 + 12345)  # above the default pid_max
