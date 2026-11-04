# Task log — myan-eval-harness-s2-rerank-model

| Field | Value |
|---|---|
| Task | S2 harness part 6b: the pinned reference reranker (ORIENT item 7) |
| Module | eval-harness |
| Branch | `myan/eval-harness/s2-rerank-model` |
| Worktree | `../wayfinder-wt/myan-eval-harness-s2-rerank-model` |
| Operator | myan |
| Agent | claude-code/opus-5.5 |
| Session | 2026-11-04T00:55Z/24535 |
| Started | 2026-11-04T00:55:13Z |
| Closed when | the last entry says TASK CLOSED (the header is never edited - this file is append-only) |

**Append-only.** Corrections are new entries. Entries are written by `scripts/log.sh` and the
`post-commit` hook; CI rejects a rewritten log (`scripts/check_agent_log.py`).

## Cards read

- (listed by `new-task.sh`; add any you read later as `READ` entries)

## Timeline

### 2026-11-04T00:55:14Z · PLAN · myan · claude-code/opus-5.5 · 303dca6
Add s2/reranker.py: the ADR-0019 pins as data; verify(dir) checks every file's SHA-256 and the artifact's size and refuses on any difference; fetch(dest) downloads the five files from the pinned revision's resolve URLs and verifies before keeping them; Reranker loads only verified files with intra_op = inter_op = 1, sequential execution and the CPU provider, and score(query, passages, length) encodes each (query, passage) pair truncated to length tokens in total, longest_first, padded to the batch's longest, as the reference CrossEncoder does. Tests use a tiny in-memory WordPiece tokenizer for truncation and real files only when WAYFINDER_S2_RERANKER points at them. Rejected: truncating the passage alone to L, which fails on a query longer than L, and dynamic padding to L, which inflates CPU for short pairs.

### 2026-11-04T00:57:23Z · TEST · myan · claude-code/opus-5.5 · 303dca6
Fetched the five pinned files from the revision's resolve URLs with python -m s2.reranker --fetch: all five SHA-256s and the export's 23,200,716 bytes match ADR-0019. Model inputs are input_ids, attention_mask, token_type_ids (int64) and the output logits [batch, 1]. With WAYFINDER_S2_RERANKER set: test_s2_reranker.py 9 passed (Berlin example scores about 8.6 and -11.2 at L 128). In the dev-only env (CI's unit sync): 7 passed, 2 skipped (no tokenizers; no model dir). uv run pytest in dev + s2: 449 passed, 29 skipped. ruff clean; context-freshness OK.

### 2026-11-04T00:57:24Z · COMMIT · myan · claude-code/opus-5.5 · parent:303dca6
feat(eval-harness): add S2's pinned reference reranker
5 files changed, 347 insertions(+), 1 deletion(-)

### 2026-11-04T00:57:24Z · HANDOFF · myan · claude-code/opus-5.5 · 4192104
S2 part 6b: s2.reranker. Open for gupta958: L as the pair's total length (longest_first), padding to the batch's longest. Next: services wiring (compose, cgroups, reset, readiness), the corpus load through db/s6_identity.py, then the passes and report. The S2 CI job (Amendment 1 §5) should sync dev + s2 and fetch/verify the reranker into its digest-keyed cache, so the tokenizer and real-model tests run there.

### 2026-11-04T00:57:24Z · COMMIT · myan · claude-code/opus-5.5 · parent:4192104
docs(agents): hand off the S2 reranker
1 file changed, 3 insertions(+)
