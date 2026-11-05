---
bcr: 1
title: The S2 corpus load's use of db/s6_identity.py's build path
requester: myan
owner: joint (schema)
modules: [schema, eval-harness]
status: accepted-as-amended   # gupta958, relayed by Myan on #107
opened: 2026-11-04
decided: 2026-11-04
labels: [schema]
---

# BCR-1: The S2 corpus load's use of db/s6_identity.py's build path

## What I need

ADR-0019 Amendment 1 §2 says S2's corpus is embedded "through `db/s6_identity.py`'s build path". The
same path is S2-6's re-index. The eval-harness module will call that build path to load the corpus.
It needs three things:
- the build path declared as the schema module's interface;
- a way to create the 100 pseudo-repository rows (§3);
- a way to add the 60k size's padding copies (Setup).

Today the schema card is silent on `s6_identity`. Its interface is the two views and `schema.sql`,
and `s6_identity` appears only in the tests table. The path also cannot load S2's corpus as written,
for the two reasons given under "Proposed contract".

## Why

This unblocks the S2 corpus load (ORIENT item 7), the next harness part after #106. The passes and
S2-6 depend on it. Task log: `docs/agent-log/myan-eval-harness-s2-corpus-bcr.md`.

Spike S3-6's fixture (`apps/api/wayfinder/retrieval/s3_6.py`) already imports `s6_identity`'s
`Spec` and `stand_in`. It also writes `repository` and the index tables itself, a coupling nobody
reviewed. S2 would be the second such consumer, so the contract should be written down before S2
copies that pattern.

## Proposed contract

**1. Interface: the card lists these, and adds `db/s6_identity.py` and `db/s6_ollama.py` to its
interface files, so their hashes are checked.** None of the listed behaviour changes.

```text
db/s6_identity.py
  DIMENSION = 768; Spec(id, model_ref, model_digest, doc_template); Embedder = (Spec, text) -> list[float]
  embedded_input(template, header, body) -> str        # one substitution pass
  input_hash(text) -> bytes                            # SHA-256 of UTF-8
  stand_in(spec, text) -> list[float]                  # ADR-0005's stand-in
  capture_spec(conn, *, model_ref, model_digest, runtime, doc_template) -> Spec
  push_and_claim(conn, repo_id) -> (desired, claim)
  new_generation(conn, repo_id, spec, *, desired, base) -> generation_id
  index_chunk(conn, embed, *, repo_id, generation_id, spec, header, body, path, start_line=1) -> representation_id
  finish_build(conn, generation_id); activate(conn, *, repo_id, new, base, desired, claim)
  ActivationRefused
db/s6_ollama.py
  Ollama(base).embed / .digest / .version; embedder(client, counter) -> Embedder  # refuses a moved alias
  TEMPLATE = "search_document: {header}\n{body}"
```

**2. `index_chunk` gains `start_line: int = 1`.** The occurrence gets `start_line` and
`end_line = start_line + body.count("\n") - 1`, the window's real lines. Today every occurrence starts
at line 1. `occurrence`'s primary key is `(generation_id, representation_id, path, start_line)`. If
two windows of one file have identical bytes (repeated blank or licence blocks), they share an input
hash and so a representation, and the second insert violates the key. The default keeps every
existing caller unchanged.

**3. A repository seed:**

```text
seed_repository(conn, *, github_repo_id: int, full_name: str, visibility: str = "private") -> repo_id
```

It inserts one `repository` row and the `connection` row it needs. It sets `serving_state 'active'`,
`data_class` equal to `visibility`, a visibility lease of one day, and `desired_generation 0`. S2
calls it 100 times, once per pseudo-repository: `github_repo_id` 0–99 and
`full_name "s2/pseudo-NN"`. Because the rows are private, only the granted array admits them, as in
S3-6.

**4. A padding copy for the 60k size:**

```text
pad_copy(conn, *, repo_id, generation_id, spec, source: int, row: int) -> representation_id
```

It copies the source representation's header, body and path into a new representation in the same
repository and generation. Each copy is distinct in two ways:
- its `input_hash` is `input_hash(embedded_input(...) + f"\0s2-pad:{row}")`;
- its vector is `stand_in(spec, str(row))`, which is ADR-0005's stand-in seeded by row number, as the
  Setup says.

It never calls an embedder. Without this function a copy cannot be a new row: `index_chunk` would
find the source's input hash and reuse it. That is correct for real chunks, but it means 60k could
never be reached.

**How S2 uses them** (harness code, after acceptance):
1. Capture the spec: `model_ref nomic-embed-text:latest`, the pinned digest, `runtime "ollama 0.34.2"`
   and `TEMPLATE`.
2. Seed 100 pseudo-repositories.
3. For each pseudo-repository, run `push_and_claim`, then `new_generation(base=None)`, then
   `index_chunk` for each window with `start_line`. The `embedder` is an `Ollama("http://127.0.0.1:11436")`,
   the ingestion container.
4. Finish with `finish_build` and `activate`.
5. The 60k size is a second build per pseudo-repository with the same windows plus `pad_copy` rows
   until there are 60,000 live representations. A copy stays in its source's pseudo-repository.

The window header is `"{owner/name} · {path}"`, which is `T_HEADER`'s form without a symbol, because
windows have none.

## Compatibility and migration

| Question | Answer |
|---|---|
| Is this additive? | Yes. One keyword argument with today's behaviour as its default, and two new functions. No migration, no table change |
| Existing consumers affected | `db/s6_ollama.py` and `db/tests/test_s6_identity.py` (unchanged by the default); `retrieval/s3_6.py` imports only `Spec` and `stand_in`, which are unchanged |
| Migration order | This BCR is accepted; then a schema PR adds the three changes with tests, updates the card and refreshes its hashes; then the eval-harness corpus load is written against the card |
| Feature flag needed | No |
| Rollback | Revert the schema PR. Nothing outside the spikes calls these functions |

## What I will do if this is refused

The harness would have to write `repository`, `representation`, `vector_d768` and `occurrence` itself,
as S3-6 does. That couples eval-harness to schema with no reviewed contract, and S2 would no longer
run Amendment 1 §2's "build path", so S2-6's re-index would not be the production-shaped path. I
would then propose an Amendment 2 to ADR-0019 that names the harness's own loader, before writing it.

## Questions for the owner

1. **Window header:** `"{owner/name} · {path}"`, or another form? It is part of the embedded input, so
   it moves the token count.
2. **Identical windows:** in one pseudo-repository they share a representation (§8.5's reuse), so the
   live representations fall slightly below the 7,175 windows. Should the report give both counts, with
   the window count still checked against `chunk_estimate` (Amendment 1 §1)? That is my proposal.
3. **Over-long windows:** `s6_ollama` embeds with `truncate: false`. A window longer than the model's
   context fails the load rather than being silently cut. The report already gives the token-length
   distribution (Amendment 1 §1). Is failing right here, or should S2 pin a truncation?

## Owner's decision

Relayed by Myan from gupta958 on #107, 2026-11-04. Recorded as ruled.

- **Decision:** amend. The shared S2/S6 build path becomes an explicit schema interface, with the
  identity, repository-shape and padding corrections below.
- **Reasoning:** the proposal was right in direction, but four parts of it were wrong:
  - its `end_line` was wrong for a last line with no newline;
  - one connection per repository does not match S3-6's fixture;
  - a hash with a hidden suffix would no longer be the SHA-256 of the stored input;
  - padding with no occurrence in the target generation would never become live.
- **If amended, the contract that was actually agreed:**
  1. **Interface files.** `db/s6_identity.py` and `db/s6_ollama.py` go on the schema card's interface
     files, with verified hashes. `s6_ollama`'s public surface is `Ollama`, `embedder` and `TEMPLATE`.
     Its S6 report runner is not a consumer contract.
  2. **`index_chunk(..., start_line: int = 1)`.**
     - It rejects `start_line < 1`.
     - `end_line` uses `universe.lines`' rule: `end_line = start_line + n - 1`, where `n` is the
       newline count plus one when a non-empty body lacks a final newline.
     - Not `start_line + body.count("\n") - 1`.
  3. **Repositories.**
     - `seed_connection(conn, ...) -> connection_id`.
     - `seed_repository(conn, *, connection_id, github_repo_id, full_name, visibility="private") -> repo_id`.
     - S2 creates **one** connection and puts all 100 pseudo-repositories under it, as S3-6's fixture
       does. There is never one connection per repository.
  4. **`pad_copy`.** It creates a representation, its vector **and an occurrence in the target
     generation**, so activation makes the copy live.
     - The stored header carries a visible deterministic suffix, `"{source header} · s2-pad:{row}"`.
     - `input_hash` is the SHA-256 of that exact stored embedded input. A suffix is never added to
       the hash alone.
     - The stand-in vector is seeded deterministically by the row and that input.
     - The occurrence copies a deterministic source occurrence location: its path and lines.
     - `row` is unique within the run.
     - Tests prove that the 60k target means **60,000 live representations after activation**.
  5. **Window header.** `"{owner/name} · {path}"`. No line number, so identical embedded inputs
     stay eligible for representation reuse.
  6. **Counting.**
     - The report gives the window (occurrence) count and the distinct representation count.
     - Each repository's window count is still checked against `chunk_estimate`, and the total
       stays 7,175.
     - 60k means 60,000 live representations.
     - ADR-0019's "one window is one representation" becomes "one window is one occurrence;
       identical embedded inputs in the same pseudo-repository may share a representation."
  7. **Over-long windows fail the load.**
     - `truncate: false` stays. S2 inputs are never silently cut.
     - The failure names the repository, path, start line and measured token count.
     - If real data exceeds the context, an ADR amendment with an explicit truncation rule comes
       back first.
     - Real data does (181 of 7,175 windows). ADR-0019 Amendment 2 and BCR-2 supersede this item:
       a rejected window is retried once with `truncate: true` and listed in the report.
- **Follow-up owed:**
  - A schema PR with items 1–4: code, tests, card and hashes.
  - ADR-0019's wording (item 6), in that PR or the corpus load's, under `Scope: agreements`.
  - The corpus load against the card (items 5–7).

Rulings on #106's open questions, from the same message:
- `eval/harness/tests/**` stays an S2 CI trigger.
- `unit` and `db` are pinned to Python 3.13 in a separate platform PR.
- The counter, preflight and calibration fixture may land with the passes PR. It must be in that
  same PR, run green in the S2 job, and be reviewed before the passes or any S2 measurement is
  accepted.

## Closure checklist (owner)

- [ ] Card updated, `Verified-at` bumped in the implementing pull request
- [ ] Fake updated so consumers can build before the implementation lands
- [ ] Contract test added that pins the new invariant
- [ ] Requester told in the pull request that the contract is ready
