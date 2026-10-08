"""S1 acquisition, GitHub API side, against replayed responses shaped like a recorded pallets/click reply."""

import datetime as dt
import json

import pytest
from s1 import github

AS_OF = dt.datetime(2026, 9, 28, tzinfo=dt.UTC)
CLICK = 19103692
NO_SCOPES = {"x-oauth-scopes": ""}


def _replay(*bodies, headers=NO_SCOPES, status=200):
    """A transport that answers each POST with the next body, recording what was sent."""
    sent, queue = [], list(bodies)

    def send(body):
        sent.append(json.loads(body))
        return status, headers, queue.pop(0)

    return send, sent


def _pr(number, merged, issues, total=None, first="a" * 40):
    nodes = [{"number": n, "updatedAt": u, "repository": {"databaseId": r}} for n, u, r in issues]
    return {
        "number": number,
        "mergedAt": merged,
        "headRefOid": "f" * 40,
        "commits": {"nodes": [{"commit": {"oid": first}}] if first else []},
        "closingIssuesReferences": {"totalCount": len(nodes) if total is None else total, "nodes": nodes},
    }


def _page(prs, cursor=None):
    info = {"hasNextPage": cursor is not None, "endCursor": cursor}
    return {"data": {"repository": {"pullRequests": {"pageInfo": info, "nodes": prs}}}}


def test_s1_5_accepts_only_a_classic_token_with_no_scopes():
    assert github.scope_problem({"x-oauth-scopes": ""}) is None
    assert github.scope_problem({"x-oauth-scopes": "  "}) is None
    assert github.scope_problem({"x-oauth-scopes": "public_repo"}) == "token has scopes: public_repo"
    assert github.scope_problem({"x-oauth-scopes": "repo, workflow"}) == "token has scopes: repo, workflow"
    assert github.scope_problem({}) == "token scopes not reported (not a classic token)"


def test_a_scoped_token_stops_the_run_and_the_call_is_still_tallied():
    send, _ = _replay({"data": {}}, headers={"x-oauth-scopes": "repo"})
    client = github.Client(send)
    with pytest.raises(PermissionError, match="S1-5: token has scopes: repo"):
        client.query("{ viewer { login } }")
    assert client.calls == {"graphql": 1, "rest": 0}


def test_graphql_errors_and_bad_status_fail_closed():
    send, _ = _replay({"errors": [{"message": "rate limited"}]})
    with pytest.raises(RuntimeError, match="rate limited"):
        github.Client(send).query("{ x }")
    send, _ = _replay({"message": "Bad credentials"}, status=401)
    with pytest.raises(RuntimeError, match="401"):
        github.Client(send).query("{ x }")


def test_repo_metadata_and_a_missing_license():
    meta = {"databaseId": CLICK, "isArchived": False, "defaultBranchRef": {"name": "main"}}
    send, sent = _replay(
        {"data": {"repository": meta | {"licenseInfo": {"spdxId": "BSD-3-Clause"}}}},
        {"data": {"repository": meta | {"licenseInfo": None}}},
    )
    client = github.Client(send)
    assert github.repo(client, "pallets", "click") == github.Repo(CLICK, "main", "BSD-3-Clause", False)
    assert github.repo(client, "pallets", "click").api_spdx is None
    assert sent[0]["variables"] == {"owner": "pallets", "name": "click"}


def test_linked_pairs_pages_every_merged_pr_and_keeps_s1_2s_pairs():
    send, sent = _replay(
        _page(
            [
                _pr(10, "2026-01-02T00:00:00Z", [(5, "2026-01-01T00:00:00Z", CLICK)]),
                _pr(11, "2026-02-01T00:00:00Z", [], first=None),  # closes nothing: never read further
                _pr(
                    12,
                    "2026-03-01T00:00:00Z",
                    [(9, "2026-04-01T00:00:00Z", CLICK), (3, "2026-02-01T00:00:00Z", CLICK)],
                ),
            ],
            cursor="c1",
        ),
        _page(
            [
                _pr(13, "2026-05-01T00:00:00Z", [(7, "2026-05-01T00:00:00Z", 999)]),  # other repository
                _pr(14, "2026-09-28T00:00:00Z", [(8, "2026-09-01T00:00:00Z", CLICK)]),  # merged at as_of: out
                _pr(15, "2026-09-27T23:59:59Z", [(8, "2026-09-30T00:00:00Z", CLICK)]),
            ]
        ),
    )
    client = github.Client(send)
    got = list(github.linked_pairs(client, "pallets", "click", CLICK, AS_OF))
    assert [(p.issue, p.pr) for p in got] == [(5, 10), (3, 12), (9, 12), (8, 15)]
    assert got[0] == github.Linked(
        5,
        10,
        "a" * 40,
        "f" * 40,
        dt.datetime(2026, 1, 2, tzinfo=dt.UTC),
        dt.datetime(2026, 1, 1, tzinfo=dt.UTC),
    )
    assert got[3].issue_updated_at > got[3].merged_at  # D-3 decides weak later; S1-2 still counts it
    assert [s["variables"]["after"] for s in sent] == [None, "c1"]
    assert sent[0]["variables"]["closing"] == github.MAX_CLOSING
    assert client.calls == {"graphql": 2, "rest": 0}


def test_a_pr_with_unread_closing_references_or_no_commits_fails_closed():
    send, _ = _replay(
        _page([_pr(20, "2026-01-01T00:00:00Z", [(1, "2026-01-01T00:00:00Z", CLICK)], total=51)])
    )
    with pytest.raises(RuntimeError, match="PR 20 closes more than 50 issues"):
        list(github.linked_pairs(github.Client(send), "pallets", "click", CLICK, AS_OF))
    send, _ = _replay(
        _page([_pr(21, "2026-01-01T00:00:00Z", [(1, "2026-01-01T00:00:00Z", CLICK)], first=None)])
    )
    with pytest.raises(RuntimeError, match="PR 21 lists no commits"):
        list(github.linked_pairs(github.Client(send), "pallets", "click", CLICK, AS_OF))
