"""The release manifest validates strictly, and its cache keys move exactly when their inputs do.

A key that ignores an input reuses a stale index (DESIGN 15.5). A key that includes an irrelevant
input throws away a good one on every commit. Both directions are tested.
"""

import copy
import importlib.util
import json
import pathlib
import sys

import pytest

HERE = pathlib.Path(__file__).resolve().parent
MODULE = HERE.parent / "release_manifest.py"
spec = importlib.util.spec_from_file_location("release_manifest", MODULE)
rm = importlib.util.module_from_spec(spec)
sys.modules["release_manifest"] = rm
spec.loader.exec_module(rm)

EXAMPLE = json.loads((HERE.parent / "example.json").read_text())


@pytest.fixture
def m():
    return copy.deepcopy(EXAMPLE)


def test_example_is_valid(m):
    assert rm.validate(m) == []


def test_every_missing_field_is_reported_not_just_the_first(m):
    del m["code_commit"], m["embedding_spec"]["dimension"]
    assert rm.validate(m) == ["missing field: code_commit", "missing field: embedding_spec.dimension"]


@pytest.mark.parametrize("path", [("chunker_versoin",), ("embedding_spec", "templat")])
def test_unknown_fields_are_rejected(m, path):
    target = m if len(path) == 1 else m[path[0]]
    target[path[-1]] = "x"
    assert any(e.startswith("unknown field:") for e in rm.validate(m))


@pytest.mark.parametrize(
    "field,value",
    [
        ("images", {"postgres": "paradedb/paradedb:0.25.9"}),  # a tag, not a digest
        ("images", {"postgres": "paradedb/paradedb@sha256:abc"}),  # truncated digest
        ("code_commit", "3926ec7"),  # short sha
        ("schema_version", "2026-09-22"),
        ("prompts", {"answer": "not-a-hash"}),
        ("datasets", {"locate": "F" * 64}),  # uppercase hex
        ("manifest_version", 2),
    ],
)
def test_malformed_values_are_rejected(m, field, value):
    m[field] = value
    assert rm.validate(m), f"{field}={value!r} should be invalid"


def test_dimension_must_be_a_positive_int_not_a_bool(m):
    m["embedding_spec"]["dimension"] = True
    assert rm.validate(m) == ["invalid value for embedding_spec.dimension: True"]


def test_schema_version_must_be_the_newest_migration(m, tmp_path):
    # A temporary tree, so a future migration never forces an edit to the example.
    for stamp in ("20260101000000", "20260202000000"):
        (tmp_path / f"{stamp}_x.sql").write_text("")
    m["schema_version"] = "20260202000000"
    assert rm.check_schema_version(m, tmp_path) == []
    m["schema_version"] = "20260101000000"
    assert rm.check_schema_version(m, tmp_path)
    assert rm.check_schema_version(m, tmp_path / "empty")  # no migrations at all is an error


# Every index input, and a representative eval-only input, must move the key it belongs to.
INDEX_INPUTS = [
    ("schema_version", None, "20990101000000"),
    ("images", "postgres", "paradedb/paradedb@sha256:" + "0" * 64),
    ("extensions", "pg_search", "0.26.0"),
    ("grammars", "python", "tree-sitter-python@0.23.6"),
    ("chunker_version", None, "leaf-residual-2"),
    ("embedding_spec", "doc_template", "search_document: {body}"),
    ("embedding_spec", "query_template", "query: {query}"),
    ("embedding_spec", "model_digest", "sha256:" + "1" * 64),
    ("embedding_spec", "truncation", "start"),
]
EVAL_ONLY_INPUTS = [
    ("retrieval", "rrf_k", 20),
    ("answerability_version", None, "ce-v2"),
    ("prompts", "answer", "2" * 64),
    ("providers", "primary", "claude-sonnet-5"),
    ("datasets", "locate", "3" * 64),
]


def _set(m, field, sub, value):
    if sub is None:
        m[field] = value
    else:
        m[field][sub] = value


@pytest.mark.parametrize("field,sub,value", INDEX_INPUTS)
def test_index_inputs_change_both_keys(m, field, sub, value):
    before = {s: rm.cache_key(m, s) for s in rm.SCOPES}
    _set(m, field, sub, value)
    assert all(rm.cache_key(m, s) != before[s] for s in rm.SCOPES)


@pytest.mark.parametrize("field,sub,value", EVAL_ONLY_INPUTS)
def test_eval_inputs_change_the_eval_key_but_not_the_index_key(m, field, sub, value):
    index, ev = rm.cache_key(m, "index"), rm.cache_key(m, "eval")
    _set(m, field, sub, value)
    assert rm.cache_key(m, "index") == index
    assert rm.cache_key(m, "eval") != ev


@pytest.mark.parametrize(
    "field,sub,value",
    [
        ("code_commit", None, "f" * 40),
        ("platform", "arch", "amd64"),
    ],
)
def test_commit_and_platform_change_no_key(m, field, sub, value):
    before = {s: rm.cache_key(m, s) for s in rm.SCOPES}
    _set(m, field, sub, value)
    assert {s: rm.cache_key(m, s) for s in rm.SCOPES} == before


def test_key_ignores_json_key_order(m):
    reordered = json.loads(json.dumps(m, sort_keys=True))
    reordered["embedding_spec"] = dict(reversed(list(m["embedding_spec"].items())))
    assert rm.cache_key(reordered, "index") == rm.cache_key(m, "index")


def test_every_field_is_either_keyed_or_deliberately_unkeyed():
    """A new field must be placed in a scope on purpose; unkeyed fields are an explicit, short list."""
    unkeyed = {name for name, (_, _, scopes) in rm.FIELDS.items() if not scopes}
    assert unkeyed == {"manifest_version", "code_commit", "platform"}


def test_cli_validate_and_cache_key(capsys):
    assert rm.main(["validate", str(HERE.parent / "example.json")]) == 0
    assert rm.main(["cache-key", str(HERE.parent / "example.json"), "--scope", "index"]) == 0
    assert capsys.readouterr().out.strip().splitlines()[-1].startswith("wf-index-v1-")


def test_cli_reports_field_and_schema_errors_together(m, tmp_path, capsys):
    """Regression (review of #32): `validate(m) or check_schema_version(m)` hid the schema-version
    error whenever a field error existed. Both must be reported in one run."""
    m["bogus"] = 1
    m["schema_version"] = "20000101000000"  # older than every migration in the tree
    f = tmp_path / "m.json"
    f.write_text(json.dumps(m))
    assert rm.main(["validate", str(f)]) == 1
    out = capsys.readouterr().out
    assert "unknown field: bogus" in out
    assert "is not the newest migration" in out


def test_cli_rejects_a_non_object_without_crashing(tmp_path, capsys):
    f = tmp_path / "m.json"
    f.write_text("[]")
    assert rm.main(["validate", str(f)]) == 1
    assert "manifest is not a JSON object" in capsys.readouterr().out
