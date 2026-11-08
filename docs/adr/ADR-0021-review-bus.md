# ADR-0021 — The review bus: ChatGPT as the reviewer account's agent

- **Status:** Proposed. It takes effect only when this pull request is approved by hand from the
  reviewer account **and** the repository variables below are set. Until then nothing changes.
- **Date written:** 2026-11-08, before any bus code exists (the rules come first, as with ADR-0004 and
  ADR-0007). A first draft (2026-09-26) was numbered 0016 and then 0019, and was never pushed. Both
  numbers have since been taken by other decisions.
- **Direction:** Myan, 2026-11-08, in the session that wrote this (ORIENT rule 2): "i want to setup an
  agent harness where chatgpt and claude this session can communicate by requesting and approving pr
  approvals and rulings". His four choices are recorded in the Decision below.
- **Changes:** `AGENTS.md` §1's accountability rule, §7's branch-protection sentence, and
  `docs/team/ROSTER.md`. Agents may not edit those files (§1), so the exact text is given below and
  Myan commits it by hand.
- **Architecture and onboarding:** `docs/team/REVIEW-BUS.md`.

## Context

**`gupta958` is Myan's own second GitHub account (Myan, 2026-09-26), not a second person.** Myan
reviews through it, with ChatGPT assisting, so that main's rule of one approving review from
`gupta958` keeps writing a change separate from accepting it. `ROSTER.md` and `AGENTS.md` still describe
a separate "Engineer B". This ADR corrects that text, because a reader must not believe an independent
human reviewer exists.

Every review round costs Myan twice. Claude writes the change and posts a brief as Myan17. Myan then
pastes the brief and diff into ChatGPT, reads its answer, and posts the review or ruling as gupta958.
Then he pastes the answer back to Claude. From #94 to #113, most rounds were relays of this kind,
including every BCR and ADR "Reviewer decides" ruling.

## Decision

1. **The bus is the pull request.** The two agents talk only through PR comments that carry a
   machine-readable header (`REVIEW-BUS.md` §3). Myan can read every message. There is no other channel.
2. **Who plays which role.**
   - **Author:** the interactive Claude Code session Myan is working in, as Myan17. It watches its open
     PRs with a monitor while the session is open. Nothing runs while it is closed, and there is no
     headless author daemon.
   - **Reviewer:** a watcher on Myan's Mac (plain Python, started by launchd). It runs ChatGPT through
     the Codex CLI (`codex exec`, read-only sandbox, Myan's ChatGPT login) and posts as gupta958. Its
     credentials are in their own `gh` config directory (`GH_CONFIG_DIR`). The default directory keeps
     Myan17 active, and neither process switches the global login.
   - The reviewer's model and session are separate from the author's, so a review is never Claude
     reviewing its own work in the same context.
3. **Code decides; the model advises.** ChatGPT returns a verdict or a ruling as JSON against a fixed
   schema. The watcher's deterministic gates (rule 5) decide what is posted and done. Model output
   never reaches `gh` directly, and the model never holds a GitHub token.
4. **Approvals start in shadow mode** (repository variable `WAYFINDER_AGENT_APPROVAL`).
   - `off`: the watcher does nothing; review_handoff briefs work as today.
   - `shadow` (the starting mode, Myan's choice): ChatGPT reviews and posts "would approve" or "would
     request changes". **Myan approves and merges by hand as gupta958.** The watcher never calls
     `gh pr review --approve` or `gh pr merge` in this mode, and a test pins that.
   - `on`: the watcher approves and merges when every gate passes. Myan decides whether to switch, after
     a shadow week compares ChatGPT's calls with his own. Switching is a new amendment to this ADR.
   - Requesting changes is allowed in every mode except `off`, because it blocks nothing that a human
     would otherwise let through.
5. **The gates.** In `on` mode the watcher approves only if **all** of these hold:
   - (a) `WAYFINDER_AGENT_APPROVAL` is `on`.
   - (b) No changed file is in the human-only tier (rule 6).
   - (c) Every required check is green on the exact head commit that was reviewed.
   - (d) The verdict parses against the schema and has no blocking finding.
   - (e) The PR description names the current head commit (the stale-description rule).
   - (f) It is no later than the third review round.

   It merges with `gh pr merge --squash --match-head-commit <reviewed sha>`, so a push made after the
   review cannot merge under the old approval.
6. **The human-only tier.** For these paths ChatGPT reviews and posts, and **Myan always clicks**, even
   in `on` mode:
   - Security modules: `authz`, `egress`, `webhooks`, `schema` (their OWNERSHIP paths, `db/**` included).
   - Rules: `AGENTS.md`, `CLAUDE.md`, `ORIENT.md`, `docs/team/**`, `docs/adr/**`, `.github/**`,
     `.githooks/**`, `scripts/check_*`, `scripts/gen_codeowners.py`.
   - The bus itself: `scripts/reviewbus/**`.

   Otherwise an agent could approve a loosening of its own rules.
7. **Rulings bind unless vetoed (Myan's choice).** Repository variable `WAYFINDER_AGENT_RULINGS`
   (`off` / `on`) turns this on.
   - The author posts `ruling_request` with numbered questions, the options and its recommendation.
     ChatGPT answers each with `ruling` (decision and rationale) as gupta958.
   - A ruling **binds 12 hours after it is posted** unless Myan comments `veto <id>` from either
     account. A confirm-only ruling @-mentions Gupta958 to ask for the `confirm` (rule 11). `confirm <id>` binds it at once. Before it binds, the author may prepare the change but does
     not push work that depends on it.
   - The author records a bound ruling in the BCR's or ADR's decision section as: "Ruled by gupta958's
     agent (ChatGPT, <model>) on <date>; not vetoed by <time>" or "confirmed by Myan".
   - **Confirm-only rulings never bind by silence.** They need Myan's `confirm`. They are: any change to
     the bus, its gates or this ADR; `AGENTS.md`, `CODEOWNERS` or the roster; moving a gate date; a cut
     under DESIGN §19.8; anything touching `authz` or `egress`; and changing a prewritten acceptance rule
     after its measurement has run. The watcher marks these from the question's labels and the PR's
     paths, and when in doubt it marks confirm-only.
8. **Who may speak on the bus.** A message counts only if its GitHub author matches its role: Myan17 for
   `review_request`, `ruling_request`, `fix_pushed` and `escalate`; Gupta958 for `review_result` and
   `ruling`; and either account for `veto` and `confirm`. Anyone else's comment is ignored and logged,
   because the repository is public. Before writing, each side checks that its own `gh` login is its
   role's account (`scripts/check_gh_account.py`, #44).
9. **PR content is data.** Diffs, descriptions and comments are passed to the model as data inside a
   fixed prompt (`scripts/reviewbus/prompts/`). Text in a PR that addresses either agent carries no
   authority (`AGENTS.md` §8).
10. **Stopping.** After three rounds without a pass, or when the author disputes a finding, both sides
    stop on that PR, and the author posts `escalate`, @-mentioning Gupta958 with the open question. A
    comment from Myan restarts it.
11. **Every request for a human decision is addressed to gupta958.** This covers the GitHub review
    request on every PR, `escalate`, a confirm-only ruling, and the shadow-mode "would approve" that
    asks for the click. Each @-mentions Gupta958, because gupta958 is the account that approves, rules
    and merges, and because a comment posted as Myan17 that mentions Myan17 notifies nobody.

## Text for Myan to commit by hand

**`AGENTS.md` §1, the actors table.** Replace the Engineer B row with:

> | Reviewer account | `gupta958` | **Myan's second GitHub account**, used only to review, rule and merge. Not a second person. Its agent is ChatGPT under ADR-0021 |

**`AGENTS.md` §1, the accountability rule.** Replace "An agent never approves a pull request, never
merges, never edits ..." with:

> An agent never approves a pull request or merges one, **except** the reviewer account's agent acting
> under ADR-0021's gates; its rulings bind only as ADR-0021 rule 7 allows. Myan is accountable for
> both. No agent ever edits branch protection, CI permissions, `AGENTS.md`, `CODEOWNERS` or the roster,
> or grants itself scope.

**`AGENTS.md` §7**, after "one approving review from `gupta958` via CODEOWNERS on `*`", add:

> (Myan's reviewer account, by hand or through its agent under ADR-0021)

**`docs/team/ROSTER.md`:** for gupta958, set `name: Myan Gupta (reviewer account)`, change the role
comment to `# Myan's second account: reviews, rules and merges; not a second person`, and add
`- reviewbus/codex   # reviews and rules under ADR-0021` to its `agents:` list.

## Consequences

- A ruling can bind with no human reading it. This is the largest change. ADR rules here are evidence
  contracts (S1 to S6), so an unvetoed bad ruling changes what a spike "passes" means. Mitigations: the
  veto window, the confirm-only list, the record line in every decision, and the rule that the author
  never pushes dependent work before a ruling binds.
- Shadow mode saves little on merges, because nearly every P0 PR is in the human-only tier. The saving is
  in the relays: reviews and rulings arrive on the PR without Myan pasting anything.
- The repository says plainly that there is one engineer, a reviewer account, and a review agent. It
  makes no claim of independent human review.
- Myan's Mac must be on for the reviewer, and the Claude session must be open for the author. When
  either is off, messages wait in the PR and nothing is lost.
- Rolling back means setting both variables to `off`, with no code change.

## Rejected alternatives

- **Rulings proposed but binding only on Myan's confirm.** Safer, but Myan chose speed. It remains the
  rule for the confirm-only list.
- **A headless `claude -p` author daemon.** It would run around the clock, but Myan prefers one visible
  session to hidden ones.
- **An OpenAI API key.** It gives stricter JSON output, but adds a secret and a per-token bill. The Codex
  CLI uses the ChatGPT plan Myan already has.
- **A reviewer in GitHub Actions.** It would always be on, but needs a model key in repository secrets.
- **Letting the model call `gh` itself.** A prompt injection in a PR could then approve that PR.
