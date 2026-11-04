import re
import subprocess
from pathlib import Path

import pytest
from s2 import ci, reranker, services

ROOT = Path(__file__).resolve().parents[3]


def diff(*paths, fail=False):
    calls = []

    def run(argv):
        calls.append(argv)
        if fail:
            raise subprocess.CalledProcessError(128, argv)
        return "".join(f"{p}\n" for p in paths)

    run.calls = calls
    return run


@pytest.mark.parametrize(
    "path",
    [
        "eval/harness/s2/services.py",
        "eval/harness/tests/test_s2_services.py",
        "apps/api/wayfinder/retrieval/query.py",
        "apps/api/wayfinder/authz/predicate.py",
        "db/views/v_chunks.sql",
        "db/migrations/0009_x.sql",
        "db/s6_identity.py",
        "eval/datasets/s1/pairs.jsonl",
        "eval/miners/s1/universe.py",
        "infra/spikes/s3/compose.yml",
        "pyproject.toml",
        "uv.lock",
        ".github/workflows/ci.yml",
    ],
)
def test_each_of_amendment_1s_inputs_runs_the_job_in_full(path):
    assert ci.changed("a" * 40, "b" * 40, diff("README.md", path)) == ("full", [path])


def test_a_change_to_none_of_them_is_a_no_op():
    run = diff("README.md", "apps/api/wayfinder/api/app.py", "db/schema.sql", "eval/miners/s1/mine.py")
    assert ci.changed("a" * 40, "b" * 40, run) == ("no-op", [])
    assert run.calls == [["git", "diff", "--no-renames", "--name-only", f"{'a' * 40}...{'b' * 40}"]]


def test_any_doubt_about_the_diff_runs_in_full():
    assert ci.changed("0" * 40, "b" * 40, diff()) == ("full", ["no base to compare against"])  # a new branch
    assert ci.changed("", "b" * 40, diff()) == ("full", ["no base to compare against"])
    mode, why = ci.changed("a" * 40, "b" * 40, diff(fail=True))
    assert mode == "full" and why[0].startswith("git diff aaaaaaaaaaaa...bbbbbbbbbbbb failed")


def test_every_trigger_exists_and_the_workflow_is_the_one_running_the_job():
    for p in ci.DIRS + ci.FILES:
        assert (ROOT / p).exists(), p  # a renamed input would otherwise stop triggering silently
    workflow = (ROOT / ci.WORKFLOW).read_text()
    assert "python3 -m s2.ci changed" in workflow
    assert re.search(r"needs: \[[^\]]*\bs2\b", workflow)  # the dispatcher requires it
    assert "steps.scope.outputs.mode == 'full'" in workflow


def test_the_cache_keys_are_the_pinned_digests(monkeypatch):
    k = ci.keys()
    assert k["model"] == f"s2-ollama-{services.MODEL_DIGEST}"
    monkeypatch.setitem(reranker.PINS, "vocab.txt", "0" * 64)
    assert ci.keys()["reranker"] != k["reranker"]  # a new pin cannot restore the old files


class FakeOllama:
    def __init__(self, digest=services.MODEL_DIGEST):
        self.urls, self.digest = [], digest

    def __call__(self, url, body):
        self.urls.append(url.rsplit("/", 1)[1])
        if url.endswith("/api/version"):
            return 200, {"version": services.OLLAMA_VERSION}
        if url.endswith("/api/tags"):
            return 200, {"models": [{"name": services.MODEL, "digest": self.digest}]}
        return 200, {"status": "success"}


def test_a_restored_model_is_checked_never_pulled_and_a_bad_one_fails():
    run = lambda argv: ""  # noqa: E731
    http = FakeOllama()
    ci.model(True, run, http)
    assert http.urls == ["version", "tags"]
    http = FakeOllama()
    ci.model(False, run, http)
    assert http.urls == ["version", "pull", "tags"]
    with pytest.raises(services.ServiceError, match="digest beef"):
        ci.model(True, run, FakeOllama(digest="beef"))


def test_the_outputs_go_to_github_output(tmp_path, monkeypatch, capsys):
    out = tmp_path / "out"
    monkeypatch.setenv("GITHUB_OUTPUT", str(out))
    monkeypatch.setattr(ci, "changed", lambda base, head: ("no-op", []))
    assert ci.main(["changed", "a", "b"]) == 0
    assert out.read_text() == "mode=no-op\n"
    assert "the job is a no-op" in capsys.readouterr().out
