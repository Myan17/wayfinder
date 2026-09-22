"""Tests for the orientation brief's plan half.

Everything under test is pure text handling over DESIGN and the context index. `run` swallows every
failure by design, so what matters at the edges is that the brief degrades instead of dying —
`test_render_survives_everything_missing` pins that.
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
                        tasks=[], cards={"written": [], "placeholder": []}, merges=[])
    assert "(unknown)" in out
    assert "no phase table found" in out


def test_render_shows_the_phase_its_tasks_and_the_cards():
    phase = {"id": "P0", "theme": "Spikes", "start": dt.date(2026, 9, 21),
             "end": dt.date(2026, 9, 27), "gate": "**G0**: every spike answered"}
    out = orient.render(head="abc1234", phase=phase, note="", tasks=[("S1 corpus", "4")],
                        cards={"written": ["authz"], "placeholder": ["cache"]},
                        merges=["abc1234 feat(authz): something"])
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
