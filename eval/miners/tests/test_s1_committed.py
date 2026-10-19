"""The committed S1 dataset and manifest (ADR-0016's Decision, run 4) stay as they landed."""

import hashlib
import json
from pathlib import Path

from s1 import landing

S1 = Path(__file__).resolve().parents[2] / "datasets" / "s1"
A3_BAR = 300
# The first commit with ADR-0013 Amendment 1's 60 s window (#78).
RUN_4_MINER = "1eaf94a8d4401c411f64fe985bb1700ba3b9c317"
# The accepted files' SHA-256, pinned here independently of the manifest's own pairs hash.
PAIRS_SHA256 = "8ac8212dd39770daaf3833f0885b0cc521367efdd67ea8b9d34ede1d039c8231"
MANIFEST_SHA256 = "5cdde3400193009bdd8e9a87e5d14df44f30a2f986c5eff9fec051d0c51614c3"
TOTAL, STRONG, WEAK = 2328, 1723, 605


def _bytes():
    return (S1 / "pairs.jsonl").read_bytes(), (S1 / "manifest.json").read_bytes()


def test_the_committed_files_are_the_accepted_bytes():
    pairs, manifest = _bytes()
    assert hashlib.sha256(pairs).hexdigest() == PAIRS_SHA256
    assert hashlib.sha256(manifest).hexdigest() == MANIFEST_SHA256


def test_the_committed_dataset_and_manifest_pass_landing():
    pairs, manifest = _bytes()
    assert landing.problems(pairs, manifest.decode()) == []


def test_the_committed_counts_are_the_accepted_ones():
    pairs, manifest = _bytes()
    rows = [json.loads(line) for line in pairs.splitlines()]
    strong = sum(row["strong"] for row in rows)
    assert (len(rows), strong, len(rows) - strong) == (TOTAL, STRONG, WEAK)
    counts = json.loads(manifest)["pairs_file"]
    assert (counts["total_count"], counts["strong_count"], counts["weak_count"]) == (TOTAL, STRONG, WEAK)


def test_the_committed_corpus_meets_a3_and_was_mined_under_the_60_s_window():
    manifest = json.loads(_bytes()[1])
    assert manifest["pairs_file"]["strong_count"] >= A3_BAR
    assert manifest["miner_commit"] == RUN_4_MINER
