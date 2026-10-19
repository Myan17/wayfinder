# ADR-0005 — Three identities, and the acceptance rules for spike S6

- **Status:** Proposed. **The decision is deliberately empty**; spike S6 fills it.
- **Date written:** 2026-10-19, **before** any S6 prototype exists.
- **Decides:** DESIGN §12.1's ADR 0005, "Three identities: content, representation (spec + input
  hash), occurrence". It is the evidence for §9.2's identity model, and the claim that test INDEX-01
  (§16.3.1) will later hold against the full pipeline.
- **Builds on:** schema v1 (#25–#30), which already has `embedding_spec`, `content`,
  `representation`, `vector_d768` and `occurrence` as §9.2 draws them. S6 changes no table.

## Why this document exists before the experiment

This follows the same rule as ADR-0004 and ADR-0007. A spike that writes its pass condition after
the run cannot fail, so these rules merge first. The prototype and its results come in later pull
requests.

## The claim under test

DESIGN §9.2, "Why three identities (WF-05)":

- `content` is the exact source text.
- `representation` is what one embedding specification produced from one embedded input (header,
  body and template). It is keyed by `(repo_id, spec_id, input_hash)`.
- `occurrence` is where that text sits in one generation.

v0.2 keyed one row by `(repo_id, content_hash)`. Re-indexing with a second model hit
`ON CONFLICT DO NOTHING`, and the first model's vector was silently kept. Under §9.2 a new
specification produces new rows, and the old rows keep serving until their generation retires.

**What the embedded input is.** `input_hash` is the SHA-256 of the UTF-8 bytes of the exact string
sent to the embedder: the specification's `doc_template`, with the header and body substituted in.
The schema does not say this precisely, so S6 pins it here, and the prototype implements it once.

## Setup (pinned, so the prototype cannot choose it after seeing results)

- A fresh database per run, with every migration applied, on the pinned ParadeDB image (ADR-0007's
  digest), the same stack CI's `pinned-extension integration` job uses.
- One repository and one source text **T**: a fixed Python function of about 40 lines, committed
  with the prototype.
- **Spec A** and **spec B**: two `embedding_spec` rows that are equal in every column except the one
  under test. There are two pairs:
  - **digest pair:** B differs from A only in `model_digest`;
  - **template pair:** B differs from A only in `doc_template`.

  Both specs in each pair have dimension 768, so both write to `vector_d768`.
- **Embedder.** S6-1 to S6-4 test storage identity, not model quality. For those rules, the embedder
  is a deterministic stand-in: a 768-dimension vector derived from SHA-256 of `(model_digest,
  embedded input)`. It is distinct per specification and stable per input. S6-5 is the only rule
  that needs a real runtime.
- **The build path.** Each embedding goes through one function: look up the representation by
  `(repo_id, spec_id, input_hash)`, embed only on a miss, insert the `representation` and
  `vector_d768` rows, and add the `occurrence` to the building generation. This is the reuse step
  in §8.5's ingestion flow (`reuse representations by (repo, spec, input hash); embed only misses`). The prototype
  counts embedder calls.

## Acceptance rules

S6 passes only if every rule passes, for both pairs where a rule applies.

| # | Rule | Pass condition |
|---|---|---|
| S6-1 | **A second specification creates new rows** | After T is indexed under A, then under B, there is exactly one `content` row for T, and two `representation` rows and two `vector_d768` rows, one per specification. The `input_hash` values differ for the template pair and are equal for the digest pair. Either way, the rows are distinct because `spec_id` is part of the key |
| S6-2 | **The first specification's vector is untouched** | A's `vector_d768.embedding` is byte-identical (compared as `halfvec` text) before and after B's build. A's representation row is unchanged in every column |
| S6-3 | **Reuse never crosses specifications** | Re-indexing T under A in a new generation makes **0** embedder calls and adds no `representation` row; it adds one `occurrence`. Indexing T under B for the first time makes **exactly 1** call. Changing only the header of T's chunk makes 1 call under A, because the embedded input changed |
| S6-4 | **The old specification keeps serving** | A's generation is active, and B's generation is `building`. `retrieval_rows` and a nearest-neighbour query over `vector_d768` with `spec_id = $1` bound to A return only A's representation. This holds even when B's vector is set **equal to the query vector**, so that B would win on distance alone. After B's generation activates under §9.3.5, the same queries bound to B return only B's representation, and A's rows still exist (retired, not deleted) |
| S6-5 | **A specification is identified by digest, not alias** | Against a real Ollama, `model_digest` is read from the runtime (`/api/show` or `/api/tags`), never copied from the model name. When the alias that `model_ref` names is re-pointed to a different model (`ollama cp`), capturing the spec again yields a **new** `embedding_spec` row. Indexing T under it creates a new representation (S6-1 holds) and makes 1 embedder call (S6-3 holds). Capturing the spec again with no change returns the **existing** row, through the `UNIQUE (model_digest, …)` key, and creates no duplicate |

### The negative control

The prototype also builds the v0.2 shape, a table keyed by `(repo_id, content_hash)` and written
with `ON CONFLICT DO NOTHING`. It runs S6-1 and S6-2's sequence against that table. **That run must
fail S6-1**: B's vector is lost and A's survives. If the control passes, the prototype cannot tell
the two designs apart, so S6 is an **error**, not a pass.

## What is deliberately not a rule

- **Embedding determinism.** S6-5's run also embeds T twice under the same spec. It records whether
  the two vectors are byte-identical and, if they are not, the largest absolute difference. This is
  a measurement for NFR-12's reproducibility tolerance, not a pass condition. Reuse does not depend
  on it, because a reused vector is never recomputed.
- **Two dimensions.** Only `vector_d768` exists. A spec of another dimension needs a migration
  (§9.2), and the `halfvec(768)` type already refuses a wrong-size vector. S6 records this and does
  not test it.
- **Rank fusion across specifications** (§9.2, "Model transitions"). That is a retrieval behaviour,
  and it belongs to the retrieval work in P1 and P2, not to storage identity.
- **The HNSW plan.** Whether the partial HNSW index is chosen with a parameterized `spec_id` is
  §9.5's plan capture, item 9c. S6-4 checks results, not plans.
- **Garbage collection of A's retired rows.** That is INDEX-06 and ADR-0017.

## Where the prototype lives

`db/tests/test_s6_identity.py`, which runs in CI's `pinned-extension integration` job, covers S6-1
to S6-4 and the control. S6-5 needs Ollama, which CI does not run. It is a separate command,
`db/s6_ollama.py`, that Myan runs locally against a pinned Ollama version and model digest. It
writes a JSON report, and the results pull request commits that report unchanged, as the D-3 probe's
report was (#76).

## Decision

*Empty until S6 runs.* It will be completed with one of:

- **Accepted:** §9.2's three identities as designed. Quote each rule's result for both pairs, the
  control's failure, S6-5's report hash, and the determinism measurement.
- **Rejected:** name the failing rule and the scenario. The schema change it needs comes first, in
  its own pull request, before §9.2's prose changes.
