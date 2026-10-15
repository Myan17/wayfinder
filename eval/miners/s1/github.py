"""S1 acquisition, GitHub API side: linkable pairs, repository metadata, S1-5's token check and tally.

Every read is a GraphQL query as an ordinary user (ADR-0016 S1-5). The transport is injectable, so
tests replay recorded responses and make no network call. The git side is `s1.repo`.
"""

from __future__ import annotations

import datetime as dt
import json
import time
import urllib.error
import urllib.request
from collections.abc import Callable, Iterator
from dataclasses import dataclass

ENDPOINT = "https://api.github.com/graphql"
MAX_CLOSING = 50  # closing references read per PR; a PR with more fails closed rather than undercount
ATTEMPTS = 4  # per query; only GitHub's transient failures are retried, after waits of 2, 4 and 8 s
TRANSIENT_STATUS = (502, 503, 504)
TRANSIENT_ERROR = "Something went wrong while executing your query"

# (body) -> (status, headers with lower-case names, parsed JSON)
Transport = Callable[[bytes], tuple[int, dict[str, str], dict]]


def urllib_transport(token: str) -> Transport:
    def send(body: bytes) -> tuple[int, dict[str, str], dict]:
        req = urllib.request.Request(ENDPOINT, data=body, method="POST")
        req.add_header("Authorization", f"bearer {token}")
        req.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                headers = {k.lower(): v for k, v in resp.headers.items()}
                return resp.status, headers, json.load(resp)
        except urllib.error.HTTPError as e:  # a status, so Client decides whether it is transient
            return e.code, {k.lower(): v for k, v in e.headers.items()}, {"message": e.reason}

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

    def __init__(self, transport: Transport, sleep: Callable[[float], None] = time.sleep):
        self._send = transport
        self._sleep = sleep
        self.calls = {"graphql": 0, "rest": 0}
        self.scopes_seen: list[str] = []  # X-OAuth-Scopes of every response that passed S1-5, in order

    def query(self, query: str, **variables) -> dict:
        payload = json.dumps({"query": query, "variables": variables}).encode()
        for attempt in range(1, ATTEMPTS + 1):
            self.calls["graphql"] += 1  # S1-5's tally counts every attempt
            try:
                status, headers, body = self._send(payload)
            except (TimeoutError, urllib.error.URLError) as e:
                status, headers, body = 0, {}, {"message": str(e)}
            if "x-oauth-scopes" in headers and (problem := scope_problem(headers)):
                raise PermissionError(f"S1-5: {problem}")  # even on a response that will be retried
            if not _transient(status, body):
                break
            if attempt == ATTEMPTS:
                raise RuntimeError(
                    f"GraphQL failed {ATTEMPTS} times ({status}): {body.get('errors') or body}"
                )
            self._sleep(2**attempt)
        if problem := scope_problem(headers):
            raise PermissionError(f"S1-5: {problem}")
        self.scopes_seen.append(headers["x-oauth-scopes"].strip())
        if status != 200 or body.get("errors"):
            raise RuntimeError(f"GraphQL failed ({status}): {body.get('errors') or body}")
        return body["data"]


def _transient(status: int, body: dict) -> bool:
    """GitHub's own failures, which a retry can cure; never a refusal, a bad query or a rate limit."""
    if status in (0, *TRANSIENT_STATUS):
        return True
    errors = body.get("errors") or []
    return status == 200 and bool(errors) and all(TRANSIENT_ERROR in e.get("message", "") for e in errors)


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
    first_commit: str | None  # D-1's base is its parent (`s1.repo.resolve`); None if the PR lists none
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
            # Empty for some merged fork PRs (cli/cli#7228); D-1 then reports the base as unresolved.
            commits = pr["commits"]["nodes"]
            first = commits[0]["commit"]["oid"] if commits else None
            for issue in sorted(refs["nodes"], key=lambda i: i["number"]):
                if issue["repository"]["databaseId"] == repo_id:
                    updated = _time(issue["updatedAt"])
                    yield Linked(issue["number"], pr["number"], first, pr["headRefOid"], merged, updated)
        if not page["pageInfo"]["hasNextPage"]:
            return
        after = page["pageInfo"]["endCursor"]
