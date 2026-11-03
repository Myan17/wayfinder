import hashlib
import json
import subprocess

import pytest
from s2 import fetch_issues, inputs

NAMES = {7: "octo/repo"}


def fake(responses):
    calls = []

    def get(url):
        calls.append(url)
        return responses[url]

    return get, calls


def test_each_issue_is_fetched_from_the_pinned_rest_endpoint_and_kept_verbatim():
    url = "https://api.github.com/repos/octo/repo/issues/3"
    get, calls = fake({url: (200, {"title": "T  ", "body": None, "state": "closed"})})
    rows = fetch_issues.fetch([inputs.Issue(7, 3, "7:4")], NAMES, get)
    assert calls == [url]
    assert rows == [{"github_repo_id": 7, "issue": 3, "title": "T  ", "body": None}]  # not normalized


@pytest.mark.parametrize(
    "status, data, match",
    [(404, {}, "HTTP 404"), (410, {}, "HTTP 410"), (200, {"title": "x", "pull_request": {}}, "pull request")],
)
def test_a_missing_issue_or_a_pull_request_stops_the_fetch(status, data, match):
    get, _ = fake({"https://api.github.com/repos/octo/repo/issues/3": (status, data)})
    with pytest.raises(RuntimeError, match=match):
        fetch_issues.fetch([inputs.Issue(7, 3, "7:4")], NAMES, get)


def test_repository_names_come_from_the_manifest_for_the_selected_ids_only():
    manifest = {
        "selected": [7],
        "candidates": [{"github_repo_id": 7, "repo": "octo/repo"}, {"github_repo_id": 8, "repo": "other/x"}],
    }
    assert fetch_issues.repo_names(manifest) == NAMES


def test_the_file_and_its_meta_record_count_time_and_sha256(tmp_path):
    out = tmp_path / "issues.jsonl"
    meta = fetch_issues.write(
        [{"github_repo_id": 7, "issue": 3, "title": "é", "body": "b"}], out, "2026-11-03T00:00:00Z"
    )
    assert meta == {
        "count": 1,
        "fetched_at": "2026-11-03T00:00:00Z",
        "sha256": hashlib.sha256(out.read_bytes()).hexdigest(),
    }
    assert json.loads(out.with_suffix(".meta.json").read_text()) == meta


def test_an_output_path_inside_a_git_checkout_is_refused(capsys):
    def never(url):
        raise AssertionError("no request may be sent")

    out = fetch_issues.ROOT / "issues.jsonl"
    assert fetch_issues.main(["--out", str(out)], get=never) == 2
    assert "never committed" in capsys.readouterr().err and not out.exists()


def test_the_real_dataset_resolves_every_query_issue_to_a_repository_name():
    manifest = json.loads(fetch_issues.MANIFEST.read_text())
    pairs = [json.loads(line) for line in fetch_issues.PAIRS.read_text().splitlines()]
    names = fetch_issues.repo_names(manifest)
    assert {q.github_repo_id for q in inputs.strong_dev_issues(pairs)} <= names.keys()


def test_a_missing_subdirectory_inside_a_checkout_is_refused_from_outside_it(tmp_path, monkeypatch):
    # Regression (gupta958, #99): with the parent missing, inside_git probed the caller's cwd, so an
    # absolute path under a repository passed when the script ran from outside that repository.
    repo, outside = tmp_path / "repo", tmp_path / "outside"
    repo.mkdir()
    outside.mkdir()
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    monkeypatch.chdir(outside)
    out = repo / "not" / "yet" / "issues.jsonl"
    assert fetch_issues.inside_git(out)
    assert not fetch_issues.inside_git(outside / "missing" / "issues.jsonl")
