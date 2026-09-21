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
scripts/review_handoff.py packet  <pr>     # paste-ready bundle for an off-platform reviewer
scripts/review_handoff.py await   <pr>     # poll until decision or merge; verifies mergedAt
scripts/review_handoff.py record  <pr> --verdict approve|changes|comment --by <handle> --notes "..."
scripts/review_handoff.py advance          # after a merge: what the stack needs now
```

## When to use which

| Situation | Verb | Notes |
|---|---|---|
| A pull request is ready | `request` | Adds the security checklist automatically when the diff touches `authz`, `egress`, `webhooks` or `schema` |
| The reviewer works outside GitHub (a chat assistant, say) | `packet` | Prints description, file list, cards touched and a bounded diff. Local output only — nothing is sent anywhere |
| Waiting | `await` | Exit 0 merged, 2 changes requested, 1 timed out. Reports every state change as it happens |
| The reviewer decided somewhere else | `record` | Posts their verdict onto the pull request so the decision lives with the code. It does **not** submit a GitHub review: an approval must come from the reviewer's own account or it is not theirs |
| A merge just landed | `advance` | Lists what is `BEHIND` (rebase, then re-approval) and what is `BLOCKED` (waiting on review). Does not touch branches |

## Notification channel

`request` and `await` post to `WAYFINDER_REVIEW_WEBHOOK_URL` when it is set — a Slack or Discord
incoming webhook. Without it they are quiet and GitHub's own review request still stands.

**Payloads are metadata only**: number, title, counts, state, URL — no diff, no file contents. Slack
and Discord are third parties, and the egress rules the design sets for the product (`DESIGN` §9.7)
apply to tooling that talks about it. A test pins this. Set it in `.env`, never committed.

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
