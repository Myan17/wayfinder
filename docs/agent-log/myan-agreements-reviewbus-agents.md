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

### 2026-11-09T04:25:26Z · EDIT · myan · claude-code/opus-5.5 · 9e5f868
Codex round 1 (before the PR): changes, five blocking, each verified. (f1) removing token variables did not hide the host's gh logins: codex now runs with HOME, XDG_CONFIG_HOME and GH_CONFIG_DIR set to an empty temp directory, XDG_* dropped, CODEX_HOME kept so codex still has its own login, and any answer containing a GitHub token pattern is refused, so a token can never reach a public PR. Remaining limit, stated in the PR: a read-only sandbox can still read a file by absolute path, such as the reviewer's plain-text hosts.yml; the sandbox has no network, and the token scan stops it being posted. (f2) the ruling options were outside the fence; they are now inside it with the rest of the author's data. (f3) the prompts told the model to read AGENTS.md from the PR's own checkout; both now declare everything the PR controls (files, diff, tool output) data, and take the rules from the base via git show. (f4) answers are now checked for exactly the schema's fields, a non-empty summary and rationale. (f5) a ruling may now be needs_human, which never binds; it is reserved and cannot be an option.

### 2026-11-09T04:25:26Z · TEST · myan · claude-code/opus-5.5 · 9e5f868
scripts/tests/reviewbus: 160 passed (new: the empty home, XDG and gh directories and kept CODEX_HOME; three token shapes refused; a missing summary, an extra field, a blank summary and an extra finding field refused; a hostile option sits inside the fence; needs_human accepted and reserved, a blank or extra-field rationale refused; both prompts take rules from the base). Real codex exec smoke test with the isolated environment: codex still authenticated, and inside it 'gh auth status' printed 'You are not logged into any GitHub hosts' and 'ls ~' printed nothing. ruff clean.

### 2026-11-09T04:25:26Z · COMMIT · myan · claude-code/opus-5.5 · parent:9e5f868
fix(agreements): review bus agents hide host logins, fence options, allow abstaining
5 files changed, 126 insertions(+), 23 deletions(-)

### 2026-11-09T04:39:02Z · DECIDE · myan · claude-code/opus-5.5 · 0045d5d
Codex round 2: f2-f5 fixed; f1 still blocking, verified: the reviewer's token was a plain-text file the read-only sandbox could read by absolute path, and an encoded copy would pass the token scan into a public comment. Probed with 'codex sandbox' (no model, exit codes only): the plain-text hosts.yml was readable, the macOS keychain was not (security exit 44 inside, 0 outside), network and writes were denied. So the fix is where the credential lives, not code: with Myan, the reviewer login was redone by device code with keychain storage. After it: the reviewer directory answers as gupta958, the default is still Myan17, hosts.yml holds no oauth_token, and inside the sandbox 'gh auth token' exits 1 and the keychain lookup for gupta958 exits 44. Myan17's token was already in the keychain. Neither account's GitHub credential is now readable by the model. The cli doctor (next PR) will refuse to run when either login is stored in plain text.

### 2026-11-09T04:39:02Z · EDIT · myan · claude-code/opus-5.5 · 0045d5d
Size: 403 lines. Folded the failed-run test into the unusable-answer cases (fail=True when the answer is None); 160 tests still pass.

### 2026-11-09T04:39:02Z · COMMIT · myan · claude-code/opus-5.5 · parent:0045d5d
test(agreements): fold the failed codex run into the unusable-answer cases
2 files changed, 8 insertions(+), 6 deletions(-)

### 2026-11-09T04:42:24Z · HANDOFF · myan · claude-code/opus-5.5 · 4a36cfd
Codex round 3: approve, no findings. make test above. PR open for gupta958 (human-only tier). Next, after the merge: rulings.py (confirm-only marking, binds_at, veto and confirm), then reviewer.py with cli.py (doctor, which also refuses a plain-text login for either role; once --dry-run; watch), the example config and the launchd entry.

### 2026-11-09T04:42:24Z · COMMIT · myan · claude-code/opus-5.5 · parent:4a36cfd
docs(agents): hand off the review bus agents task
1 file changed, 3 insertions(+)

### 2026-11-09T05:01:56Z · COMMIT · myan · human · parent:7ac48e4
tmp-size-check
2 files changed, 25 insertions(+), 9 deletions(-)

### 2026-11-09T05:02:42Z · DECIDE · myan · claude-code/opus-5.5 · 7ac48e4
Myan, reviewing #124 before approving: "No I agree and add the line public repository only". review() and ruling() now take a required visibility and refuse anything but 'public' before codex runs, since a PR's code and text go to ChatGPT. The watcher passes the repository's visibility from gh in the next PR.

### 2026-11-09T05:02:42Z · EDIT · myan · claude-code/opus-5.5 · 7ac48e4
visibility added to check_ids, with private, internal and missing visibility refused before codex runs (folded into the existing outside-the-fence test). The JSON schemas are built with a small obj() helper, the same schema byte for byte, to stay under 400 lines. 160 tests pass; ruff clean.

### 2026-11-09T05:02:42Z · COMMIT · myan · claude-code/opus-5.5 · parent:7ac48e4
feat(agreements): review bus sends only public repositories to the model
3 files changed, 51 insertions(+), 42 deletions(-)
