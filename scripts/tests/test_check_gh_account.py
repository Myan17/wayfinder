"""Tests for the GitHub-account guard. Pure text handling; gh and git are the only inputs."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import check_gh_account as guard

ROSTER = """
```yaml
engineers:
  - handle: myan
    name: Myan Gupta
    github: Myan17
  - handle: gupta958
    name: Engineer B
    github: Gupta958
```
"""


def test_the_operator_maps_to_their_roster_login():
    assert guard.expected_login(ROSTER, "myan") == "Myan17"
    assert guard.expected_login(ROSTER, "gupta958") == "Gupta958"
    assert guard.expected_login(ROSTER, "nobody") is None


def test_the_right_account_passes_whatever_its_case():
    assert guard.problem("myan", "myan17", ROSTER) is None


def test_the_reviewers_account_is_refused_for_the_implementer():
    # The 2026-09-26 incident: PRs #36-#39 were opened as gupta958 by myan's session.
    msg = guard.problem("myan", "gupta958", ROSTER)
    assert "gupta958" in msg and "Myan17" in msg
    assert "gh auth switch --hostname github.com --user Myan17" in msg


def test_unknown_operator_or_login_fails_closed():
    assert "wayfinder.operator" in guard.problem("", "Myan17", ROSTER)
    assert "not in docs/team/ROSTER.md" in guard.problem("nobody", "Myan17", ROSTER)
    assert "could not read" in guard.problem("myan", "", ROSTER)
