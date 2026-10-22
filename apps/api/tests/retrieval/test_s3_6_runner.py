"""The S3-6 evidence runner (`python -m wayfinder.retrieval.s3_6`), which step 5 runs at both sizes.
Here it runs only the 7,175 size against the pinned database, from a throwaway git repository, so the
report's provenance fields can be checked without the 60,000 build. (A smaller fixture was slower: at 700
representations each custom-plan case took about 25 s.)"""

import json
import subprocess

import pytest

from wayfinder.retrieval import s3_6

from .conftest import DSN


def repo(path, *, dirty=False):
    """A one-commit git repository at `path`, optionally with an untracked file."""
    path.mkdir()
    git = ["git", "-C", str(path)]
    subprocess.run([*git, "init", "-q"], check=True)
    subprocess.run([*git, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q", "--allow-empty",
                    "-m", "x"], check=True)
    if dirty:
        (path / "untracked").write_text("x")
    return path, subprocess.run([*git, "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()


def test_it_refuses_without_a_database(monkeypatch):
    monkeypatch.delenv("WAYFINDER_TEST_DSN", raising=False)
    with pytest.raises(SystemExit, match="WAYFINDER_TEST_DSN"):
        s3_6.main([])


def test_it_refuses_a_dirty_tree(monkeypatch, tmp_path):
    monkeypatch.setenv("WAYFINDER_TEST_DSN", "postgresql://unused")
    monkeypatch.setattr(s3_6, "ROOT", repo(tmp_path / "r", dirty=True)[0])
    with pytest.raises(SystemExit, match="uncommitted"):
        s3_6.main([])


def test_the_report_names_its_image_server_commit_and_every_case(pinned, monkeypatch, tmp_path):
    root, head = repo(tmp_path / "r")
    monkeypatch.setenv("WAYFINDER_TEST_DSN", DSN)
    monkeypatch.setattr(s3_6, "ROOT", root)
    monkeypatch.setattr(s3_6, "SIZES", s3_6.SIZES[:1])
    out = tmp_path / "report.json"
    code = s3_6.main([str(out)])
    report = json.loads(out.read_text())
    assert report["commit"] == head
    assert report["image"].startswith("paradedb/paradedb@sha256:")
    assert report["server"]["pg_search"] and "PostgreSQL" in report["server"]["version"]
    assert {(c["size"], c["granted"], c["mode"]) for c in report["cases"]} == {
        (s3_6.SIZES[0], g, m) for g in s3_6.SELECTIVITIES for m in s3_6.MODES}
    assert set(report["checks"]) == {"S3-6a", "S3-6b", "S3-6c", "S3-6d", "S3-6e"}
    assert code == (0 if report["passed"] else 1)
