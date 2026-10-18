"""The committed D-3 report (gupta958's ruling, 2026-10-17) is what s1.d3_probe writes, unedited."""

import collections
import json
from pathlib import Path

from s1 import d3_probe

REPORT = Path(__file__).parents[2] / "datasets" / "s1-d3-probe.json"
RUN_3_PAIRS = "d5ae8d34a7f0d13c2fbbbe12bc298d5827104d7f605bff249de86ffe9fcb3fcc"


def _report():
    return json.loads(REPORT.read_text())


def test_the_report_is_the_probes_encoding_of_its_own_rows():
    report = _report()
    assert REPORT.read_text() == d3_probe.encoded(report) + "\n"
    assert report["summary"] == json.loads(json.dumps(d3_probe.summary(report["rows"])))
    assert report["sample"] == d3_probe.SAMPLE


def test_each_rows_deltas_and_d3_class_follow_from_its_own_times():
    for row in _report()["rows"]:
        pair = {"github_repo_id": row["github_repo_id"], "issue": row["issue"], "pr": row["pr"]}
        pair |= {"split": row["split"], "strong": row["strong_in_run_3"]}
        issue = {"closedAt": row["closed_at"], "updatedAt": row["updated_at"]}
        repository = {f"i{row['issue']}": issue, f"p{row['pr']}": {"mergedAt": row["merged_at"]}}
        assert d3_probe.measure(pair, repository) == row


def test_the_report_covers_run_3_with_four_graphql_calls_and_no_rest():
    report = _report()
    assert report["pairs_sha256"] == RUN_3_PAIRS
    assert report["api_calls"] == {"graphql": 4, "rest": 0}


def test_the_rows_are_three_weak_and_one_strong_per_cell_and_hold_no_text():
    rows = _report()["rows"]
    cells = collections.Counter((r["github_repo_id"], r["split"], r["strong_in_run_3"]) for r in rows)
    assert len(rows) == 48 and len({(r["github_repo_id"], r["issue"], r["pr"]) for r in rows}) == 48
    assert set(cells.values()) == {1, 3} and len(cells) == 24
    assert all(n == (1 if strong else 3) for (_, _, strong), n in cells.items())
    assert not {"title", "body"} & set().union(*rows)
