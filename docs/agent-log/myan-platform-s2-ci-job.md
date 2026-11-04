# Task log — myan-platform-s2-ci-job

| Field | Value |
|---|---|
| Task | S2 harness part 8: S2's CI job (ADR-0019 Amendment 1 §5) |
| Module | platform |
| Branch | `myan/platform/s2-ci-job` |
| Worktree | `../wayfinder-wt/myan-platform-s2-ci-job` |
| Operator | myan |
| Agent | claude-code/opus-5.5 |
| Session | 2026-11-04T22:49Z/30285 |
| Started | 2026-11-04T22:49:00Z |
| Closed when | the last entry says TASK CLOSED (the header is never edited - this file is append-only) |

**Append-only.** Corrections are new entries. Entries are written by `scripts/log.sh` and the
`post-commit` hook; CI rejects a rewritten log (`scripts/check_agent_log.py`).

## Cards read

- (listed by `new-task.sh`; add any you read later as `READ` entries)

## Timeline

### 2026-11-04T22:49:09Z · READ · myan · claude-code/opus-5.5 · f89f8f5
ADR-0019 Amendment 1 §5 and its rulings 4 and 5; .github/workflows/ci.yml (dispatcher requires every job in needs); platform and eval-harness cards; s2.services, s2.reranker and the env-gated tests (WAYFINDER_S2_DOCKER, WAYFINDER_S2_RERANKER, Linux counters).

### 2026-11-04T22:49:09Z · PLAN · myan · claude-code/opus-5.5 · f89f8f5
A job s2 in ci.yml, on ubuntu-24.04-arm, listed in the dispatcher's needs so it is required. s2.ci (stdlib only) decides full or no-op from git diff --no-renames base...head against Amendment 1 §5's trigger list; any doubt (zero base, git failure) runs in full. Caches restore by keys built from the pinned digests (model digest; SHA-256 of the reranker pins), and are verified after every restore (check_model on /api/tags, reranker --verify) or populated by a verified pull/fetch and then saved. Only /root/.ollama/models is cached, never Ollama's key. Tests run as root with WAYFINDER_S2_DOCKER=1 and WAYFINDER_S2_RERANKER set. Rejected: a separate workflow file (it would need a new required check in branch protection, an owner action, where the dispatcher already gates); dorny/paths-filter (one more third-party action, and its no-op cannot fail closed on a bad base). The counter, preflight and calibration fixture against the services waits for the passes, which wire them.

### 2026-11-04T22:51:50Z · TEST · myan · claude-code/opus-5.5 · f89f8f5
uv run pytest (dev + s2): 478 passed, 31 skipped; eval/harness/tests in dev only: 86 passed, 9 skipped. test_s2_ci.py 19 passed. Mutations: dropping db/views/ from DIRS fails 1; removing the zero-base check fails 1. PYTHONPATH=eval/harness python3.12 -m s2.ci on real diffs: main's merge base to HEAD is no-op; #105's merge is full (compose.yml, services.py, test_s2_services.py); #100's is full (counters). keys under 3.12: s2-ollama-0a109f42..., s2-reranker-dcdbaf03.... ci.yml parses (PyYAML): jobs unit, db, go, s2, dispatcher; dispatcher needs s2. ruff clean; context-freshness --fix eval-harness (16 interface files). NOT RUN: actionlint (installing it was refused here) and the job itself, which only CI's arm runner can run; this pull request changes ci.yml and eval/harness, so its own CI run is the job's first full run.

### 2026-11-04T22:51:50Z · COMMIT · myan · claude-code/opus-5.5 · parent:f89f8f5
ci(platform): add S2's CI job, in full only when S2's inputs change
8 files changed, 354 insertions(+), 3 deletions(-)
