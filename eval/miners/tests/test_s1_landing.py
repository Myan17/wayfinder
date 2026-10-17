"""The manifest's mechanical checks (gupta958, 2026-10-17): schema, encoding, rounds, selection, pairs."""

import datetime as dt
import hashlib
import json

import pytest
from s1 import corpus, landing, select

T0 = dt.datetime(2026, 1, 1, tzinfo=dt.UTC)
SHA = "0123456789abcdef" * 2 + "01234567"


def _cand(rid, lang, strong, chunks=1000, ok=True):
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
    pairs = [
        {
            "repo_id": rid,
            "issue": n,
            "pr": n,
            "base": SHA,
            "reason": None,
            "gold": ["a.py"],
            "strong": True,
            "merged_at": T0 + dt.timedelta(days=n),
        }
        for n in range(1, strong + 1)
    ]
    return {"entry": entry, "pairs": pairs}


def _built(measured=None, widened=False):
    measured = measured or [_cand(1, "py", 120), _cand(2, "go", 90), _cand(3, "py", 100), _cand(4, "go", 5)]
    data, manifest = corpus.build(measured, "abc1234", {"graphql": 1, "rest": 0}, widened=widened)
    return data, manifest


def _check(data, manifest):
    return landing.problems(data, landing.encoded(manifest))


def _rehash(rows, manifest):
    """A pairs file from `rows`, with the manifest's hash and counts made to match it."""
    data = b"".join(json.dumps(r, sort_keys=True).encode() + b"\n" for r in rows)
    strong = sum(r["strong"] for r in rows)
    manifest["pairs_file"] |= {
        "sha256": hashlib.sha256(data).hexdigest(),
        "total_count": len(rows),
        "strong_count": strong,
        "weak_count": len(rows) - strong,
    }
    return data


def test_what_the_miner_builds_passes():
    data, manifest = _built()
    assert manifest["selected"] and len(manifest["selection_rounds"][0]["feasible"]) > 1
    assert _check(data, manifest) == []


def test_a_widened_short_run_with_two_rounds_passes():
    data, manifest = _built([_cand(1, "py", 20), _cand(2, "go", 20), _cand(3, "py", 20)], widened=True)
    assert [r["max_files"] for r in manifest["selection_rounds"]] == [10, 15]
    assert _check(data, manifest) == []


def test_a_run_with_no_feasible_corpus_passes_and_its_reason_is_checked():
    data, manifest = _built([_cand(1, "py", 120), _cand(2, "py", 90), _cand(3, "py", 100)])
    assert manifest["selection_rounds"][0]["no_feasible_reason"] == "language mix"
    assert _check(data, manifest) == []
    manifest["selection_rounds"][0]["no_feasible_reason"] = "chunk bound"
    assert any("no_feasible_reason" in p for p in _check(data, manifest))


@pytest.mark.parametrize(
    "encode",
    [
        lambda m: json.dumps(m, sort_keys=True) + "\n",  # compact
        lambda m: json.dumps(m, indent=2) + "\n",  # keys in insertion order
        lambda m: json.dumps(m, indent=2, sort_keys=True),  # no final newline
        lambda m: json.dumps(m, indent=4, sort_keys=True) + "\n",
    ],
)
def test_only_the_canonical_encoding_is_accepted(encode):
    data, manifest = _built()
    manifest = {k: manifest[k] for k in reversed(manifest)}  # so insertion order is not sorted
    assert any("canonical encoding" in p for p in landing.problems(data, encode(manifest)))


def test_non_json_constants_and_schema_violations_are_refused():
    data, manifest = _built()
    text = landing.encoded(manifest).replace('"chunk_lines": 60', '"chunk_lines": NaN')
    assert landing.problems(data, text) == ["manifest: not JSON"]
    manifest["rules"]["chunk_lines"] = 50
    assert any(p.startswith("manifest: ") and "60" in p for p in _check(data, manifest))


@pytest.mark.parametrize(
    "tamper",
    [
        lambda fs: fs.pop(),  # a feasible subset dropped
        lambda fs: fs.append([1, 2, 3, 4, 5]),  # one added
        lambda fs: fs.reverse(),  # out of canonical order
        lambda fs: fs[0].reverse(),  # a subset's ids unsorted
    ],
)
def test_the_feasible_list_must_equal_the_one_rebuilt_from_the_candidates(tamper):
    data, manifest = _built()
    tamper(manifest["selection_rounds"][0]["feasible"])
    assert any("feasible subsets differ" in p for p in _check(data, manifest))


@pytest.mark.parametrize(
    "tamper",
    [
        lambda c: c[3]["rules"]["S1-4"].update({"pass": False}),  # one candidate no longer qualifies
        lambda c: c[3].update({"lang": "py"}),  # a language changed
        lambda c: c[3].update({"chunk_estimate": 59_000}),  # a chunk estimate that crosses the bound
    ],
)
def test_a_changed_candidate_record_no_longer_matches_the_recorded_rounds(tamper):
    data, manifest = _built()
    tamper(manifest["candidates"])
    assert any("feasible subsets differ" in p for p in _check(data, manifest))


@pytest.mark.parametrize(
    "chunks, want",
    [
        ((20_000, 20_000, 20_000), ([[1, 2, 3]], None)),  # exactly ADR-0016's 60,000 is feasible
        ((20_000, 20_000, 20_001), ([], "chunk bound")),  # 60,001 is not
    ],
)
def test_the_chunk_bound_is_adr_0016s_60000_inclusive(chunks, want):
    langs = ("py", "go", "py")
    cands = [
        _cand(rid, lang, 1, chunks=c)["entry"] for rid, lang, c in zip((1, 2, 3), langs, chunks, strict=True)
    ]
    assert landing._feasible(cands) == want


def test_the_chunk_bound_does_not_follow_the_producers_constant(monkeypatch):
    # If s1.select's bound drifted from ADR-0016's, the producer would accept 60,001; the check must not.
    loose = select.best  # its default bound is bound at definition, so the call is patched too
    monkeypatch.setattr(select, "MAX_CHUNKS", 60_001)
    monkeypatch.setattr(select, "best", lambda cands: loose(cands, max_chunks=60_001))
    data, manifest = _built(
        [_cand(1, "py", 120, 20_000), _cand(2, "go", 90, 20_000), _cand(3, "py", 100, 20_001)]
    )
    assert manifest["selected"] == [1, 2, 3]
    found = _check(data, manifest)
    assert any("feasible subsets differ" in p for p in found)
    assert any("rebuilt 'chunk bound'" in p for p in found)


def test_round_candidates_must_be_the_measured_ids():
    data, manifest = _built()
    manifest["selection_rounds"][0]["candidates"].pop()
    assert any("candidates are not the measured" in p for p in _check(data, manifest))


def test_a_candidate_id_may_not_repeat():
    data, manifest = _built()
    manifest["candidates"].append(manifest["candidates"][0])
    assert "candidates: a github_repo_id appears twice" in _check(data, manifest)


def test_the_winner_must_be_feasible_and_selected_must_equal_it():
    data, manifest = _built()
    final = manifest["selection_rounds"][-1]
    final["winner"] = [1, 3]  # Python only, and too few
    found = _check(data, manifest)
    assert any("is not a feasible subset" in p for p in found)
    assert any("is not the final round's winner" in p for p in found)


def test_selected_must_be_the_final_rounds_winner_even_when_both_are_feasible():
    data, manifest = _built()
    other = next(s for s in manifest["selection_rounds"][0]["feasible"] if s != manifest["selected"])
    manifest["selected"] = other
    assert any("is not the final round's winner" in p for p in _check(data, manifest))


@pytest.mark.parametrize("steps, rule", [([15], 15), ([10, 10], 10), ([10, 15], 10)])
def test_rounds_follow_r03_and_rules_max_files_is_the_final_rounds(steps, rule):
    data, manifest = _built()
    first = manifest["selection_rounds"][0]
    manifest["selection_rounds"] = [first | {"max_files": s} for s in steps]
    manifest["rules"]["max_files"] = rule
    assert any("max_files" in p for p in _check(data, manifest))


def test_pairs_come_only_from_selected_repositories():
    data, manifest = _built()
    rows = [json.loads(line) for line in data.splitlines()]
    rows.append(rows[-1] | {"github_repo_id": 99, "group_id": "99:1"})
    data = _rehash(rows, manifest)
    assert any("not selected: [99]" in p for p in _check(data, manifest))


def test_split_counts_must_equal_the_files_per_repository_counts():
    data, manifest = _built()
    repo = next(iter(manifest["splits"]))
    manifest["splits"][repo]["dev"] += 1
    assert any(f"splits.{repo}.dev" in p for p in _check(data, manifest))
    del manifest["splits"][repo]
    assert any("splits are keyed by" in p for p in _check(data, manifest))


def test_the_pairs_files_hash_and_counts_are_still_checked():
    data, manifest = _built()
    manifest["pairs_file"]["sha256"] = "0" * 64
    assert "sha256 does not match the manifest" in _check(data, manifest)


def test_the_command_exits_1_and_names_each_problem(tmp_path, capsys):
    data, manifest = _built()
    (tmp_path / "p.jsonl").write_bytes(data)
    (tmp_path / "m.json").write_text(landing.encoded(manifest))
    assert landing.main([str(tmp_path / "p.jsonl"), str(tmp_path / "m.json")]) == 0
    (tmp_path / "m.json").write_text(json.dumps(manifest))
    assert landing.main([str(tmp_path / "p.jsonl"), str(tmp_path / "m.json")]) == 1
    assert "canonical encoding" in capsys.readouterr().err
