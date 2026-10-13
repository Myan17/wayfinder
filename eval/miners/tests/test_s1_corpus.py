"""S1's corpus: D-6 survivors, selection rounds and the dataset, from measured candidates built in memory."""

import datetime as dt
import json

import pytest
from s1 import corpus, dataset, repo

T0 = dt.datetime(2026, 1, 1, tzinfo=dt.UTC)
SHA = "0123456789abcdef" * 2 + "01234567"


def _pair(rid, pr, issue=None, gold=("a.py",), strong=True, reason=None, day=0):
    return {
        "repo_id": rid,
        "issue": issue or pr,
        "pr": pr,
        "base": None if reason and "D-1" in reason else SHA,
        "reason": reason.removeprefix("D-1: ") if reason else None,
        "gold": list(gold),
        "strong": strong,
        "merged_at": T0 + dt.timedelta(days=day or pr),
    }


def _cand(rid, lang, strong, chunks=1000, ok=True, extra=()):
    rules = {r: {"value": None, "pass": ok} for r in ("S1-1", "S1-2", "S1-3", "S1-4", "S1-5")}
    entry = {
        "repo": f"o/r{rid}",
        "github_repo_id": rid,
        "lang": lang,
        "as_of_commit": SHA,
        "spdx": "MIT",
        "rules": rules,
        "file_count": 10,
        "chunk_estimate": chunks,
    }
    return {"entry": entry, "pairs": [_pair(rid, n) for n in range(1, strong + 1)] + list(extra)}


def test_survivors_count_each_exclusion_reason_under_d6():
    eleven = [f"f{i}.py" for i in range(11)]
    cand = _cand(
        1,
        "py",
        1,
        extra=[
            _pair(1, 50, reason="D-1: first commit not in the clone"),
            _pair(1, 51, reason=repo.MERGE_IN_HISTORY),
            _pair(1, 52, gold=()),
            _pair(1, 53, gold=eleven),
        ],
    )
    kept, excluded = corpus.survivors(cand, 10)
    assert [p["pr"] for p in kept] == [1]
    assert excluded == {
        "D-1: first commit not in the clone": 1,
        "merge_commit_in_pr_history": 1,
        "D-2: no source files": 1,
        "D-2: more than 10 source files": 1,
    }
    assert [p["pr"] for p in corpus.survivors(cand, 15)[0]] == [1, 53]


def test_one_round_when_the_winner_meets_the_a3_bar():
    done = corpus.rounds(
        [_cand(1, "py", 150), _cand(2, "go", 100), _cand(3, "go", 50), _cand(4, "py", 5, ok=False)]
    )
    assert len(done) == 1
    assert done[0]["winner"] == [1, 2, 3] and done[0]["strong"] == 300 and done[0]["max_files"] == 10


def test_r03_step_2_relaxes_d2_only_when_the_winner_is_short():
    wide = [_pair(1, 900 + i, gold=[f"f{j}.py" for j in range(12)]) for i in range(40)]
    done = corpus.rounds([_cand(1, "py", 100, extra=wide), _cand(2, "go", 100), _cand(3, "go", 80)])
    assert [r["max_files"] for r in done] == [10, 15]
    assert done[0]["strong"] == 280 and done[1]["strong"] == 320


def test_no_feasible_corpus_names_the_constraint_and_still_writes_the_measurements():
    measured = [_cand(1, "py", 200), _cand(2, "py", 200), _cand(3, "go", 200)]
    measured[2]["entry"]["rules"]["S1-3"]["pass"] = False  # one failed rule is enough to disqualify
    data, manifest = corpus.build(measured, SHA, {"graphql": 3, "rest": 0})
    assert data == b"" and manifest["selected"] == []
    assert manifest["selection_rounds"] == [
        {
            "candidates": [1, 2, 3],
            "max_files": 10,
            "feasible": [],
            "winner": None,
            "no_feasible_reason": "qualification count",
        }
    ]
    assert len(manifest["candidates"]) == 3


def test_build_writes_a_dataset_that_passes_its_landing_checks():
    weak = _pair(2, 7, issue=70, strong=False)
    measured = [
        _cand(1, "py", 3, extra=[_pair(1, 5, issue=1), _pair(1, 60, reason=repo.MERGE_IN_HISTORY)]),
        _cand(2, "go", 2, extra=[weak]),
        _cand(3, "go", 1),
        _cand(4, "py", 9, ok=False),
    ]
    data, manifest = corpus.build(measured, SHA, {"graphql": 12, "rest": 0})
    rows = [json.loads(line) for line in data.splitlines()]
    assert dataset.problems(data, manifest) == []
    assert [(r["github_repo_id"], r["pr"], r["issue"]) for r in rows] == sorted(
        (r["github_repo_id"], r["pr"], r["issue"]) for r in rows
    )
    assert {r["github_repo_id"] for r in rows} == {1, 2, 3}  # the unqualified candidate's pairs never land
    assert manifest["pairs_file"] | {"sha256": None} == {
        "path": corpus.PAIRS_PATH,
        "sha256": None,
        "total_count": 8,
        "strong_count": 7,
        "weak_count": 1,
    }
    assert manifest["selected"] == [1, 2, 3] and manifest["rules"]["max_files"] == 15  # 7 strong is short
    assert set(manifest["splits"]) == {"1", "2", "3"}
    assert manifest["exclusions"] == {"merge_commit_in_pr_history": 1}
    assert manifest["as_of"] == "2026-09-28T00:00:00Z" and manifest["api_calls"] == {"graphql": 12, "rest": 0}


def test_build_refuses_a_manifest_that_fails_its_schema():
    with pytest.raises(ValueError, match="refusing to write the dataset: manifest:"):
        corpus.build(
            [_cand(1, "py", 3), _cand(2, "go", 2), _cand(3, "go", 1)], "HEAD", {"graphql": 1, "rest": 0}
        )


def test_the_dataset_follows_the_last_round_when_relaxing_d2_changes_the_winner():
    wide = [_pair(4, 900 + i, gold=[f"f{j}.py" for j in range(12)]) for i in range(200)]
    four = [_cand(1, "py", 100), _cand(2, "go", 100), _cand(3, "go", 80), _cand(4, "py", 10, extra=wide)]
    for c in four:
        c["entry"]["chunk_estimate"] = 20_000  # no 4-subset fits the 60,000 bound
    _, manifest = corpus.build(four, SHA, {"graphql": 1, "rest": 0})
    assert [r["winner"] for r in manifest["selection_rounds"]] == [[1, 2, 3], [1, 2, 4]]
    assert manifest["selected"] == [1, 2, 4] and manifest["pairs_file"]["strong_count"] == 410
