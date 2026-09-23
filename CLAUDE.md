# CLAUDE.md — Wayfinder

**Read `AGENTS.md` first and follow it exactly. It is the operating contract for every coding agent on
this repository, and nothing here overrides it.** This file only adds what a Claude Code session needs
at startup.

## Before your first action

**Hard requirement: read `ORIENT.md` first, every session.** The `SessionStart` hook in
`.claude/settings.json` prints it and the `scripts/orient.py` brief into your context. If that output
is missing, run `cat ORIENT.md && python3 scripts/orient.py` yourself before doing anything else. The
next task is the first open item in `ORIENT.md`. Do not offer the user a menu of next steps; the plan
has already made that choice.

```bash
git config core.hooksPath .githooks          # once per clone or worktree
git config wayfinder.operator myan           # the implementer handle from docs/team/ROSTER.md
export WAYFINDER_AGENT="claude-code/opus-5"  # tool/model, recorded in every commit
export WAYFINDER_SESSION="$(date -u +%Y-%m-%dT%H:%MZ)/$RANDOM"
```

Then either start a task (`scripts/new-task.sh <module> <slug> "<description>"`) or `cd` into the
existing worktree and read the last `HANDOFF` entry in its task log.

## The rules you will be tempted to break

| Temptation | What to do instead |
|---|---|
| "I'll just peek at the other module's implementation to see how it works" | Read its card in `docs/context/modules/`. If the card does not answer it, log `BLOCKED` and open a BCR |
| "This one-line fix doesn't need a branch" | It does. One task, one branch, one worktree, one log |
| "I'll write the log at the end" | Log as you go; the log is the record a reviewer reads, and CI checks it covers every commit |
| "The interface change is small, the card can wait" | CI fails the build. Update the card in the same pull request |
| "I'll fix that other module while I'm here" | Out of task scope (AGENTS.md §2.5). Revert it, or declare `Scope:` in the pull request and justify it |
| "I'll approve/merge this since it's obviously fine" | Agents never approve and never merge |
| "Here are some options for what to do next" | `ORIENT.md` already says. Take its first open item |
| "This tooling would help, I'll build it first" | Not in `ORIENT.md` means not now, unless an owner directs it (AGENTS.md rule 6) |

## Project facts worth loading early

- **Design:** `docs/DESIGN.md` (v0.3). Section numbers are stable; cards cite them.
- **Ownership and scope:** `docs/team/OWNERSHIP.md`. Modules, path globs, phase plan. `myan`
  implements; `gupta958` reviews and merges every pull request.
- **Context map:** `docs/context/INDEX.md`. What to read for anything you do not own.
- **Phase you are in:** see `docs/DESIGN.md` §19. Phase 1 is the safety kernel — until it passes,
  only public and synthetic data is used.
- **Stack:** Python 3.13 + FastAPI (read path), Go (write path), Postgres with pgvector and
  ParadeDB `pg_search`, Ollama embeddings, Next.js static export, Terraform on Oracle Cloud.
- **Security posture:** private repository content never reaches a provider or exporter that is not
  approved for it (`DESIGN` §9.7.1, §17.1). When in doubt, treat data as private and log the question.

## Definition of done

`docs/team/WORKING-AGREEMENT.md` §4. Short version: test at the right layer, card accurate, log has
`PLAN` + `TEST` + `HANDOFF`, telemetry present, design claims updated in the same pull request.
