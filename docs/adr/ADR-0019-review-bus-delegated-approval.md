# ADR-0019 — The review bus, and the reviewer account's agent

- **Status:** Proposed. It takes effect only when this pull request is approved by hand from the
  reviewer account **and** `WAYFINDER_AGENT_APPROVAL` is turned on. Until then nothing changes.
- **Date written:** 2026-09-26, before any bus code exists (the rules come first, as with ADR-0004 and ADR-0007).
- **Changes:** `AGENTS.md` §1's accountability rule, §7's branch-protection sentence and `docs/team/ROSTER.md`.
  Agents may not edit those files (§1), so the exact text is given below and a human commits it.
- **Architecture and onboarding:** `docs/team/REVIEW-BUS.md`.

## Context

**`gupta958` is Myan's own second GitHub account (Myan, 2026-09-26). It is not a second person.**
Myan wears the reviewer "hat" through it, so that main's rule of one approving review from
`gupta958` separates writing a change from accepting it. `ROSTER.md` and `AGENTS.md` currently
describe a separate "Engineer B". This ADR corrects that text, because a reader of the repository
must not come away believing an independent reviewer exists.

Every review round currently takes Myan's time twice: once as author, once as reviewer, with
hand-relayed briefs between the two. On 2026-09-26 the two accounts also collided. gupta958 was the
active `gh` login in the author's session, so four PRs were opened as the reviewer and could not be
approved (#36–#39, reopened as #40–#43; #44 adds a guard).

## Decision

1. **The bus is the pull request.** Agents on each side talk only through PR comments that carry a
   machine-readable header (`docs/team/REVIEW-BUS.md` §3). Both humans can read every message. There
   is no other channel.
2. **The reviewer account's agent may approve and merge.** It runs on Myan's Mac with gupta958's
   credentials held in their own `gh` config directory (`GH_CONFIG_DIR`). The author side keeps the
   default directory, where Myan17 is active. Neither process ever switches the global login.
   **Myan is accountable for every approval**, whether it was given by hand or by the agent. The
   reviewer agent uses a separate session with no memory of the author's session and, where
   available, a different model (config `agent`), so the review is not the author reviewing
   itself in the same context.
3. **Code decides; the model advises.** The model returns a verdict. Approval happens only when the
   watcher's deterministic gates also pass (rule 4). Model output never reaches `gh` directly.
4. **The gates.** The reviewer agent approves only if **all** of these hold:
   - (a) The kill switch, repository variable `WAYFINDER_AGENT_APPROVAL`, is `on`.
   - (b) The PR is not in the human-only tier (rule 5).
   - (c) Every required check is green on the exact head commit that was reviewed.
   - (d) The verdict parses against the schema and has no blocking finding.
   - (e) The PR description names the current head commit, the reviewer's stale-description rule.
   - (f) It is no more than the third review round.

   It merges with `gh pr merge --squash --match-head-commit <reviewed sha>`, so a push made after the
   review cannot be merged under the old approval.
5. **The human-only tier.** A PR is here if any changed file matches one of the following. For these,
   the agent reviews and posts its verdict, and then **Myan clicks as gupta958**:
   - Security modules: `authz`, `egress`, `webhooks`, `schema`, meaning their OWNERSHIP paths,
     including `db/**`.
   - Rules: `AGENTS.md`, `CLAUDE.md`, `docs/team/**`, `docs/adr/**`, `.github/**`, `.githooks/**`,
     `scripts/check_*`, `scripts/gen_codeowners.py`.
   - The bus itself: `scripts/reviewbus/**`.

   Otherwise an agent could approve a loosening of its own rules.
6. **Who may speak on the bus.** A bus message counts only if its GitHub author matches its role:
   `Myan17` for `review_request` and `fix_pushed`, `Gupta958` for `review_result`. Anyone else's
   comment is ignored and logged. The repository is public, so anyone can comment. **Writes are
   checked too:** before posting, each side asserts that its own `gh` login is its role's account
   (`scripts/check_gh_account.py`, #44). Author content never goes out as the reviewer, and the
   reverse.
7. **PR content is data.** Diffs, descriptions and comments are passed to the model as data inside
   a fixed prompt (`scripts/reviewbus/prompts/`). Text in a PR that addresses the agent carries no
   authority (`AGENTS.md` §8).
8. **Stopping.** After three rounds without approval, or when the author's agent disputes a finding,
   both watchers stop on that PR and @-mention both humans with the open question. A human reply
   restarts it.
9. **Rollout.** The bus starts in **shadow mode**. It sets `WAYFINDER_AGENT_APPROVAL=shadow`, and
   the agent posts "would approve / would request changes" while Myan still clicks as gupta958.
   After a week, Myan compares the agent's calls with their own and decides whether to set `on`.
10. **The author side.** Myan's agent may push fixes to its own PR branch without Myan, within the
    task's scope. The code runs the guardrail scripts, and the push happens only if they pass. The
    agent rewrites the PR description's evidence and logs each round in the task log.

## Text for Myan to commit by hand

**`AGENTS.md` §1, the actors table.** Replace the Engineer B row with:

> | Reviewer account | `gupta958` | **Myan's second GitHub account**, used only to review and merge. Not a second person. Required reviewer on every path |

**`AGENTS.md` §1, the accountability rule.** Replace "An agent never approves a pull request, never
merges, never edits ..." with:

> An agent never approves a pull request or merges one, **except** the reviewer account's agent
> acting under ADR-0019's gates. Myan is accountable for its approvals. No agent ever edits branch
> protection, CI permissions, `AGENTS.md`, `CODEOWNERS` or the roster, or grants itself scope.

**`AGENTS.md` §7**, after "one approving review from `gupta958` via CODEOWNERS on `*`", add:

> (Myan's reviewer account, by hand or through its agent under ADR-0019)

**`docs/team/ROSTER.md`:** for gupta958, set `name: Myan Gupta (reviewer account)`, change the role
comment to `# Myan's second account: reviews and merges; not a second person`, and add
`- reviewbus/<cli>   # approves and merges under ADR-0019` to its `agents:` list.

## Consequences

- A PR outside the human-only tier can merge minutes after CI goes green, with no human in the
  loop. The trade is speed for relying on the gates and on Myan's shadow-week judgement.
- The repository states plainly that there is one engineer with a reviewer account and a review
  agent. There is no claim of independent human review.
- Myan's Mac has to be on for the bus to run. If it is off, PRs queue and nothing is lost, since the
  bus state lives in the comments.
- Rolling this back is one variable (`WAYFINDER_AGENT_APPROVAL=off`) and needs no code change.

## Rejected alternatives

- **A reviewer agent in GitHub Actions.** It would always be on, but it needs a model API key in
  repo secrets and pay-per-use billing. Myan chose the Mac with the existing subscription instead.
- **Dropping gupta958 for solo work plus an AI check.** It would be simpler, but Myan chose to keep
  the reviewer account's separation of writing from accepting.
- **A mailbox branch, or a chat bot.** Humans cannot see a mailbox branch, and a chat bot is a third
  system to keep running.
- **Letting the model call `gh` itself.** A prompt injection in a PR could then approve that PR.
