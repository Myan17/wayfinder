"""S2's load command, without a database or Ollama: the corpus refusal, the runtime check and the report."""

from datetime import timedelta
from pathlib import Path

import pytest
from s2 import load, load_plan, load_run, services
from s2.inputs import Window

MANIFEST = {
    "selected": [8, 7],
    "candidates": [
        {"github_repo_id": 7, "repo": "o/a", "as_of_commit": "c7", "chunk_estimate": 2},
        {"github_repo_id": 8, "repo": "o/b-c", "as_of_commit": "c8", "chunk_estimate": 1},
        {"github_repo_id": 9, "repo": "o/x", "as_of_commit": "c9", "chunk_estimate": 5},
    ],
}


def snapshot(sizes):
    seen = []

    def snap(git_dir, commit, repo):
        seen.append((git_dir, commit, repo))
        return [Window(repo, f"f{i}.py", 0, 1, "x\n", 0) for i in range(sizes[repo])]

    snap.seen = seen
    return snap


def test_each_selected_repository_is_read_from_its_mirror_at_its_as_of_commit():
    snap = snapshot({7: 2, 8: 1})
    windows, names = load_run.corpus(MANIFEST, Path("/m"), snap)
    assert snap.seen == [(Path("/m/o__a.git"), "c7", 7), (Path("/m/o__b-c.git"), "c8", 8)]
    assert len(windows) == 3 and names == {7: "o/a", 8: "o/b-c"}


def test_a_count_that_differs_from_the_manifest_refuses_the_run():
    with pytest.raises(load_run.Refused, match="7: 3 windows, manifest chunk_estimate 2"):
        load_run.corpus(MANIFEST, Path("/m"), snapshot({7: 3, 8: 1}))


def ollama(version=services.OLLAMA_VERSION, digest=services.MODEL_DIGEST):
    def http(url, body):
        if url.endswith("/api/version"):
            return 200, {"version": version}
        return 200, {"models": [{"name": services.MODEL, "digest": digest}]}

    return http


def test_the_runtime_must_be_the_pinned_version_and_digest():
    assert load_run.check_runtime(ollama()) == f"ollama/{services.OLLAMA_VERSION}"
    with pytest.raises(load_run.Refused, match=r"Ollama 0\.5\.0, pinned"):
        load_run.check_runtime(ollama(version="0.5.0"))
    with pytest.raises(load_run.Refused, match="digest beef"):
        load_run.check_runtime(ollama(digest="beef"))


def test_the_distribution_is_nearest_rank():
    assert load_run.distribution(list(range(1, 101))) == {"count": 100, "p50": 50, "p95": 95, "max": 100}
    assert load_run.distribution([7]) == {"count": 1, "p50": 7, "p95": 7, "max": 7}
    assert load_run.distribution([]) == {"count": 0, "p50": None, "p95": None, "max": None}


def loaded():
    t = load_plan.Truncated(7, 3, "b.py", 61, 120, 2048, "the input length exceeds the context length")
    return load.Loaded(
        durations={0: timedelta(seconds=90), 3: timedelta(minutes=2)},
        real={0: 3, 3: 1},
        padded={0: 9, 3: 3},
        windows=5,
        accepted_tokens=[10, 30, 20, 40],
        truncated=[t],
    )


def test_the_report_gives_the_lease_counts_padding_and_every_truncated_window():
    r = load_run.report(loaded(), "60k", {"commit": "abc"})
    assert r["lease_seconds"] == 3600 and r["build_seconds"] == {"00": 90.0, "03": 120.0}
    assert (r["windows"], r["distinct_representations"], r["live_representations"]) == (5, 4, 16)
    assert r["padding_fraction"] == 0.75 and r["per_pseudo_repository"]["03"] == {"real": 1, "padded": 3}
    assert r["truncated"]["count"] == 1 and r["truncated"]["fraction"] == 0.2
    assert r["truncated"]["rejected_length"] == "exceeds 2,048"
    assert r["truncated"]["windows"][0] == {
        "github_repo_id": 7,
        "pseudo_repo": 3,
        "path": "b.py",
        "start_line": 61,
        "end_line": 120,
        "prompt_eval_count": 2048,
        "error": "the input length exceeds the context length",
    }
    assert r["accepted_tokens"] == {"count": 4, "p50": 20, "p95": 40, "max": 40}
    assert r["label"].startswith("scale evidence") and "not DESIGN §9.4's chunker" in r["chunker"]
    assert r["commit"] == "abc"


def test_the_real_size_is_not_labelled_scale_evidence_and_has_no_padding():
    got = loaded()
    got.padded = {0: 0, 3: 0}
    r = load_run.report(got, "real", {})
    assert r["label"] == "real corpus" and r["padding_fraction"] == 0 and r["live_representations"] == 4


def test_a_refusal_exits_1_before_anything_is_loaded(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(load_run, "corpus", lambda m, p: (_ for _ in ()).throw(load_run.Refused("no mirror")))
    monkeypatch.setattr(load_run, "run", lambda *a: pytest.fail("loaded after a refusal"))
    out = tmp_path / "r.json"
    assert load_run.main(["--mirrors", str(tmp_path), "--size", "real", "--out", str(out)]) == 1
    assert "refused: no mirror" in capsys.readouterr().err and not out.exists()
