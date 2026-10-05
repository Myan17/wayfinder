"""The pairs file's four landing checks (gupta958 on #50): order, schema, SHA-256, counts."""

import hashlib
import json
from pathlib import Path

import pytest
from s1 import dataset

SCHEMA = Path(__file__).parents[2] / "datasets" / "manifest.schema.json"


def _pair(repo=1, pr=10, issue=5, strong=True, **over):
    p = {
        "github_repo_id": repo,
        "issue": issue,
        "pr": pr,
        "base_commit": "a" * 40,
        "gold": ["x.py"],
        "strong": strong,
        "group_id": f"{repo}:{issue}",
        "t_g": "2026-01-02T03:04:05Z",
        "split": "dev",
    }
    return p | over


def _file(pairs):
    return b"".join(json.dumps(p).encode() + b"\n" for p in pairs)


def _manifest(data, total, strong, weak):
    return {
        "pairs_file": {
            "path": "eval/datasets/s1/pairs.jsonl",
            "sha256": hashlib.sha256(data).hexdigest(),
            "total_count": total,
            "strong_count": strong,
            "weak_count": weak,
        }
    }


def test_a_canonical_file_matching_its_manifest_has_no_problems():
    data = _file([_pair(1, 10, 5), _pair(1, 11, 3, strong=False), _pair(2, 1, 9)])
    assert dataset.problems(data, _manifest(data, 3, 2, 1)) == []
    assert dataset.problems(b"", _manifest(b"", 0, 0, 0)) == []


@pytest.mark.parametrize(
    "order",
    [
        [(1, 11, 3), (1, 10, 5)],  # pr out of order
        [(2, 1, 1), (1, 9, 9)],  # repository out of order
        [(1, 10, 6), (1, 10, 5)],  # issue out of order within a pr
        [(1, 10, 5), (1, 10, 5)],  # duplicate
    ],
)
def test_lines_out_of_canonical_order_or_duplicated_are_refused(order):
    data = _file([_pair(r, p, i) for r, p, i in order])
    found = dataset.problems(data, _manifest(data, 2, 2, 0))
    assert len(found) == 1 and found[0].startswith("line 2:") and "is not after" in found[0]


@pytest.mark.parametrize(
    "over, why",
    [
        ({"github_repo_id": "1"}, "github_repo_id: '1' is not of type 'integer'"),
        ({"pr": True}, "pr: True is not of type 'integer'"),
        ({"base_commit": "A" * 40}, "base_commit: 'AAAA"),
        ({"base_commit": "a" * 39}, "base_commit: 'aaaa"),
        ({"gold": []}, "gold: [] should be non-empty"),
        ({"gold": [3]}, "gold.0: 3 is not of type 'string'"),
        ({"strong": 1}, "strong: 1 is not of type 'boolean'"),
        ({"split": "train"}, "split: 'train' is not one of"),
    ],
)
def test_every_line_is_validated_against_the_pair_schema(over, why):
    data = _file([_pair(**over)])
    found = dataset.problems(data, _manifest(data, 1, 1, 0))
    assert any(f.startswith(f"line 1: {why}") for f in found), found


@pytest.mark.parametrize(
    "t_g",
    [
        "2026-01-02T03:04:05",  # no offset
        "2026-01-02T03:04:05+05",  # offset without minutes
        "2026-01-02 03:04:05Z",  # space for T; Python's fromisoformat accepts it
        "20260102T030405Z",  # ISO 8601 basic format; fromisoformat accepts it too
        "2026-13-02T03:04:05Z",  # month 13
        "2026-02-30T00:00:00Z",  # Feb 30
        "2026-01-02T25:00:00Z",  # hour 25
        "yesterday",
    ],
)
def test_t_g_must_be_an_rfc_3339_date_time(t_g):
    data = _file([_pair(t_g=t_g)])
    found = dataset.problems(data, _manifest(data, 1, 1, 0))
    assert f"line 1: t_g: {t_g!r} is not a 'date-time'" in found, found


@pytest.mark.parametrize("constant", ["NaN", "Infinity", "-Infinity"])
def test_non_standard_numeric_constants_are_not_json(constant):
    line = json.dumps(_pair()).replace('"github_repo_id": 1', f'"github_repo_id": {constant}').encode()
    assert constant.encode() in line
    data = line + b"\n"
    assert dataset.problems(data, _manifest(data, 0, 0, 0)) == ["line 1: not JSON"]


def test_a_missing_field_or_a_line_that_is_not_json_is_refused():
    missing = {k: v for k, v in _pair().items() if k != "split"}
    data = _file([missing]) + b"{not json\n" + b"[1]\n"
    found = dataset.problems(data, _manifest(data, 0, 0, 0))
    assert found == [
        "line 1: 'split' is a required property",
        "line 2: not JSON",
        "line 3: [1] is not of type 'object'",
    ]


def test_a_sha256_that_does_not_match_is_refused():
    data = _file([_pair()])
    m = _manifest(data, 1, 1, 0)
    assert dataset.problems(data + b"\n", m)[0] == "sha256 does not match the manifest"


def test_counts_must_match_the_manifest_and_add_up():
    data = _file([_pair(1, 10, 5), _pair(1, 11, 3, strong=False)])
    assert dataset.problems(data, _manifest(data, 2, 2, 0)) == [
        "strong_count: file has 1, manifest says 2",
        "weak_count: file has 1, manifest says 0",
    ]
    assert dataset.problems(data, _manifest(data, 3, 1, 1)) == [
        "manifest: total_count 3 != strong_count 1 + weak_count 1",
        "total_count: file has 2, manifest says 3",
    ]


def test_a_file_without_a_final_newline_is_refused():
    data = _file([_pair()])[:-1]
    assert dataset.problems(data, _manifest(data, 1, 1, 0)) == ["the file does not end with a newline"]


def test_lines_are_validated_against_the_committed_schema():
    assert dataset.PAIR.schema == json.loads(SCHEMA.read_text())["$defs"]["pair"]
    assert dataset.PAIR.format_checker is not None


def test_the_command_exits_1_and_names_each_problem(tmp_path, capsys):
    data = _file([_pair()])
    (tmp_path / "p.jsonl").write_bytes(data)
    (tmp_path / "m.json").write_text(json.dumps(_manifest(data, 1, 1, 0)))
    assert dataset.main([str(tmp_path / "p.jsonl"), str(tmp_path / "m.json")]) == 0
    (tmp_path / "m.json").write_text(json.dumps(_manifest(data, 1, 0, 1)))
    assert dataset.main([str(tmp_path / "p.jsonl"), str(tmp_path / "m.json")]) == 1
    assert "strong_count: file has 1, manifest says 0" in capsys.readouterr().err
