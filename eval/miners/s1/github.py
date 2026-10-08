"""S1 acquisition, GitHub API side: linkable pairs, repository metadata, S1-5's token check and tally.

Every read is a GraphQL query as an ordinary user (ADR-0016 S1-5). The transport is injectable, so
tests replay recorded responses and make no network call. The git side is `s1.repo`.
"""

from __future__ import annotations

import datetime as dt
import json
import urllib.request
from collections.abc import Callable, Iterator
from dataclasses import dataclass

ENDPOINT = "https://api.github.com/graphql"
MAX_CLOSING = 50  # closing references read per PR; a PR with more fails closed rather than undercount

# (body) -> (status, headers with lower-case names, parsed JSON)
Transport = Callable[[bytes], tuple[int, dict[str, str], dict]]


def urllib_transport(token: str) -> Transport:
    def send(body: bytes) -> tuple[int, dict[str, str], dict]:
        req = urllib.request.Request(ENDPOINT, data=body, method="POST")
        req.add_header("Authorization", f"bearer {token}")
        req.add_header("Content-Type", "application/json")
        with urllib.request.urlopen(req, timeout=60) as resp:
            headers = {k.lower(): v for k, v in resp.headers.items()}
            return resp.status, headers, json.load(resp)

    return send


def scope_problem(headers: dict[str, str]) -> str | None:
    """S1-5: None only if the token is a classic token with no scopes at all.

    A classic token reports its scopes in X-OAuth-Scopes. Any scope (`repo`, `workflow`, even
    `public_repo`) is more access than an ordinary user's public reads, and a missing header means
    a token whose scopes cannot be proven (fine-grained or App), so both fail.
    """
    if "x-oauth-scopes" not in headers:
        return "token scopes not reported (not a classic token)"
    scopes = headers["x-oauth-scopes"].strip()
    return f"token has scopes: {scopes}" if scopes else None


class Client:
    """Posts GraphQL queries, checks S1-5 on every response, and keeps S1-5's call tally."""

    def __init__(self, transport: Transport):
        self._send = transport
        self.calls = {"graphql": 0, "rest": 0}

    def query(self, query: str, **variables) -> dict:
        self.calls["graphql"] += 1
        status, headers, body = self._send(json.dumps({"query": query, "variables": variables}).encode())
        if problem := scope_problem(headers):
            raise PermissionError(f"S1-5: {problem}")
        if status != 200 or body.get("errors"):
            raise RuntimeError(f"GraphQL failed ({status}): {body.get('errors') or body}")
        return body["data"]


REPO_QUERY = """query($owner: String!, $name: String!) {
  repository(owner: $owner, name: $name) {
    databaseId isArchived defaultBranchRef { name } licenseInfo { spdxId }
  }
}"""


@dataclass(frozen=True)
class Repo:
    github_repo_id: int
    default_branch: str
    api_spdx: str | None  # the API's license, cross-checked against the clone's (S1-1)
    archived: bool


def repo(client: Client, owner: str, name: str) -> Repo:
    r = client.query(REPO_QUERY, owner=owner, name=name)["repository"]
    spdx = (r["licenseInfo"] or {}).get("spdxId")
    return Repo(r["databaseId"], r["defaultBranchRef"]["name"], spdx, r["isArchived"])


PRS_QUERY = """query($owner: String!, $name: String!, $after: String, $closing: Int!) {
  repository(owner: $owner, name: $name) {
    pullRequests(states: MERGED, first: 50, after: $after, orderBy: {field: CREATED_AT, direction: ASC}) {
      pageInfo { hasNextPage endCursor }
      nodes {
        number mergedAt headRefOid
        commits(first: 1) { nodes { commit { oid } } }
        closingIssuesReferences(first: $closing) {
          totalCount nodes { number updatedAt repository { databaseId } }
        }
      }
    }
  }
}"""


@dataclass(frozen=True)
class Linked:
    """One S1-2 pair: a merged PR and a same-repository issue it closes, before any D-rule."""

    issue: int
    pr: int
    first_commit: str  # D-1's base is this commit's parent (`s1.repo.resolve`)
    head: str
    merged_at: dt.datetime
    issue_updated_at: dt.datetime  # D-3


def _time(s: str) -> dt.datetime:
    return dt.datetime.fromisoformat(s.replace("Z", "+00:00"))


def linked_pairs(client: Client, owner: str, name: str, repo_id: int, as_of: dt.datetime) -> Iterator[Linked]:
    """Every (issue, PR) pair S1-2 counts: merged before `as_of`, closing an issue in this repository.

    All merged PRs are paged, because the search API caps at 1,000 results and would undercount.
    """
    after = None
    while True:
        page = client.query(PRS_QUERY, owner=owner, name=name, after=after, closing=MAX_CLOSING)
        page = page["repository"]["pullRequests"]
        for pr in page["nodes"]:
            merged = _time(pr["mergedAt"])
            refs = pr["closingIssuesReferences"]
            if merged >= as_of or not refs["totalCount"]:
                continue
            if refs["totalCount"] > len(refs["nodes"]):
                raise RuntimeError(f"PR {pr['number']} closes more than {MAX_CLOSING} issues")
            if not pr["commits"]["nodes"]:
                raise RuntimeError(f"PR {pr['number']} lists no commits")
            first = pr["commits"]["nodes"][0]["commit"]["oid"]
            for issue in sorted(refs["nodes"], key=lambda i: i["number"]):
                if issue["repository"]["databaseId"] == repo_id:
                    updated = _time(issue["updatedAt"])
                    yield Linked(issue["number"], pr["number"], first, pr["headRefOid"], merged, updated)
        if not page["pageInfo"]["hasNextPage"]:
            return
        after = page["pageInfo"]["endCursor"]
