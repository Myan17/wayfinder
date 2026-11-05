---
bcr: 2
title: s6_ollama's embed returns its token count, and may truncate a rejected window
requester: myan
owner: joint (schema)
modules: [schema, eval-harness]
status: proposed   # direction ruled by gupta958 on 2026-11-04; accepted when ADR-0019 Amendment 2 merges
opened: 2026-11-04
decided: —
labels: [schema]
---

# BCR-2: s6_ollama's embed returns its token count, and may truncate a rejected window

## What I need

S2's corpus loader embeds through `db/s6_ollama.py` (schema's interface since BCR-1). It needs two
things the card does not give it:
- each call's token count (Ollama's `prompt_eval_count`), for Amendment 1 §1's token-length
  distribution and Amendment 2's truncated-window list;
- one retry with `truncate: true`, made only after Ollama rejects an input for exceeding the context,
  with Ollama's raw error kept.

Today `Ollama.embed` returns only the vector and always sends `truncate: false`. An over-context input
surfaces as a bare `urllib.error.HTTPError`.

## Why

ADR-0019 Amendment 2 (this same pull request) sets S2's truncation rule. Under BCR-1 ruling 7, 181 of
the 7,175 windows would fail the load (Amendment 2 gives the measurement). The loader is the next
harness part (ORIENT item 7), and gupta958 ruled that it waits for this contract to merge. Task log:
`docs/agent-log/myan-agreements-adr-0019-amendment-2.md`.

## Proposed contract

```text
db/s6_ollama.py
  CONTEXT_EXCEEDED = "the input length exceeds the context length"   # Ollama 0.34.2's error, exactly
  class ContextExceeded(RuntimeError): model: str, error: str        # error is Ollama's raw string
  Embedded(NamedTuple): vector: list[float], prompt_eval_count: int
  Call(NamedTuple): input_hash: bytes, prompt_eval_count: int, truncated: bool, error: str | None

  Ollama.embed(model, text) -> list[float]                                  # unchanged: truncate false
  Ollama.embed_counted(model, text, *, truncate: bool = False) -> Embedded
  embedder(client, counter, *, record: list[Call] | None = None,
           truncate_rejected: bool = False) -> Embedder
```

**The truncate flag**
- `embed_counted` sends `"truncate": truncate` exactly as given, with the same `OPTIONS` as today.
  It refuses a `truncate` that is not a `bool` with a `TypeError`, before any request.
- `embed` keeps its signature and behaviour: `truncate: false`, vector only.
- `embedder`'s defaults keep S6's behaviour. With `truncate_rejected=False`, a `ContextExceeded`
  propagates and nothing is retried.
- With `truncate_rejected=True`, a `ContextExceeded` triggers exactly one retry of the same text with
  `truncate=True`. Any other error is never retried. A failed retry propagates.

**The returned count**
- `Embedded.prompt_eval_count` is the response's `prompt_eval_count`, as Ollama reported it, for that
  one input.
- With `record`, every successful embedder call appends one `Call`:
  - `input_hash` is `s6_identity.input_hash(text)` of the full stored input, never the truncated one;
  - `prompt_eval_count` is the successful request's count;
  - `truncated` is true only for a retry;
  - `error` is the rejected request's raw error, or `None`.
- `counter["calls"]` still counts embedder calls, never HTTP requests, so S6-3's "one embedder call
  each" keeps its meaning.

**Validation**
- The response must hold exactly one embedding, and its `prompt_eval_count` must be an `int` (not a
  `bool`) of at least 1. Otherwise the call raises `RuntimeError`, naming the model and the field.
- `ContextExceeded` is raised only for an HTTP 400 whose JSON `error` equals `CONTEXT_EXCEEDED`
  exactly. Any other status or error text raises the original `HTTPError` unchanged, so a new Ollama
  message is never mistaken for an over-context input. The pinned 0.34.2 has this message (Amendment 2).
- The alias's digest is checked before every request, the retry included. An alias that moves between
  the rejection and the retry raises `RuntimeError`, and no retry request is sent.
- The 768-dimension check stays, and applies to the retry too.
- No count is invented for a rejected input (gupta958's ruling 2). The caller reports "exceeds 2,048"
  and the raw `error`.

**Tests** (`db/tests/test_s6_ollama.py`, on the fake Ollama; `db/tests` is collected by `make db-test`, CI's `db` job):
1. `embed` and `embed_counted` send `truncate: false` by default. `embed_counted(truncate=True)`
   sends `true`. `truncate="false"` and `truncate=1` are refused before any request.
2. `embed_counted` returns the count. A missing, zero, negative, `bool` or `float` count is refused,
   as is a response with zero or two embeddings.
3. A 400 with `CONTEXT_EXCEEDED` raises `ContextExceeded`, and its `.error` equals the raw string. A
   400 with other text, and a 500, raise `HTTPError` and are not `ContextExceeded`.
4. The default `embedder` lets `ContextExceeded` propagate after one request, and `record` stays
   empty. S6-5's existing tests pass unchanged.
5. `truncate_rejected=True`:
   - a rejected call becomes exactly two requests, the second with `truncate: true`, and records
     `(input_hash of the full text, the retry's count, True, the raw error)`;
   - an accepted call records `(hash, count, False, None)`;
   - a second rejection propagates;
   - a 500 is not retried.
6. The alias moves between the rejection and the retry: `RuntimeError`, and the fake sees no second
   embed request.

## Compatibility and migration

| Question | Answer |
|---|---|
| Is this additive? | Yes. New names, and keyword arguments whose defaults keep today's behaviour. No migration and no table change |
| Existing consumers affected | `db/s6_ollama.py`'s S6-5 runner and `db/tests/test_s6_ollama.py`. The runner uses `embedder(client, calls)`, which keeps its behaviour. The fake gains `embed_counted` |
| Migration order | ADR-0019 Amendment 2 with this BCR merges first. Then the schema PR adds the code and tests, updates the card and its hashes, and sets this BCR to `accepted`. Then the eval-harness loader is written against the card |
| Feature flag needed | No |
| Rollback | Revert the schema PR. Only spikes call `s6_ollama` |

## What I will do if this is refused

The loader would have to call Ollama's HTTP API itself, beside the build path, which repeats the
digest check and the request shape that S6 tested. S2 would also lose the token-length distribution
Amendment 1 §1 requires, or else pin a separate tokenizer only to count tokens.

## Owner's decision

Direction ruled by gupta958 on 2026-11-04, relayed by Myan after #109 merged. The contract above is
written to that ruling; merging Amendment 2 accepts it.
- Put the `Ollama.embed` interface BCR inside Amendment 2. Specify the truncate flag, the returned
  count, the validation and the tests. Merge the amendment before implementing the loader.
- "Exceeds 2,048" is sufficient. Ollama gives no exact count for a rejected input, so keep its raw
  error and do not invent one.

## Closure checklist (owner)

- [ ] Card updated, `Verified-at` bumped in the implementing pull request
- [ ] Fake updated so consumers can build before the implementation lands
- [ ] Contract test added that pins the new invariant
- [ ] Requester told in the pull request that the contract is ready
