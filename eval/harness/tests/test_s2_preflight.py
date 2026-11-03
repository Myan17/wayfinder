import pytest
from s2 import preflight
from s2.counters import CounterError

THREAD = (
    "clone3({flags=CLONE_VM|CLONE_FS|CLONE_FILES|CLONE_SIGHAND|CLONE_THREAD|CLONE_SYSVSEM|"
    "CLONE_SETTLS|CLONE_PARENT_SETTID|CLONE_CHILD_CLEARTID, child_tid=0x7f, parent_tid=0x7f, "
    "exit_signal=0, stack=0x7f, stack_size=0x7fff00, tls=0x7f} => {parent_tid=[4201]}, 88) = 4201"
)
CHILD = (
    "clone(child_stack=NULL, flags=CLONE_CHILD_CLEARTID|CLONE_CHILD_SETTID|SIGCHLD, child_tidptr=0x7f) = 4300"
)


def test_the_strace_command_is_adr_0019s():
    assert preflight.strace_command(4100) == [
        "strace",
        "-f",
        "-qq",
        "-e",
        "trace=clone,clone3,fork,vfork",
        "-p",
        "4100",
    ]


def test_no_creation_is_none():
    assert preflight.classify("").kind == "none"
    assert preflight.classify("--- SIGALRM {si_signo=SIGALRM} ---\n").kind == "none"


def test_clone_thread_creations_are_threads_even_from_a_thread_and_when_split():
    out = "\n".join(
        [
            THREAD,
            "[pid  4201] clone3({flags=CLONE_VM|CLONE_THREAD|CLONE_SIGHAND, stack=0x1}, 88 <unfinished ...>",
            "[pid  4100] --- SIGUSR1 ---",
            "[pid  4201] <... clone3 resumed> => {parent_tid=[4202]}, 88) = 4202",
            "clone3({flags=CLONE_VM|CLONE_THREAD}, 88) = -1 EAGAIN (Resource temporarily unavailable)",
        ]
    )
    found = preflight.classify(out)
    assert found.kind == "threads" and found.threads == (4201, 4202) and found.children == ()


@pytest.mark.parametrize(
    "line",
    [CHILD, "fork() = 4301", "vfork() = 4302", "clone3({flags=CLONE_VM, exit_signal=SIGCHLD}, 88) = 4303"],
)
def test_any_child_process_is_a_child(line):
    found = preflight.classify(THREAD + "\n" + line)
    assert found.kind == "child" and len(found.children) == 1 and found.threads == (4201,)


def test_an_unreadable_creation_or_a_call_that_never_resumes_fails_closed():
    with pytest.raises(ValueError, match="cannot parse"):
        preflight.classify("clone(garbled")
    with pytest.raises(ValueError, match="never resumed"):
        preflight.classify("[pid 9] fork( <unfinished ...>")
    with pytest.raises(ValueError, match="no start"):
        preflight.classify("[pid 9] <... fork resumed>) = 4")


def test_clock_rules_per_kind():
    none, threads = preflight.Creations((), ()), preflight.Creations((4201,), ())
    assert preflight.check_clock(none, [1_000_000, 2_000_000], [995_000, 2_010_000]) == [5_000, -10_000]
    with pytest.raises(CounterError, match="disagree"):
        preflight.check_clock(none, [1_000_000], [989_999])
    assert preflight.check_clock(threads, [3_000_000], [1_000_000]) == [2_000_000]
    with pytest.raises(CounterError, match="below schedstat"):
        preflight.check_clock(threads, [999_999], [1_000_000])
    with pytest.raises(CounterError, match="child processes"):
        preflight.check_clock(preflight.Creations((), (4300,)), [1], [1])


def test_twelve_cases_two_sizes_three_levels_warm_and_cold():
    cs = preflight.cases()
    assert len(cs) == 12 and len(set(cs)) == 12
    assert {(c.size, c.level) for c in cs if c.cold} == {
        (s, lv) for s in ("real", "60k") for lv in (1, 10, 100)
    }
    assert {(c.size, c.level) for c in cs if not c.cold} == {(c.size, c.level) for c in cs if c.cold}


def test_a_cold_case_resets_before_it_connects_and_traces_only_the_new_backend():
    calls, pids = [], iter([501, 502])

    def connect():
        calls.append("connect")
        return next(pids)

    def traced(pid, case):
        calls.append(("trace", pid))
        return "", 1_000_000, 1_000_000

    warm = preflight.run_case(
        preflight.Case("real", 1, False), lambda: calls.append("reset"), connect, traced
    )
    cold = preflight.run_case(preflight.Case("real", 1, True), lambda: calls.append("reset"), connect, traced)
    assert calls == ["connect", ("trace", 501), "reset", "connect", ("trace", 502)]
    assert warm.found.kind == cold.found.kind == "none" and cold.diffs == [0]
