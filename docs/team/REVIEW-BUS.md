# The review bus — architecture, reading list, onboarding

The rules are in ADR-0016. This file says how the bus works, what to read to understand it, how to
run it, and how to extend it.

## 1. Reading list for gupta958 (about 40 minutes, in this order)

| # | File | Why you read it | Time |
|---|---|---|---|
| 1 | `docs/adr/ADR-0016-review-bus-delegated-approval.md` | What your agent may do, and every gate it must pass | 10 min |
| 2 | This file, §2–§5 | How the two sides talk and what each message means | 10 min |
| 3 | `scripts/reviewbus/gates.py` | **The one file that decides whether your account approves.** Every gate is a small function with a test | 8 min |
| 4 | `scripts/reviewbus/protocol.py` | The message format, and the author check that ignores comments from anyone else | 5 min |
| 5 | `scripts/reviewbus/prompts/review.md` | Exactly what your model is told, and the verdict schema it must return | 5 min |
| 6 | `scripts/reviewbus/reviewer.py` | Your watcher's loop: poll, review, gate, act | 5 min |
| 7 | `docs/team/reviewbus.example.toml` | The only settings you choose: agent CLI, interval, mode | 1 min |

The files you do not need to read: `author.py` and `prompts/fix.md` run only on Myan's machine, and
`github.py` is a thin `gh` wrapper. Each one is still under 200 lines if you want to look.

## 2. The whole picture

```
Myan's Mac                           GitHub PR = the bus                    gupta958's machine
author watcher (plain Python)        comments with a JSON header            reviewer watcher (plain Python)
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
| `escalate` | either | reason, question | A human is needed. The comment @-mentions both of you |

A finding has `id`, `file`, `line`, `severity`, `blocking` and `text`. Messages from any other
GitHub account are ignored (ADR-0016 rule 6).

## 4. The life of one PR

`requested` → `reviewing` → `approved`, and then merged by the watcher. Or:

- `changes` → the author side fixes and sends `fix_pushed` → back to `reviewing` for round 2, then 3.
- `needs_human` → gupta958 clicks. The watcher does nothing more on that head.
- `escalated`, after round 4, a dispute or an error → both watchers stop on this PR until a human
  comments.

**When main moves** (another PR merged), the author watcher rebases the PR, runs guardrails,
refreshes the description, pushes and sends `fix_pushed` with `"rebase": true`. The reviewer
re-checks the gates but does not re-run the model unless the diff changed beyond the rebase.

## 5. Modes (repository variable `WAYFINDER_AGENT_APPROVAL`)

| Value | Reviewer watcher does |
|---|---|
| `off` (default) | Nothing on its own. The review_handoff briefs keep working as now |
| `shadow` | Reviews and posts "would approve / would request changes". gupta958 still clicks |
| `on` | Approves and merges when every gate passes. The human-only tier is always gupta958's click |

Either of you can switch modes from a phone: GitHub → Settings → Variables, or
`gh variable set WAYFINDER_AGENT_APPROVAL --body off`.

## 6. Setup for gupta958 (one time, about 10 minutes)

1. `gh auth login`, as Gupta958.
2. Install one agent CLI you already pay for: Codex CLI (ChatGPT plan), or Claude Code.
3. `git clone` the repo, then `cp docs/team/reviewbus.example.toml ~/.config/wayfinder/reviewbus.toml`
   and set `agent = "codex"` or `"claude"`.
4. `python3 scripts/reviewbus/cli.py doctor`. It checks gh auth, the agent CLI, the variable and the
   config, and prints what it would do. It posts nothing.
5. `python3 scripts/reviewbus/cli.py watch --role reviewer`. `docs/team/reviewbus.example.toml`
   lists launchd (macOS), systemd (Linux) and Task Scheduler (Windows) entries that start it at
   login.

## 7. Package layout (`scripts/reviewbus/`)

Each file has one job, and one test file of the same name in `scripts/tests/reviewbus/`.

| File | One job | Depends on |
|---|---|---|
| `protocol.py` | Build and parse bus messages; the author-role check | nothing |
| `state.py` | The PR life cycle (§4), rebuilt from comments; the local cache | protocol |
| `gates.py` | ADR-0016 rule 4: one function per gate, and `decide()` | protocol, tier config |
| `tier.py` | Is a file in the human-only tier? Paths come from OWNERSHIP.md, not a copy | OWNERSHIP.md |
| `github.py` | Every `gh` call in one place (list PRs, comments, checks, review, merge) | `gh` |
| `agents.py` | Run the configured CLI (`codex exec` / `claude -p`) with a prompt; parse the JSON verdict | the CLI |
| `reviewer.py` | gupta958's loop | all of the above |
| `author.py` | Myan's loop: request review, fix, rebase, reply | all of the above, and `scripts/log.sh` |
| `cli.py` | `watch`, `doctor`, `once <pr>` (one pass on one PR), `--dry-run` | reviewer, author |
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
- There is a spoofing test: a `review_result` from another account is ignored.
- `cli.py once <pr> --dry-run` runs the whole pipeline on a real PR and prints the actions without
  posting. It is the first thing run on each machine.

## 10. How it lands

| PR | Content | Approved by |
|---|---|---|
| 1 | ADR-0016 and this file, the spec | gupta958 by hand. The AGENTS.md and ROSTER text is committed by a human |
| 2 | `protocol`, `state`, `tier`, `gates`, `github`, with tests | gupta958 by hand |
| 3 | `agents`, `reviewer`, `prompts/review.md`, `cli doctor/once/watch`, example config | gupta958 by hand |
| 4 | `author`, `prompts/fix.md`, launchd entry for Myan, CLAUDE.md pointer | gupta958 by hand, then **shadow week** |
