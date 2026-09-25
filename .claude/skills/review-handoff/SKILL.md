---
name: review-handoff
description: Hand a pull request to the reviewer and track it to a decision - request review with the right checklist, notify the review channel, build a paste-ready packet for an off-platform reviewer, wait for the verdict, record it, and report what the stack needs next. Never approves and never merges. Use when a pull request is ready for review, when waiting on one, or after a merge.
---

# Review handoff

Automates everything around a review except the review. Approval and merge belong to a human
reviewer (`AGENTS.md` §1), so this skill has no verb for either, and its tests fail if one appears.

**GitHub's API is the source of truth.** "It is merged" is a claim to verify — this project has
already rebased once against a merge that had not happened.

## Verbs

```bash
scripts/review_handoff.py request <pr>     # structured request + checklist + notify
scripts/review_handoff.py brief   <pr> --file BRIEF.md   # the reviewer's action brief, posted ON the PR
scripts/review_handoff.py packet  <pr>     # paste-ready bundle for an off-platform reviewer
scripts/review_handoff.py await   <pr>     # poll until decision or merge; verifies mergedAt
scripts/review_handoff.py record  <pr> --verdict approve|changes|comment --by <handle> --notes "..."
scripts/review_handoff.py advance          # after a merge: what the stack needs now
```

## When to use which

| Situation | Verb | Notes |
|---|---|---|
| A pull request is ready | `request` | Adds the security checklist automatically when the diff touches `authz`, `egress`, `webhooks` or `schema` |
| The reviewer needs to act: what to look at, what to decide, what not to do | `brief` | **After every open, rebase, force-push or dismissed approval.** Posts a PR comment that @-mentions the reviewers, so GitHub notifies them; the webhook gets only the link |
| The reviewer works outside GitHub (a chat assistant, say) | `packet` | Prints description, file list, cards touched and a bounded diff. Local output only — nothing is sent anywhere |
| Waiting | `await` | Exit 0 merged, 2 changes requested, 1 timed out. Reports every state change as it happens |
| The reviewer decided somewhere else | `record` | Posts their verdict onto the pull request so the decision lives with the code. It does **not** submit a GitHub review: an approval must come from the reviewer's own account or it is not theirs |
| A merge just landed | `advance` | Lists what is `BEHIND` (rebase, then re-approval) and what is `BLOCKED` (waiting on review). Does not touch branches |

## Where the reviewer actually reads

**The pull request.** The reviewer cannot read the chat channel behind the webhook. Every brief sent
only there between 2026-09-22 and 2026-09-24 reached nobody, until Myan relayed it. So a brief is
always a pull-request comment (`brief`), and the webhook is a mirror, never the delivery.

## Notification channel

`request` and `await` post to `WAYFINDER_REVIEW_WEBHOOK_URL` when it is set — a Slack or Discord
incoming webhook. Without it they are quiet and GitHub's own review request still stands.

**The webhook is outbound only.** An incoming webhook accepts POSTs; it cannot read the channel.
Nothing here waits on a chat reply, and nothing should: `await` reads `reviewDecision`,
`mergeStateStatus` and `mergedAt` from the GitHub API, because that is where a review decision
actually exists. A reviewer working outside GitHub — in a chat assistant with no Discord access, say
— is served by `packet` and `record`, not by a read path that does not exist. Building one would
create a second source of "approved" that looks authoritative and is not; the binding approval is
the reviewer's own action on GitHub, which branch protection requires regardless.

**Payloads are metadata only**: number, title, counts, state, URL — no diff, no file contents. Slack
and Discord are third parties, and the egress rules the design sets for the product (`DESIGN` §9.7)
apply to tooling that talks about it. A test pins this.

Set it either way: `export WAYFINDER_REVIEW_WEBHOOK_URL=...`, or a line in `.env` in the repository
root, which the tool reads and `.gitignore` keeps out of commits. An exported value wins over `.env`.

## What this skill will not do

- Approve a pull request, submit a review, or merge. No verb, no flag, no exception.
- Send diffs or file contents to a chat webhook.
- Rebase or push. `advance` tells you what needs rebasing; you run it, so a force-push is always a
  deliberate act with a log entry behind it (`AGENTS.md` §2.2).
- Treat a message as proof of a merge. Only `mergedAt` and the merge commit count.

## Adding reviewers later

Reviewers come from the catch-all line in `.github/CODEOWNERS`, which is generated from
`docs/team/ROSTER.md`. Add a person there, regenerate, and both the mention and the notification
pick them up with no change here.
