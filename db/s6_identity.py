"""Spike S6 (ADR-0005): the one build path that both embedders share.

db/tests/test_s6_identity.py passes `stand_in`, and db/s6_ollama.py passes a real Ollama. The embedder is
the only thing that differs (gupta958's ruling on #80), so hashing, reuse, insertion, activation and the
serving queries exist only here.
"""

from __future__ import annotations

import hashlib
import re
from collections.abc import Callable
from dataclasses import dataclass

DIMENSION = 768  # every S6 specification writes to vector_d768


class ActivationRefused(Exception):
    """A §9.3.5 precondition did not hold; nothing was changed."""


@dataclass(frozen=True)
class Spec:
    id: int
    model_ref: str
    model_digest: str
    doc_template: str


Embedder = Callable[[Spec, str], list[float]]

# The source text T. The fixture is fixed, so a result can only change with the code under test.
T_PATH = "wayfinder/ranges.py"
T_HEADER = "acme/r · wayfinder/ranges.py · parse_range"
T_BODY = '''def parse_range(spec: str, total: int) -> tuple[int, int]:
    """Parse a line range such as "10-20", "10-" or "-5" against a file of `total` lines.

    Returns 1-based inclusive bounds clamped to the file. Raises ValueError on anything else.
    """
    spec = spec.strip()
    if not spec:
        raise ValueError("empty range")
    if spec.count("-") != 1:
        start = end = int(spec)
    else:
        left, right = spec.split("-")
        if not left and not right:
            raise ValueError("a range needs at least one bound")
        if not left:
            start, end = max(1, total - int(right) + 1), total
        elif not right:
            start, end = int(left), total
        else:
            start, end = int(left), int(right)
    if start < 1 or end < start:
        raise ValueError(f"bad range {spec!r}")
    return start, min(end, total)


def format_range(start: int, end: int) -> str:
    """The inverse of parse_range for a closed range: {start}-{end}, or one number when equal."""
    return str(start) if start == end else f"{start}-{end}"


RANGES = {name: parse_range(name, 100) for name in ("1-10", "90-", "-5", "7")}
'''


def embedded_input(template: str, header: str, body: str) -> str:
    """The exact string sent to the embedder. One pass over the template, so a brace in the header or
    body is never read as a placeholder."""
    values = {"header": header, "body": body}
    return re.sub(r"\{(header|body)\}", lambda m: values[m[1]], template)


def input_hash(text: str) -> bytes:
    """ADR-0005: SHA-256 of the UTF-8 bytes of the embedded input."""
    return hashlib.sha256(text.encode("utf-8")).digest()


def stand_in(spec: Spec, text: str) -> list[float]:
    """A 768-d vector from SHA-256 of (model_digest, input): distinct per spec, stable per input."""
    seed = f"{spec.model_digest}\0{text}".encode()
    out: list[float] = []
    counter = 0
    while len(out) < DIMENSION:
        block = hashlib.sha256(seed + counter.to_bytes(4, "big")).digest()
        out.extend((b - 127.5) / 127.5 for b in block)
        counter += 1
    return out[:DIMENSION]


def vector_text(v: list[float]) -> str:
    return "[" + ",".join(repr(float(x)) for x in v) + "]"


def capture_spec(conn, *, model_ref: str, model_digest: str, runtime: str, doc_template: str) -> Spec:
    """Insert the specification, or return the existing row with the same identity key (§9.2's UNIQUE)."""
    key = (model_digest, runtime, doc_template, "search_query: {query}", "mean", True, DIMENSION, "end")
    row = conn.execute(
        "INSERT INTO embedding_spec (model_ref, model_digest, runtime, doc_template, query_template,"
        " pooling, normalize, dimension, truncation, tokenizer_ref)"
        " VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
        " ON CONFLICT (model_digest, runtime, doc_template, query_template, pooling, normalize, dimension,"
        " truncation) DO NOTHING RETURNING id",
        (model_ref, *key, model_ref),
    ).fetchone()
    if row is None:
        row = conn.execute(
            "SELECT id FROM embedding_spec WHERE model_digest = %s AND runtime = %s AND doc_template = %s"
            " AND query_template = %s AND pooling = %s AND normalize = %s AND dimension = %s"
            " AND truncation = %s",
            key,
        ).fetchone()
    return Spec(row[0], model_ref, model_digest, doc_template)


def new_generation(conn, repo_id: int, spec: Spec, *, desired: int, base: int | None) -> int:
    return conn.execute(
        "INSERT INTO generation (repo_id, desired_generation, commit_sha, spec_id, chunker_version, status,"
        " base_generation_id) VALUES (%s, %s, %s, %s, 's6', 'building', %s) RETURNING id",
        (repo_id, desired, f"c{desired}", spec.id, base),
    ).fetchone()[0]


def index_chunk(
    conn,
    embed: Embedder,
    *,
    repo_id: int,
    generation_id: int,
    spec: Spec,
    header: str = T_HEADER,
    body: str = T_BODY,
    path: str = T_PATH,
) -> int:
    """§8.5's reuse step: look up (repo, spec, input hash), embed only on a miss, add the occurrence."""
    text = embedded_input(spec.doc_template, header, body)
    ihash = input_hash(text)
    chash = hashlib.sha256(body.encode("utf-8")).digest()
    with conn.transaction():
        conn.execute(
            "INSERT INTO content (content_hash, body, token_count) VALUES (%s, %s, %s)"
            " ON CONFLICT DO NOTHING",
            (chash, body, len(body.split())),
        )
        row = conn.execute(
            "SELECT id FROM representation WHERE repo_id = %s AND spec_id = %s AND input_hash = %s",
            (repo_id, spec.id, ihash),
        ).fetchone()
        if row:
            rep = row[0]
        else:
            vector = embed(spec, text)
            rep = conn.execute(
                "INSERT INTO representation (repo_id, spec_id, input_hash, content_hash, header, body_text)"
                " VALUES (%s, %s, %s, %s, %s, %s) RETURNING id",
                (repo_id, spec.id, ihash, chash, header, body),
            ).fetchone()[0]
            conn.execute(
                "INSERT INTO vector_d768 (representation_id, repo_id, spec_id, embedding)"
                " VALUES (%s, %s, %s, %s::halfvec)",
                (rep, repo_id, spec.id, vector_text(vector)),
            )
        conn.execute(
            "INSERT INTO occurrence (repo_id, generation_id, representation_id, path, blob_sha, start_line,"
            " end_line) VALUES (%s, %s, %s, %s, %s, 1, %s)",
            (repo_id, generation_id, rep, path, chash.hex()[:40], body.count("\n")),
        )
    return rep


def finish_build(conn, generation_id: int) -> None:
    conn.execute(
        "UPDATE generation SET status = 'ready', chunk_count = (SELECT count(*) FROM occurrence"
        " WHERE generation_id = %s) WHERE id = %s AND status = 'building'",
        (generation_id, generation_id),
    )


def push_and_claim(conn, repo_id: int) -> tuple[int, object]:
    """Accept a push and claim the repository. S6 does not test scheduling (that is S5); it only needs
    §9.3.5's preconditions to be real."""
    return conn.execute(
        "UPDATE repository SET desired_generation = desired_generation + 1, claim_token = gen_random_uuid(),"
        " claim_expires_at = now() + interval '5 minutes' WHERE id = %s"
        " RETURNING desired_generation, claim_token",
        (repo_id,),
    ).fetchone()


def activate(conn, *, repo_id: int, new: int, base: int | None, desired: int, claim) -> None:
    """DESIGN §9.3.5's fenced activation, as one transaction."""
    with conn.transaction():
        d, active, token, owned = conn.execute(
            "SELECT desired_generation, active_generation_id, claim_token,"
            " coalesce(claim_expires_at > now(), false) FROM repository WHERE id = %s FOR UPDATE",
            (repo_id,),
        ).fetchone()
        status, chunks, occurrences = conn.execute(
            "SELECT status, chunk_count, (SELECT count(*) FROM occurrence WHERE generation_id = g.id)"
            " FROM generation g WHERE id = %s",
            (new,),
        ).fetchone()
        if not (
            token == claim
            and owned
            and d == desired
            and active == base
            and status == "ready"
            and chunks == occurrences
        ):
            raise ActivationRefused(f"repository {repo_id}, generation {new}")
        diff = (
            "SELECT representation_id FROM occurrence WHERE generation_id = %s"
            " EXCEPT SELECT representation_id FROM occurrence WHERE generation_id = %s"
        )
        added = [r for (r,) in conn.execute(diff, (new, base))]
        removed = [r for (r,) in conn.execute(diff, (base, new))] if base is not None else []
        for table, column in (("representation", "id"), ("vector_d768", "representation_id")):
            conn.execute(f"UPDATE {table} SET live = true WHERE {column} = ANY(%s)", (added,))
            conn.execute(f"UPDATE {table} SET live = false WHERE {column} = ANY(%s)", (removed,))
        if base is not None:
            conn.execute("UPDATE generation SET status = 'retired' WHERE id = %s", (base,))
        conn.execute("UPDATE generation SET status = 'active', activated_at = now() WHERE id = %s", (new,))
        moved = conn.execute(
            "UPDATE repository SET active_generation_id = %s, updated_at = now()"
            " WHERE id = %s AND active_generation_id IS NOT DISTINCT FROM %s",
            (new, repo_id, base),
        ).rowcount
        if moved != 1:
            raise ActivationRefused(f"repository {repo_id} moved underneath generation {new}")


def serving_rows(conn, repo_id: int, spec: Spec) -> list[int]:
    """What retrieval may read: the retrieval_rows view, bound to one specification."""
    return [
        r
        for (r,) in conn.execute(
            "SELECT representation_id FROM retrieval_rows WHERE repo_id = %s AND spec_id = %s ORDER BY 1",
            (repo_id, spec.id),
        )
    ]


def nearest(conn, repo_id: int, spec: Spec, query: list[float], k: int = 5) -> list[int]:
    """Nearest live vectors for one specification, with spec_id as an ordinary bound predicate (§9.2)."""
    return [
        r
        for (r,) in conn.execute(
            "SELECT representation_id FROM vector_d768 WHERE live AND repo_id = %s AND spec_id = %s"
            " ORDER BY embedding <=> %s::halfvec LIMIT %s",
            (repo_id, spec.id, vector_text(query), k),
        )
    ]
