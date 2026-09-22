#!/usr/bin/env python3
"""Spike S3: measure ADR-0007's acceptance rules against a pinned ParadeDB image.

    docker compose -f infra/spikes/s3/compose.yml up -d
    uv run python infra/spikes/s3/run.py
    docker compose -f infra/spikes/s3/compose.yml down

Every rule here is defined in docs/adr/ADR-0007-lexical-search-engine-acceptance.md, which is on
`main` and was merged before this file existed. This script does not decide what passes; it reports
what happened against rules it cannot edit. If a rule seems wrong, the honest move is to change the
ADR in its own pull request and say so -- not to soften an assertion here.

S3-1b is not implemented: it requires the provisioned Oracle A1, and there is no way to fake it from
a development machine. It is reported as OUTSTANDING so a partial run can never read as acceptance.
"""

from __future__ import annotations

import json
import platform
import subprocess

import psycopg

DSN = "postgresql://wayfinder:spike_local_only_not_a_secret@localhost:55432/s3spike"
DIGEST = "paradedb/paradedb@sha256:c17153b8b7307734c3aede0393dfe8fa447f4a528ec028b1c3937186ab3ee242"

# DESIGN §9.2, copied exactly. S3-2 requires this DDL to be accepted verbatim, so it is pasted
# rather than adapted; if it needs adapting, that is the finding.
BM25_DDL = """
CREATE INDEX rep_bm25 ON representation USING bm25 (id, header, body_text, repo_id, live)
  WITH (key_field = 'id')
"""

# A cut-down `representation` (DESIGN §9.2) carrying the columns the BM25 index names, plus a `gen`
# label the real table does not have. In the real schema a generation is bound through `occurrence`
# and activation flips `live`; `gen` exists only so a test can assert *which* generation a row came
# from. It is spike scaffolding and is not proposed for the schema.
SCHEMA = """
CREATE TABLE representation (
  id         bigserial PRIMARY KEY,
  repo_id    bigint  NOT NULL,
  gen        int     NOT NULL,
  header     text    NOT NULL,
  body_text  text    NOT NULL,
  live       boolean NOT NULL DEFAULT false
)
"""


class Results:
    def __init__(self) -> None:
        self.rows: list[tuple[str, str, str]] = []

    def record(self, rule: str, verdict: str, detail: str) -> None:
        self.rows.append((rule, verdict, detail))
        print(f"{rule:8} {verdict:11} {detail}")

    @property
    def failed(self) -> list[str]:
        return [r for r, v, _ in self.rows if v == "FAIL"]


def sh(*args: str) -> str:
    return subprocess.run(args, check=True, capture_output=True, text=True).stdout.strip()


def s3_1a(r: Results, connected: bool, conn_detail: str) -> None:
    """All four of ADR-0007 S3-1's points, including point 4 — Postgres accepts a connection.

    `connected` is passed in rather than tested here because the rule is "the container starts and
    Postgres accepts a connection", and the connection the rest of the run uses is the one that
    settles it. An earlier version recorded PASS on points 1-3 and opened the connection afterwards,
    so S3-1a could read PASS in a run where Postgres never answered.
    """
    host = platform.machine()
    daemon = sh("docker", "version", "--format", "{{.Server.Arch}}")
    arch = sh("docker", "image", "inspect", DIGEST, "--format", "{{.Architecture}}")
    variant = sh("docker", "image", "inspect", DIGEST, "--format", "{{.Variant}}")

    checks = {
        "host is arm64/aarch64": host in {"arm64", "aarch64"},
        "daemon is arm64": daemon == "arm64",
        "image Architecture is arm64": arch == "arm64",
        # The ADR was corrected here: variant is optional in the OCI platform object, so an empty
        # one is not a failure. Only a declared, wrong variant is.
        "variant is v8 or absent": variant in {"v8", ""},
        "postgres accepts a connection": connected,
    }
    detail = (f"host={host} daemon={daemon} image={arch} variant={variant or '(absent)'} "
              f"connection={conn_detail}")
    failed = [name for name, ok in checks.items() if not ok]
    r.record("S3-1a", "FAIL" if failed else "PASS", detail + (f" -- failed: {failed}" if failed else ""))


def s3_1b(r: Results) -> None:
    r.record(
        "S3-1b",
        "OUTSTANDING",
        "requires the provisioned Oracle A1; cannot be measured from a development machine",
    )


def s3_2(r: Results, conn: psycopg.Connection) -> None:
    """CREATE EXTENSION plus §9.2's BM25 DDL verbatim, as SUPERUSER. ADR-0007 S3-2."""
    with conn.cursor() as cur:
        cur.execute("SELECT current_setting('is_superuser')")
        superuser = cur.fetchone()[0]
        if superuser != "on":
            # ADR-0007 declares SUPERUSER in advance, under option A, precisely so that "it needed
            # more privileges than expected, but we can arrange those" cannot become a pass. The
            # DDL below is not attempted: a success under some other privilege set would be
            # evidence for a rule nobody wrote.
            r.record("S3-2", "FAIL", f"is_superuser={superuser}, ADR-0007 S3-2 declares SUPERUSER")
            return
        cur.execute("CREATE EXTENSION IF NOT EXISTS pg_search")
        cur.execute("SELECT extversion FROM pg_extension WHERE extname = 'pg_search'")
        version = cur.fetchone()[0]
        cur.execute(SCHEMA)
        cur.execute(BM25_DDL)
    conn.commit()
    r.record("S3-2", "PASS", f"pg_search {version}, is_superuser={superuser}, §9.2 DDL accepted verbatim")


def seed(conn: psycopg.Connection) -> None:
    with conn.cursor() as cur:
        cur.executemany(
            "INSERT INTO representation (repo_id, gen, header, body_text, live) VALUES (%s,%s,%s,%s,%s)",
            [(1, 1, "old header", f"widget alpha beta {i}", True) for i in range(5)],
        )
    conn.commit()


def bm25(cur: psycopg.Cursor, term: str = "widget") -> list[tuple[int, int]]:
    """Rows matching `term` through the BM25 index, as (id, gen). Ordered for determinism."""
    cur.execute(
        "SELECT id, gen FROM representation WHERE body_text @@@ %s AND live ORDER BY id",
        (term,),
    )
    return cur.fetchall()


def s3_3(r: Results, conn: psycopg.Connection, other: psycopg.Connection) -> None:
    """Same query twice in one REPEATABLE READ transaction, with a commit in between. S3-3."""
    conn.rollback()
    with conn.cursor() as cur:
        cur.execute("BEGIN ISOLATION LEVEL REPEATABLE READ")
        first = bm25(cur)
        with other.cursor() as ocur:
            ocur.executemany(
                "INSERT INTO representation (repo_id, gen, header, body_text, live) VALUES (%s,%s,%s,%s,%s)",
                [(1, 1, "mid header", f"widget gamma {i}", True) for i in range(3)],
            )
        other.commit()
        second = bm25(cur)
        cur.execute("COMMIT")
    same = first == second
    r.record(
        "S3-3",
        "PASS" if same else "FAIL",
        f"{len(first)} rows then {len(second)} rows in one snapshot; identical={same}",
    )


def s3_4(r: Results, conn: psycopg.Connection, other: psycopg.Connection) -> None:
    """The five-step interleaving. ADR-0007 S3-4; step 4 is the rule, step 5 catches staleness."""
    conn.rollback()
    steps: dict[str, str] = {}
    with conn.cursor() as cur:
        # 1. Reader establishes a snapshot on the old generation.
        cur.execute("BEGIN ISOLATION LEVEL REPEATABLE READ")
        before = bm25(cur)
        steps["1-2 reader sees"] = str(sorted({g for _, g in before}))

        # 3. Writer activates generation 2 and commits: new rows live, old rows not.
        with other.cursor() as ocur:
            ocur.executemany(
                "INSERT INTO representation (repo_id, gen, header, body_text, live) VALUES (%s,%s,%s,%s,%s)",
                [(1, 2, "new header", f"widget delta {i}", True) for i in range(4)],
            )
            ocur.execute("UPDATE representation SET live = false WHERE gen = 1")
        other.commit()
        steps["3 writer"] = "activated gen 2, retired gen 1, committed"

        # 4. Same transaction, same query. The rule.
        after = bm25(cur)
        steps["4 same txn sees"] = str(sorted({g for _, g in after}))
        cur.execute("COMMIT")

    # 5. A new transaction must see only the new generation.
    with conn.cursor() as cur:
        cur.execute("BEGIN")
        fresh = bm25(cur)
        cur.execute("COMMIT")
    steps["5 new txn sees"] = str(sorted({g for _, g in fresh}))

    old_only = {g for _, g in after} == {1}
    unchanged = before == after
    new_only = {g for _, g in fresh} == {2}
    verdict = "PASS" if (old_only and unchanged and new_only) else "FAIL"
    detail = "; ".join(f"{k}={v}" for k, v in steps.items())
    if verdict == "FAIL":
        # One rule, one row: a second record() would double-count S3-4 in the failure list.
        detail += f" -- step4 old-only={old_only} identical-to-step2={unchanged} step5 new-only={new_only}"
    r.record("S3-4", verdict, detail)


def s3_5(r: Results, conn: psycopg.Connection, other: psycopg.Connection) -> None:
    """A deleted row leaves the index; an older snapshot still sees it. ADR-0007 S3-5."""
    conn.rollback()
    with conn.cursor() as cur:
        cur.execute("BEGIN ISOLATION LEVEL REPEATABLE READ")
        before = bm25(cur)
        with other.cursor() as ocur:
            ocur.execute("DELETE FROM representation WHERE gen = 2 AND live")
        other.commit()
        old_snapshot = bm25(cur)
        cur.execute("COMMIT")
    with conn.cursor() as cur:
        cur.execute("BEGIN")
        after = bm25(cur)
        cur.execute("COMMIT")
    held = before == old_snapshot
    gone = after == []
    r.record(
        "S3-5",
        "PASS" if (held and gone) else "FAIL",
        f"old snapshot kept {len(old_snapshot)} rows (held={held}); "
        f"new transaction sees {len(after)} (gone={gone})",
    )


def s3_6(r: Results, conn: psycopg.Connection) -> None:
    """OUTSTANDING: S3-6's rule is DESIGN §9.5's two-leg query, and this harness has one leg.

    The rule reads "EXPLAIN (ANALYZE, BUFFERS) on the two-leg hybrid query of §9.5". That query
    fuses a BM25 leg with a dense HNSW leg per embedding specification under RRF, and this spike's
    table has no vector column, no pgvector index and no embeddings. Running the lexical leg alone
    and recording PASS would be answering an easier question than the one the ADR asked.

    The single-leg plan is still captured, because it is real evidence about the lexical half and
    the follow-up builds on it -- but it is recorded as OUTSTANDING and labelled, so it cannot be
    read as S3-6. The two-leg harness is its own pull request.
    """
    conn.rollback()
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO representation (repo_id, gen, header, body_text, live) "
            "SELECT 1, 3, 'h', 'widget epsilon ' || g, true FROM generate_series(1, 2000) g"
        )
        conn.commit()
        cur.execute("ANALYZE representation")
        cur.execute(
            "EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT) "
            "SELECT id FROM representation WHERE body_text @@@ 'widget' AND live ORDER BY id LIMIT 100"
        )
        plan = "\n".join(line[0] for line in cur.fetchall())

    # "Custom Scan" only says the planner used *a* custom scan node. DESIGN §9.5 is explicit that
    # the existence of an index is not evidence that it is used (WF-25), so the observation that
    # carries weight is the index's own name appearing in the plan.
    named = "Index: rep_bm25" in plan
    seq_scan = "Seq Scan on representation" in plan
    r.record(
        "S3-6",
        "OUTSTANDING",
        f"single-leg BM25 plan only, NOT §9.5's two-leg query; rep_bm25_named={named} "
        f"seq_scan={seq_scan}",
    )
    print("\n--- EXPLAIN (ANALYZE, BUFFERS), lexical leg only, not S3-6 ---\n" + plan + "\n")


def main() -> int:
    r = Results()
    # Point 4 of S3-1 is "the container starts and Postgres accepts a connection", so the
    # connection is attempted before S3-1a is recorded rather than after it.
    conn = other = None
    try:
        conn = psycopg.connect(DSN, autocommit=True)
        other = psycopg.connect(DSN, autocommit=True)
        connected, detail = True, "accepted"
    except psycopg.OperationalError as exc:
        connected, detail = False, f"refused ({str(exc).splitlines()[0]})"

    s3_1a(r, connected, detail)
    s3_1b(r)

    if not connected:
        print("::error::cannot reach the spike database; S3-1a fails on point 4")
        print("start it with: docker compose -f infra/spikes/s3/compose.yml up -d")
    else:
        with conn, other:
            s3_2(r, conn)
            if "S3-2" in r.failed:
                print("::error::S3-2 failed; the rules below assume the extension and its index")
            else:
                seed(conn)
                s3_3(r, conn, other)
                s3_4(r, conn, other)
                s3_5(r, conn, other)
                s3_6(r, conn)

    print(json.dumps([{"rule": a, "verdict": b, "detail": c} for a, b, c in r.rows], indent=2))
    if r.failed:
        print(
            f"\n::error::FAILED: {', '.join(r.failed)} -- ADR-0007 says this is the fallback to built-in FTS"
        )
        return 1
    outstanding = [rule for rule, v, _ in r.rows if v == "OUTSTANDING"]
    print(f"\nNo rule failed. OUTSTANDING: {', '.join(outstanding)} -- this is NOT an acceptance (ADR-0007).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
