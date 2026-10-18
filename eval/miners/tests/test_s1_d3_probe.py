"""The D-3 diagnostic (gupta958, 2026-10-17): sample, query, buckets and report, with no network."""

import datetime as dt
import hashlib
import itertools
import json
import random

import pytest
from s1 import corpus, d3_probe, github, landing

NO_SCOPES = {"x-oauth-scopes": ""}


def _pair(repo, issue, pr, split="dev", strong=False):
    return {"github_repo_id": repo, "issue": issue, "pr": pr, "split": split, "strong": strong}


def _corpus():  # 6 pairs in every (repository, split, strong) cell of 2 repositories
    cells = itertools.product((1, 2), d3_probe.SPLITS, (False, True), range(6))
    return [_pair(repo, n, 1000 + n, split, strong) for n, (repo, split, strong, _) in enumerate(cells)]


def _in(rows, cell):
    return [p for p in rows if (p["github_repo_id"], p["split"], p["strong"]) == cell]


def _key(p):
    return hashlib.sha256(f"{p['github_repo_id']}:{p['issue']}:{p['pr']}".encode()).hexdigest()


def test_the_sample_is_three_weak_and_one_strong_per_cell_by_lowest_sha256_in_any_input_order():
    rows = _corpus()
    picked = d3_probe.sample(rows)
    assert len(picked) == 2 * 3 * 4
    for cell in itertools.product((1, 2), d3_probe.SPLITS, (False, True)):
        assert _in(picked, cell) == sorted(_in(rows, cell), key=_key)[: 1 if cell[2] else 3]
    assert d3_probe.sample(random.Random(7).sample(rows, len(rows))) == picked


def test_a_cell_too_small_to_sample_fails_closed():
    rows = [p for p in _corpus() if not (p["github_repo_id"] == 2 and p["split"] == "test" and p["strong"])]
    with pytest.raises(ValueError, match="cell 2 test strong=True has 0"):
        d3_probe.sample(rows)


def test_the_query_reads_only_the_three_times_and_reads_a_shared_pr_once():
    q = d3_probe.query([_pair(1, 5, 9), _pair(1, 6, 9)])
    assert "i5: issue(number: 5) { closedAt updatedAt }" in q
    assert q.count("p9: pullRequest(number: 9) { mergedAt }") == 1
    for field in ("title", "body", "author", "comments", "labels"):
        assert field not in q


def test_buckets_are_disjoint_at_5_s_60_s_and_1_h():
    seconds = (-30, 0, 5, 6, 60, 61, 3600, 3601, None)
    want = ["<=5s"] * 3 + ["<=60s"] * 2 + ["<=1h"] * 2 + [">1h", "not closed"]
    assert [d3_probe.bucket(x) for x in seconds] == want


def _repo_result(issue, pr, merged, closed, updated):
    return {f"i{issue}": {"closedAt": closed, "updatedAt": updated}, f"p{pr}": {"mergedAt": merged}}


def test_measure_reports_both_deltas_and_d3_on_todays_updated_at():
    got = d3_probe.measure(
        _pair(1, 5, 9, "test", True),
        _repo_result(5, 9, "2024-01-01T00:00:00Z", "2024-01-01T00:00:02Z", "2024-01-01T00:00:03Z"),
    )
    assert got["closed_minus_merged_s"] == 2 and got["updated_minus_merged_s"] == 3
    assert got["weak_now"] is True and got["strong_in_run_3"] is True
    assert not {"title", "body"} & set(got) and len(got) == 11


def test_an_issue_that_is_open_again_has_no_close_delta():
    got = d3_probe.measure(
        _pair(1, 5, 9), _repo_result(5, 9, "2024-01-01T00:00:00Z", None, "2024-01-01T00:00:00Z")
    )
    assert got["closed_minus_merged_s"] is None and got["weak_now"] is False


@pytest.mark.parametrize(
    "repository",
    [
        {"i5": None, "p9": {"mergedAt": "2024-01-01T00:00:00Z"}},
        {"i5": {"closedAt": None, "updatedAt": None}, "p9": None},
    ],
)
def test_an_unreadable_issue_or_pr_fails_closed(repository):
    with pytest.raises(RuntimeError, match="not readable"):
        d3_probe.measure(_pair(1, 5, 9), repository)


def _row(repo, split, strong, closed, updated):
    keys = ("github_repo_id", "split", "strong_in_run_3", "closed_minus_merged_s", "updated_minus_merged_s")
    return dict(zip(keys, (repo, split, strong, closed, updated), strict=True)) | {
        "issue": 1,
        "pr": 2,
        "weak_now": updated > 0,
    }


def test_the_summary_counts_buckets_by_group_and_names_strong_controls_now_weak():
    rows = [
        _row(1, "dev", False, 1, 2),
        _row(1, "test", False, 30, 4000),
        _row(2, "dev", True, -10, 0),
        _row(2, "held_out", True, 2, 2),
    ]
    s = d3_probe.summary(rows)
    assert s["closed_minus_merged_s"]["all"] == {"<=5s": 3, "<=60s": 1, "<=1h": 0, ">1h": 0, "not closed": 0}
    assert s["updated_minus_merged_s"]["by_repository"]["1"] == dict.fromkeys(d3_probe.BUCKETS, 0) | {
        "<=5s": 1,
        ">1h": 1,
    }
    assert s["updated_minus_merged_s"]["by_split"]["dev"]["<=5s"] == 2
    assert s["closed_minus_merged_s"]["by_run_3_class"]["strong"]["<=5s"] == 2
    assert s["closed_minus_merged_s"]["negative"] == 1  # -10 s
    assert s["updated_minus_merged_s"]["negative"] == 0  # 0 s is not negative
    assert s["strong_controls"] == 2 and s["strong_controls_now_weak"] == [[2, 1, 2]]


def test_the_encoding_is_json_with_one_line_per_row():
    value = {"rows": [{"b": 1, "a": None}, {"a": 2}], "summary": {"x": {"all": {"<=5s": 1}}}, "n": 3}
    text = d3_probe.encoded(value)
    assert json.loads(text) == value
    assert '    {"a": null, "b": 1},' in text.splitlines()
    assert '      "all": {"<=5s": 1}' in text.splitlines()


def _replay(bodies, headers=NO_SCOPES):
    sent = []

    def send(body):
        sent.append(json.loads(body))
        return 200, headers, {"data": bodies.pop(0)}

    return send, sent


def _dataset(tmp_path):
    """A valid pairs file and manifest from `corpus.build`: 3 repositories, 3+ weak and strong per cell."""
    pair_keys = ("repo_id", "issue", "pr", "base", "reason", "gold", "strong", "merged_at")
    entry_keys = (
        "repo",
        "github_repo_id",
        "lang",
        "as_of_commit",
        "spdx",
        "rules",
        "file_count",
        "chunk_estimate",
    )
    rules = {r: {"value": None, "pass": True} for r in ("S1-1", "S1-2", "S1-3", "S1-4", "S1-5")}
    when, measured = dt.datetime(2024, 1, 1, tzinfo=dt.UTC), []
    for rid, lang in ((1, "py"), (2, "go"), (3, "py")):
        values = [
            (rid, n, n, "a" * 40, None, ["a.py"], n % 2 == 0, when + dt.timedelta(days=n))
            for n in range(1, 31)
        ]
        pairs = [dict(zip(pair_keys, v, strict=True)) for v in values]
        entry = (f"o/r{rid}", rid, lang, "a" * 40, "MIT", rules, 1, 10)
        measured.append({"entry": dict(zip(entry_keys, entry, strict=True)), "pairs": pairs})
    data, manifest = corpus.build(measured, "abc1234", {"graphql": 0, "rest": 0})
    (tmp_path / "pairs.jsonl").write_bytes(data)
    (tmp_path / "manifest.json").write_text(landing.encoded(manifest))
    return data, [json.loads(line) for line in data.splitlines()]


def _answers(picked, repo):
    out = {}
    for p in (p for p in picked if p["github_repo_id"] == repo):  # weak: +1 s; strong: before the merge
        later = "2023-12-31T00:00:00Z" if p["strong"] else "2024-01-01T00:00:01Z"
        out |= _repo_result(p["issue"], p["pr"], "2024-01-01T00:00:00Z", "2024-01-01T00:00:01Z", later)
    return {"repository": out}


def _run(tmp_path, monkeypatch, send):
    monkeypatch.setattr(github, "urllib_transport", lambda token: send)
    monkeypatch.setenv("WAYFINDER_S1_TOKEN", "t")
    return d3_probe.main([str(tmp_path / "pairs.jsonl"), str(tmp_path / "out.json")])


def test_the_command_makes_one_read_only_query_per_repository_and_writes_the_report(tmp_path, monkeypatch):
    data, rows = _dataset(tmp_path)
    picked = d3_probe.sample(rows)
    send, sent = _replay([_answers(picked, r) for r in (1, 2, 3)])
    assert _run(tmp_path, monkeypatch, send) == 0
    assert [s["variables"]["name"] for s in sent] == ["r1", "r2", "r3"]
    report = json.loads((tmp_path / "out.json").read_text())
    assert report["pairs_sha256"] == hashlib.sha256(data).hexdigest()
    assert report["api_calls"] == {"graphql": 3, "rest": 0}
    assert len(report["rows"]) == 36 and report["summary"]["strong_controls_now_weak"] == []
    assert report["summary"]["updated_minus_merged_s"]["by_run_3_class"]["weak"]["<=5s"] == 27


def test_a_tampered_pairs_file_is_refused_before_any_transport_or_report(tmp_path, monkeypatch, capsys):
    data, _ = _dataset(tmp_path)
    (tmp_path / "pairs.jsonl").write_bytes(data.replace(b'"strong": true', b'"strong": false', 1))
    monkeypatch.setattr(github, "urllib_transport", lambda token: pytest.fail("transport created"))
    monkeypatch.setattr(github.Client, "query", lambda *a, **k: pytest.fail("query made"))
    monkeypatch.setenv("WAYFINDER_S1_TOKEN", "t")
    assert d3_probe.main([str(tmp_path / "pairs.jsonl"), str(tmp_path / "out.json")]) == 1
    assert "sha256 does not match the manifest" in capsys.readouterr().err
    assert not (tmp_path / "out.json").exists()


def test_a_scoped_token_stops_the_diagnostic(tmp_path, monkeypatch):
    _dataset(tmp_path)
    with pytest.raises(PermissionError, match="S1-5"):
        _run(tmp_path, monkeypatch, _replay([{}], headers={"x-oauth-scopes": "repo"})[0])
    assert not (tmp_path / "out.json").exists()


def test_the_command_refuses_to_start_without_the_token(monkeypatch):
    monkeypatch.delenv("WAYFINDER_S1_TOKEN", raising=False)
    assert d3_probe.main([]) == 2
