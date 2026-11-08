# The review bus — architecture, reading list, onboarding

The rules are in ADR-0021. This file says how the bus works, what to read to understand it, how to
run it, and how to extend it.

**Who is who.** `Myan17` is Myan's author account, driven by the interactive Claude Code session he
works in. `gupta958` is Myan's second account, used only to review, rule and merge. It is not a second
person (ADR-0021, Context). Its agent is ChatGPT, run through the Codex CLI by a watcher on Myan's Mac.
Each side has its own `gh` login.

## 1. Reading list (about 40 minutes, in this order)

For Myan before switching the bus on, and for anyone joining who needs to trust what it merges.

| # | File | Why you read it | Time |
|---|---|---|---|
| 1 | `docs/adr/ADR-0021-review-bus.md` | What the reviewer agent may do, and every gate it must pass | 10 min |
| 2 | This file, §2–§5 | How the two sides talk and what each message means | 10 min |
| 3 | `scripts/reviewbus/gates.py` | **The one file that decides whether the reviewer account approves.** Every gate is a small function with a test | 8 min |
| 4 | `scripts/reviewbus/protocol.py` | The message format, and the author check that ignores comments from anyone else | 5 min |
| 5 | `scripts/reviewbus/prompts/review.md` | Exactly what the reviewer model is told, and the verdict schema it must return | 5 min |
| 6 | `scripts/reviewbus/reviewer.py` | The reviewer watcher's loop: poll, review, gate, act | 5 min |
| 7 | `docs/team/reviewbus.example.toml` | The only settings: agent CLI per role, gh config directory per role, interval | 1 min |
| 8 | `scripts/check_gh_account.py` (#44) | The guard that stops either side posting as the other | 2 min |

You can skip `github.py`, a thin `gh` wrapper, and `prompts/ruling.md`, the ruling twin of
`review.md`.

## 2. The whole picture

```
Claude Code session, role author     GitHub PR = the bus                    Myan's Mac, role reviewer
gh default dir (Myan17)              comments with a JSON header            GH_CONFIG_DIR reviewer (gupta958)
a Monitor on its open PRs                                                   reviewer watcher (plain Python, launchd)
  PR opened or pushed ─────────────► review_request {head, round} ───────► new head, checks green
                                                                              codex exec (ChatGPT) on the PR
                                                                              gets a JSON verdict
                                     review_result {verdict, findings} ◄──  gates.py decides the action
  fixes in the worktree ◄──────────                                          shadow: "would approve", or
  guardrails pass? then push ──────► fix_pushed {head, round, disputes} ──►  request changes, or needs_human
  open question ───────────────────► ruling_request {questions[]} ───────►  codex exec, ruling prompt
  records it once bound ◄──────────  ruling {id, decision, binds_at}  ◄──   confirm_only from labels + paths
                                     veto / confirm (Myan)
                                     escalate @Gupta958  (round 4, dispute, error)
```

- **The reviewer watcher is plain Python.** It polls `gh` every few minutes and starts ChatGPT only
  when a PR has a new head to review or an unanswered ruling request. A quiet poll costs no tokens.
- **The author is the live session, not a daemon.** The Claude Code session Myan works in arms a
  Monitor on its open PRs that prints only bus messages from Gupta958. When the session is closed,
  nothing on the author side runs and messages wait on the PR.
- **Two logins, never switched.** The watcher's `gh` calls carry the reviewer's `GH_CONFIG_DIR`, and
  each side checks its own login before it writes. The global active account stays Myan17, so the
  #36–#39 collision cannot recur.
- **Two contexts, two models.** ChatGPT starts a fresh `codex exec` each round, with no memory of the
  author's session, in a read-only sandbox, and is never given a GitHub token.
- **The bus is the only state that matters.** The watcher keeps a small cache
  (`~/.local/state/wayfinder-reviewbus/`) of what it has handled, and can rebuild it from the PR
  comments. Deleting the cache is always safe.

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
| `ruling_request` | PR author (Myan17) | questions[] (id, text, options[], recommendation, labels[]) | Rule on these, ADR-0021 rule 7 |
| `ruling` | Gupta958 | id, decision, rationale, model, binds_at, confirm_only | A ruling; it binds at `binds_at` unless vetoed, or on `confirm` when `confirm_only` |
| `veto` / `confirm` | Myan17 or Gupta958 (plain comment `veto <id>` / `confirm <id>`) | id | Myan stops a ruling, or binds it now |
| `review_result` | Gupta958 | head, round, verdict (`approve` / `changes` / `needs_human`), findings[], model, gates{} | The reviewer's call, and which gates passed |
| `fix_pushed` | PR author | head, round, addressed[], disputes[] | A new head answers the findings; disputes stop the loop |
| `escalate` | either | reason, question | A human is needed. The comment @-mentions Gupta958, the approving account (ADR-0021 rule 11) |

A finding has `id`, `file`, `line`, `severity`, `blocking` and `text`. Messages from any other
GitHub account are ignored (ADR-0021 rule 8).

## 4. The life of one PR

`requested` → `reviewing` → `would approve` (shadow), and then Myan approves and merges by hand. Or:

- `changes` → the author side fixes and sends `fix_pushed` → back to `reviewing` for round 2, then 3.
- `needs_human` → Myan clicks as gupta958. The watcher does nothing more on that head.
- `escalated`, after round 4, a dispute or an error → both watchers stop on this PR until a human
  comments.

**When main moves** (another PR merged), the author session rebases the PR, runs guardrails,
refreshes the description, pushes and sends `fix_pushed` with `"rebase": true`. The reviewer
re-checks the gates but does not re-run the model unless the diff changed beyond the rebase.

## 5. Modes (repository variables)

`WAYFINDER_AGENT_APPROVAL` starts at `shadow`:

| Value | Reviewer watcher does |
|---|---|
| `off` (default) | Nothing on its own. The review_handoff briefs keep working as now |
| `shadow` | Reviews and posts "would approve / would request changes". Myan still clicks as gupta958 |
| `on` | Approves and merges when every gate passes. The human-only tier is always Myan's click |

`WAYFINDER_AGENT_RULINGS` is `off` or `on`. With `on`, a ruling binds 12 hours after it is posted
unless Myan comments `veto <id>`; `confirm <id>` binds it at once, and confirm-only rulings bind only
that way (ADR-0021 rule 7).

Switch modes from a phone: GitHub → Settings → Variables, or
`gh variable set WAYFINDER_AGENT_APPROVAL --body off`.

## 6. Setup on Myan's Mac (one time, about 10 minutes)

1. Give the reviewer login its own `gh` directory:
   `GH_CONFIG_DIR=~/.config/wayfinder/gh-reviewer gh auth login` as gupta958. The default directory
   keeps Myan17 active. Then sign gupta958 out of the default directory:
   `gh auth logout -h github.com -u gupta958`.
2. Install and sign in to the Codex CLI with the ChatGPT plan: `npm i -g @openai/codex`, then
   `codex login`. Check it with `codex exec --sandbox read-only "say ok"`.
3. `cp docs/team/reviewbus.example.toml ~/.config/wayfinder/reviewbus.toml` and fill in the reviewer's
   `gh_config_dir` and the Codex model.
4. `python3 scripts/reviewbus/cli.py doctor`. It checks that each role's directory is logged in as
   that role's account, that the default is Myan17, that `codex exec` answers, and what both
   variables are set to. It posts nothing.
5. `python3 scripts/reviewbus/cli.py watch`. The example config has a launchd entry that starts it
   at login.

## 7. Package layout (`scripts/reviewbus/`)

Each file has one job, and one test file of the same name in `scripts/tests/reviewbus/`.

| File | One job | Depends on |
|---|---|---|
| `protocol.py` | Build and parse bus messages; the author-role check | nothing |
| `state.py` | The PR life cycle (§4), rebuilt from comments; the local cache | protocol |
| `gates.py` | ADR-0021 rule 5: one function per gate, and `decide()` | protocol, tier config |
| `tier.py` | Is a file in the human-only tier? Paths come from OWNERSHIP.md, not a copy | OWNERSHIP.md |
| `github.py` | Every `gh` call in one place (list PRs, comments, checks, review, merge), each run with its role's `GH_CONFIG_DIR` and account check | `gh`, `check_gh_account` |
| `agents.py` | Run `codex exec` read-only with a prompt; parse the JSON verdict or ruling | the Codex CLI |
| `rulings.py` | ADR-0021 rule 7: confirm-only marking, `binds_at`, veto and confirm | protocol, tier |
| `reviewer.py` | The reviewer role's loop | all of the above |
| `cli.py` | `watch`, `doctor`, `once <pr>` (one pass on one PR), `--dry-run` | reviewer |
| `prompts/review.md`, `prompts/ruling.md` | What ChatGPT is told, with the verdict and ruling schemas | — |

`scripts/codemap.py` lists the package, and `python3 scripts/reviewbus/cli.py --help` lists every
command.

## 8. Extending it

- **Add a gate:** a function in `gates.py` that returns `(ok, reason)`, added to `GATES`, with a test
  that it blocks. Then add a line to ADR-0021 rule 5 in the same PR. The human-only tier applies,
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
- Shadow mode never approves or merges: with `WAYFINDER_AGENT_APPROVAL=shadow`, a passing verdict on
  a non-tier PR produces no `gh pr review --approve` and no `gh pr merge` call.
- Rulings: one binds at exactly 12 hours with no veto, a `veto` from either account stops it, a
  `veto` from a third account is ignored, `confirm` binds at once, and a confirm-only ruling never
  binds by time (every confirm-only class, plus an unlabeled question on a tier path).
- `cli.py once <pr> --dry-run` runs the whole pipeline on a real PR and prints the actions without
  posting. It is the first thing run on each machine.

## 10. How it lands

| PR | Content | Approved by |
|---|---|---|
| 1 | ADR-0021 and this file, the spec | Myan as gupta958 by hand. The AGENTS.md and ROSTER text is committed by Myan by hand |
| 2 | `protocol`, `state`, `tier`, `gates`, `github`, with tests | Myan as gupta958 by hand |
| 3 | `agents`, `rulings`, `reviewer`, both prompts, `cli doctor/once/watch`, example config, launchd entry | Myan as gupta958 by hand |
| 4 | `review_handoff.py request` and `ruling-request` emit bus headers; CLAUDE.md pointer for the author Monitor | Myan as gupta958 by hand, then **shadow week** |
