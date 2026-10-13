"""S1's runner: `measure` end to end against a local mirror and replayed GraphQL responses."""

from s1 import github, repo, run
from test_s1_repo import _commit, _run

MIT = (
    b"Permission is hereby granted, free of charge, to any person obtaining a copy of this software.\n"
    b"The above copyright notice and this permission notice shall be included in all copies.\n"
)


def test_measure_records_every_rule_and_gold_for_each_resolved_pair(tmp_path, monkeypatch):
    work = tmp_path / "work"
    work.mkdir()
    _run(work, "init", "-q", "-b", "main")
    docs = {f"docs/p{i}.md": b"word " * 500 for i in range(5)}
    c1 = _commit(work, {"LICENSE": MIT, "app/core.py": b"x = 1\n", **docs}, "c1", "2026-01-01T00:00:00Z")
    _run(work, "checkout", "-q", "-b", "pr", c1)
    p1 = _commit(work, {"app/core.py": b"x = 2\n"}, "p1", "2026-01-05T00:00:00Z")
    _run(work, "update-ref", "refs/pull/7/head", p1)
    _run(work, "checkout", "-q", "-b", "other", c1)
    _commit(work, {"other.py": b"y = 1\n"}, "o1", "2026-01-06T00:00:00Z")
    _run(work, "checkout", "-q", "-b", "pr9", c1)
    r1 = _commit(work, {"app/core.py": b"x = 3\n"}, "r1", "2026-01-07T00:00:00Z")
    _run(work, "merge", "-q", "--no-ff", "-m", "m", "other")  # Amendment 1: base resolves, pair excluded
    _run(work, "update-ref", "refs/pull/9/head", "HEAD")
    r2 = _run(work, "rev-parse", "HEAD")
    _run(work, "checkout", "-q", "main")
    monkeypatch.setattr(repo, "mirror", lambda url, dest: _mirror(work, dest))
    meta = {
        "data": {
            "repository": {
                "databaseId": 42,
                "isArchived": False,
                "defaultBranchRef": {"name": "main"},
                "licenseInfo": {"spdxId": "Apache-2.0"},
            }
        }
    }

    def pr(number, first, head, issue, updated):
        refs = {
            "totalCount": 1,
            "nodes": [{"number": issue, "updatedAt": updated, "repository": {"databaseId": 42}}],
        }
        return {
            "number": number,
            "mergedAt": "2026-01-10T00:00:00Z",
            "headRefOid": head,
            "commits": {"nodes": [{"commit": {"oid": first}}]},
            "closingIssuesReferences": refs,
        }

    page = {
        "data": {
            "repository": {
                "pullRequests": {
                    "pageInfo": {"hasNextPage": False, "endCursor": None},
                    "nodes": [
                        pr(7, p1, p1, 3, "2026-01-09T00:00:00Z"),
                        pr(8, "e" * 40, p1, 4, "2026-02-01T00:00:00Z"),
                        pr(9, r1, r2, 5, "2026-01-09T00:00:00Z"),
                    ],
                }
            }
        }
    }
    queue = [meta, page]
    client = github.Client(lambda body: (200, {"x-oauth-scopes": ""}, queue.pop(0)))

    got = run.measure(client, "o/r", "py", tmp_path)
    rules = got["entry"]["rules"]
    assert rules["S1-1"] == {"value": {"file": "MIT", "api": "Apache-2.0"}, "pass": False}
    assert got["entry"]["spdx"] == "MIT"  # the clone's id, not the API's
    assert rules["S1-2"] == {"value": 3, "pass": False}
    assert rules["S1-3"] == {"value": {"resolved": 2, "of": 3}, "pass": False}  # the merge PR's base resolved
    assert rules["S1-4"] == {"value": {"md_files": 5, "md_words": 2500}, "pass": True}
    assert got["entry"]["as_of_commit"] == c1 and client.calls == {"graphql": 2, "rest": 0}
    seven, eight, nine = got["pairs"]
    assert (seven["base"], seven["reason"], seven["gold"], seven["strong"]) == (
        c1,
        None,
        ["app/core.py"],
        True,
    )
    assert (eight["base"], eight["reason"], eight["gold"], eight["strong"]) == (
        None,
        "first commit not in the clone",
        [],
        False,
    )
    assert (nine["base"], nine["reason"], nine["gold"]) == (c1, repo.MERGE_IN_HISTORY, [])


def _mirror(work, dest):
    _run(work.parent, "clone", "-q", "--mirror", f"file://{work}", str(dest))
    return dest


def test_main_refuses_to_start_without_the_token(monkeypatch, capsys):
    monkeypatch.delenv("WAYFINDER_S1_TOKEN", raising=False)
    assert run.main([]) == 2
    assert "WAYFINDER_S1_TOKEN is not set" in capsys.readouterr().err
