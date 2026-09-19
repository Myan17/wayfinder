# Wayfinder

Permission-aware retrieval and question answering over a GitHub organization's code and Markdown.
Ask *where* something is implemented, or *why* it behaves the way it does, and get an answer whose
citations resolve to passages you are authorized to see — or an explicit refusal.

**Status:** Phase 0 (spikes and foundations). Nothing is deployed. No claim in this README is
evidence until `manifests/` holds a release manifest that reproduces it.

## Start here

| Document | What it is |
|---|---|
| [`docs/DESIGN.md`](docs/DESIGN.md) | The design (v0.3), including what the system will not claim |
| [`AGENTS.md`](AGENTS.md) | Operating rules for coding agents — read before any session |
| [`docs/team/WORKING-AGREEMENT.md`](docs/team/WORKING-AGREEMENT.md) | How the two of us work: review, cadence, escalation |
| [`docs/team/OWNERSHIP.md`](docs/team/OWNERSHIP.md) | Modules, task scope, phase plan |
| [`docs/context/INDEX.md`](docs/context/INDEX.md) | Contract cards — read these instead of other people's code |

## Working on it

```bash
make hooks                                  # once per clone and per worktree
git config wayfinder.operator myan
export WAYFINDER_AGENT="claude-code/opus-5"
make setup && make test

scripts/new-task.sh <module> <slug> "<task>"   # branch + worktree + task log
```

Every task gets a branch, a worktree and an append-only log in `docs/agent-log/`. CI enforces that,
along with task scope, contract-card freshness and commit identity.

## People

- **Myan Gupta** (`@Myan17`) — implementation.
- **Engineer B** (`@Gupta958`) — code review on every pull request.

Coding agents assist both of us and are named in every commit's trailers (`Agent:`, `Operator:`,
`Session:`). The accountable author is always a person.
