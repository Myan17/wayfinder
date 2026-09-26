#!/usr/bin/env python3
"""Review handoff: request, notify, wait, record, advance -- never approve, never merge.

    scripts/review_handoff.py request <pr>    post a structured request and notify the reviewers
    scripts/review_handoff.py brief   <pr> --file BRIEF.md
                                              post the reviewer's action brief ON the pull request
    scripts/review_handoff.py packet  <pr>    build a paste-ready review bundle (local output only)
    scripts/review_handoff.py await   <pr>    poll until the review decision or merge state changes
    scripts/review_handoff.py record  <pr> --verdict approve|changes|comment --by <handle> --notes <text>
    scripts/review_handoff.py advance         after a merge, print what the stack needs next

Two rules, both pinned by tests in scripts/tests/: it never approves and never merges (AGENTS.md
reserves both for a human), and GitHub's API is the source of truth for merge state rather than
anyone's say-so. Webhook payloads carry metadata only -- no diff, no file contents.

Where the reviewer reads: the pull request. Action briefs are pull-request comments that @-mention
the reviewers, so GitHub notifies them; the webhook only mirrors a link. A brief sent only to a chat
channel the reviewer cannot read was delivered to nobody (2026-09-24).
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import subprocess
import time
import urllib.error
import urllib.request

SECURITY_MODULES = ("authz", "egress", "webhooks", "schema")
PACKET_DIFF_BUDGET = 60_000  # characters; a reviewer pasting into a chat window needs a bound


def gh(*args: str) -> str:
    return subprocess.run(["gh", *args], check=True, capture_output=True, text=True).stdout


def pr_json(pr: str, fields: str) -> dict:
    return json.loads(gh("pr", "view", pr, "--json", fields))


def reviewers() -> list[str]:
    """GitHub handles to notify, from CODEOWNERS' catch-all line."""
    try:
        with open(REPO_ROOT / ".github" / "CODEOWNERS") as fh:  # not the caller's cwd
            for line in fh:
                if line.startswith("*"):
                    return [tok for tok in line.split() if tok.startswith("@")]
    except OSError:
        pass
    return []


WEBHOOK_VAR = "WAYFINDER_REVIEW_WEBHOOK_URL"
REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
"""The repository this script lives in -- the directory holding .env.example, and so .env.

Derived from the script's own location, never from the caller's working directory. The tool is run
from wherever the author happens to be, and a `Path(".env")` would have made the webhook work or not
work depending on that -- with the common case, a subdirectory of the worktree, being the one that
silently found nothing.
"""


def main_checkout() -> pathlib.Path | None:
    """The primary checkout, when this script is running inside a linked worktree.

    A worktree has its own root but shares `.git` with the main clone, and the author configures
    `.env` once, beside `.env.example`, in the checkout they cloned. Every pull request here is
    authored from a worktree, so anchoring only on the script's own root left the tool silently
    unconfigured in the one place it is always run from. The alternative -- a copy of the same
    secret in every worktree -- is worse than the bug.
    """
    try:
        common = subprocess.run(
            ["git", "-C", str(REPO_ROOT), "rev-parse", "--path-format=absolute", "--git-common-dir"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    except (subprocess.CalledProcessError, OSError):
        return None  # not a repository, or no git; the caller falls back to REPO_ROOT alone
    return pathlib.Path(common).parent if common else None


def env_files() -> list[pathlib.Path]:
    """Where `.env` may live, nearest first: this checkout, then the clone a worktree belongs to."""
    roots = [REPO_ROOT]
    shared = main_checkout()
    if shared and shared != REPO_ROOT:
        roots.append(shared)
    return [root / ".env" for root in roots]


def webhook_url() -> str:
    """The webhook, from the environment or from .env at the repository root.

    The repository ships .env.example documenting this variable, so a reader who puts it in .env is
    doing the obvious thing; the tool honours that rather than silently ignoring it. An exported
    value is the more deliberate act, so it wins. No dependency: the file is four lines of parsing.
    """
    exported = os.environ.get(WEBHOOK_VAR, "").strip()
    if exported:
        return exported
    for env_file in env_files():
        try:
            lines = env_file.read_text().splitlines()
        except OSError:
            continue
        for line in lines:
            line = line.strip()
            if line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            if key.strip() == WEBHOOK_VAR:
                return value.strip().strip("\"'")
    return ""


USER_AGENT = "wayfinder-review-handoff/1.0 (+https://github.com/Myan17/wayfinder)"
"""Who is posting. Discord's edge answers 403 Forbidden to urllib's default `Python-urllib/3.x`,
so without this the tool reports a failed webhook and nothing reaches the channel; Slack accepts the
default, which is why this survived three pull requests. The value names the tool and the repository
rather than imitating a browser -- a channel admin looking at where this traffic comes from should
be able to see what it actually is.
"""


def notify(text: str) -> str:
    """Post metadata to the review webhook, if one is configured. Never content."""
    url = webhook_url()
    if not url:
        return "webhook: not configured (set WAYFINDER_REVIEW_WEBHOOK_URL to enable)"
    # Slack and Discord both accept a JSON body with a text-ish field; send both keys.
    body = json.dumps({"text": text, "content": text}).encode()
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json", "User-Agent": USER_AGENT},
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return f"webhook: {resp.status}"
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        # TimeoutError is not a URLError subclass, so catching URLError alone let a slow webhook
        # take down the caller. A notification is a courtesy; GitHub already holds the request.
        return f"webhook: FAILED ({exc}) -- GitHub still has the request"


def touches_security(files: list[str]) -> list[str]:
    hit = []
    for module in SECURITY_MODULES:
        if any(module in path for path in files):
            hit.append(module)
    return hit


def cmd_request(pr: str) -> int:
    data = pr_json(pr, "number,title,url,additions,deletions,files,headRefName,body")
    files = [f["path"] for f in data["files"]]
    security = touches_security(files)

    checklist = [
        "- [ ] Diff matches the stated scope; no unrelated files",
        "- [ ] Contract cards accurate; `verified_at` bumped if an interface moved",
        "- [ ] Tests pin the behaviour claimed, and you saw real output",
        "- [ ] Design claims edited in the same pull request where affected",
    ]
    if security:
        checklist.append(
            f"- [ ] `docs/team/REVIEW-CHECKLIST-SECURITY.md` — touches {', '.join(security)}; "
            "say which items you checked"
        )

    mention = " ".join(reviewers()) or "@reviewers"
    comment = (
        f"{mention} — review requested.\n\n"
        f"**{data['title']}** · +{data['additions']}/-{data['deletions']} · "
        f"{len(files)} files · `{data['headRefName']}`\n\n"
        "The work record in the description has the cards read, the contract changes and the "
        "evidence. What to look at first is at the bottom of it.\n\n"
        + "\n".join(checklist)
        + "\n\nApproval and merge are yours; this tooling does neither."
    )
    gh("pr", "comment", pr, "--body", comment)

    status = notify(
        f"Review requested: #{data['number']} {data['title']} "
        f"(+{data['additions']}/-{data['deletions']}, {len(files)} files"
        + (f", touches {', '.join(security)}" if security else "")
        + f") {data['url']}"
    )
    print(f"requested review on #{data['number']}; {status}")
    return 0


def cmd_brief(pr: str, path: pathlib.Path) -> int:
    """Post an action brief as a pull-request comment the reviewers are notified of."""
    text = path.read_text().strip()
    if not text:
        print("brief is empty; nothing posted")
        return 1
    missing = [m for m in reviewers() if m.lower() not in text.lower()]
    if missing:
        text = " ".join(missing) + " — what this pull request needs from you\n\n" + text
    url = gh("pr", "comment", pr, "--body", text).strip().splitlines()[-1]
    status = notify(f"Brief for #{pr} posted on the pull request: {url}")
    print(f"posted brief on #{pr}: {url}; {status}")
    return 0


def cmd_packet(pr: str) -> int:
    """A paste-ready bundle: description, changed files, cards touched, diff. Local output only."""
    data = pr_json(pr, "number,title,body,files,baseRefName,headRefName")
    files = [f["path"] for f in data["files"]]
    base = data["baseRefName"]
    diff = gh("pr", "diff", pr)
    truncated = len(diff) > PACKET_DIFF_BUDGET
    if truncated:
        diff = diff[:PACKET_DIFF_BUDGET]

    cards = [p for p in files if p.startswith("docs/context/modules/")]
    out = [
        f"# Review packet: #{data['number']} {data['title']}",
        f"\nBase `{base}` ← head `{data['headRefName']}`. {len(files)} files.",
        "\n## What the author says\n",
        data["body"] or "(no description)",
        "\n## Files\n",
        *[f"- {p}" for p in files],
    ]
    if cards:
        out += ["\n## Contract cards in this diff\n", *[f"- {c}" for c in cards]]
    out += [
        "\n## Diff\n",
        "```diff",
        diff,
        "```",
    ]
    if truncated:
        out.append(
            f"\n**Diff truncated at {PACKET_DIFF_BUDGET} characters.** Review the remainder on "
            "GitHub, or ask for the pull request to be split — over this size it is too big to "
            "review in one sitting anyway."
        )
    print("\n".join(out))
    return 0


def cmd_await(pr: str, interval: int, timeout: int) -> int:
    fields = "number,url,reviewDecision,mergeStateStatus,mergedAt,mergeCommit,statusCheckRollup"
    first = pr_json(pr, fields)
    print(
        f"watching #{first['number']}: review={first['reviewDecision'] or 'none'} "
        f"state={first['mergeStateStatus']}"
    )
    deadline = time.time() + timeout
    last = (first["reviewDecision"], first["mergeStateStatus"])

    while time.time() < deadline:
        time.sleep(interval)
        now = pr_json(pr, fields)

        if now["mergedAt"]:
            sha = (now.get("mergeCommit") or {}).get("oid", "")[:7]
            msg = f"#{now['number']} MERGED at {now['mergedAt']} as {sha or 'unknown commit'}"
            print(msg)
            print(notify(f"{msg} {now['url']}"))
            print("\nrun: scripts/review_handoff.py advance")
            return 0

        current = (now["reviewDecision"], now["mergeStateStatus"])
        if current != last:
            print(f"review={current[0] or 'none'} state={current[1]}")
            if current[0] == "CHANGES_REQUESTED":
                print(notify(f"Changes requested on #{now['number']} {now['url']}"))
                return 2
            last = current

    print(f"no decision within {timeout}s; the request stands on GitHub")
    return 1


def cmd_record(pr: str, verdict: str, by: str, notes: str) -> int:
    """Post a reviewer's verdict onto the pull request, where decisions belong.

    This records what a reviewer decided. It does not submit a GitHub review: an approval must come
    from the reviewer's own account, or it is not their approval.
    """
    label = {"approve": "Approved", "changes": "Changes requested", "comment": "Comment"}[verdict]
    gh(
        "pr",
        "comment",
        pr,
        "--body",
        f"**{label}** — recorded on behalf of @{by}, who reviewed this off-platform.\n\n{notes}\n\n"
        "_Recorded by tooling; the binding approval and the merge are @"
        f"{by}'s own actions on GitHub._",
    )
    print(f"recorded '{label}' from {by} on #{pr}")
    return 0


def cmd_advance() -> int:
    """After a merge: say what the stack needs, without touching anything."""
    open_prs = json.loads(gh("pr", "list", "--json", "number,title,baseRefName,mergeStateStatus,headRefName"))
    if not open_prs:
        print("no open pull requests")
        return 0
    print("open pull requests:")
    for p in sorted(open_prs, key=lambda x: x["number"]):
        note = ""
        if p["mergeStateStatus"] == "BEHIND":
            note = "  <- rebase onto main, then it needs re-approval (protection dismisses stale reviews)"
        elif p["mergeStateStatus"] == "BLOCKED":
            note = "  <- waiting on review"
        print(f"  #{p['number']} {p['title'][:52]} [{p['mergeStateStatus']}]{note}")
    print(
        "\nRebases are mechanical; approval and merge are not. This tool does the former only when "
        "you run the rebase yourself."
    )
    return 0


POSTING_VERBS = ("request", "brief", "record")


def account_guard() -> int:
    """scripts/check_gh_account.py: post only as the operator's own GitHub login."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("check_gh_account",
                                                  REPO_ROOT / "scripts/check_gh_account.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.main()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="verb", required=True)
    for verb in ("request", "packet"):
        s = sub.add_parser(verb)
        s.add_argument("pr")
    b = sub.add_parser("brief")
    b.add_argument("pr")
    b.add_argument("--file", type=pathlib.Path, required=True)
    w = sub.add_parser("await")
    w.add_argument("pr")
    w.add_argument("--interval", type=int, default=30)
    w.add_argument("--timeout", type=int, default=3600)
    r = sub.add_parser("record")
    r.add_argument("pr")
    r.add_argument("--verdict", choices=["approve", "changes", "comment"], required=True)
    r.add_argument("--by", required=True)
    r.add_argument("--notes", default="")
    sub.add_parser("advance")
    a = ap.parse_args()

    if a.verb in POSTING_VERBS and account_guard() != 0:
        return 1  # posting as the wrong account notifies no one and cannot be approved
    if a.verb == "request":
        return cmd_request(a.pr)
    if a.verb == "brief":
        return cmd_brief(a.pr, a.file)
    if a.verb == "packet":
        return cmd_packet(a.pr)
    if a.verb == "await":
        return cmd_await(a.pr, a.interval, a.timeout)
    if a.verb == "record":
        return cmd_record(a.pr, a.verdict, a.by, a.notes)
    return cmd_advance()


if __name__ == "__main__":
    raise SystemExit(main())
