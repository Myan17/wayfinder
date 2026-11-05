# Task log — myan-agreements-adr-0019-amendment-2

| Field | Value |
|---|---|
| Task | ADR-0019 Amendment 2: truncation of over-context windows, with BCR-2 for s6_ollama's embed interface |
| Module | agreements |
| Branch | `myan/agreements/adr-0019-amendment-2` |
| Worktree | `../wayfinder-wt/myan-agreements-adr-0019-amendment-2` |
| Operator | myan |
| Agent | claude-code/opus-5.5 |
| Session | 2026-11-05T03:32Z/30831 |
| Started | 2026-11-05T03:32:40Z |
| Closed when | the last entry says TASK CLOSED (the header is never edited - this file is append-only) |

**Append-only.** Corrections are new entries. Entries are written by `scripts/log.sh` and the
`post-commit` hook; CI rejects a rewritten log (`scripts/check_agent_log.py`).

## Cards read

- (listed by `new-task.sh`; add any you read later as `READ` entries)

## Timeline

### 2026-11-05T03:33:51Z · READ · myan · claude-code/opus-5.5 · 0301eaf
BCR-1:180-184 (ruling 7: fail the load, amendment first if real data exceeds the context); db/s6_ollama.py:75-90 (embed returns vector only, truncate false); db/s6_identity.py:97-115 (capture_spec records truncation 'end'); DESIGN §9.4.2:1057-1059 (truncation explicit in embedding_spec).

### 2026-11-05T03:33:51Z · PLAN · myan · claude-code/opus-5.5 · 0301eaf
One PR under agreements: ADR-0019 Amendment 2 (the truncation rule, gupta958's rulings 1-4 of 2026-11-04) plus BCR-2 in docs/context/boundary/ (s6_ollama.embed_counted, ContextExceeded, embedder record/truncate_rejected, validation, tests), and a superseded-by pointer on BCR-1 ruling 7. Rejected: a separate BCR PR, because gupta958 ruled the BCR goes inside the amendment.

### 2026-11-05T03:33:51Z · DECIDE · myan · claude-code/opus-5.5 · 0301eaf
Fact-finding, local Ollama 0.34.2 on the Mac, not evidence: of 7,175 windows, 6,994 accepted (prompt_eval_count p50 621, p95 884, p99 1,234, max 2,029) and 181 rejected with HTTP 400 'the input length exceeds the context length', from 5 files. /api/tokenize is 404. With truncate true, inputs X+Y and X+Z give identical vectors at count 2048 while Y+X and Z+X differ, so Ollama keeps the start, which matches embedding_spec.truncation 'end'.

### 2026-11-05T03:33:51Z · EDIT · myan · claude-code/opus-5.5 · 0301eaf
ADR-0019: Amendment 2 inserted before Decision. New BCR-2 file. BCR-1 ruling 7 gains a superseded-by pointer.

### 2026-11-05T03:33:51Z · TEST · myan · claude-code/opus-5.5 · 0301eaf
Docs-only change, so there are no code tests. Checked: check_context_freshness passes; no card interface changes; BCR-2's contract matches s6_ollama.py:75-90 as it stands today (embed signature kept).

### 2026-11-05T03:33:51Z · COMMIT · myan · claude-code/opus-5.5 · parent:0301eaf
docs(agreements): ADR-0019 Amendment 2 — over-context windows, with BCR-2
4 files changed, 233 insertions(+)

### 2026-11-05T03:33:52Z · HANDOFF · myan · claude-code/opus-5.5 · 4cbbfc0
For review. Next, once it merges: the schema PR implementing BCR-2; the follow-up moving the 60,000-row test into the s2 job (ruling 4); then the loader.

### 2026-11-05T03:33:52Z · HANDOFF · myan · claude-code/opus-5.5 · 4cbbfc0
TASK CLOSED. Pull request open for review.

### 2026-11-05T03:33:52Z · COMMIT · myan · claude-code/opus-5.5 · parent:4cbbfc0
docs(agents): close task log for myan-agreements-adr-0019-amendment-2
1 file changed, 6 insertions(+)
