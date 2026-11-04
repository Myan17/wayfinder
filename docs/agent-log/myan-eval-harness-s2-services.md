# Task log — myan-eval-harness-s2-services

| Field | Value |
|---|---|
| Task | S2 harness part 7: the services — compose, readiness, model digest, cold reset, backend pid (ORIENT item 7) |
| Module | eval-harness |
| Branch | `myan/eval-harness/s2-services` |
| Worktree | `../wayfinder-wt/myan-eval-harness-s2-services` |
| Operator | myan |
| Agent | claude-code/opus-5.5 |
| Session | 2026-11-04T15:44Z/30990 |
| Started | 2026-11-04T15:44:54Z |
| Closed when | the last entry says TASK CLOSED (the header is never edited - this file is append-only) |

**Append-only.** Corrections are new entries. Entries are written by `scripts/log.sh` and the
`post-commit` hook; CI rejects a rewritten log (`scripts/check_agent_log.py`).

## Cards read

- (listed by `new-task.sh`; add any you read later as `READ` entries)

## Timeline

### 2026-11-04T15:44:55Z · PLAN · myan · claude-code/opus-5.5 · 43b6b0c
Add eval/harness/s2/compose.yml and s2/services.py. Compose: ParadeDB at ADR-0007's digest with max_parallel_workers_per_gather = 0 and a named volume, not S3's tmpfs, because drop_caches cannot evict tmpfs and a cold pass must read from disk; the query and ingestion Ollama containers at 0.34.2's linux/arm64 digest (the ParadeDB pin's architecture and CI's arm runner), each its own cgroup. services.py: the compose command, a service's host pid and cgroup, readiness (pg_isready; /api/version must equal 0.34.2), the model digest check against /api/tags, ADR-0019's reset in order (stop, sync, drop_caches, start, wait, digest), and connect() returning a new connection with its backend's host pid. Every docker and HTTP call goes through injected callables so the order is tested anywhere. Rejected: reusing infra/spikes/s3/compose.yml (tmpfs, no Ollama, platform-owned).

### 2026-11-04T15:47:54Z · TEST · myan · claude-code/opus-5.5 · 43b6b0c
test_s2_services.py: 6 passed, 1 skipped (the real Docker test, which needs Linux, root and WAYFINDER_S2_DOCKER=1) in both the dev and dev + s2 environments. uv run pytest (dev + s2): 458 passed, 31 skipped. ruff clean; context-freshness OK (15 interface files). Ollama 0.34.2's linux/arm64 digest e87cf598… was read from Docker Hub's manifest index (index da6e0dc5…). NOT RUN: the real test. Docker on this Mac hangs (as on #100), and Amendment 1 §5 rules out S2-dev on a Mac; it runs once S2's CI job exists.

### 2026-11-04T15:47:55Z · COMMIT · myan · claude-code/opus-5.5 · parent:43b6b0c
feat(eval-harness): add S2's services: compose, readiness, cold reset, backend pid
6 files changed, 376 insertions(+), 2 deletions(-)
