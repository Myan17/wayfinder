#!/usr/bin/env python3
"""Release manifest: one file pinning everything a reported number depends on (DESIGN 16.9).

usage: infra/manifest/release_manifest.py validate FILE
       infra/manifest/release_manifest.py cache-key FILE --scope index|eval

A manifest is JSON. `validate` reports every problem, not just the first, and rejects unknown keys:
a misspelt field would otherwise drop silently out of a cache key, which is exactly the stale-reuse
bug the key exists to prevent.

Cache keys (DESIGN 15.5) are a hash over the fields a scope depends on, nothing more:

- `index`: anything that changes what an index contains - schema, the Postgres image and its
  extensions, the tree-sitter grammars, the chunker, and the full embedding specification.
- `eval`:  the index inputs plus everything that changes a scored result - retrieval parameters,
  the answerability version, prompts, provider models and dataset hashes.

`code_commit` and `platform` are in neither. A commit that touches none of those inputs must reuse
the cache, and the platform is recorded for reproduction, not for keying (arm64 in CI and on the A1).

Standard library only, like the guardrail scripts, so it runs before any dependency is installed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re
import sys
from typing import Any

MANIFEST_VERSION = 1
ROOT = pathlib.Path(__file__).resolve().parents[2]

SHA256 = re.compile(r"^[0-9a-f]{64}$")
COMMIT = re.compile(r"^[0-9a-f]{40}$")
IMAGE = re.compile(r"^[a-z0-9][a-z0-9._/-]*@sha256:[0-9a-f]{64}$")  # by digest, never by tag
MIGRATION = re.compile(r"^\d{14}$")  # dbmate timestamp prefix


def _str(v: Any) -> bool:
    return isinstance(v, str) and v != ""


def _int(v: Any) -> bool:
    return isinstance(v, int) and not isinstance(v, bool)


def _match(pattern: re.Pattern[str]):
    return lambda v: isinstance(v, str) and bool(pattern.match(v))


def _map(check):
    return lambda v: isinstance(v, dict) and bool(v) and all(_str(k) and check(x) for k, x in v.items())


# Fields of embedding_spec, mirroring the table of the same name (DESIGN 9.2).
EMBEDDING_SPEC = {
    "model_ref": _str,
    "model_digest": _str,
    "runtime": _str,
    "doc_template": _str,
    "query_template": _str,
    "pooling": _str,
    "normalize": lambda v: isinstance(v, bool),
    "dimension": lambda v: _int(v) and v > 0,
    "truncation": _str,
    "tokenizer_ref": _str,
}
RETRIEVAL = {
    "rrf_k": lambda v: _int(v) and v > 0,
    "per_file_cap": lambda v: _int(v) and v > 0,
    "lexical_top_n": lambda v: _int(v) and v > 0,
    "dense_top_n": lambda v: _int(v) and v > 0,
    "rerank": lambda v: (
        v is None
        or (
            isinstance(v, dict)
            and set(v) == {"model", "n", "l"}
            and _str(v["model"])
            and _int(v["n"])
            and _int(v["l"])
        )
    ),
}
PLATFORM = {"os": _str, "arch": _str, "python": _str}

# Top-level fields: (checker, nested field table or None, scopes that key on it).
FIELDS: dict[str, tuple[Any, dict | None, frozenset[str]]] = {
    "manifest_version": (lambda v: v == MANIFEST_VERSION, None, frozenset()),
    "code_commit": (_match(COMMIT), None, frozenset()),
    "platform": (None, PLATFORM, frozenset()),
    "schema_version": (_match(MIGRATION), None, frozenset({"index", "eval"})),
    "images": (_map(_match(IMAGE)), None, frozenset({"index", "eval"})),
    "extensions": (_map(_str), None, frozenset({"index", "eval"})),
    "grammars": (_map(_str), None, frozenset({"index", "eval"})),
    "chunker_version": (_str, None, frozenset({"index", "eval"})),
    "embedding_spec": (None, EMBEDDING_SPEC, frozenset({"index", "eval"})),
    "retrieval": (None, RETRIEVAL, frozenset({"eval"})),
    "answerability_version": (lambda v: v is None or _str(v), None, frozenset({"eval"})),
    "prompts": (lambda v: v == {} or _map(_match(SHA256))(v), None, frozenset({"eval"})),
    "providers": (lambda v: v == {} or _map(_str)(v), None, frozenset({"eval"})),
    "datasets": (lambda v: v == {} or _map(_match(SHA256))(v), None, frozenset({"eval"})),
}
SCOPES = ("index", "eval")


def validate(m: Any) -> list[str]:
    """Every problem with the manifest; an empty list means valid."""
    if not isinstance(m, dict):
        return ["manifest is not a JSON object"]
    errors = [f"unknown field: {k}" for k in sorted(set(m) - set(FIELDS))]
    for name, (check, nested, _) in FIELDS.items():
        if name not in m:
            errors.append(f"missing field: {name}")
            continue
        value = m[name]
        if nested is None:
            if not check(value):
                errors.append(f"invalid value for {name}: {value!r}")
            continue
        if not isinstance(value, dict):
            errors.append(f"{name} must be an object")
            continue
        errors += [f"unknown field: {name}.{k}" for k in sorted(set(value) - set(nested))]
        for sub, subcheck in nested.items():
            if sub not in value:
                errors.append(f"missing field: {name}.{sub}")
            elif not subcheck(value[sub]):
                errors.append(f"invalid value for {name}.{sub}: {value[sub]!r}")
    return errors


def check_schema_version(m: dict, migrations: pathlib.Path = ROOT / "db" / "migrations") -> list[str]:
    """The manifest's schema_version must be the newest migration actually in the tree."""
    stamps = sorted(p.name[:14] for p in migrations.glob("*.sql"))
    if not stamps:
        return [f"no migrations under {migrations}"]
    if m.get("schema_version") != stamps[-1]:
        return [f"schema_version {m.get('schema_version')!r} is not the newest migration {stamps[-1]!r}"]
    return []


def cache_key(m: dict, scope: str) -> str:
    """Deterministic key over exactly the fields `scope` depends on. Call only on a valid manifest."""
    if scope not in SCOPES:
        raise ValueError(f"unknown scope {scope!r}; expected one of {SCOPES}")
    keyed = {name: m[name] for name, (_, _, scopes) in FIELDS.items() if scope in scopes}
    canonical = json.dumps(keyed, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return f"wf-{scope}-v{MANIFEST_VERSION}-{hashlib.sha256(canonical.encode()).hexdigest()[:16]}"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    v = sub.add_parser("validate")
    v.add_argument("file", type=pathlib.Path)
    k = sub.add_parser("cache-key")
    k.add_argument("file", type=pathlib.Path)
    k.add_argument("--scope", choices=SCOPES, required=True)
    a = ap.parse_args(argv)

    m = json.loads(a.file.read_text())
    errors = validate(m) or check_schema_version(m)
    if errors:
        for e in errors:
            print(f"::error::{a.file}: {e}")
        return 1
    print(f"{a.file}: valid" if a.cmd == "validate" else cache_key(m, a.scope))
    return 0


if __name__ == "__main__":
    sys.exit(main())
