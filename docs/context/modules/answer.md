---
module: answer
owner: myan
paths:
  - apps/api/wayfinder/answer/**
  - docs/context/modules/answer.md
interface_files:
  - apps/api/wayfinder/answer/interface.py
  - docs/api/sse.md
tables_owned:
  - answer
  - answer_trace
  - feedback
depends_on:
  - retrieval
  - egress
  - authz
  - cache
design_sections:
  - "DESIGN §9.6 (answerability, modes, citations)"
  - "DESIGN §9.9 (SSE contract)"
  - "DESIGN §15.3 (judge calibration)"
verified_at: 0000000
verified_on: 2026-09-18
---

# answer

## Purpose

Decides whether a question can be answered, produces the answer in one of four modes, and owns the
durable record of what was said and on what evidence. It is the state machine between retrieval and
the client.

## Public interface

```python
# apps/api/wayfinder/answer/interface.py
class Mode(StrEnum):
    LOCATE = "locate"; GENERATED = "generated"; REFUSED = "refused"; EXTRACTIVE = "extractive"

class Status(StrEnum):
    PENDING="pending"; STREAMING="streaming"; COMPLETED="completed"; REFUSED="refused"
    EXTRACTIVE="extractive"; FAILED="failed"; CANCELLED="cancelled"

@dataclass(frozen=True)
class Answerability:
    answerable: bool; signal: float | None; version: str; reason: str

def decide(result: RetrievalResult) -> Answerability: ...

async def ask(query: str, principal: Principal, scope: AuthorizedScope,
              *, idempotency_key: bytes | None) -> AsyncIterator[SSEEvent]: ...

async def read(answer_id: UUID, principal: Principal) -> AnswerRecord | None: ...   # re-authorizes
async def record_feedback(answer_id: UUID, principal: Principal, rating: int, reason: str) -> None: ...
```

The SSE event contract (`retrieval`, `token`, `citation`, `done`, `reset`, `error`) is specified in
`docs/api/sse.md` and is part of this interface.

## Invariants a caller may rely on

- **No relevance signal, no generation.** If `rerank_score` is `None` — reranking shed, dense
  retrieval unavailable, lexical-only mode — `decide()` returns not-answerable and the answer is
  refused or extractive. Rank-fusion scores are never used as evidence of relevance.
- **Streamed tokens are provisional.** The `done` event carries the canonical text, the citation map,
  the validation status, and the count of sentences with no citation marker.
- Every citation marker in the canonical text resolves to a passage retrieved for this request and
  authorized for this principal. Unknown markers are stripped and the answer is flagged
  `citation_repair`.
- Claim support is **measured, not guaranteed** — a valid marker does not prove the passage supports
  the sentence. The README says so, and §15.3 reports it with an interval.
- Only `completed`, `refused` and `extractive` are cacheable. A partial answer is never reusable.
- A provider may be swapped **before** the first token; after that the stream ends with a typed
  terminal event and, if a replacement is produced, an explicit `reset`.
- Every answer stores an evidence manifest of **stable identifiers** (github repo id, commit sha,
  chunker version, specification digest, policy revisions), and `read()` re-authorizes against it.
- `idempotency_key` deduplicates in flight: a reconnecting client never pays for a second generation.

## What this module will never do

- Never decide authorization itself; it asks `authz` and re-asks on artifact reads.
- Never send anything outward directly; all egress goes through `egress`.
- Never render model text as HTML, or emit a link or image the server did not construct.
- Never treat passage text as instructions.

## Failure modes the caller must handle

| Condition | Client sees | Notes |
|---|---|---|
| Not answerable | `done` with `status=refused` and closest passages | Counts toward refusal metrics, not errors |
| Generation unavailable | `done` with `status=extractive`, `degraded` includes `generation_unavailable` | HTTP 200 |
| Provider fails after partial output | `error` (terminal), optionally `reset` + replacement id | Partial text is not cached, not stored as canonical |
| Client disconnects | Upstream generation cancelled | Bounded work; connection released before any provider call |
| Artifact read after access loss | `read()` returns `None` → 404 | Never a redacted-but-present answer |

## Tests that pin this contract

| Test | Pins |
|---|---|
| `apps/api/tests/answer/test_answerability.py::test_no_signal_no_generation` | RETR-04 / §9.6.1 |
| `…/test_citations.py::test_unknown_marker_split_across_tokens` | GEN-01 |
| `…/test_citations.py::test_markers_resolve_to_authorized_passages` | Citation validity |
| `…/test_stream.py::test_provider_failure_after_partial` | GEN-03 |
| `…/test_stream.py::test_idempotent_retry_does_not_regenerate` | GEN-04 |
| `…/test_artifacts.py::test_read_after_revocation_denied` | AUTH-08 |
| `…/test_render.py::test_no_remote_images_or_foreign_links` | GEN-05 |

## Fake

`apps/api/wayfinder/answer/fakes.py` — a scripted answer stream (normal, refusal, extractive,
mid-stream failure, reset) so `http`, `web` and the load-test stub share one definition of the
protocol.

## Open questions

- Whether an uncited sentence should block completion once the numbers are in (today: counted and
  reported, not blocked).
- Whether refusals should offer a "search instead" affordance automatically.

## Change log

| Date | Change | BCR |
|---|---|---|
| 2026-09-18 | Card created from DESIGN v0.3 before implementation | — |
