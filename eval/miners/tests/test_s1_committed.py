"""The committed S1 dataset and manifest (ADR-0016's Decision, run 4) stay as they landed."""

import json
from pathlib import Path

from s1 import landing

S1 = Path(__file__).resolve().parents[2] / "datasets" / "s1"
A3_BAR = 300
# The first commit with ADR-0013 Amendment 1's 60 s window (#78).
RUN_4_MINER = "1eaf94a8d4401c411f64fe985bb1700ba3b9c317"


def _files():
    return (S1 / "pairs.jsonl").read_bytes(), (S1 / "manifest.json").read_text()


def test_the_committed_dataset_and_manifest_pass_landing():
    assert landing.problems(*_files()) == []


def test_the_committed_corpus_meets_a3_and_was_mined_under_the_60_s_window():
    manifest = json.loads(_files()[1])
    assert manifest["pairs_file"]["strong_count"] >= A3_BAR
    assert manifest["miner_commit"] == RUN_4_MINER
