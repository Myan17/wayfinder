"""The canonical two-leg hybrid query -- DESIGN 9.5 steps 2, 3, 5 and 6, pinned by ADR-0007 Amendment 1.

One statement: a lexical leg over `representation` through `rep_bm25`, one dense leg per embedding
specification over `vector_d768` through `vec768_hnsw`, RRF fusion, then `retrieval_rows` for the
location in the active generation. This is the shape the indexing card documents; nothing else of
indexing's tables is read.

Each leg joins `eligible_repo` and takes its filter from authz's `sql_predicate`, applied to the
relation that leg scans (9.1.5), so the iterative scan keeps going until it finds authorized rows.
`execute` asserts every row again with `assert_rows_authorized`.

Every value a caller supplies is a bound parameter. The lexical leg uses `paradedb.match`, which
tokenizes its input with the field's own tokenizer and has no query grammar, so query text cannot
inject query syntax (WF-25).

S3-6 captures this statement's plans and S2 times it. Both import it; neither copies it. Once merged,
a change to the statement is a new amendment to ADR-0007, and its plans are captured again.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from wayfinder.authz.interface import AuthorizedScope
from wayfinder.authz.predicate import assert_rows_authorized, sql_predicate

LEG_LIMIT = 100        # top-N per leg (9.5 diagram)
RRF_K = 60             # 9.5 step 5
PER_FILE_CAP = 3       # 9.5 step 6
DIMENSION = 768        # the only vector table so far (vector_d768)

# The six fields of rep_bm25 (ADR-0007 Amendment 1, migration _representation_path_bm25).
LEXICAL_FIELDS = ("header", "header_ident", "body_text", "body_ident", "path", "path_code")

SESSION = "SET LOCAL hnsw.iterative_scan = relaxed_order"


@dataclass(frozen=True)
class HybridQuery:
    sql: str
    params: dict[str, Any]


def _vector(values: Sequence[float]) -> str:
    if len(values) != DIMENSION:
        raise ValueError(f"query vector has {len(values)} dimensions, not {DIMENSION}")
    return "[" + ",".join(repr(float(v)) for v in values) + "]"


def build(
    query_text: str,
    query_vectors: Mapping[int, Sequence[float]],
    scope: AuthorizedScope,
    *,
    k: int,
    now: datetime | None = None,
) -> HybridQuery:
    """The statement for one query. `query_vectors` maps each specification in scope to the query's
    embedding under it; there is one dense leg per entry, in spec_id order."""
    if not query_vectors:
        raise ValueError("at least one specification is required")
    params: dict[str, Any] = {"q": query_text, "k": k}

    lexical_pred, p = sql_predicate("rep", scope, eligible_alias="el_lex", now=now)
    params.update(p)
    matches = ", ".join(f"paradedb.match('{f}', %(q)s)" for f in LEXICAL_FIELDS)
    ctes = [f"""lexical AS (
  SELECT rep.id, rep.repo_id, rep.path, paradedb.score(rep.id) AS score
    FROM representation rep
    JOIN eligible_repo el_lex ON el_lex.repo_id = rep.repo_id
   WHERE rep.id @@@ paradedb.boolean(should => ARRAY[{matches}])
     AND {lexical_pred}
   ORDER BY score DESC, rep.repo_id, rep.path, rep.id
   LIMIT {LEG_LIMIT}
), lexical_ranked AS (
  SELECT id, row_number() OVER (ORDER BY score DESC, repo_id, path, id) AS r FROM lexical
)"""]
    legs = ["SELECT id, r, 'lexical' AS leg FROM lexical_ranked"]

    for i, spec_id in enumerate(sorted(query_vectors)):
        pred, p = sql_predicate("v", scope, eligible_alias=f"el_d{i}", now=now)
        params.update(p)
        params[f"spec_{i}"] = spec_id
        params[f"qvec_{i}"] = _vector(query_vectors[spec_id])
        qvec = f"%(qvec_{i})s::halfvec({DIMENSION})"
        # The cut is the index's own order (deterministic for a fixed index state); the ranks use
        # exact distance and the dense tie key, after the relaxed scan.
        ctes.append(f"""dense_{i} AS (
  SELECT v.representation_id AS id, v.repo_id, v.embedding <=> {qvec} AS distance
    FROM vector_d768 v
    JOIN eligible_repo el_d{i} ON el_d{i}.repo_id = v.repo_id
   WHERE v.spec_id = %(spec_{i})s
     AND {pred}
   ORDER BY v.embedding <=> {qvec}
   LIMIT {LEG_LIMIT}
), dense_{i}_ranked AS (
  SELECT d.id, row_number() OVER (ORDER BY d.distance, d.repo_id, rep.path, d.id) AS r
    FROM dense_{i} d JOIN representation rep ON rep.id = d.id
)""")
        legs.append(f"SELECT id, r, 'dense' AS leg FROM dense_{i}_ranked")

    union = "\n  UNION ALL ".join(legs)
    ctes.append(f"""legs AS (
  {union}
), fused AS (
  SELECT id,
         sum(1.0 / ({RRF_K} + r)) AS fused,
         min(r) FILTER (WHERE leg = 'lexical') AS lexical_rank,
         min(r) FILTER (WHERE leg = 'dense') AS dense_rank
    FROM legs GROUP BY id
), located AS (
  SELECT rr.representation_id, rr.repo_id, rr.path, rr.blob_sha, rr.start_line, rr.end_line,
         rr.symbol, rr.header, rr.body_text, f.lexical_rank, f.dense_rank, f.fused,
         row_number() OVER (PARTITION BY rr.repo_id, rr.path
                            ORDER BY f.fused DESC, rr.start_line, rr.representation_id) AS file_rank
    FROM fused f JOIN retrieval_rows rr ON rr.representation_id = f.id
)""")
    sql = "WITH " + ",\n".join(ctes) + f"""
SELECT representation_id, repo_id, path, blob_sha, start_line, end_line, symbol, header, body_text,
       lexical_rank, dense_rank, fused
  FROM located
 WHERE file_rank <= {PER_FILE_CAP}
 ORDER BY fused DESC, repo_id, path, start_line, representation_id
 LIMIT %(k)s"""
    return HybridQuery(sql, params)


def execute(conn, query: HybridQuery, scope: AuthorizedScope) -> list[dict[str, Any]]:
    """Run the statement in its own transaction with the dense legs' session setting, then assert
    every row against the scope (9.1.5's second layer). `conn` is a psycopg connection."""
    with conn.transaction():
        conn.execute(SESSION)
        cur = conn.execute(query.sql, query.params)
        names = [c.name for c in cur.description]
        rows = [dict(zip(names, r, strict=True)) for r in cur.fetchall()]
    assert_rows_authorized(rows, scope)
    return rows
