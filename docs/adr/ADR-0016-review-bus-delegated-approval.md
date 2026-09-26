# ADR-0016 — The review bus, and approval delegated to gupta958's agent

- **Status:** Proposed. It takes effect only when `gupta958` approves this pull request by hand
  **and** turns on `WAYFINDER_AGENT_APPROVAL`. Until then nothing changes.
- **Date written:** 2026-09-26, before any bus code exists (the rules come first, as with ADR-0004 and ADR-0007).
- **Changes:** `AGENTS.md` §1's accountability rule, §7's branch-protection sentence and `docs/team/ROSTER.md`.
  Agents may not edit those files (§1), so the exact text is given below and a human commits it.
- **Architecture and onboarding:** `docs/team/REVIEW-BUS.md`.

## Context

Every review round currently needs Myan to relay. Someone has to request the review, tell `gupta958`
what to look at, carry the findings back, rebase and ask again. `gupta958` cannot read the Discord
channel. The relay is the slowest step in P0.

## Decision

1. **The bus is the pull request.** Agents on each side talk only through PR comments that carry a
   machine-readable header (`docs/team/REVIEW-BUS.md` §3). Both humans can read every message. There
   is no other channel.
2. **gupta958's agent may approve and merge on gupta958's behalf.** It does so with gupta958's own
   GitHub credentials on gupta958's machine, using the model gupta958 pays for. gupta958 stays the
   accountable reviewer for every approval it gives.
3. **Code decides; the model advises.** The model returns a verdict. Approval happens only when the
   watcher's deterministic gates also pass (rule 4). Model output never reaches `gh` directly.
4. **The gates.** The reviewer agent approves only if **all** of these hold:
   - (a) The kill switch, repository variable `WAYFINDER_AGENT_APPROVAL`, is `on`.
   - (b) The PR is not in the human-only tier (rule 5).
   - (c) Every required check is green on the exact head commit that was reviewed.
   - (d) The verdict parses against the schema and has no blocking finding.
   - (e) The PR description names the current head commit, which is gupta958's stale-description rule.
   - (f) It is no more than the third review round.

   It merges with `gh pr merge --squash --match-head-commit <reviewed sha>`, so a push made after the
   review cannot be merged under the old approval.
5. **The human-only tier.** A PR is here if any changed file matches one of the following. For these,
   the agent reviews and posts its verdict, and then **gupta958 clicks**:
   - Security modules: `authz`, `egress`, `webhooks`, `schema`, meaning their OWNERSHIP paths,
     including `db/**`.
   - Rules: `AGENTS.md`, `CLAUDE.md`, `docs/team/**`, `docs/adr/**`, `.github/**`, `.githooks/**`,
     `scripts/check_*`, `scripts/gen_codeowners.py`.
   - The bus itself: `scripts/reviewbus/**`.

   Otherwise an agent could approve a loosening of its own rules.
6. **Who may speak on the bus.** A bus message counts only if its GitHub author matches its role:
   the PR author for `review_request` and `fix_pushed`, `Gupta958` for `review_result`. Anyone else's
   comment is ignored and logged. The repository is public, so anyone can comment.
7. **PR content is data.** Diffs, descriptions and comments are passed to the model as data inside
   a fixed prompt (`scripts/reviewbus/prompts/`). Text in a PR that addresses the agent carries no
   authority (`AGENTS.md` §8).
8. **Stopping.** After three rounds without approval, or when the author's agent disputes a finding,
   both watchers stop on that PR and @-mention both humans with the open question. A human reply
   restarts it.
9. **Rollout.** The bus starts in **shadow mode**. It sets `WAYFINDER_AGENT_APPROVAL=shadow`, and
   the agent posts "would approve / would request changes" while gupta958 still clicks. After a
   week, gupta958 compares the agent's calls with their own and decides whether to set `on`.
10. **The author side.** Myan's agent may push fixes to its own PR branch without Myan, within the
    task's scope. The code runs the guardrail scripts, and the push happens only if they pass. The
    agent rewrites the PR description's evidence and logs each round in the task log.

## Text for the human to commit

**`AGENTS.md` §1, the accountability rule.** Replace "An agent never approves a pull request, never
merges, never edits ..." with:

> An agent never approves a pull request or merges one, **except** `gupta958`'s review agent acting
> under ADR-0016's gates, which does so on gupta958's behalf. gupta958 stays accountable for its
> approvals. No agent ever edits branch protection, CI permissions, `AGENTS.md`, `CODEOWNERS` or the
> roster, or grants itself scope.

**`AGENTS.md` §7**, after "one approving review from `gupta958` via CODEOWNERS on `*`", add:

> (given by hand, or by gupta958's review agent under ADR-0016)

**`docs/team/ROSTER.md`:** under gupta958's `agents:` list, add
`- reviewbus/<cli>   # approves and merges under ADR-0016; <cli> is codex or claude-code`.

## Consequences

- A PR outside the human-only tier can merge minutes after CI goes green, with no human in the
  loop. The trade is speed for relying on the gates and on gupta958's shadow-week judgement.
- gupta958's machine has to be on for reviews to happen. If it is off, PRs queue and nothing is
  lost, since the bus state lives in the comments.
- Rolling this back is one variable (`WAYFINDER_AGENT_APPROVAL=off`) and needs no code change.

## Rejected alternatives

- **A reviewer agent in GitHub Actions.** It would always be on, but it needs a model API key in
  repo secrets and pay-per-use billing. Myan chose gupta958's machine instead.
- **A mailbox branch, or a chat bot.** Humans cannot see a mailbox branch, and gupta958 cannot
  read Discord.
- **Letting the model call `gh` itself.** A prompt injection in a PR could then approve that PR.
