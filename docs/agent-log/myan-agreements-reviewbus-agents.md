# Task log — myan-agreements-reviewbus-agents

| Field | Value |
|---|---|
| Task | Review bus: run Codex read-only and parse its verdict and rulings, with the two prompts (ADR-0021 rules 3, 9; off-plan, directed by Myan) |
| Module | agreements |
| Branch | `myan/agreements/reviewbus-agents` |
| Worktree | `../wayfinder-wt/myan-agreements-reviewbus-agents` |
| Operator | myan |
| Agent | claude-code/opus-5.5 |
| Session | 2026-11-09T06:00Z/18959 |
| Started | 2026-11-09T04:21:00Z |
| Closed when | the last entry says TASK CLOSED (the header is never edited - this file is append-only) |

**Append-only.** Corrections are new entries. Entries are written by `scripts/log.sh` and the
`post-commit` hook; CI rejects a rewritten log (`scripts/check_agent_log.py`).

## Cards read

- (listed by `new-task.sh`; add any you read later as `READ` entries)

## Timeline

### 2026-11-09T04:21:00Z · PLAN · myan · claude-code/opus-5.5 · 05e53f8
Off-plan (Myan's direction, quoted in myan-agreements-reviewbus-protocol's DECIDE). scripts/reviewbus/agents.py: run(kind, workdir, fields, model) builds one codex exec call (read-only sandbox, ephemeral, -C the PR checkout, --output-schema, -o a temp file, stdin closed, no GitHub token or GH_CONFIG_DIR in its environment: rule 3, the model never holds a token), fills prompts/review.md or prompts/ruling.md with string.Template, puts PR-supplied text inside a fence whose delimiter is random per run (rule 9, PR content is data), then parses the last message as JSON and validates it: a review verdict with gates.verdict_problem, a ruling against the question's own options. Anything unparseable raises AgentError, which the watcher turns into needs_human. Run injected for tests; no test starts Codex. rulings.py, reviewer.py and cli.py follow.

### 2026-11-09T04:22:50Z · TEST · myan · claude-code/opus-5.5 · 05e53f8
scripts/tests/reviewbus: 150 passed (agents: 17 — codex runs read-only, ephemeral, in the checkout, with -m and the prompt after --; no token or GH_CONFIG_DIR reaches it; hostile PR text with a fake fence and $-words stays verbatim inside a 32-hex random fence; four unusable answers and a failed run raise AgentError; a bad PR number or sha is refused before codex runs; a ruling must match an option exactly; a bad question id or options list is refused before codex runs). A real codex exec smoke test (codex-cli 0.167.0, ChatGPT login, empty scratch directory) accepted the review schema and the '--' separator and returned {verdict: needs_human, findings: [], summary: 'smoke test'}; the schema dropped 'minimum' and added string types, which strict structured output needs. ruff clean.

### 2026-11-09T04:22:50Z · COMMIT · myan · claude-code/opus-5.5 · parent:05e53f8
feat(agreements): review bus — run Codex read-only and parse its verdict and rulings
5 files changed, 334 insertions(+)
