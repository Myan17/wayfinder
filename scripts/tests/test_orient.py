"""Tests for the orientation brief.

Everything under test is pure text handling. `worktrees` and `open_prs` are thin wrappers over
`run`, which swallows every failure by design, so what matters there is that the brief degrades
instead of dying — `test_render_survives_everything_missing` pins that.
"""

import datetime as dt
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import orient

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


def test_last_handoff_is_clipped_at_a_sentence():
    text = orient.last_handoff(LOG, limit=60)
    assert text == "First sentence stops here. […]"


def test_last_handoff_returns_the_whole_entry_when_it_is_short():
    assert orient.last_handoff(LOG, limit=400).startswith("First sentence stops here. Second")


def test_a_log_with_no_handoff_yet_is_not_an_error():
    assert orient.last_handoff("## Timeline\n\n### t · PLAN · a · b · c\nonly a plan\n") == ""


def test_the_templates_closing_sentence_is_not_a_closed_task():
    # "TASK CLOSED" appears in every log's header, explaining the marker. Only the timeline counts.
    assert "TASK CLOSED" in LOG
    assert "TASK CLOSED" not in orient.timeline(LOG)


def test_render_survives_everything_missing():
    out = orient.render(head="", phase=None, note="no phase table found in DESIGN §19.1",
                        tasks=[], cards={"written": [], "placeholder": []}, trees=[], prs={},
                        merges=[], network=False)
    assert "(unknown)" in out
    assert "nothing — start with scripts/new-task.sh" in out
    assert "--no-network" in out


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
