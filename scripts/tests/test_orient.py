"""Tests for the orientation brief.

Everything under test is pure text handling. `worktrees` and `open_prs` are thin wrappers over
`run`, which swallows every failure by design, so what matters there is that the brief degrades
instead of dying — `test_render_survives_everything_missing` pins that.
"""

import datetime as dt
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import orient

WINDOW = "| Planned build window | Mon 2026-09-21 \u2192 Sun 2026-11-15 (8 weeks) |\n"

EN = "\u2013"  # DESIGN.md writes date spans with an en dash, so the fixture must too

DESIGN = f"""
### 19.1 Phases and timeline

| Phase | Weeks | Dates | Theme | Gate |
|---|---|---|---|---|
| P0 | 1 | Sep 21 {EN} 27 | Spikes | **G0**: every spike answered |
| P1 | 2{EN}3 | Sep 28 {EN} Oct 11 | Kernel | **G1**: authorization proven |
| P5 | 8 | Dec 28 {EN} Jan 3 | Release | **G5**: exit criteria met |

### 19.2 Phase 0 — spikes and decisions (32 h planned)

| Task | h | Output |
|---|---|---|
| S1 corpus | 4 | Source manifest |
| Schema v1 | 3 | |

### 19.3 Phase 1 — kernel
"""

LOG = """# Task log — myan-authz-demo

| Field | Value |
|---|---|
| Closed when | the last entry says TASK CLOSED (the header is never edited) |

## Timeline

### 2026-09-22T01:00:00Z · PLAN · myan · claude-code/opus-5 · abc1234
Chose the fenced refresh.

### 2026-09-22T02:00:00Z · HANDOFF · myan · claude-code/opus-5 · abc1234
First sentence stops here. Second sentence adds detail nobody needs at orientation time, and it
runs on long enough to be clipped.

### 2026-09-22T03:00:00Z · COMMIT · myan · claude-code/opus-5 · parent:abc1234
feat(authz): something
"""


def test_phase_dates_resolve_and_roll_into_the_next_year():
    phases = orient.parse_phases(DESIGN, base_year=2026)
    assert [p["id"] for p in phases] == ["P0", "P1", "P5"]
    assert phases[0]["start"] == dt.date(2026, 9, 21)
    assert phases[0]["end"] == dt.date(2026, 9, 27)      # a bare day inherits September
    assert phases[1]["end"] == dt.date(2026, 10, 11)     # a span can cross a month
    assert phases[2]["end"] == dt.date(2027, 1, 3)       # and can cross the year


def test_current_phase_inside_and_outside_the_plan():
    phases = orient.parse_phases(DESIGN, base_year=2026)
    assert orient.current_phase(phases, dt.date(2026, 9, 22))[0]["id"] == "P0"
    assert orient.current_phase(phases, dt.date(2026, 10, 1))[0]["id"] == "P1"

    early, note = orient.current_phase(phases, dt.date(2026, 9, 1))
    assert early["id"] == "P0" and "not started" in note

    late, note = orient.current_phase(phases, dt.date(2027, 6, 1))
    assert late["id"] == "P5" and "past the plan" in note

    assert orient.current_phase([], dt.date(2026, 9, 22)) == (None, "no phase table found in DESIGN §19.1")


def test_phase_tasks_skips_the_header_row_and_finds_the_right_section():
    assert orient.phase_tasks(DESIGN, "P0") == [("S1 corpus", "4"), ("Schema v1", "3")]
    assert orient.phase_tasks(DESIGN, "P1") == []        # no task table written yet
    assert orient.phase_tasks(DESIGN, "P9") == []        # no such phase


def test_cards_split_by_status():
    index = (
        "| `authz` | myan | ✅ [modules/authz.md](x) | i.py | f.py |\n"
        "| `cache` | myan | 🟡 [modules/cache.md](x) | i.py | f.py |\n"
        "| `eval-data` | myan | 🟡 [modules/eval-data.md](x) | i.py | — |\n"
    )
    assert orient.parse_cards(index) == {"written": ["authz"], "placeholder": ["cache", "eval-data"]}


def test_render_survives_everything_missing():
    out = orient.render(head="", phase=None, note="no phase table found in DESIGN §19.1",
                        tasks=[], cards={"written": [], "placeholder": []}, trees=[], prs={},
                        merges=[], network=False)
    assert "(unknown)" in out
    assert "nothing — start with scripts/new-task.sh" in out
    assert "--no-network" in out


def test_render_shows_the_phase_its_tasks_and_the_cards():
    phase = {"id": "P0", "theme": "Spikes", "start": dt.date(2026, 9, 21),
             "end": dt.date(2026, 9, 27), "gate": "**G0**: every spike answered"}
    out = orient.render(head="abc1234", phase=phase, note="", tasks=[("S1 corpus", "4")],
                        cards={"written": ["authz"], "placeholder": ["cache"]}, trees=[], prs={},
                        merges=["abc1234 feat(authz): something"], network=True)
    assert "P0 Spikes · 2026-09-21 to 2026-09-27" in out
    assert "gate G0: every spike answered" in out          # the ** markers are stripped
    assert "4h  S1 corpus" in out
    assert "written      authz" in out and "placeholder  cache" in out


def test_the_year_comes_from_designs_build_window_not_from_today():
    # Regression: base_year was dt.date.today().year, so every phase shifted on 1 January and the
    # current phase silently read as past. The window is the design's own statement of when.
    assert orient.build_window_year(WINDOW + DESIGN) == 2026
    assert orient.build_window_year(DESIGN) is None          # no window row: no guess

    phases = orient.parse_phases(DESIGN, orient.build_window_year(WINDOW + DESIGN))
    assert phases[0]["start"] == dt.date(2026, 9, 21)        # stable whatever year it is run in


def test_the_brief_renders_from_a_subdirectory():
    # Regression: DESIGN/INDEX were relative to the caller's directory, so running from scripts/
    # missed every file and reported "no phase table found" instead of the phase.
    script = Path(orient.__file__)
    out = subprocess.run([sys.executable, script.name, "--no-network"], cwd=script.parent,
                         capture_output=True, text=True, timeout=60)
    assert out.returncode == 0, out.stderr
    assert "no phase table found" not in out.stdout
    assert "P0" in out.stdout and "CARDS" in out.stdout


def test_last_handoff_is_clipped_at_a_sentence():
    text = orient.last_handoff(LOG, limit=60)
    assert text == "First sentence stops here. […]"


def test_last_handoff_returns_the_whole_entry_when_it_is_short():
    assert orient.last_handoff(LOG, limit=400).startswith("First sentence stops here. Second")


def test_a_log_with_no_handoff_yet_is_not_an_error():
    assert orient.last_handoff("## Timeline\n\n### t · PLAN · a · b · c\nonly a plan\n") == ""


def test_only_a_line_that_starts_with_the_marker_closes_a_task():
    # The marker appears in every log's header, and an entry may quote it while describing a bug.
    assert "TASK CLOSED" in LOG and not orient.is_closed(LOG)
    assert not orient.is_closed(LOG + "\n### t · TEST · a · b · c\nread as TASK CLOSED wrongly\n")
    assert orient.is_closed(LOG + "\n### t · HANDOFF · a · b · c\nTASK CLOSED. Merged as abc1234.\n")


def test_render_names_the_worktree_you_are_in_and_its_review_state():
    tree = {"path": "/wt/myan-authz-demo", "branch": "myan/authz/demo",
            "log": "docs/agent-log/myan-authz-demo.md", "handoff": "stopped at the lease test",
            "closed": False, "here": True}
    out = orient.render(head="abc1234", phase=None, note="", tasks=[],
                        cards={"written": [], "placeholder": []}, trees=[tree],
                        prs={"myan/authz/demo": "PR #7 APPROVED"}, merges=[], network=True)
    assert "myan/authz/demo  [PR #7 APPROVED]  <- you are here" in out
    assert "stopped at the lease test" in out


def test_render_says_so_when_a_branch_has_no_pull_request():
    tree = {"path": "/wt/x", "branch": "myan/authz/x", "log": "l.md", "handoff": "",
            "closed": True, "here": False}
    out = orient.render(head="abc1234", phase=None, note="", tasks=[],
                        cards={"written": [], "placeholder": []}, trees=[tree], prs={},
                        merges=[], network=True)
    assert "[no pull request]" in out and "CLOSED" in out
    assert "none yet — read l.md" in out
