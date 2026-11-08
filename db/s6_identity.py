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
from datetime import timedelta

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


def line_count(body: str) -> int:
    """`universe.lines`' rule: the newlines, plus one when a non-empty body lacks a final newline."""
    return body.count("\n") + (1 if body and not body.endswith("\n") else 0)


def seed_connection(conn, *, account_login: str = "s2", valid: str = "1 day") -> int:
    """One read-only connection. S2 puts all 100 pseudo-repositories under one, as S3-6 does (BCR-1)."""
    return conn.execute(
        "INSERT INTO connection (mode, account_login, state, state_observed_at, state_valid_until,"
        " egress_policy, config) VALUES ('public_readonly', %s, 'active', now(), now() + %s::interval,"
        " '{}', '{}') RETURNING id",
        (account_login, valid),
    ).fetchone()[0]


def seed_repository(
    conn,
    *,
    connection_id: int,
    github_repo_id: int,
    full_name: str,
    visibility: str = "private",
    valid: str = "1 day",
) -> int:
    """An active repository with a visibility lease of `valid`. A private one is admitted only by a grant."""
    return conn.execute(
        "INSERT INTO repository (connection_id, github_repo_id, full_name, default_branch, visibility,"
        " visibility_observed_at, visibility_valid_until, serving_state, data_class)"
        " VALUES (%s, %s, %s, 'main', %s, now(), now() + %s::interval, 'active', %s) RETURNING id",
        (
            connection_id,
            github_repo_id,
            full_name,
            visibility,
            valid,
            "public" if visibility == "public" else "private",
        ),
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
    start_line: int = 1,
) -> int:
    """§8.5's reuse step: look up (repo, spec, input hash), embed only on a miss, add the occurrence at
    `start_line`. Identical bodies in one file share a representation, never an occurrence (BCR-1)."""
    if start_line < 1:
        raise ValueError(f"start_line must be at least 1, not {start_line}")
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
                "INSERT INTO representation (repo_id, spec_id, input_hash, content_hash, header, body_text,"
                " path) VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id",
                (repo_id, spec.id, ihash, chash, header, body, path),
            ).fetchone()[0]
            conn.execute(
                "INSERT INTO vector_d768 (representation_id, repo_id, spec_id, embedding)"
                " VALUES (%s, %s, %s, %s::halfvec)",
                (rep, repo_id, spec.id, vector_text(vector)),
            )
        conn.execute(
            "INSERT INTO occurrence (repo_id, generation_id, representation_id, path, blob_sha, start_line,"
            " end_line) VALUES (%s, %s, %s, %s, %s, %s, %s)",
            (
                repo_id,
                generation_id,
                rep,
                path,
                chash.hex()[:40],
                start_line,
                start_line + line_count(body) - 1,
            ),
        )
    return rep


PAD = " · s2-pad:{row}"  # visible in the stored header, so the hash is of what is stored


def pad_copy(conn, *, repo_id: int, generation_id: int, spec: Spec, source: int, row: int) -> int:
    """A scale-padding copy of `source` (ADR-0019 Setup, BCR-1): a new representation, vector and
    occurrence in `generation_id`, so activation makes it live. Its header is the source's plus
    `PAD`; its input hash is that exact stored input's; its vector is `stand_in` over that input, so
    it is seeded by the row and the input. It sits at the source's first occurrence in the same
    generation, by path then start line. No embedder is called. `row` must be unique within a run:
    reusing one for the same source violates (repo_id, spec_id, input_hash)."""
    if row < 0:
        raise ValueError(f"row must be at least 0, not {row}")
    found = conn.execute(
        "SELECT r.header, r.body_text, r.content_hash, o.path, o.blob_sha, o.start_line, o.end_line"
        " FROM representation r JOIN occurrence o ON o.representation_id = r.id AND o.generation_id = %s"
        " WHERE r.id = %s AND r.repo_id = %s AND r.spec_id = %s ORDER BY o.path, o.start_line LIMIT 1",
        (generation_id, source, repo_id, spec.id),
    ).fetchone()
    if found is None:
        raise ValueError(f"representation {source} has no occurrence in generation {generation_id}")
    header, body, chash, path, blob, start, end = found
    header += PAD.format(row=row)
    text = embedded_input(spec.doc_template, header, body)
    with conn.transaction():
        rep = conn.execute(
            "INSERT INTO representation (repo_id, spec_id, input_hash, content_hash, header, body_text, path)"
            " VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id",
            (repo_id, spec.id, input_hash(text), chash, header, body, path),
        ).fetchone()[0]
        conn.execute(
            "INSERT INTO vector_d768 (representation_id, repo_id, spec_id, embedding)"
            " VALUES (%s, %s, %s, %s::halfvec)",
            (rep, repo_id, spec.id, vector_text(stand_in(spec, text))),
        )
        conn.execute(
            "INSERT INTO occurrence (repo_id, generation_id, representation_id, path, blob_sha, start_line,"
            " end_line) VALUES (%s, %s, %s, %s, %s, %s, %s)",
            (repo_id, generation_id, rep, path, blob, start, end),
        )
    return rep


def finish_build(conn, generation_id: int) -> None:
    conn.execute(
        "UPDATE generation SET status = 'ready', chunk_count = (SELECT count(*) FROM occurrence"
        " WHERE generation_id = %s) WHERE id = %s AND status = 'building'",
        (generation_id, generation_id),
    )


CLAIM_FOR = timedelta(minutes=5)  # S6's claim; S2 passes timedelta(minutes=60) (BCR-3)


def push_and_claim(conn, repo_id: int, *, claim_for: timedelta = CLAIM_FOR) -> tuple[int, object]:
    """Accept a push and claim the repository for `claim_for`. S6 does not test scheduling (that is S5);
    it only needs §9.3.5's preconditions to be real.

    BCR-3: `claim_for` must be a positive `timedelta`. Anything else is refused before any statement is
    sent, so the repository row is unchanged. Nothing extends a claim; a build that outlives it is
    refused by `activate`."""
    if not isinstance(claim_for, timedelta):
        raise TypeError(f"claim_for must be a datetime.timedelta, not {type(claim_for).__name__}")
    if claim_for <= timedelta(0):
        raise ValueError(f"claim_for must be positive, got {claim_for!r}")
    return conn.execute(
        "UPDATE repository SET desired_generation = desired_generation + 1, claim_token = gen_random_uuid(),"
        " claim_expires_at = now() + %s WHERE id = %s"
        " RETURNING desired_generation, claim_token",
        (claim_for, repo_id),
    ).fetchone()


def activate(conn, *, repo_id: int, new: int, base: int | None, desired: int, claim) -> None:
    """DESIGN §9.3.5's fenced activation, as one transaction."""
    with conn.transaction():
        d, active, token, owned = conn.execute(
            "SELECT desired_generation, active_generation_id, claim_token,"
            " coalesce(claim_expires_at > now(), false) FROM repository WHERE id = %s FOR UPDATE",
            (repo_id,),
        ).fetchone()
        # The generation's own repository, base and target, so a caller cannot substitute current values
        # for the ones it was built against (gupta958's review of #82).
        gen_repo, gen_base, gen_desired, status, chunks, occurrences = conn.execute(
            "SELECT repo_id, base_generation_id, desired_generation, status, chunk_count,"
            " (SELECT count(*) FROM occurrence WHERE generation_id = g.id) FROM generation g WHERE id = %s",
            (new,),
        ).fetchone()
        if not (
            token == claim
            and owned
            and gen_repo == repo_id
            and gen_base == base
            and gen_desired == desired
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
