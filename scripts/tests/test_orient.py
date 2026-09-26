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


def test_cards_split_by_status():
    index = (
        "| `authz` | myan | ✅ [modules/authz.md](x) | i.py | f.py |\n"
        "| `cache` | myan | 🟡 [modules/cache.md](x) | i.py | f.py |\n"
        "| `eval-data` | myan | 🟡 [modules/eval-data.md](x) | i.py | — |\n"
    )
    assert orient.parse_cards(index) == {"written": ["authz"], "placeholder": ["cache", "eval-data"]}


def test_render_survives_everything_missing():
    out = orient.render(head="", phase=None, note="no phase table found in DESIGN §19.1",
                        cards={"written": [], "placeholder": []}, trees=[], prs={},
                        merges=[], network=False)
    assert "(unknown)" in out
    assert "nothing — start with scripts/new-task.sh" in out
    assert "--no-network" in out


def test_render_shows_the_phase_and_the_cards():
    phase = {"id": "P0", "theme": "Spikes", "start": dt.date(2026, 9, 21),
             "end": dt.date(2026, 9, 27), "gate": "**G0**: every spike answered"}
    out = orient.render(head="abc1234", phase=phase, note="",
                        cards={"written": ["authz"], "placeholder": ["cache"]}, trees=[], prs={},
                        merges=["abc1234 feat(authz): something"], network=True)
    assert "P0 Spikes · 2026-09-21 to 2026-09-27" in out
    assert "gate G0: every spike answered" in out          # the ** markers are stripped
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
    out = orient.render(head="abc1234", phase=None, note="",
                        cards={"written": [], "placeholder": []}, trees=[tree],
                        prs={"myan/authz/demo": "PR #7 APPROVED"}, merges=[], network=True)
    assert "myan/authz/demo  [PR #7 APPROVED]  <- you are here" in out
    assert "stopped at the lease test" in out


def test_render_says_so_when_a_branch_has_no_pull_request():
    tree = {"path": "/wt/x", "branch": "myan/authz/x", "log": "l.md", "handoff": "",
            "closed": True, "here": False}
    out = orient.render(head="abc1234", phase=None, note="",
                        cards={"written": [], "placeholder": []}, trees=[tree], prs={},
                        merges=[], network=True)
    assert "[no pull request]" in out and "CLOSED" in out
    assert "none yet — read l.md" in out


ORIENT = """
Sep 21 {EN} 27. Gate **G0**: every spike answered. 32 h planned, 3 h of contingency.

| # | Item | h | Why it is here in the order | Status |
|---|---|---|---|---|
| 1 | ADRs | 1 | G0 needs them | done #24 |
| 4 | S5 River scheduling proof | 5 | Evidence for 9.3.3 | open |
| 5 | S1 corpus | 4 | Needs ADR-0013 | open |
| 9b | S3-1b: provision the A1 | {EM} | | blocked: Myan provisions the A1 |
| 9c | S3-6 hybrid query | {EM} | Follow-up | open |

## Owner actions

These are `myan`'s to do, not an agent's.

- Add `dispatcher` as a required status check
  on main.

## Next phase
""".format(EN=EN, EM="\u2014")

S5_LOG = """# Task log — myan-platform-s5-harness

| Field | Value |
|---|---|
| Task | S5 harness against ADR-0004's rules (ORIENT item 4) |

## Timeline

### 2026-09-25T15:59:41Z · HANDOFF · myan · claude-code/opus-5 · 2bddc30
State: 11/17 pass. Next, in order: (1) rerun the six; (2) mutation checks. Brief B on #34 and #35.

### 2026-09-26T16:29:57Z · TEST · myan · claude-code/opus-5.5 · 6d11737
Remaining six at 1 run each: four PASS. B2-pause FAIL S5-4, and the failure is past any clip
because a TEST after a handoff can overturn it, which is why it is kept whole in the brief.
"""


def test_orient_items_keep_their_status_and_hours():
    items = orient.orient_items(ORIENT)
    assert [i["id"] for i in items] == ["1", "4", "5", "9b", "9c"]
    assert items[1] == {"id": "4", "item": "S5 River scheduling proof", "hours": 5, "status": "open"}
    assert items[3]["hours"] is None                           # an em dash is unsized, not zero


def test_next_item_is_the_first_open_one_that_is_not_blocked():
    assert orient.next_item(orient.orient_items(ORIENT))["id"] == "4"
    assert orient.next_item([]) is None


def test_budget_flags_open_work_the_rest_of_the_phase_cannot_hold():
    items = orient.orient_items(ORIENT)
    phase = {"id": "P0", "start": dt.date(2026, 9, 21), "end": dt.date(2026, 9, 27),
             "gate": "**G0**: x"}
    lines = orient.budget(ORIENT, items, phase, dt.date(2026, 9, 26))
    assert "9 h open (4 5; unsized 9c)" in lines[0] and "2 days left" in lines[0]
    assert "3 h contingency" in lines[0]
    assert len(lines) == 1                                     # 32 h / 7 days holds 9 h in 2 days
    tight = orient.budget(ORIENT, items, phase, dt.date(2026, 9, 27))
    assert "rule 5" in tight[1]                                # 1 day holds about 4.6 h, not 9


def test_owner_actions_are_the_bullets_of_their_section_only():
    assert orient.owner_actions(ORIENT) == ["Add `dispatcher` as a required status check on main."]
    assert orient.owner_actions("no such section") == []


def test_a_log_names_its_orient_item_and_what_came_after_its_handoff():
    assert orient.orient_item_of(S5_LOG) == "4"
    assert orient.orient_item_of(LOG) is None
    handoff, later = orient.handoff_and_after(S5_LOG)
    assert handoff.endswith("Brief B on #34 and #35.")         # whole entry, not clipped
    assert len(later) == 1 and later[0].startswith("TEST 2026-09-26: Remaining six")
    assert later[0].endswith("kept whole in the brief.")      # a TEST is never clipped


def test_merged_pull_requests_are_marked_where_a_handoff_mentions_them():
    assert orient.mark_merged("Waiting on B for #34 and #35.", {34}) == \
        "Waiting on B for #34 [merged] and #35."


def test_render_resumes_the_next_item_in_its_worktree_instead_of_restarting_it():
    tree = {"path": "/wt/s5", "branch": "myan/platform/s5-harness", "log": "l.md",
            "handoff": "State: 11/17 pass. [\u2026]", "closed": False, "here": False,
            "item": "4", "task": "S5 harness (ORIENT item 4)",
            "full": "State: 11/17 pass. Next, in order: (1) rerun the six.",
            "later": ["TEST 2026-09-26: four PASS"]}
    items = orient.orient_items(ORIENT)
    out = orient.render(head="abc1234", phase=None, note="", cards={"written": [], "placeholder": []},
                        trees=[tree], prs={}, merges=[], network=True, items=items,
                        actions=["Add dispatcher."], budget_lines=["BUDGET x"])
    assert "NEXT  item 4 · S5 River scheduling proof" in out
    assert "resume  myan/platform/s5-harness" in out and "do not run new-task.sh" in out
    assert "Next, in order: (1) rerun the six." in out         # the full handoff, not the clip
    assert "since    TEST 2026-09-26: four PASS" in out
    assert "OWNER ACTIONS" in out and "Add dispatcher." in out
    assert out.index("NEXT") < out.index("OTHER IN FLIGHT") or "OTHER IN FLIGHT" not in out


def test_render_says_how_to_start_the_next_item_when_no_worktree_has_it():
    out = orient.render(head="abc1234", phase=None, note="", cards={"written": [], "placeholder": []},
                        trees=[], prs={}, merges=[], network=True,
                        items=orient.orient_items(ORIENT))
    assert "start   scripts/new-task.sh" in out and "(ORIENT item 4)" in out
