# The review bus — architecture, reading list, onboarding

The rules are in ADR-0016. This file says how the bus works, what to read to understand it, how to
run it, and how to extend it.

**Who is who.** `Myan17` is Myan's author account. `gupta958` is Myan's second account, used only to
review and merge. It is not a second person (ADR-0016, Context). Both watchers run on Myan's Mac,
and each has its own `gh` login.

## 1. Reading list (about 40 minutes, in this order)

For Myan before switching the bus on, and for anyone joining who needs to trust what it merges.

| # | File | Why you read it | Time |
|---|---|---|---|
| 1 | `docs/adr/ADR-0016-review-bus-delegated-approval.md` | What the reviewer agent may do, and every gate it must pass | 10 min |
| 2 | This file, §2–§5 | How the two sides talk and what each message means | 10 min |
| 3 | `scripts/reviewbus/gates.py` | **The one file that decides whether the reviewer account approves.** Every gate is a small function with a test | 8 min |
| 4 | `scripts/reviewbus/protocol.py` | The message format, and the author check that ignores comments from anyone else | 5 min |
| 5 | `scripts/reviewbus/prompts/review.md` | Exactly what the reviewer model is told, and the verdict schema it must return | 5 min |
| 6 | `scripts/reviewbus/reviewer.py` | The reviewer watcher's loop: poll, review, gate, act | 5 min |
| 7 | `docs/team/reviewbus.example.toml` | The only settings: agent CLI per role, gh config directory per role, interval | 1 min |
| 8 | `scripts/check_gh_account.py` (#44) | The guard that stops either side posting as the other | 2 min |

You can skip `author.py`, `prompts/fix.md` and `github.py`, a thin `gh` wrapper. Each is under 200
lines if you want to look.

## 2. The whole picture

```
Myan's Mac, role author             GitHub PR = the bus                    Myan's Mac, role reviewer
GH_CONFIG_DIR default (Myan17)       comments with a JSON header            GH_CONFIG_DIR reviewer (gupta958)
author watcher (plain Python)                                               reviewer watcher (plain Python)
  PR opened or pushed ─────────────► review_request {head, round} ───────► new head seen
                                                                              runs the agent CLI on the diff
                                                                              gets a JSON verdict
                                     review_result {verdict, findings} ◄──  gates.py decides the action
  changes requested ◄──────────────                                          approve + merge, or
  runs `claude -p` in the worktree                                            request changes, or
  guardrails pass? then push ──────► fix_pushed {head, round, disputes} ──►  needs_human (tier or stuck)
                                     escalate @Myan17 @Gupta958  (round 4, dispute, error)
```

- **The watchers are plain Python.** They poll `gh` every few minutes and start the agent only when
  a PR has a new head to review or a new verdict to act on. A quiet poll costs no model tokens.
- **One Mac, two logins, never switched.** `cli.py watch` runs both roles. Each role's `gh` calls
  carry that role's `GH_CONFIG_DIR`, and each role checks its own login before it writes. The global
  active account stays Myan17, so the #36–#39 collision cannot recur.
- **Two contexts.** The reviewer agent starts a fresh session each round, with no memory of the
  author's session. Where one is available it uses a different model from the author's.
- **The bus is the only state that matters.** Each watcher keeps a small cache
  (`~/.local/state/wayfinder-reviewbus/`) of what it has already handled, and can rebuild it from
  the PR comments. Deleting the cache is always safe.

## 3. Messages

Each bus message is a PR comment. Its first line is a hidden header, and the rest is for humans:

```
<!-- reviewbus v1 {"type":"review_result","pr":36,"head":"6e32783","round":1,"verdict":"changes"} -->
**Changes requested** (round 1, head 6e32783)
1. [blocking] scripts/orient.py:52 — orient_items reads every table ...
```

| type | Posted by | Fields | Meaning |
|---|---|---|---|
| `review_request` | PR author (Myan17) | head, round | Review this head |
| `review_result` | Gupta958 | head, round, verdict (`approve` / `changes` / `needs_human`), findings[], model, gates{} | The reviewer's call, and which gates passed |
| `fix_pushed` | PR author | head, round, addressed[], disputes[] | A new head answers the findings; disputes stop the loop |
| `escalate` | either | reason, question | A human is needed. The comment @-mentions Myan17 |

A finding has `id`, `file`, `line`, `severity`, `blocking` and `text`. Messages from any other
GitHub account are ignored (ADR-0016 rule 6).

## 4. The life of one PR

`requested` → `reviewing` → `approved`, and then merged by the watcher. Or:

- `changes` → the author side fixes and sends `fix_pushed` → back to `reviewing` for round 2, then 3.
- `needs_human` → Myan clicks as gupta958. The watcher does nothing more on that head.
- `escalated`, after round 4, a dispute or an error → both watchers stop on this PR until a human
  comments.

**When main moves** (another PR merged), the author watcher rebases the PR, runs guardrails,
refreshes the description, pushes and sends `fix_pushed` with `"rebase": true`. The reviewer
re-checks the gates but does not re-run the model unless the diff changed beyond the rebase.

## 5. Modes (repository variable `WAYFINDER_AGENT_APPROVAL`)

| Value | Reviewer watcher does |
|---|---|
| `off` (default) | Nothing on its own. The review_handoff briefs keep working as now |
| `shadow` | Reviews and posts "would approve / would request changes". Myan still clicks as gupta958 |
| `on` | Approves and merges when every gate passes. The human-only tier is always Myan's click |

Switch modes from a phone: GitHub → Settings → Variables, or
`gh variable set WAYFINDER_AGENT_APPROVAL --body off`.

## 6. Setup on Myan's Mac (one time, about 10 minutes)

1. Give the reviewer login its own `gh` directory:
   `GH_CONFIG_DIR=~/.config/wayfinder/gh-reviewer gh auth login` as gupta958. The default directory
   keeps Myan17 active. Then sign gupta958 out of the default directory:
   `gh auth logout -h github.com -u gupta958`.
2. Choose the agent CLI for each role. Using a different model for the reviewer is better; the
   default is Claude Code for both, in separate sessions.
3. `cp docs/team/reviewbus.example.toml ~/.config/wayfinder/reviewbus.toml` and fill in the two
   `gh_config_dir` values and the agents.
4. `python3 scripts/reviewbus/cli.py doctor`. It checks that each role's directory is logged in as
   that role's account, that the default is Myan17, that the CLIs work and what the variable is set
   to. It posts nothing.
5. `python3 scripts/reviewbus/cli.py watch`. The example config has a launchd entry that starts it
   at login.

## 7. Package layout (`scripts/reviewbus/`)

Each file has one job, and one test file of the same name in `scripts/tests/reviewbus/`.

| File | One job | Depends on |
|---|---|---|
| `protocol.py` | Build and parse bus messages; the author-role check | nothing |
| `state.py` | The PR life cycle (§4), rebuilt from comments; the local cache | protocol |
| `gates.py` | ADR-0016 rule 4: one function per gate, and `decide()` | protocol, tier config |
| `tier.py` | Is a file in the human-only tier? Paths come from OWNERSHIP.md, not a copy | OWNERSHIP.md |
| `github.py` | Every `gh` call in one place (list PRs, comments, checks, review, merge), each run with its role's `GH_CONFIG_DIR` and account check | `gh`, `check_gh_account` |
| `agents.py` | Run the configured CLI (`codex exec` / `claude -p`) with a prompt; parse the JSON verdict | the CLI |
| `reviewer.py` | The reviewer role's loop | all of the above |
| `author.py` | The author role's loop: request review, fix, rebase, reply | all of the above, and `scripts/log.sh` |
| `cli.py` | `watch` (both roles), `doctor`, `once <pr>` (one pass on one PR), `--dry-run` | reviewer, author |
| `prompts/review.md`, `prompts/fix.md` | What each model is told, with the verdict schema | — |

`scripts/codemap.py` lists the package, and `python3 scripts/reviewbus/cli.py --help` lists every
command.

## 8. Extending it

- **Add a gate:** a function in `gates.py` that returns `(ok, reason)`, added to `GATES`, with a test
  that it blocks. Then add a line to ADR-0016 rule 4 in the same PR. The human-only tier applies,
  since `scripts/reviewbus/**` is in it.
- **Add an agent CLI:** one entry in `agents.py`'s `COMMANDS` (argv template and output parsing),
  plus a fake-CLI test.
- **Add a message type:** a row in §3, the builder and parser in `protocol.py`, and a transition
  in `state.py`, each with a test.

## 9. Testing

- Unit tests use a fake `gh`, which replays recorded JSON, and a fake agent CLI, which prints fixed
  JSON. No test calls GitHub or a model.
- Each gate has a test proving it can block: a red check, a head that moved, a tier path, round 4,
  a stale description, a malformed verdict and the switch off.
- There are spoofing tests: a `review_result` from another account is ignored, and a role whose `gh` login is the other role's account refuses to write.
- `cli.py once <pr> --dry-run` runs the whole pipeline on a real PR and prints the actions without
  posting. It is the first thing run on each machine.

## 10. How it lands

| PR | Content | Approved by |
|---|---|---|
| 1 | ADR-0016 and this file, the spec | Myan as gupta958 by hand. The AGENTS.md and ROSTER text is committed by Myan by hand |
| 2 | `protocol`, `state`, `tier`, `gates`, `github`, with tests | Myan as gupta958 by hand |
| 3 | `agents`, `reviewer`, `prompts/review.md`, `cli doctor/once/watch`, example config | Myan as gupta958 by hand |
| 4 | `author`, `prompts/fix.md`, launchd entry for Myan, CLAUDE.md pointer | Myan as gupta958 by hand, then **shadow week** |
