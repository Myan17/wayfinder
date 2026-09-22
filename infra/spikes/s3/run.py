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


def s3_1a(r: Results) -> None:
    """Host, daemon and image architectures agree, and the container ran. ADR-0007 S3-1."""
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
    }
    detail = f"host={host} daemon={daemon} image={arch} variant={variant or '(absent)'}"
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
    """EXPLAIN shows the BM25 index in use, and the plan is capturable. ADR-0007 S3-6."""
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
    used_index = "bm25" in plan.lower() or "Custom Scan" in plan
    seq_scan = "Seq Scan on representation" in plan
    r.record(
        "S3-6",
        "PASS" if (used_index and not seq_scan) else "RECORDED",
        f"index_in_plan={used_index} seq_scan={seq_scan}",
    )
    print("\n--- EXPLAIN (ANALYZE, BUFFERS) ---\n" + plan + "\n")


def main() -> int:
    r = Results()
    s3_1a(r)
    s3_1b(r)
    try:
        conn = psycopg.connect(DSN, autocommit=True)
        other = psycopg.connect(DSN, autocommit=True)
    except psycopg.OperationalError as exc:
        print(f"::error::cannot reach the spike database: {exc}")
        print("start it with: docker compose -f infra/spikes/s3/compose.yml up -d")
        return 1

    with conn, other:
        s3_2(r, conn)
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
    print("\nNo rule failed. S3-1b remains OUTSTANDING, so this is NOT an acceptance (ADR-0007).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
