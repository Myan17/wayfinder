---
bcr: 3
title: push_and_claim takes the claim's duration, so S2 can build a pseudo-repository within one lease
requester: myan
owner: joint (schema)
modules: [schema, eval-harness]
status: amended   # accepted with an amendment by gupta958, relayed by Myan, 2026-11-05
opened: 2026-11-05
decided: 2026-11-05
labels: [schema]
---

# BCR-3: push_and_claim takes the claim's duration

## What I need

S2's corpus loader builds each pseudo-repository through `db/s6_identity.py` (schema's interface
since BCR-1). `push_and_claim(conn, repo_id)` always claims the repository for 5 minutes, and
`activate` refuses a build whose claim has expired. The loader needs to choose a longer claim for a
pseudo-repository's build. S6's callers must keep the 5 minutes they have today.

## Why

ADR-0019 Amendment 3 (this same pull request) gives the measurement. The 7,175 windows fall into the
100 pseudo-repositories with between 14 and 724 windows each (median 53; the largest five are 179,
193, 205, 411 and 724). All of a pseudo-repository's windows are embedded inside its one claim. For
the 724-window pseudo-repository to finish within 5 minutes, the embedder would need 0.41 s per
window or less, including the 2,048-token truncated windows of `profiling/mix_huge.py`. S2-6 then
re-indexes the corpus at lower OS priority while queries run, which is slower still. #108 already saw
an expired claim on synthetic data. Task log: `docs/agent-log/myan-agreements-adr-0019-amendment-3.md`.

## Proposed contract

As amended by gupta958 (the proposal used an interval string; the ruling replaced it with a
`timedelta`):

```text
db/s6_identity.py
  push_and_claim(conn, repo_id, *, claim_for: timedelta = timedelta(minutes=5)) -> (desired, claim)
```

- `claim_for` is a `datetime.timedelta`. Anything else raises `TypeError`, and a zero or negative
  duration raises `ValueError`, both before any statement is sent, so the repository row is unchanged.
- The claim expires at `now() + claim_for`. The duration is a bound query parameter, never formatted
  into the SQL text.
- The default is exactly today's 5 minutes, so S6-5 and every existing caller keep their behaviour.
- S2 passes exactly `timedelta(minutes=60)`. Nothing extends a claim. A build that outlives its claim
  is refused by `activate`, as today, and the loader fails the load (Amendment 3 §1).

**Tests** (`db/tests/test_s6_identity.py`, collected by `make db-test`, CI's `db` job):
1. The default claim expires 5 minutes after `now()`, and `claim_for=timedelta(minutes=60)` expires
   60 minutes after it (read back from `claim_expires_at - now()` in the same transaction).
2. `timedelta(0)`, `timedelta(seconds=-1)`, the string `"60 minutes"`, and the int `3600` are each
   refused before writing: `desired_generation`, `claim_token` and `claim_expires_at` are unchanged.
3. A build activated within its claim succeeds, and one whose claim has expired is refused. The
   existing S6 tests already cover this, and they pass unchanged.

## Compatibility and migration

| Question | Answer |
|---|---|
| Is this additive? | Yes. One keyword argument whose default keeps today's behaviour. No migration and no table change |
| Existing consumers affected | `db/s6_ollama.py`'s S6-5 runner and the `db/tests` callers. All use the default |
| Migration order | ADR-0019 Amendment 3 with this BCR merges first. Then the schema PR adds the code and tests, updates the card and its hashes, and ticks the closure checklist. Then the eval-harness loader is written against the card |
| Feature flag needed | No |
| Rollback | Revert the schema PR. Only spikes call `s6_identity` |

## What I will do if this is refused

The loader could embed every window first and build from the stored vectors, which takes the
embedder out of the build path that S2-6 times. Or it could keep 5 minutes and fail the load when the
claim runs out.

## Owner's decision

Relayed by Myan from gupta958, 2026-11-05. Recorded as ruled.

- **Decision:** accept, with an amendment.
- **If amended, the contract that was actually agreed:**
  - `claim_for: timedelta = timedelta(minutes=5)`, not an arbitrary interval string.
  - S2 passes exactly `timedelta(minutes=60)`.
  - Zero or negative durations are refused before writing.
  - The SQL stays parameterized.
  - The report records the 60-minute lease and each pseudo-repository's build duration.
  - If any build exceeds 60 minutes, the load fails rather than silently extending the claim.
- **Follow-up owed:** implement BCR-3 with its tests and the schema card's hashes before the corpus
  loader is written.

## Closure checklist (owner)

- [x] Card updated, `Verified-at` bumped in the implementing pull request
- [x] Fake updated so consumers can build before the implementation lands
- [x] Contract test added that pins the new invariant
- [x] Requester told in the pull request that the contract is ready
