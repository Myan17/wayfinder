---
module: egress
owner: myan
paths:
  - apps/api/wayfinder/egress/**
  - docs/context/modules/egress.md
interface_files:
  - apps/api/wayfinder/egress/interface.py
  - docs/api/egress-policy.md
tables_owned: []
depends_on:
  - authz
design_sections:
  - "DESIGN §9.7 (classification and provider layer)"
  - "DESIGN §11.2–11.4 (unit economics, budget)"
  - "DESIGN §17.1 (telemetry content policy)"
verified_at: 0000000
verified_on: 2026-09-18
---

# egress

## Purpose

Decides what may leave this process, to whom, and under what budget. Classifies the whole request
envelope, intersects the policies of the contributing connections, and runs the provider chain with
reservations and deadlines. Every outbound byte — prompts, rewrites, judge inputs, telemetry content —
passes its policy.

## Public interface

```python
# apps/api/wayfinder/egress/interface.py
class DataClass(StrEnum):
    PUBLIC = "public"; PRIVATE = "private"

@dataclass(frozen=True)
class Envelope:
    question: str
    passages: Sequence[Passage]
    derived: Sequence[str] = ()          # rewrites, judge inputs, anything else that would leave
    connection_ids: Sequence[int] = ()

def classify(envelope: Envelope, scope: AuthorizedScope) -> DataClass: ...
def approved_providers(cls: DataClass, connection_ids: Sequence[int]) -> list[ProviderRef]: ...
async def generate(envelope: Envelope, cls: DataClass, *, deadline_s: float) -> AsyncIterator[Token]: ...
def may_export_content(cls: DataClass, sink: Literal["trace", "error", "log"]) -> bool: ...
```

## Invariants a caller may rely on

- **Classification is not derived from retrieval.** It comes from the connection's declared
  `input_class`; an installation-mode request is private even when every passage is public. The
  anonymous public demo is the only public-classified path.
- Multiple connections intersect: the approved set is the intersection of their policies. An empty
  intersection returns no provider, and the caller must go extractive — never "best effort".
- Unknown or unverified provider terms mean **not approved**.
- A reservation (input tokens, max output, one request slot, an upper-bound cost) is taken before
  dispatch and reconciled after; an unreconciled reservation expires conservatively.
- One end-to-end deadline per ask, a first-token budget, and a total attempt budget of 3 across all
  providers. Provider SDK retries are disabled so retries are counted once, here.
- `may_export_content` returns `False` for every private-classified request, for every sink. The
  telemetry collector and the error reporter both ask before recording content.
- Errors are classified — throttling, token-window, daily quota, spend cap, authorization, malformed,
  outage — and only the first three are retryable on another provider.

## What this module will never do

- Never send private-classified content to a provider whose terms permit training on inputs.
- Never decide *whether* to answer — that is `answer`'s answerability decision. This module decides
  only whether an answer may be generated *somewhere*.
- Never log prompts or completions; it counts tokens and costs.
- Never swap providers after the first token has been emitted.

## Failure modes the caller must handle

| Condition | Caller sees | Do this |
|---|---|---|
| No approved provider | `NoApprovedProvider` | Extractive answer with the notice; not an error |
| All providers exhausted or failing | `GenerationUnavailable` | Extractive answer; `degraded=["generation_unavailable"]` |
| Deadline exceeded before first token | `DeadlineExceeded` | Terminal SSE error, no partial text |
| Spend cap reached | `BudgetExhausted` | Extractive; alert fires at the provider too |

## Tests that pin this contract

| Test | Pins |
|---|---|
| `apps/api/tests/egress/test_classification.py::test_secret_in_question_is_private` | EGRESS-01 |
| `…::test_mixed_connections_intersect` | EGRESS-02 |
| `…/test_derived.py::test_rewrites_and_judge_inherit_class` | EGRESS-03 |
| `…/test_sinks.py::test_no_content_to_trace_or_sentry_when_private` | Telemetry policy |
| `…/test_budget.py::test_reservation_before_dispatch_and_reconcile` | Budget accounting |
| `…/test_chain.py::test_no_provider_swap_after_first_token` | Answer-stream contract |

## Fake

`apps/api/wayfinder/egress/fakes.py` — `StubGenerator` with scripted latency, token streams and every
error class, plus `RecordingSink` used by the security tests to prove no content escaped.

## Open questions

- Whether an installation may declare `input_class: public` per *endpoint* rather than per connection.
- Whether to add a local generation provider later, which would change the private-data story.

## Change log

| Date | Change | BCR |
|---|---|---|
| 2026-09-18 | Card created from DESIGN v0.3 before implementation | — |
