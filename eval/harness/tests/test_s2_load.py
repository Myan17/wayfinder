"""S2's corpus load (ADR-0019 Amendments 1-3) against the pinned database, with a fake embedder.

These need WAYFINDER_TEST_DSN (CI's db job runs them through `make db-test`) and skip without it.
"""

import sys
from collections import namedtuple
from datetime import timedelta
from pathlib import Path

import psycopg
import pytest
from s2 import load, load_plan
from s2.inputs import Window

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "db" / "tests"))
import conftest as schema_tests  # the schema tests' real-database fixtures

db, empty_db = schema_tests.db, schema_tests.empty_db  # registered here so pytest finds them


@pytest.fixture(autouse=True)
def pinned():
    """Skip, before `db` tries to create a database, when the pinned database is not reachable: CI's
    unit job exports a DSN but has no database (retrieval's tests do the same)."""
    try:
        psycopg.connect(schema_tests.DSN or "", connect_timeout=2).close()
    except psycopg.OperationalError:
        pytest.skip("the pinned database is not reachable; make db-test runs these")


s6 = load.s6
Call = namedtuple("Call", "input_hash prompt_eval_count truncated error")  # s6_ollama.Call's shape
NAMES = {7: "o/a", 8: "o/b"}
SPEC = dict(
    model_ref="nomic-embed-text:latest",
    model_digest="sha256:" + "0a" * 32,
    runtime="ollama 0.34.2",
    doc_template="search_document: {header}\n{body}",
)
RAW = "the input length exceeds the context length"


class Exceeded(RuntimeError):
    def __init__(self, error):
        super().__init__(error)
        self.error = error


class Fake:
    """`s6_ollama.embedder(record=..., truncate_rejected=True)`'s behaviour: a `long` input is retried
    truncated and recorded so; a `too_long` one is rejected again."""

    def __init__(self, long=(), too_long=(), during=None):
        self.calls, self.long, self.too_long, self.during = [], set(long), set(too_long), during

    def __call__(self, spec, text):
        if self.during:
            self.during()
        body = text.split("\n", 1)[1]
        if body in self.too_long:
            raise Exceeded(RAW)
        truncated = body in self.long
        self.calls.append(
            Call(s6.input_hash(text), 2048 if truncated else len(text), truncated, RAW if truncated else None)
        )
        return s6.stand_in(spec, text)


def w(path, first, text, pr, repo=7):
    return Window(repo, path, (first - 1) // 60, first, text, pr)


CORPUS = [
    w("a.py", 1, "one\n", 0),
    w("a.py", 61, "one\n", 0),  # identical to the window above: one representation, two occurrences
    w("b.py", 1, "two\n", 0),
    w("c.md", 1, "three\n", 3, repo=8),
    w("d.go", 1, "four\n", 99, repo=8),
]


def run(db, fake=None, **kw):
    fake = fake or Fake()
    got = load.load(
        db,
        fake,
        CORPUS,
        NAMES,
        s6.capture_spec(db, **SPEC),
        calls=fake.calls,
        context_exceeded=Exceeded,
        **kw,
    )
    return got, fake


def test_every_window_is_an_occurrence_and_identical_ones_share_a_representation(db):
    got, fake = run(db)
    assert len(got.repo_ids) == 100 and sorted(got.durations) == [0, 3, 99]
    assert got.real == {**{p: 0 for p in range(100)}, 0: 2, 3: 1, 99: 1} and got.windows == 5
    assert load.live_representations(db, got.repo_ids.values()) == 4
    assert db.execute("SELECT count(*) FROM occurrence").fetchone()[0] == 5
    assert len(fake.calls) == 4 and got.accepted_tokens and not got.truncated
    names = db.execute("SELECT full_name FROM repository ORDER BY github_repo_id").fetchall()
    assert names[0] == ("s2/pseudo-00",) and names[99] == ("s2/pseudo-99",)
    headers = {h for (h,) in db.execute("SELECT header FROM representation")}
    assert headers == {"o/a · a.py", "o/a · b.py", "o/b · c.md", "o/b · d.go"}


def test_each_build_claims_exactly_60_minutes(db, monkeypatch):
    leases, real = [], s6.push_and_claim
    monkeypatch.setattr(
        s6,
        "push_and_claim",
        lambda c, r, *, claim_for: leases.append(claim_for) or real(c, r, claim_for=claim_for),
    )
    run(db)
    assert leases == [timedelta(minutes=60)] * 3


def test_padding_reaches_the_target_proportionally_with_rows_from_zero(db):
    got, _ = run(db, pad_to=12)  # 4 real, 8 copies over weights 2,1,1: 4, 2, 2
    assert {p: n for p, n in got.padded.items() if n} == {0: 4, 3: 2, 99: 2}
    assert load.live_representations(db, got.repo_ids.values()) == 12
    pads = sorted(h for (h,) in db.execute("SELECT header FROM representation WHERE header LIKE '%s2-pad%'"))
    assert sorted(int(h.rsplit(":", 1)[1]) for h in pads) == list(range(8))  # each row once, from 0
    first = db.execute("SELECT header FROM representation WHERE header LIKE '%s2-pad:0'").fetchone()[0]
    assert first == "o/a · a.py · s2-pad:0"  # pseudo-repository 0's first source, by path then line


def test_a_build_over_the_lease_fails_the_load_and_names_it(db):
    ticks = iter([0.0, 3600.000001])
    with pytest.raises(load_plan.LoadFailed, match="pseudo-repository 0"):
        run(db, clock=lambda: next(ticks))


def test_an_expired_claim_is_refused_at_activation_and_fails_the_load(db):
    def expire():
        db.execute("UPDATE repository SET claim_expires_at = now() - interval '1 second'")

    with pytest.raises(load_plan.LoadFailed, match="pseudo-repository 0: activation refused"):
        run(db, Fake(during=expire))


def test_a_truncated_window_is_listed_and_kept_out_of_the_accepted_counts(db):
    got, _ = run(db, Fake(long={"two\n"}))
    assert [(t.path, t.start_line, t.end_line, t.prompt_eval_count, t.error) for t in got.truncated] == [
        ("b.py", 1, 1, 2048, RAW)
    ]
    assert len(got.accepted_tokens) == 4  # five windows, one truncated


def test_a_rejected_retry_fails_the_load_naming_the_window(db):
    with pytest.raises(load_plan.LoadFailed, match=f"8 c.md:1 exceeds 2,048: {RAW}"):
        run(db, Fake(too_long={"three\n"}))
