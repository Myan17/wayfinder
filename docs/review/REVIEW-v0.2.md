# Wayfinder v0.2 — principal engineering design review

Review date: 2026-09-18. Source: `DESIGN.md`, version 0.2, dated 2026-09-17, 1,966 lines.

Source SHA-256: `97c5886374e1488e6c8848186b1323d0ad599222b796c1fcd39fe0b4277f05e3`.

**Recommendation: approve a bounded prototype with changes; do not approve the current document as the contract for a launch handling real private repositories.** Keep the central architecture. Fix the permission lifecycle, data identity, job scheduling, evidence guarantees, and validation protocol before those decisions become expensive to change.

This is a review recommendation, not an organizational security sign-off. All 22 sections, the revision history, SQL examples, requirements, workload calculations, and three appendices were read. Findings distinguish contradictions demonstrable from the specification, incomplete contracts, external facts checked against primary documentation, and assumptions that still require measurements. No Wayfinder implementation, migrations, deployment, CI results, billing account, or production metrics were supplied. Consequently, this review cannot certify implemented behavior or claim that the proposed continuous tests are already running.

## Decision and product understanding

The actual project is a one-engineer portfolio system demonstrating permission-aware search over GitHub. Its two useful customer outcomes are finding the right implementation and explaining behavior with inspectable evidence. Hiring reviewers are the real audience; developer, new-hire, support-engineer, and administrator personas are simulated but sensible. The strongest portfolio evidence will be reproducible experiments and demonstrated failure recovery, not the number of frameworks included.

The proposed architecture is proportionate to the bounded corpus: Postgres as the transaction boundary; Go ingestion and Python retrieval; local embeddings; a static client; externally hosted generation; and explicit degradation. A dedicated vector database, Kubernetes, or additional microservices would not address the principal findings here.

Several parts deserve to survive the next revision: transactional webhook acceptance; content-addressed embedding reuse; version activation under a repository lock; the repeatable-read cache/retrieval snapshot; a fail-closed permission intent; experiments with frozen artifacts; a provider policy; cancellation of abandoned streams; and separate stub-based capacity tests. Version 0.2 already fixes meaningful problems. In particular, it would be inaccurate to say this document lacks evaluation, testing, observability, or recovery planning. Their contracts need strengthening.

The largest product mismatch is that historical “why” questions and bug/PR discovery headline the product while issue/PR ingestion is stretch. For the four-week release, describe the product as **locating and explaining behavior from default-branch Python/Go code and Markdown**. Historical rationale is available only when supported by indexed documentation. Promote the broader promise only when thread ingestion, thread provenance, and its evaluation actually ship.

## Severity and evidence conventions

| Label | Meaning in this review |
|---|---|
| P0 | Close before exposing real confidential inputs or private repositories to multiple users. These are design-level disclosure paths, not reports of an observed production breach. |
| P1 | Close before making the affected launch, correctness, capacity, recovery, or evaluation claim. |
| P2 | Important bounded improvement; record an explicit limitation if deferred. |
| P3 | Documentation cleanup that makes implementation and review less ambiguous. |
| Demonstrated | Follows from the supplied specification, arithmetic, a small executable counterexample, or a directly verified dependency contract. |
| Incomplete | A required behavior is not specified sufficiently to establish the guarantee; implementation might already address it, but none was supplied. |
| Measurement | Requires the named spike or a running system; not a proven performance failure. |

## Prioritized finding register

| ID | Priority | Finding | Primary source sections |
|---|---|---|---|
| WF-01 | P0 | Public visibility and installation eligibility can remain stale beyond the revocation bound | 9.1, 9.5, 13.4 |
| WF-02 | P0 | Asynchronous permission refresh does not reliably invalidate grants or fence stale refreshes | 9.2.2, 9.5 |
| WF-03 | P0 | Provider and telemetry policy classify retrieved repositories, not the complete request | 9.8, 17.1 |
| WF-04 | P0 | Historical artifacts need current authorization; anonymous ownership is undefined | 9.1, 9.9–9.10, 16.6 |
| WF-05 | P1 | Chunk identity cannot safely represent embedding changes and contextual variants | 9.1–9.3 |
| WF-06 | P1 | Deletion/GC contract conflicts with foreign keys, persistent caches, and retention | 9.2.4, 9.9, 13.4, 17.4 |
| WF-07 | P1 | River uniqueness design conflicts with the current documented required states | 9.2.2 |
| WF-08 | P1 | Compare-and-swap prevents a lost update, but does not prevent an obsolete build winning later | 9.2.3–9.2.4 |
| WF-09 | P1 | Streaming citation checks do not establish claim support or the advertised output guarantee | 1, 5, 9.6 |
| WF-10 | P1 | RRF rank scores are insufficient evidence of answerability | 9.6, 9.13 |
| WF-11 | P1 | Durable answers and partial-stream failure semantics are incomplete | 9.1, 9.9–9.10 |
| WF-12 | P1 | Provider limits, deadlines, policy intersections, and spend accounting are underspecified | 9.8, 10, 11 |
| WF-13 | P1 | Filtered ANN experiment uses the wrong exact-search reference | 15.4 E7 |
| WF-14 | P1 | Temporal evaluation still permits leakage and mismatched historical labels | 14.2, 15.2 |
| WF-15 | P1 | Continuous gates do not yet protect all changes or the final held-out evaluation | 14–16, 19 |
| WF-16 | P1 | The load protocol can overstate uncached capacity and permission correctness | 10, 16.6–16.8 |
| WF-17 | P1 | Capacity remains a hypothesis, with unresolved CPU and quality budgets | 1, 10 |
| WF-18 | P1 | One-hour recovery conflicts with rebuilding an index that takes hours | 6.2, 14.1, 17.4 |
| WF-19 | P1 | Untrusted repository ingestion lacks resource and execution boundaries | 9.2–9.3, 13 |
| WF-20 | P1 | Corpus acquisition and installation onboarding are not one implementable workflow yet | 5, 9.2, 14.1 |
| WF-21 | P1 | Thread ingestion does not fit a commit-only version and citation model | 1, 6.1, 9, 19 |
| WF-22 | P1 | Schedule and cut policy put required verification at risk | 16, 19 |
| WF-23 | P1 | Administrative authorization, session lifecycle, and deployment trust need explicit contracts | 9.10, 13, 18 |
| WF-24 | P2 | Chunk coverage and normalization rules need precise semantics | 9.3–9.4, 16.2 |
| WF-25 | P2 | Retrieval needs deterministic ranking, code tokenization, and bounded fallback | 9.4, 15.4 |
| WF-26 | P2 | Readiness, SLO denominators, and trace sampling can misrepresent service health | 9.10, 17 |
| WF-27 | P2 | Free-tier and fallback deployment claims need account-specific evidence | 7, 10.6, 11, Appendix B |
| WF-28 | P2 | Quality estimates need stronger baselines and clearer uncertainty | 3, 14–15 |
| WF-29 | P2 | Reproducibility requires a full release manifest and tested execution profiles | 12, 16.9, 18 |
| WF-30 | P3 | Resolve editorial contradictions and imprecise invariants | Throughout |

## Detailed findings and required verification

### WF-01 — P0: repository visibility is itself an expiring authorization fact

**Evidence:** §9.5, source lines 801–817, always unions public repositories into the visible set. Only `user_access_state` has a validity deadline. `repository.visibility` has no corresponding validity lease; `installation` has no serving/suspension/deletion state. Reconciliation is described as comparing branch SHAs every six hours. This is an incomplete contract with a direct counterexample.

**Failure:** repository R changes from public to private, with no code commit. Its webhook is lost. Refreshing user grants does not remove R from the separately unioned public set. Anonymous queries have no user-grant TTL at all. SHA reconciliation can see no change. R can remain searchable indefinitely under the specified mechanism. Similarly, uninstalling or removing R from an installation has no immediate eligibility predicate, while physical cleanup may take 24 hours.

**Change:** make serving eligibility independent of index freshness. Add repository/installation lifecycle state, a policy revision, and a deadline for the authority of visibility information. Expired or uncertain public visibility is not public authorization. Signed negative lifecycle events must disable the affected repository/installation in the webhook transaction, before asynchronous cleanup. Every retrieval, cache replay, artifact read, and source rendering checks eligibility. Periodically reconcile visibility and installation membership, not just git heads. An outage must deny repositories whose authorization evidence has expired, even if their index remains healthy.

**Verify:** public→private with no commit and a dropped webhook; uninstall; installation suspension; removal from selected repositories; transfer between accounts; visibility refresh failure; restore from a stale backup. Probe anonymous search, signed-in search, cache hits, traces, and citation expansions. Measure the complete bound from GitHub change to the last server disclosure. GitHub does not automatically redeliver failed webhooks, so delivery recovery cannot be assumed. [GitHub failed-delivery documentation](https://docs.github.com/en/webhooks/using-webhooks/handling-failed-webhook-deliveries).

### WF-02 — P0: revoke first, refresh second, and fence concurrent refreshes

**Evidence:** §9.5 enqueues `RefreshAccess` after a permission webhook, while unexpired cached grants are still used. The user-state row has no authorization revision, invalidation timestamp, or refresh fencing token. §9.2.2 also assigns Go workers to permission refresh, whereas §8 assigns permission resolution and token use to Python. Ownership of this security-sensitive operation is unclear.

**Failure:** an access-removal event arrives; GitHub is unavailable; the refresh worker fails. The existing grant remains usable until ten minutes, violating the 60-second delivered-webhook promise. A second race is worse: refresh A starts before revocation, refresh B installs the new denied set, then A completes and reinstalls the older grants with a new TTL. A queue backlog or a team-change fan-out across 1,000 users can also exceed 60 seconds.

**Change:** atomically mark the affected grant scope invalid when accepting a negative event. If identifying affected users is uncertain, temporarily deny the repository or installation for the affected scope. Fetch pages outside long DB transactions, then replace grants and their lease atomically only if a captured authorization revision still matches. Partial pagination must never be treated as a successful full refresh. Use single-flight refresh across processes and fence token refresh similarly. Choose one owner for permission refresh; share the contract rather than implementing divergent policy in Go and Python. Handle `github_app_authorization` revocation, which GitHub sends when a user revokes the app. [GitHub user-token documentation](https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app/generating-a-user-access-token-for-a-github-app).

**Verify:** intentionally reverse completion order of two refreshes; revoke during pagination; return an error on page two; deliver a team event during GitHub downtime; expire tokens in two workers simultaneously. A known denial cannot be overwritten by an older observation. GitHub refresh tokens rotate and invalidate the prior token pair, so parallel refresh is not a harmless duplicate. [GitHub refresh-token contract](https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app/refreshing-user-access-tokens).

### WF-03 — P0: classify every outbound byte, including the question

**Evidence:** §9.8 classifies data from repositories represented in retrieved passages; §17 permits content capture for public-scope requests. This misses the original user input and, if enabled, rewritten queries or other derived content.

**Failure:** a user pastes a confidential stack trace, customer identifier, or private code into a question. Retrieval finds only public `httpx` passages. The request is classified public, so the pasted material can go to a free provider or sampled cloud telemetry. Prompt-injection delimiters do not fix this data-classification error.

**Change:** classify the complete request envelope and all derived artifacts. For a private installation, use an explicit approved-egress policy for user input as well as source passages. Treat unknown classification conservatively. Public demo input needs a clear public-data-only contract. Query rewrite, judging, exception capture, feedback export, debug logging, and caching inherit the same policy. Disable raw request/prompt capture by default. For mixed-installation queries, intersect approved provider sets; an empty intersection means extractive output. Also prevent model-controlled browser egress: disable remote Markdown images and other automatically fetched resources, and render only server-constructed citation destinations. Restricting anchor links alone does not govern image loading. A provider's no-training default is one policy input, not sufficient evidence of an organization's approval of retention and processing terms.

**Verify:** a synthetic secret only in the question, only in a rewritten query, only in an exception, and only in feedback. Use recording transports for every provider, OTel, Sentry, and export path; the secret must not reach a disallowed destination. Test a public-only result set for a private-classified question. Google's unpaid-service terms explicitly restrict submitting confidential/sensitive information; Anthropic documents a default of no training for commercial inputs/outputs. [Gemini terms](https://ai.google.dev/gemini-api/terms), [Anthropic commercial-data policy](https://privacy.claude.com/en/articles/7996868-is-my-data-used-for-model-training).

### WF-04 — P0: ownership is not current source authorization

**Evidence:** trace/feedback endpoints are owner-protected (§9.10); historical answers/traces persist 30 days (§13.4). Current-source authorization at artifact access is not specified. `answer.user_id` is NULL for every anonymous user. Source dependencies of a stored answer are not explicit relational records.

**Failure:** Alice receives an answer, loses repository access, then reads her old trace or reopens an answer. An owner check still passes. Cache-copy trace links can retain the same issue. For anonymous requests, treating NULL as a shared principal could expose other visitors' question/trace metadata; treating it as no principal means the promised trace feature cannot work for them. The schema does not establish which behavior is intended.

**Change:** store an explicit artifact principal and the repository/version dependencies of every answer and trace. Reauthorize those dependencies on each server read and replay. On revocation, redact or deny the affected artifact; do not present an old mixed-repository generated answer as valid after merely hiding its citation. Either issue an opaque anonymous session for ownership or disable historical trace/feedback access for anonymous users. A user-controlled answer UUID is not authorization. Recheck an authorization lease before provider dispatch and during long streams; cap stream lifetimes so a request started just before lease expiry cannot disclose indefinitely. Already downloaded material cannot be recalled; state that boundary explicitly.

**Verify:** same-owner access after revocation; public→private after anonymous generation; cross-anonymous trace requests; copying a cached answer; an SSE stream crossing an authorization deadline; revoked session in both API workers. The oracle must use the expected current grants, not the application's own cached set.

### WF-05 — P1: separate content, representation, and occurrence identity

**Evidence:** `chunk` is unique on `(repo_id, content_hash)` and stores one embedding (§9.1, source lines 509–523). Idempotent inserts use `DO NOTHING` on that key (§9.2.3). Model identity is present on `index_version` and `embedding_cache`, but absent from chunk uniqueness. Header/location semantics are ambiguous: the header includes a path and is embedded, yet chunk rows are described as location-independent content.

**Failure:** reindex the same text with embedding model B. The new version row exists, but the chunk insert conflicts and preserves model A's vector. A new query embedding is compared against the wrong space, even if both dimensions are 768. Updating the existing vector in place instead would corrupt the old active generation. A rename or identical body in two contextual locations can similarly reuse a stale path header if the hash excludes the header.

**Change:** distinguish exact source content, occurrence metadata, and embedding representation. At minimum use `(repo_id, embedding_spec_id, embedded_input_hash)` for the searchable representation, with occurrence/source-span records per version. `embedding_spec_id` includes immutable model digest, tokenizer/runtime contract, document/query templates, pooling/normalization, and dimension. Hash the exact embedded input, including its header and template. Reuse only truly identical inputs. Declare a model-transition strategy: a maintenance-window rebuild for the small MVP is acceptable, or build a complete compatible generation alongside the old one. Never switch a single global query embedder while some active repositories still use another vector space.

**Verify:** same text across two models with the same dimension; changed dimensions; changed template; rename with unchanged body; identical bodies at different paths; activation and rollback while queries run. A small relational counterexample in this review preserved `model-A-vector` after the specified conflict behavior attempted a model-B insert. Nomic's model card also distinguishes query and document prefixes; “same model name” alone is not a full embedding specification. [Nomic model card](https://huggingface.co/nomic-ai/nomic-embed-text-v1.5).

### WF-06 — P1: define the deletion closure and GC order

**Evidence:** GC deletes non-live chunks not referenced by building/ready/active versions (§9.2.4). But `version_chunk` and `code_edge` have foreign keys to chunks without cascades (§9.1). Retired-version references still block deletion. The embedding cache is permanent; traces/answers last 30 days; backups last 14 days. Source clones and derived metadata have no deletion policy.

**Failure:** delete a file, retire its version, and run the specified chunk deletion: the FK rejects it if retired memberships remain. Alternatively, implementation adds cascading deletion without a retention design and breaks answer citations. A sensitive file removed from the current tree remains in a local git object database, cached output, or retained backup after the advertised 24 hours.

**Change:** distinguish immediate serving denial, active-store deletion, derivative retention, backup expiration, and original-source retention outside Wayfinder's control. Define ordered cleanup of retired memberships/edges, then unreachable chunks and representations. Add answer→source dependencies to invalidate affected caches and historical views. Decide whether unused private embeddings may remain and document the decision; an unbounded permanent cache contradicts an unqualified deletion promise. Handle shared-content reference counts without deleting another permitted source's representation. Retain deletion tombstones outside stale snapshots or replay them before restored data can serve. State explicit exceptions for encrypted backups if those expire later than 24 hours.

**Verify:** real PostgreSQL GC with retired references; a chunk reused by a building version; delete and immediately revert; uninstall with cached answers; expired answer with `cached_from` children; restore a pre-deletion backup. This review's minimal SQLite FK model reproduced the blocked delete, but it is not a PostgreSQL integration test. PostgreSQL documents `NO ACTION` as the default FK delete behavior. [PostgreSQL constraints](https://www.postgresql.org/docs/current/ddl-constraints.html).

### WF-07 — P1: replace the assumed River uniqueness contract

**Evidence:** §9.2.2 relies on uniqueness only while a job is pending/scheduled and enqueues another `IndexRepo{repo}` while the current worker is still running. Current River documentation requires `pending`, `scheduled`, `available`, and `running` in custom `ByState` lists. The proposed waiting-only setting is therefore not supported by that documented contract. [River unique jobs](https://riverqueue.com/docs/unique-jobs).

**Failure:** with supported uniqueness including `running`, the same-argument follow-up enqueue is skipped. A push arriving while indexing can remain unprocessed until reconciliation. Excluding `running` is not an acceptable fix without evidence from the pinned implementation that it is supported.

**Change:** pin River first and implement a durable repository work-generation/dirty marker independent of queue uniqueness. A worker processes the desired generation; event acceptance advances that generation transactionally. Completion must either establish no newer work or arrange the successor through a supported atomic completion-and-enqueue mechanism. Another valid implementation is generation-specific queue arguments plus repository serialization and coalescing. The desired state must survive a crash between the final head check and job completion. Check `UniqueSkippedAsDuplicate`; a skipped insert is not evidence that future desired work is covered.

**Verify:** use the actual pinned River library for pushes before job start, during the build, during final head check, during completion, and during retry. Kill the process at each boundary. The final desired head must eventually become active without waiting six hours. Add this to G0, not week four.

### WF-08 — P1: fence build ownership and obsolete targets

**Evidence:** the activation CAS compares the active version with the build's base version; on mismatch the instruction is to recompute the diff and retry (§9.2.4). Heartbeats mark stale builds failed, but activation does not require a valid build lease or an allowed status transition.

**Failure:** A builds older head A; B builds newer head B and activates first. A loses the CAS, recomputes its diff against B, and activates A if its old target is retained. Both switches were individually serialized, yet freshness regressed. A paused worker can also resume after its build has been marked failed. Git commit ancestry cannot solve this alone because a legitimate force-push can move to an unrelated or older commit.

**Change:** add a repository desired-generation and a worker/build fencing token. On a CAS conflict, re-resolve desired work rather than retrying the obsolete target automatically. Activation requires a complete ready version, correct repository ownership, valid lease, matching expected base, and the current eligible desired generation. Enforce one active version per repository with a partial unique constraint, and prevent cross-repository membership/active-pointer references with appropriate composite constraints or checked transactional routines. Define `building → ready → active → retired` and the permitted retry from `failed`; do not leave `ready` as an unused word.

**Verify:** the older worker finishes last; heartbeat is stale then resumes; force-push races ordinary push; cross-repository chunk membership is attempted; GC runs while a version is assembled. The simplified CAS model in this review demonstrated the stale-target rollback permitted by the prose. It does not establish that an implementation would necessarily retain the old target.

### WF-09 — P1: citation validity and factual support are different guarantees

**Evidence:** the executive summary promises every claim is cited. US-02 and §9.6 allow uncited sentences and validate markers only after completion. Checking that `[c3]` exists in the retrieved set does not check that c3 supports the claim.

**Failure:** a valid marker accompanies a false numeric claim, or an invalid marker is already rendered during streaming and removed later. The client receives no explicit canonical replacement event. An attacker can induce an unsupported answer using only valid citation IDs. The statement in §13 that answers “can only contain” permitted retrieved content is also too strong: a model may generate arbitrary text or draw on prior knowledge.

**Change:** choose a truthful v1 contract: citation IDs are authorized and well-formed; model prose is provisional until completion; support quality is empirically evaluated and may be imperfect. If every factual claim must have a valid marker, buffer by sentence/claim before release and fall back for unsupported structure. Marker validation alone still does not prove entailment. If allowing provisional token streams, define a final canonical answer/replace event, validation status, and non-cacheable failure state. Score claim support, citation completeness, and answer usefulness separately. Escape passage delimiters and test malicious passages; do not call prompt delimiters a security boundary.

**Verify:** fabricated marker split across tokens; cited passage that contradicts the claim; uncited answer; truncation mid-marker; repaired final text; reconnect to a partially generated answer; malicious Markdown/image syntax. Offline judges must use only the provided evidence for support labels, not their outside knowledge.

### WF-10 — P1: the fallback evidence gate measures ranking agreement, not relevance

**Evidence:** §9.6 falls back to a calibrated RRF threshold when reranking is shed. With k=60, a document ranked first by both legs always scores `2/61 ≈ 0.0327869`, whether both retrievers found a relevant document or merely the least irrelevant one. A single-leg top result has `1/61`, irrespective of its raw similarity. This is a mathematical counterexample, not a claim that a calibrated threshold can never have useful empirical correlation.

**Failure:** an out-of-corpus question makes both systems rank the same generic README first. Its RRF score passes the gate despite no evidence. When dense retrieval fails, score distributions change again. The system is most likely to generate weakly supported answers precisely when overloaded.

**Change:** use RRF for candidate ordering. Treat answerability as a separately versioned decision with mode-specific validation. For the small MVP, if the reliable answerability mechanism is unavailable, return authorized passages without generation. If generation without reranking is retained, calibrate using features with relevance information and report risk/coverage for each mode. A high best-passage score cannot by itself guarantee that all parts of a multi-part question are answerable.

**Verify:** two queries with identical rank orders but very different relevance; high-agreement negatives; partly answerable questions; lexical-only mode; reranker timeout; provider/model swaps. A degraded mode does not inherit the normal mode's quality numbers.

### WF-11 — P1: make stored answers and stream completion a complete state machine

**Evidence:** the abridged schema stores answer metadata but no canonical output, citation mapping, evidence version manifest, or completion status (§9.1). The cache promises SSE replay (§9.9), and the UI has an answer route (§9.12), but no read-answer endpoint is listed. These may be omitted implementation details, but they are necessary for evaluating caching, deletion, and recovery.

**Failure:** a provider emits half an answer and fails. Appending a fallback provider's new answer produces incoherent output; silently caching the partial result makes it permanent. A client retry after disconnect creates duplicate charged generations. Trace-copy references become dangling after source GC.

**Change:** specify `pending / streaming / completed / refused / extractive / failed / cancelled` answer states, immutable evidence and policy manifests, canonical final text, citation resolution, and usage. Cache only explicitly eligible terminal states. Before any token is emitted, fallback can replace the provider; after emission, send a typed terminal error or an explicit reset and replacement protocol. Add an authenticated retrieval contract if reopening answers is in scope. Define idempotency for retries and in-flight deduplication within an authorization/policy partition. Copy sufficient evidence while the read snapshot is open, then release DB connections before awaiting the model or client.

**Verify:** failure before first token and after token 100; slow client; client disconnect; duplicate request ID; cancelled upstream still bills; cached repaired answer; historical view after GC. Assert pool connections are returned during every stream and no partial answer enters the reusable cache.

### WF-12 — P1: quotas and deadlines need a resource budget, not just RPM

**Evidence:** §9.8 specifies a request token bucket per provider and waits up to two seconds per provider. The request has no total generation deadline, maximum output-token contract, SDK retry budget, or per-installation budget. Per-installation routing is ambiguous for a cross-installation query.

**Failure:** successive waits consume six seconds before upstream generation; the nominal TTFT target is already missed. An RPM-compliant workload breaches token or daily quotas. SDK retries multiply application fallbacks. One installation consumes the entire paid allowance. At the stated nominal rate, 5,000-token prompts imply roughly 2.75 million input tokens/minute, far more informative than the “100–200 RPM aggregate” estimate.

**Change:** pin provider/model combinations; reserve estimated input, maximum output, requests, and spend before dispatch; reconcile actual usage afterward. Apply one end-to-end deadline and a bounded total attempt budget, including Instructor and SDK retries. Distinguish throttling, monthly spend exhaustion, authorization failures, malformed inputs, and provider outages. Share provider health/quota state as required across workers and cap half-open probes. Intersect all contributing installation policies and include their revisions, chosen request class, and generation configuration in cache eligibility. The local budget is conservative accounting; provider-side caps remain a backstop.

**Verify:** abundant RPM but depleted TPM; exhausted daily quota; exact spend cap; three-provider failure chain; cancellation with missing final usage; concurrent final-budget requests; conflicting installation policies. Groq documents multiple request/token windows; Gemini says actual account limits vary and are not guaranteed; Anthropic distinguishes spend-limit errors from ordinary rate limiting. [Groq limits](https://console.groq.com/docs/rate-limits), [Gemini limits](https://ai.google.dev/gemini-api/docs/rate-limits), [Anthropic limits](https://platform.claude.com/docs/en/api/rate-limits).

### WF-13 — P1: evaluate ANN against the exact authorized subset

**Evidence:** E7 says “Recall@10 vs unfiltered exact search” while varying visibility (§15.4, source line 1430).

**Failure:** the globally nearest ten vectors all belong to a forbidden repository. A secure filtered retriever correctly returns different neighbors, then is scored as wrong against an unauthorized gold set. That experiment rewards an impossible or unsafe target. It also conflates ANN approximation quality with the task's file-level relevance metric.

**Change:** for each query, user, corpus snapshot, and filter, compute exact top-K over the same **authorized, eligible, live** rows. Compare approximate neighbor overlap against that oracle. Separately report file-level relevance recall over only accessible gold files, and define what happens when no gold file is accessible. Use permitted-set sizes 0, <K, K, and large; report rows actually returned and scan-limit exhaustion. Post-filtering is an experiment only and must never release forbidden content.

**Verify:** a deliberately constructed corpus whose global nearest neighbors are all forbidden; an empty visible set; one allowed row; highly selective filters; exact/iterative/relaxed modes. pgvector explicitly documents that filtered approximate scans may underfill, that iterative scans have limits, and that relaxed results can be slightly out of distance order. [pgvector filtering and iterative scans](https://github.com/pgvector/pgvector#iterative-index-scans).

### WF-14 — P1: historical evaluation needs historical text and isolated snapshots

**Evidence:** quarterly snapshots precede each window; labels are changed files from PRs later in that quarter; issue/PR eligibility is based on creation time (§14.2). The query uses current issue text. Multiple snapshots are pseudo-repositories in one database. The dev/test split is by pair date, not necessarily grouped by underlying issue/PR.

**Failure:** an issue created in January is edited in March to name its fix. Filtering on January's creation date still admits March's text. A quarterly source snapshot can precede the actual bug or later renames, even when a same-named gold file existed. Multiple issues closed by the same PR can cross the split. If retrieval accidentally includes other pseudo-repositories, a future snapshot can reveal the answer directly.

**Change:** prefer a reproducible pre-fix base commit for each pair, or explicitly call the quarterly benchmark an approximation and audit its temporal validity. Exclude mutable threads from historical retrieval unless their historical contents can be reconstructed. Capture query provenance and edits; exclude post-fix revisions that cannot be validated or tag them as a separate weaker benchmark. Group connected issue/PR examples before temporal splitting. Scope each query to exactly its allowed snapshot and corpus; enforce that restriction independently. Record excluded examples and reasons so filtering does not silently make the task easier.

**Verify:** post-fix edited issue, changed title, renamed file, bug introduced after snapshot, one PR closing multiple issues, and a future-only sentinel answer in a different pseudo-repository. The sentinel must never be retrieved. Audit a stratified sample, not only 30 globally random pairs, and report error rates by failure type.

### WF-15 — P1: make quality regression gating a release contract

**Evidence:** the CI gate checks Recall@10/MRR only for retrieval changes, relative to main's last run. Generation/prompt/policy changes have no equivalent explicit gate. Test data is scored at G2 and launch; three generation configurations are costed across all 80 explain/unanswerable examples without a dev-only selection restriction. Cuts can remove requirements still present in the exit checklist (§16, §19).

**Failure:** prompt changes degrade faithfulness while retrieval CI stays green; several small decreases accumulate because each is below two points; a large uncertain regression passes because the small sample's CI crosses zero. After viewing G2 test results, tuning before launch turns the test set into another dev set. A stale cached evaluation dump hides a parser/header/schema change.

**Change:** run security/authorization invariants on every PR. Trigger deterministic and quality gates for all retrieval, generation, parser, policy, config, dependency, and migration changes. Run baseline and candidate on identical manifests. Compare both to main and a pinned approved-release baseline. Retain the statistical gate, but give large inconclusive regressions a “needs review” state rather than automatic green; do not relax zero-leak gates statistically. Select generation configurations on dev only. If G2's test result influences changes, the later assessment is no longer a fresh held-out test: either freeze the release config or reserve a final untouched set. Apply corrections to gates when scope changes, with an explicit decision record.

**Verify:** intentionally introduce a permission leak, bad prompt, broken citation parser, template/hash change, and cumulative small retrieval regressions; each must trigger the appropriate required check. A required check that is skipped by path filters must not silently count as a release pass. See the concrete continuous-verification matrix later in this report.

### WF-16 — P1: distinguish session capacity, uncached capacity, and useful service

**Evidence:** §16.8 calls uniform sampling from a 2,000-query pool “cold caches, worst case,” while each API worker has a 10,000-entry query-embedding cache. L1 primarily uses synthetic grants; its server invariant tests membership in the same visible set used for retrieval.

**Failure:** both workers warm the entire embedding-query pool and report a much cheaper workload than the estimated cold embedding path. Answer-cache behavior differs because visible sets create many distinct keys; uniform questions alone do not determine its hit rate. A wrong permission provider returns an overly broad visible set and the server assertion happily validates its own mistake. A single laptop's shared source IP can rate-limit all 1,000 virtual users, making the apparent capacity test mostly rejection handling.

**Change:** keep L1's closed-session model because it matches the stated requirement, and add an open arrival-rate profile to expose overload independently of slower client iterations. Run separate uncached, warmed, and realistic-repetition profiles. Disable caches in the uncached profile or use a genuinely large semantically representative pool; do not append meaningless nonces that change retrieval quality. Publish actual throughput, embedding/answer hit rates, accepted/generated/extractive/refused/rejected fractions, full-stream completion, and latency by outcome. Assert permissions against an independent fixture oracle, including dynamic mutations. Specify test IP/user rate-limit profiles so test bypass is explicit and ordinary rate limiting is separately verified. Use realistic token/session lookups in addition to cheap fixture authorization.

**Verify:** stable arrival rate under slowdown; cold embeddings with real query-length distribution; expired access leases; 0%, tiny, and broad permissions; 429s counted separately; client CPU/network saturation; stream parser and first-token timing. The chosen xk6-sse project does support POST bodies, so it need not be replaced on that basis. [k6 open/closed models](https://grafana.com/docs/k6/latest/using-k6/scenarios/concepts/open-vs-closed/), [xk6-sse POST example](https://github.com/phymbert/xk6-sse).

### WF-17 — P1: make the capacity claim conditional on measured whole-system demand

**Evidence:** the workload arithmetic is sound, but all central service costs are estimates. §1 says capacity is achievable before S2 runs. The ~15 ms query embedding assumption uses ~20 tokens, while input can be 2,000 characters and mined issues include code/stack traces. The no-cache short-rerank configuration consumes about 82% of two cores before all background activity. Memory allocations total the entire 12 GB, including stated headroom.

**Failure:** production embeddings are longer than the microbenchmark; ingestion and database maintenance compete with retrieval; per-worker limits shed despite spare capacity in another worker; degraded fast responses satisfy latency while answer utility collapses. Two Ollama processes isolate request queues but do not make query latency independent of shared CPU, memory bandwidth, or disk pressure. API workers, PostgreSQL, and Ollama all share the two cores.

**Change:** label capacity a hypothesis until whole-system tests pass. S2 must measure process CPU, not just wall time, across query-length percentiles, cache states, ACL selectivity, batching, and concurrent indexing. Reserve explicit background CPU and memory budgets; bound model threads, ingestion, concurrent index maintenance, and per-connection memory. Measure the real plan for lexical and dense filters. Use a rerank policy that meets the target without assuming an unmeasured 30% answer-cache hit rate. Report how often the measured quality configuration actually runs under load. L6 must satisfy the absolute search SLO as well as its relative degradation bound; a 30% increase from 500 ms is a failing 650 ms.

**Verify:** final production query/model/config on A1, not laptop inference times; a representative 60k-chunk corpus; cold and warm cases; full reindex plus autovacuum/GC; long-running streams; CPU and resident-memory breakdowns. Report a measured lower user limit if the target fails. Stub tests substantiate application streaming capacity, not 1,000-user live LLM generation quality or quota availability.

### WF-18 — P1: define recovery as usable search, not a healthy empty API

**Evidence:** NFR-07 requires RTO ≤1 hour. The runbook restores only non-index tables and starts a full reindex. §14.1 expects initial indexing to take hours. The app encryption key lives outside the backed-up database, and no independent recovery procedure for it is specified.

**Failure:** the VM and index are lost; the API returns healthy, but search is unusable for several hours. Restored repository pointers can refer to excluded index-version rows. Historical traces can reference absent chunks. User tokens are unrecoverable if the encryption key was lost, or stale grants/session state revive after restoration. Recreating an unavailable free shape can itself exceed an hour.

**Change:** split control-plane RTO, minimal usable-search RTO, and full-corpus RTO, or back up a consistent index snapshot within the storage budget. Define exact backed-up tables and restore order; clear active pointers and cached authorization on recovery until reconciled. Restore durable application records using stable source identifiers, not assumptions about regenerated serial IDs. Securely back up essential encryption/configuration secrets separately, or explicitly invalidate credentials and require reauthorization. Persist deletion tombstones and reapply them before serving. Set targets from a measured drill rather than asserting that Terraform guarantees provisioning time.

**Verify:** recover into an empty host with unavailable old disks and no warm model cache; validate encrypted-token handling, absence of revoked/deleted data, schema consistency, and a real known query at the promised recovery milestone. Measure total time including provisioning, image/model download, restore, and indexing. Rebuildability also assumes the source still exists and is accessible; state that limitation.

### WF-19 — P1: treat source repositories as hostile inputs

**Evidence:** the threat model covers hostile retrieved text but not the full git/parser ingestion surface. Limits are provided for questions and HTTP bodies, not source repositories, files, parser work, or clone storage (§9.2–9.3, §13).

**Failure:** a selected repository contains enormous generated files, a very long syntax node, symlinks, unexpected encodings, pathological nesting, or credentials. A clone or parser monopolizes the shared VM. Following a symlink reads a mounted secret. Running project tooling to “help parse” executes untrusted code. Shallow history cannot resolve the old/new tree needed after a force-push. A failed git command logs a token-bearing URL.

**Change:** use git object/tree reads where practical; never execute repository code, hooks, build scripts, LFS filters, or recursive submodule commands as part of indexing. Explicitly bound clone bytes, files, per-file bytes/tokens, parser time/memory, and installation corpus size. Define handling of binaries, symlinks, submodules, vendored/generated paths, unsupported languages, malformed syntax, LFS pointers, and empty/deleted default branches. Obtain credentials without persisting them in remote URLs/logs. Fetch the exact required commits/trees or fall back to a bounded full snapshot when shallow history is insufficient. Sensitive-file exclusions and secret scanning are defense in depth, not proof that all source content is safe to export.

**Verify:** fixtures for each input class, adversarial paths beginning with option-like characters, newline/unicode paths, missing old commits, clone interruption, and a synthetic credential in parser error text. Partial parse failures must be visible in repository status and must not silently activate a version advertised as complete. Return a manifest of skipped material with reasons.

### WF-20 — P1: specify how the demo corpus is actually authorized and acquired

**Evidence:** FR-01 only indexes repositories selected in a GitHub App installation. §14 proposes third-party projects such as `pydantic/pydantic` and `encode/httpx`. The document does not establish installation authority on those organizations. A public repository being readable does not give the author permission to install an organization-scoped app there. [GitHub installation rules](https://docs.github.com/en/apps/using-github-apps/installing-a-github-app-from-a-third-party).

**Failure:** S1 successfully mines public pairs but the production connector cannot onboard those sources under FR-01. Forks provide owned code repositories but do not automatically reproduce upstream issue/PR discussion histories and webhook behavior. `Source.Snapshot` alone does not settle this authorization difference.

**Change:** separate two explicit source modes: owned installed repositories for real webhook/permission demonstrations; allowlisted public upstream sources for evaluation or the public corpus, with permitted read credentials and polling. Alternatively, serve owned mirrors/forks while preserving upstream attribution and use upstream metadata only for the evaluation miner. Define which mode ships. Add the app registration/installation callback, configuration authority, repo selection updates, indexing progress, failure/retry UI, and removal workflow. `config-only onboarding` still needs an authenticated person authorized to approve the configuration.

**Verify:** fresh installation into the author's organization; selected-repository addition/removal; public upstream source with no installation; denied configuration change; 100+ repositories requiring pagination; empty repository; deleted installation during initial indexing. G0 should produce an actual readable source manifest, not merely a candidate list.

### WF-21 — P1: keep thread indexing out of the commit-only core contract

**Evidence:** the connector contract takes git-like revisions; `index_version` is identified by a commit SHA; `version_chunk` has file paths and line ranges. Issues/comments are mutable independently of commits. `updatedAt` is described as a cursor but pagination, watermark semantics, deletions, and review comments are unspecified. §1 nonetheless promises code, docs, issues, and PRs.

**Failure:** a comment is edited without a git push. The active commit/cache key does not change, and the answer remains stale. A deleted comment is never encountered in an updated-items scan. An issue citation is incorrectly represented as a commit-pinned source. Design rationale stored in review threads is missing even if PR descriptions are ingested.

**Change:** for v1, defer thread retrieval consistently in the title, summary, stories, metrics, and launch checklist. If it is promoted, introduce typed sources and citations: git blob + commit + lines versus issue/PR/comment ID + captured revision/hash + source URL + observed timestamp. Use an opaque connection cursor only for pagination and a durable timestamp/ID watermark with overlap/reconciliation for updates; do not assume `updatedAt` is a historical snapshot or a deletion feed. Version the thread corpus independently and include that epoch in answer-cache dependencies. GitHub thread URLs identify mutable sources, so retain the captured evidence revision or explicitly state when the citation cannot reproduce it.

**Verify:** thread edit with unchanged code SHA; deletion; pagination with updates during traversal; identical timestamps; renamed/transferred issues; PR review comments; force-push with unchanged PR body. “Why” answers must distinguish documented rationale from inference from current code.

### WF-22 — P1: protect the evidence, not all experiments, when cutting scope

**Evidence:** the 120-hour WBS exactly consumes 120 hours. Several tasks bundle substantial integration and verification into 1–4 hours. The cut order removes fault coverage, continuous freshness probing, and the browser smoke test while preserving many experiments. G4 still requires the full fault table and checks that cuts can remove. At most four full load runs are budgeted, but L1–L6 plus uniform/Zipf variants and reruns need a defined accounting unit.

**Failure:** implementation overruns and the system ships with the most consequential paths exercised only manually. The final checklist becomes a list of waived promises. Security review is concentrated late, after the shared schema and caching model are already implemented.

**Change:** freeze a smaller core with explicit contingency. Preserve authorization mutation tests, atomic activation/GC, one real browser flow, recovery, and continuous freshness detection. Cut agentic/MCP/graph work as already planned; next reduce breadth of E2/E4/E5/E6 or postpone online generated answers instead of removing safety/recovery evidence. Move permission/lifecycle and River/GC prototypes to week one. Count test-building work with each feature rather than reserving “leak suite completion” for week four. Specify the load-run budget in requests/telemetry units and reserve a rerun after fixes. A revised 90-hour planned core plus 30-hour contingency is a budgeting target, not a validated new effort estimate; re-estimate after the spikes.

**Verify:** each Must story has an implementation task, a required test, and an owner; each cut automatically changes dependent claims and approval gates. Review planned versus actual hours weekly. If the fixed date is non-negotiable, a well-tested locate-first release is more defensible than claiming the entire current spec shipped.

### WF-23 — P1: specify privileged operations and environment separation

**Evidence:** `/admin/reindex/{repo}` is simply “admin”; token creation exists without list/revoke/expiry endpoints; same-origin cookies and PKCE are named but mutation CSRF checks and cross-worker session invalidation are not. The production load-test issuer is guarded by an expiring flag, not by a distinct deployment/data boundary. Deploy-only SSH is named without privilege constraints (§9.10, §13, §18).

**Failure:** an authenticated user invokes a rebuild for a repository they do not administer; logout leaves the 30-second worker cache usable; a fixture token maps to a real private repository; an untrusted PR gets a production secret or poisons a trusted evaluation artifact. The Cloud Run capacity fallback proposes a publicly reachable DB protected by TLS/password only without a complete network/role design.

**Change:** define platform operator versus installation administrator authority using stable GitHub identities and explicit checks. Bind OAuth state/PKCE to a short-lived single-use browser transaction and validate redirect targets; PKCE is currently supported for GitHub Apps. Require Origin/CSRF defenses for cookie-authenticated mutations, safe methods, and explicit content types. Add token revocation/expiry/scopes before MCP ships. Decide and test the permitted logout propagation bound. Confine fixture auth to a separate synthetic-data profile with an unmistakable startup guard; an expiry alone is insufficient. Use least-privilege DB/service roles, protected deployment environments, immutable action/image versions, and no production secrets for untrusted fork code. Treat cross-cloud serving as a new security/capacity ADR, including connectivity and source restrictions, not a toggle.

**Verify:** IDOR on every admin/trace/token endpoint; OAuth state replay; cross-origin POST; revoked session across workers; synthetic issuer pointed at production data; untrusted PR paths; image rollback against migrated schema. [GitHub PKCE parameters](https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app/generating-a-user-access-token-for-a-github-app), [GitHub Actions secure-use guidance](https://docs.github.com/en/actions/reference/security/secure-use).

### WF-24 — P2: make chunking invariants match real syntax

**Evidence:** one chunk is emitted per function/method/class body, while the property test demands every nonblank line exactly once except configured overlap. Classes containing methods naturally overlap under a naive implementation. A >512-token statement cannot be split solely at statement boundaries. Hashes use “normalized chunk text,” whose normalization is not defined.

**Failure:** a large class and all of its methods duplicate most evidence; decorators/imports disappear; an enormous string breaks the token limit; whitespace normalization changes Python indentation or string literals; header text is incorrectly treated as a verbatim file slice.

**Change:** choose explicit structural ownership: emit leaf callable chunks plus class/module residual spans, or permit documented parent/child overlap. Track source spans separately from synthetic headers and overlap. Define fallback splitting for oversized single nodes/paragraphs and invalid ASTs. Preserve original source bytes for citations; normalize only a separately defined retrieval representation. Hash exact representation bytes. Query normalization must preserve code blocks, string-literal spaces, case, and syntax where meaningful. Count tokens with the relevant model tokenizer and budget the combined query/header/body.

**Verify:** nested classes/functions, decorators, Go receiver methods, Unicode, CRLF, Markdown code fences, huge literals, malformed files, and identical-looking code with different indentation/string spaces. A coverage manifest should account for every accepted source span and every explicit exclusion. Ollama defaults to truncating overlong embedding inputs; use an explicit policy so truncation is not silent. [Ollama embed API](https://docs.ollama.com/api/embed).

### WF-25 — P2: define deterministic and code-aware retrieval behavior

**Evidence:** exact SQL and lexical tokenizers are deferred; relaxed HNSW ordering feeds rank fusion; final aggregation takes a maximum per file. The small-corpus exact-scan choice is an experiment but no runtime underfill policy is specified.

**Failure:** relaxed distance ordering changes ranks; many chunks from one file consume the candidate pool and return fewer useful files; punctuation-bearing identifiers tokenize poorly; an unescaped lexical-query language raises errors despite parameterized SQL; ties vary between builds and create noisy metrics.

**Change:** re-sort bounded relaxed candidates by exact distance before assigning dense ranks, with a stable tie-breaker. Define lexical parsing/escaping, identifier/path fields, case handling, and code-specific tokenization. Keep SQL parameterization; it protects SQL structure, not the semantics of a separate search query language. Set per-file candidate limits and measure diversity. For highly selective authorized subsets, benchmark and permit exact vector search; it may be simpler at this corpus size. Specify bounded iterative-scan exhaustion, underfill reporting, and safe fallback. Use `EXPLAIN` evidence on the actual two-leg query; the presence of an index is not proof it is used.

**Verify:** `Client.send`, snake_case, camelCase, paths, punctuation, quoted errors, case-sensitive symbols, more than 100 chunks in one file, repeated ties, and <K permitted chunks. Keep graph expansion disabled unless measured; approximate graph edges can change the selected evidence and answer quality, so their cost is not latency alone.

### WF-26 — P2: separate service health from optional capability health

**Evidence:** readiness requires Ollama/reranker, but the degradation ladder promises serving without them. Availability is measured on `/readyz`, not successful user operations. Tail sampling keeps all unexpected 5xx, and per-request traceability is promised despite sampled export. The search SLO alternates between request percentiles and percentages of five-minute windows.

**Failure:** an optional model outage causes the proxy/deployment to remove a usable lexical service or trigger rollback. An error storm exhausts the telemetry cap. `/readyz` remains up while every search fails semantically. Local unsampled traces/answer rows grow until disk pressure, despite a cloud sampling budget. Legitimately quiet repositories are flagged stale merely because they have not received a push.

**Change:** readiness should represent the minimum safe serving path; report optional capabilities separately. Define availability and latency on eligible user requests with clear denominators and separate semantic failures/terminal SSE errors. Pick request-based or window-based SLO math and derive burn alerts consistently. Keep cheap request IDs/counters for every request and sampled detailed spans; specify local trace retention/size caps and bounded exporter queues. Security counters and denial events must survive ordinary sampling and rate-limit classifications. Bound error exports while preserving aggregate counts. Freshness measures desired-head lag and convergence, not time since last commit.

**Verify:** stop only Ollama; send a 5xx storm; stop exporters; fill the telemetry allowance; simulate a healthy readiness endpoint with a broken query; and run an unchanged repository for a day. The failure-injection disk test must reserve enough write space for WAL, authorization invalidations, and queue control, not merely pause model work at 90% occupancy.

### WF-27 — P2: free quotas are deployment constraints, not architectural guarantees

**Evidence:** Oracle's primary documentation supports the 2 OCPU/12 GB baseline. The PAYG 4/24 claim is explicitly unconfirmed in the design. A $1 Oracle budget alert is not a spending cap; Oracle describes budgets as soft limits. Free generation capacity and the alternative Cloud Run/Neon deployment are not verified for this account. [Oracle free resources](https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm), [Oracle budgets](https://docs.oracle.com/en-us/iaas/Content/Billing/Concepts/budgetsoverview.htm).

**Failure:** conversion or a deployment fallback creates billable resources even though an alert exists. Multiple providers have correlated quota exhaustion. A free API key does not expose the proposed model. A second VM's boot volume or backup footprint is omitted from the free storage ledger.

**Change:** retain 2/12 as the sizing baseline; remove PAYG-derived extra capacity from any essential path until account-specific evidence exists. Record quotas, supported models, regions, data terms, billing boundaries, and remaining allowances in the release manifest. Use infrastructure policy checks that reject unapproved shapes/resources; alerts are supplementary. Treat fallback hosting as a separately measured option, including database features, latency, network, and free-tier resource limits. Set live public generation's guaranteed capacity to zero until measured; extraction remains the known fallback.

**Verify:** account quota/model availability snapshots, Terraform plan against the allowed resource list, provider-specific cap exhaustion, and a resource inventory including both test and application VMs. The published Haiku/Sonnet prices in this draft are supported by the current Anthropic table; they should not be labeled invented or outdated without contrary evidence. [Anthropic pricing](https://platform.claude.com/docs/en/about-claude/pricing).

### WF-28 — P2: improve what the quality numbers actually demonstrate

**Evidence:** the headline must beat dense-only, although BM25 is likely a strong code-search baseline. Locate labels are changed files, not necessarily all relevant files. Twenty answerable test examples support only coarse precision estimates. The judge cross-check uses another Claude-family model despite citing same-family bias. The rule-of-three leakage bound assumes a trial model that the correlated fixture suite does not establish.

**Failure:** hybrid beats a weak dense baseline but loses to the inexpensive lexical baseline. A system retrieves a genuinely relevant unchanged file and is marked wrong. Over-refusal scores well on faithfulness because little is said. A 90% point estimate from 18/20 answers is mistaken for a reliable 90% population guarantee. Many correlated synthetic checks are presented as proof of a tiny real-world leakage probability.

**Change:** report BM25-only, dense-only, and deployed hybrid under the same budget. Retain mined-file metrics but label the proxy honestly and add task-based human checks: can someone locate the change or verify the explanation? Define answer precision, refusal recall, useful coverage, citation completeness, and macro/micro aggregation exactly. Use a confusion matrix and uncertainty intervals. Human labels are the calibration anchor; a second Claude model provides size/model sensitivity, not independence from family bias. Publish zero observed violations plus tested invariants/coverage. If showing `3/n`, explicitly restrict it to an idealized independent-trial interpretation, not a security guarantee.

**Verify:** manually audit false positives and false negatives; test the always-refuse baseline; stratify repository/language/query type; cluster resampling by related issue/PR where appropriate. For orientation, the Wilson 95% interval for 18/20 is approximately 0.699–0.972; 16/20 is 0.584–0.919. These were calculated during this review and are not measured Wayfinder results.

### WF-29 — P2: pin the whole experiment and test the actual local profile

**Evidence:** images and models will be pinned at kickoff; CI indexes are keyed by chunker and embedding model; the local plan mentions Compose and Ollama on Metal. The release is polyglot and uses native extensions on two architectures.

**Failure:** a tokenizer/header change reuses an old database dump; a model alias changes under the same name; CPU/Metal results are numerically close but nearest-neighbor ties alter ranking; the local Compose profile actually runs CPU Ollama and misses its indexing-time estimate. Public CI cache churn evicts large multi-snapshot dumps, turning a supposedly fast required gate into hours of rebuilding.

**Change:** manifest code commit, schema, extension/image digests, parser grammar, embedding/query template, tokenizer, model artifact hash, precision, retrieval parameters, prompt, provider model ID, dataset/snapshot/label hashes, and platform. Derive cache keys from that manifest. Document whether macOS Ollama runs on the host and how containers reach it; do not assume a Linux container inherits Metal acceleration. Use a small deterministic integration index in every PR and separately cached larger dev evaluations. Verify artifact provenance before restoring executable/data artifacts into trusted CI. Reproducibility means equivalent behavior within a stated tolerance, not necessarily bitwise LLM outputs.

**Verify:** cold clean-clone run on the documented laptop/CI/Arm profiles; changed grammar with unchanged model; cache miss/eviction; pinned model digest mismatch; and quality comparisons as well as the 0.999 cosine parity check. The `make up` 15-minute promise should state network and predownload assumptions.

### WF-30 — P3: reconcile the remaining text before the v0.3 review

These edits are smaller individually, but a canonical document should not leave implementers choosing between conflicting statements. Each item needs a decision and a document consistency check.

| Source | Issue | Required edit |
|---|---|---|
| §1, §6.3 versus §9.8/§11.4 | Paid spend is “only” evaluation, but private demos use it | Say evaluation plus explicitly budgeted private demos |
| §3.3 versus US-05 | Revocation timer starts at access removal in one place and webhook delivery in another | Publish both end-to-end target and delivered-event processing target; bound the lost-webhook path separately |
| §3.3 versus NFR-01/L1 | Server-error accounting excludes admission 503s only in some places | One eligibility/error/rejection definition everywhere |
| NFR-03 versus §10.2 | Stub TTFT already includes 400 ms, but production wording says upstream is “added” | Report total TTFT and measured components; do not add a provider p95 to a whole-request p95 |
| §8 diagram/table versus §9.2.2 | One Ollama service shown, two required | Show both runtime instances and their resource limits |
| §8 coordination versus §9.2.2 | Go access worker versus Python permission resolution | Assign the refresh implementation and token-owner boundary explicitly |
| §6 FR-16 versus US-11/§19 | MCP appears unconditional in FRs, stretch elsewhere | Mark FR-16 conditional/stretch |
| §12 parser list versus FR-02 | TypeScript appears in the chosen parser stack but is stretch | Label deployed language support separately from available grammars |
| §9.2.2 | “Job exists iff delivery was recorded” is too literal when deduplication coalesces multiple deliveries | Say acceptance durably records the event and guarantees its desired work is covered |
| §9.2.4 | Activation updates are O(diff), but complete membership copying can be O(repository size) | State full-version membership construction cost separately |
| §9.2.4/§16.2 | “Exactly one wins” is not true if both calls retry serially; a first activation/revert also needs definition | Specify one winner per competing expected-base generation and the retry semantics |
| §16.2 | RRF “adding a document” is ambiguous about its rank and effects on other documents | State the precise property: an additional contribution for the same document at fixed existing ranks cannot reduce its score |
| §9.10 | “All endpoints under /v1” excludes listed auth/admin/health/webhook routes | Say business API endpoints are versioned under `/v1` |
| §9.13 | L0–L7 are presented as ordered levels but can occur simultaneously | Represent independent capability/degradation flags plus a separate admission outcome |
| §14.6 | “0 to 12 grants” includes public repositories already visible to everybody | Distinguish explicit private grants from the derived visible set; add a truly empty-source test |
| §17.3/§16.8 | Four full load runs versus six scenarios and sampling variants | Define a run bundle and a request/telemetry budget, including reruns |
| §3.2/§13.3 versus §17.2 | A read-only GitHub App cannot perform the hourly synthetic commit | Use a separately scoped synthetic-repository probe credential or an external fixture updater; keep the serving app read-only |
| §4 RACI/§22 | Manager and security reviewer may be simulated, while sign-off looks organizational | Name actual reviewers if any, otherwise label self-review and external-review status honestly |
| §2 competitive claims | Broad claims about all generic RAG/search products are unsupported | Describe the chosen baseline's observed limitations, not whole categories |
| §19.5 | Cuts leave Must goals and QA exit criteria unchanged | Update all dependent claims and gates in the same revision |

**Verify:** a v0.3 consistency pass over FRs, stories, acceptance criteria, schema, WBS, runbook, and launch checklist. Do not replace these small corrections with new systems or features.

## Replacement contracts for v0.3

The following is proposed specification language. It makes the architecture reviewable without prescribing a large rewrite or pretending that application code was supplied.

### Authorization and repository lifecycle

> A repository is eligible for serving only while its source connection is active, selection is valid, and its visibility/lifecycle facts have an unexpired authority lease. Private access additionally requires a valid user grant. A negative authorization event invalidates the affected authority in the same transaction that records the event. A background refresh cannot override a newer invalidation. This rule applies to search, prompts sent to providers, generated and cached answers, historical artifacts, traces, source expansions, and future MCP tools.

Use one conceptual predicate, evaluated with a recorded policy revision:

```text
allowed(user, repo, time) =
    connection_eligible(repo, time)
    AND repository_eligible(repo, time)
    AND (
        verified_public(repo, time)
        OR valid_user_grant(user, repo, time)
    )
```

`verified_public` includes a validity deadline. It cannot mean only `repository.visibility = 'public'`. A public-only degradation still evaluates this predicate; it does not bypass it.

For the delivered-webhook objective, measure event receipt → denial enforcement, including queue and process effects. Prefer synchronous invalidation so GitHub availability is not on the denial path. For the lost-webhook objective, the authority deadline bounds stale source facts. A long-running request is not allowed to extend that deadline. Avoid claiming instantaneous agreement with GitHub while allowing a ten-minute stale-read window: that window is an explicit accepted product trade-off.

### Snapshot and activation consistency

> A successful retrieval binds its active-version manifest, candidates, source locations, and answer-cache identity to one database snapshot. The transaction ends after copying the bounded authorized evidence needed for the response. Version activation is atomic and requires a complete ready build, a valid build fence, and the current desired generation. A failed or obsolete worker cannot activate. Provider calls and SSE backpressure never hold the retrieval transaction open.

Define the visibility boundary for ordinary updates explicitly: new retrievals after activation use the new version; an already accepted request may finish its pinned snapshot within a bounded lifetime, subject to current security authorization. If a deletion requires stronger immediate suppression, treat it as a tombstone that also invalidates in-flight/historical serving. Do not blur routine source updates with security revocation.

### Cache eligibility

> Cache keys use a canonical, length-delimited serialization of the exact semantic request; effective source scope and versions; authorization and policy revisions; retrieval and generation configuration; endpoint; requested options; and request data classification. A cache hit remains subject to current eligibility and source authorization. Only validated eligible terminal answers may be cached. Private question/trace metadata is principal-scoped unless a deliberate sharing policy permits otherwise.

Hashing a concatenated string does not resolve ambiguous serialization. Hashing a question also does not anonymize its stored plaintext or make it appropriate for cloud export. Invalidation by a changed key is sufficient for source freshness only when every relevant dimension is in that key; it is not physical deletion.

### Answer modes and error reporting

| Mode | Required response behavior | Release evidence |
|---|---|---|
| Locate | Authorized distinct files with exact source locations; deterministic tie handling | File-level retrieval metrics and latency |
| Generated | Completed answer, authorized citations, declared validation status and model/config manifest | Faithfulness, citation completeness, usefulness, answer/refusal coverage |
| Refused | No generated factual claims; closest authorized evidence clearly labeled insufficient | Answerable/unanswerable confusion matrix |
| Extractive | Authorized passages; explicit notice that generation was unavailable or unsupported | Citation/source integrity and correct degraded outcome |
| Failed after streaming | Typed terminal error or explicit reset/replacement protocol; partial answer not reusable | Partial-provider-failure and reconnect tests |
| Rejected before work | 429 or 503 with bounded retry instructions, counted in availability/admission reporting | Rate-limit/admission tests |

The ask TTFT SLO must say whether it applies only to generated answers. Extractive/refusal responses may not emit any `token` event; give them a time-to-terminal-response objective rather than silently omitting them from measurements. Report all outcome denominators.

### Recovery and deletion

> Recovery success means the named service capability is usable, verified by a known search and authorization probe. Empty-index readiness is not search recovery. Restores begin with cached permissions invalid, deleted-source tombstones reapplied, and index pointers either valid or explicitly absent. Deletion guarantees distinguish immediate exclusion from serving, removal from active data stores, derivative retention, and backup expiry.

For the MVP, choose either a measured full-index backup/restore that meets one hour, or publish a longer full-corpus RTO and retain one hour only for the narrower verified capability. Do not silently redefine RTO after an incident.

## Continuous and rigorous verification mechanism

The original §16 is a good starting structure. The missing mechanism is a protected chain from each critical requirement to an executable test and from each release to immutable evidence. The implementation repository should contain a versioned requirements/test manifest, required CI checks, an approved baseline manifest, and release reports. These are required implementation deliverables; this review does not claim to have installed them in a repository that was not attached.

### Required execution schedule

| Cadence | Required suite | Blocking rule | Artifact to retain |
|---|---|---|---|
| Every PR | Unit/property tests; SQL/HTTP/config contracts; deterministic output parsing | Any violated invariant or invalid contract blocks merge | Seed, failing case, code/config manifest |
| Every PR | Full deterministic permission suite, including mutation sequences and independent oracle | Any unauthorized disclosure, stale-denial resurrection, or disallowed egress blocks merge; no statistical waiver | Redacted event history and reproducible fixture |
| Every relevant PR | Pinned Postgres + pgvector + pg_search + River integration | Any activation, FK/GC, job-loss, migration, or retry failure blocks merge | Extension versions, query plans, transition log |
| Every relevant PR | Retrieval baseline/candidate comparison on identical dev data | Existing two-point/significance rule plus large-uncertain-change review; zero security regressions | Per-query metrics, paired differences, cache manifest |
| Every relevant PR | Deterministic generation-mode tests using a stub | Invalid citation protocol, partial-answer caching, unsafe provider routing, or missing terminal event blocks merge | Normal/refusal/extractive/failure transcripts |
| Every PR | Browser smoke: login, search, ask, final citations, logout; scanner checks | Critical flow or exposed-secret failure blocks merge | Redacted browser test report |
| Nightly | Larger seeded state-machine runs, webhook reorder/replay, longer integration and full dev evaluation | Failure blocks release and opens a tracked issue; reproduce with retained seed | Nightly report and minimized counterexample |
| Budgeted scheduled run | Real-model faithfulness/refusal/injection checks on dev/canary examples | A safety failure disables the affected generated-answer mode; a quality regression needs review | Model IDs, prompts, authorized evidence, human/judge labels, spend |
| Before a release | Exact candidate images: L1/L2/L5/L6, relevant soak/breakpoint results, migration/rollback, restore drill | Release requires the actual promised SLOs and every protected invariant | Signed-off release manifest/report, not only screenshots |
| After each deployment | Public and private synthetic search; cache; revoke; source update; provider fallback smoke | Security failure stops affected serving immediately; functional failure triggers defined rollback | Deployment ID and probe history |
| Continuously | Request outcomes, permission-denial age, freshness, queue age, exporter health, resource usage, spend | Alert on explicit thresholds; security breach is stop-the-line | Unsampled counters and bounded audit events |
| Weekly / on dependency change | Provider terms/model availability/quotas; extension/runtime compatibility; backup restore spot check | Unknown data terms disable that egress route; incompatible dependency blocks deployment | Updated dependency verification ledger |

“Relevant PR” includes code, SQL, prompts, model/template/config files, lockfiles, test fixtures, provider policy, and deployment settings that can affect the behavior. It must not mean only files under a directory named `retrieval/`. Provide a cheap always-running dispatcher/check that verifies the necessary suites ran; required checks cannot be bypassed by an accidental path-filter skip.

Do not require paid model calls for all 50,000 permission cases. Exercise those deterministically with recording transports and a stub. Allocate a small explicit monthly live-model budget for injection and quality canaries, in addition to the two planned evaluation cycles. Every paid run records a reserved maximum spend before dispatch. If the live-model budget is exhausted, preserve deterministic/security CI and explicitly mark live quality evidence stale.

### Minimum critical test inventory

| Test ID | Scenario | Independent expected result | Findings |
|---|---|---|---|
| AUTH-01 | User never had private access | No forbidden source data in any output or provider payload | 01–04 |
| AUTH-02 | Revoke via delivered webhook; GitHub refresh then fails | Negative event blocks access within the delivered-event bound | 02 |
| AUTH-03 | Revoke with webhook dropped | All subsequent disclosure ceases by the authority deadline | 01–02 |
| AUTH-04 | Public→private, unchanged SHA, dropped webhook | Anonymous cache/search/trace cannot outlive the visibility lease | 01 |
| AUTH-05 | Installation suspend/delete/repo removal during build | Immediate serving denial; build cannot reactivate eligibility | 01, 08 |
| AUTH-06 | Old refresh completes after newer deny | Older result cannot restore grants or renew authority | 02 |
| AUTH-07 | Paginated grant refresh fails midway | No partial-success lease and no retained stale private grant | 02 |
| AUTH-08 | Revoked owner reopens historical answer/trace | Current source authorization is enforced | 04 |
| AUTH-09 | Two anonymous visitors exchange answer IDs | No shared-null-principal authorization | 04 |
| AUTH-10 | Grant expires during long SSE stream | No disclosure beyond the agreed bound | 04 |
| AUTH-11 | Session/token revoke across two workers | Agreed revocation behavior holds in both processes | 23 |
| EGRESS-01 | Confidential sentinel only in query, public passages | No sentinel in disallowed providers or telemetry | 03 |
| EGRESS-02 | Mixed-installation provider allowlists | Only an intersection-approved provider, or extractive answer | 03, 12 |
| EGRESS-03 | Exception/debug/feedback/rewrite path | Same classification policy as primary request | 03 |
| INDEX-01 | Same exact text; changed model/template | New compatible representation; old active one remains intact | 05 |
| INDEX-02 | Rename / identical body in two paths | Correct headers, locations, and source citations | 05, 24 |
| INDEX-03 | Two builders finish in reverse desired order | Obsolete build cannot regress the active generation | 08 |
| INDEX-04 | Worker heartbeat expires then worker resumes | Invalid build fence prevents activation | 08 |
| INDEX-05 | Push at each River completion boundary | Latest desired generation eventually serves | 07 |
| INDEX-06 | GC with retired refs and a concurrent reuse | No FK failure/data loss; unreachable data eventually removed | 06 |
| INDEX-07 | Force-push with missing shallow ancestor | Correct bounded resnapshot/diff; no partial activation | 19 |
| INDEX-08 | Repo deletion/uninstall followed by backup restore | Tombstone remains effective; no resurrection | 01, 06, 18 |
| INPUT-01 | Hostile size/path/symlink/parser fixtures | Bounded processing; no source execution or secret exposure | 19 |
| RETR-01 | Nearest global vectors all forbidden | Matches filtered exact oracle, zero forbidden outputs | 13 |
| RETR-02 | Relaxed ordering/ties/underfilled ANN | Stable legal ordering and documented fallback | 25 |
| RETR-03 | Future snapshot sentinel | Retrieval remains within the selected historical snapshot | 14 |
| RETR-04 | Identical rank agreement on relevant/irrelevant questions | Evidence gate does not equate rank agreement with support | 10 |
| GEN-01 | Unknown marker split across token boundaries | Correct buffering or canonical repair contract | 09 |
| GEN-02 | Valid marker on contradicted/unsupported claim | Quality evaluation detects failure; ID validity alone cannot pass | 09 |
| GEN-03 | Provider failure after partial output | Typed terminal/reset behavior; no reusable partial answer | 11 |
| GEN-04 | Disconnect/retry/slow consumer | Bounded work, connection release, explicit idempotency | 11 |
| GEN-05 | Tokens/daily/spend exhausted but RPM available | Correct bounded fallback without retry storm | 12 |
| MODE-01 | Ollama/reranker/provider unavailable independently and together | Declared mode, safe evidence gate, minimum service remains ready | 10, 26 |
| LOAD-01 | Cold versus warmed versus Zipf, realistic query lengths | Hit rates and mode-specific throughput reported | 16–17 |
| LOAD-02 | Fixed offered rate with ingestion and maintenance | Absolute SLOs, not only relative slowdown, hold | 16–17 |
| LOAD-03 | One laptop IP, 1,000 synthetic users | Explicit test policy; rate-limit rejection not miscounted as service | 16 |
| OPS-01 | Empty-host restore with lost key/index | Measured recovery milestone and explicit credential behavior | 18 |
| OPS-02 | Bad readiness/optional dependency outage/migration rollback | Capability-aware health and safe rollback behavior | 23, 26 |
| OPS-03 | Exporter outage, error storm, disk pressure | Serving control/audit writes remain bounded and functional | 26 |
| CI-01 | Bad prompt/config/parser/dependency change | Correct required tests run and block the regression | 15, 29 |
| CI-02 | Multiple small retrieval regressions | Approved-release baseline exposes cumulative drift | 15 |

State-machine testing should generate sequences, not just independent calls: grant, refresh, query, switch, cache, revoke, refresh completion, stream, delete, restore. Compare the implementation to a small reference model whose grant/source history is controlled by the test. That reference model must not call the production permission resolver to decide whether the production resolver was correct.

For the 50,000-case suite, preserve seeds and mutation schedules, and minimize failures into a small regression fixture. A nondeterministic failure is not fixed by rerunning until green. Browser, fault, and provider tests should have bounded deadlines and clear retry rules; test-runner retries must not hide product retries or duplicated charges.

### Proposed protected release checklist

- [ ] WF-01 through WF-04 closed with independently checked mutation/egress tests before real private data is permitted.
- [ ] Pinned River scheduling proof, embedding-identity migration, activation fencing, and real FK/GC tests pass.
- [ ] V1 source scope, corpus acquisition method, and typed citation contract match the user-facing claims.
- [ ] Baseline and candidate run on identical verified historical datasets; final held-out status is declared truthfully.
- [ ] Every shipped degraded mode has a security test, a latency outcome, and either quality evidence or an extractive-only policy.
- [ ] Cold and warm capacity reports identify model/config, cache ratios, accepted outcomes, query lengths, corpus size, and host limits.
- [ ] Restore, deletion, and session/permission revocation meet their explicitly stated bounds.
- [ ] Source/provider policy and actual account quotas are recorded; infrastructure plans remain within the allowed resource envelope.
- [ ] CI required checks protect the exact release commit, and no missing/scoped-out check is reported as executed.
- [ ] Outstanding P1s affecting an advertised capability either close or remove that capability/claim from the release.

The author owns implementation and the test manifest. A named external reviewer can review evidence and make a launch recommendation; until then, mark sign-off as self-review. Security failures block the affected capability automatically rather than waiting for the next weekly gate.

## Quantitative verification performed for this review

These are recalculations and small design models, not production benchmarks.

| Item | Recalculated result | Assessment |
|---|---|---|
| Mean response time assumed in workload | `0.7×0.5 + 0.3×8 = 2.75 s` | Correct under the assumptions; 0.5 s is used as a mean estimate even though the SLO itself is a percentile |
| Nominal throughput | `1000 / 32.75 = 30.534 req/s` | Draft's ~30.5 is correct |
| Nominal split | 21.374 search/s; 9.160 ask/s | Draft rounding is reasonable |
| Nominal active asks | `9.160×8 = 73.28` | Draft's ~74 is reasonable |
| Stress throughput | `1000 / 12.75 = 78.431 req/s` | Draft's ~78 is correct |
| Stress active asks | `0.3×78.431×8 = 188.24` | Exceeds the 150-total ask admission limit; stress rejection is expected |
| Short-rerank CPU at nominal, no cache | About 1.634 core-s/s using unrounded rates | Approximately 82% on two cores, before omitted/background work |
| No-rerank CPU at nominal | About 0.901 core-s/s | Approximately 45%; still a planning model |
| Memory allocations | 12.0 GB | Arithmetic correct; does not prove actual peak fits |
| Haiku ask at stated token counts | `$0.005 + $0.002 = $0.007` | Correct at the verified listed prices |
| Paid nominal generation/hour | About $230.84 using unrounded workload; $231.84 with 9.2/s | Draft's ~$232/hour is correct |
| Core evaluation cycle | `$0.84 + $0.36 + $0.22 = $1.42` | Draft's ~$1.45 is harmless rounding, not a substantive error |
| Nominal input-token throughput | About 2.75M input tokens/minute before hits/fallback | Must be checked against token quotas, not RPM alone |
| Top dual-leg RRF score, k=60 | `2/61 ≈ 0.0327869` | Unchanged if absolute relevance changes but ranks do not |
| Uniform 2,000-query pool | Entire pool fits each 10,000-entry cache | Cannot represent sustained cold query embeddings; in a simple no-eviction/no-duplicate-fill model, at most 4,000 worker-key warmups over ~55,000 requests |
| 18/20 success, Wilson 95% interval | Approximately 0.699–0.972 | A 0.90 point estimate has substantial uncertainty |
| 16/20 success, Wilson 95% interval | Approximately 0.584–0.919 | Same issue for an 0.80 refusal point estimate |

The published availability target permits about 7.2 hours of downtime in a 30-day month. That is compatible with a deliberately non-HA demo, but it does not make the one-hour RTO feasible or establish achieved availability. An unavailable A1 allocation remains a deployment dependency, not a number an arithmetic model can verify.

The ~8-second ask-time assumption is conservatively rounded from the listed components, which sum to 7.4 seconds. Cache hits and quick extractive responses shorten mean response time and thus increase offered throughput in a closed-session model; rerun the model with observed outcome proportions rather than holding 30.5 req/s fixed for every degradation scenario.

### Executed small counterexamples

1. A minimal relational schema with `UNIQUE(repo_id, content_hash)` and the specified conflict behavior retained the old embedding when a new model attempted to insert the same content.
2. A minimal FK schema refused to delete a chunk still referenced by a retired version membership.
3. A short state model allowed an older target to activate after a newer target when CAS failure was followed by recomputing the base and retaining the old target.
4. Permission reference models showed why enqueue-only revocation can exceed 60 seconds during refresh failure, why a user-grant TTL does not bound an unconditional public-repository union, and how an authorization revision rejects a stale refresh result.
5. Query normalization mapped distinct string-literal queries (`"a  b"` versus `"a b"`) to the same collapsed-whitespace text, confirming the need to preserve code semantics.

The first two models used in-memory SQLite solely for the shared uniqueness/FK mechanics. PostgreSQL, pg_search, pgvector, River, model inference, GitHub webhooks, and Wayfinder code were not run. No PostgreSQL client or Docker executable was available in this workspace. The relevant real-system tests are explicitly listed above rather than being inferred from these models.

## External-fact verification ledger

Status is as observed during this review on 2026-09-18. A verified public document does not establish this user's account entitlement. Sources below are primary documentation, maintainer repositories, or explicitly qualified vendor-hosted discussions. Secondary articles from the original Appendix B were not treated as authoritative when a primary source was available.

| Claim/dependency | Review result | Source and follow-up |
|---|---|---|
| Oracle A1 baseline | Current primary page supports 1,500 OCPU-hours and 9,000 GB-hours/month, equivalent to 2 OCPU/12 GB for Always Free | [Oracle resources](https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm). Historical change date and extra PAYG allowance were not established; retain as unverified. |
| Oracle idle reclamation | The listed seven-day CPU/network/memory criteria are supported | Same [Oracle page](https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm). Actual host survival and spare capacity remain unverified. |
| Oracle storage/AMD micro/egress | Primary page lists the resource allowances used for planning | Same [Oracle page](https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm). Inventory both hosts and actual boot/data/backup resources in S3. |
| Oracle budget protection | Budget is a soft spending threshold, not an automatic resource/spending stop | [Oracle Budgets](https://docs.oracle.com/en-us/iaas/Content/Billing/Concepts/budgetsoverview.htm). Correct Q-4's implied safeguard. |
| GitHub user-visible repositories | The selected installation/user endpoint is appropriate; pagination is required | [GitHub installation API](https://docs.github.com/en/rest/apps/installations#list-repositories-accessible-to-the-user-access-token). Contract-test complete enumeration. |
| GitHub App PKCE | Supported in the current documented web flow | [User access tokens](https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app/generating-a-user-access-token-for-a-github-app). Do not flag it as unsupported based on older documentation. |
| Expiring user tokens | Eight-hour user token, six-month refresh token; rotation invalidates the old pair | [Refreshing tokens](https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app/refreshing-user-access-tokens). Concurrency control still required. |
| GitHub `team` and `member` events | Read-level organization Members permission is documented for these events | [Webhook reference](https://docs.github.com/en/webhooks/webhook-events-and-payloads). Build an action-by-action lifecycle matrix, including app authorization and installation events. |
| GitHub webhook delivery | Ten-second response bound; failed deliveries are not automatically redelivered | [Failed deliveries](https://docs.github.com/en/webhooks/using-webhooks/handling-failed-webhook-deliveries). The async acceptance pattern is appropriate. |
| GitHub account limit | One free personal account plus one permitted machine account is supported | [GitHub Terms](https://docs.github.com/en/site-policy/github-terms/github-terms-of-service). Synthetic test identities remain appropriate. |
| Third-party app installation | App installation is permissioned, not implied by public repository access | [Installation rules](https://docs.github.com/en/apps/using-github-apps/installing-a-github-app-from-a-third-party). Choose a corpus acquisition mode. |
| River waiting-only uniqueness | Conflicts with current documentation requiring running among custom uniqueness states | [Unique jobs](https://riverqueue.com/docs/unique-jobs). Pin version and prove the successor scheduling protocol. |
| pgvector features | Iterative scans and HNSW halfvec/vector dimension limits are supported; changelog documents introduction history | [README](https://github.com/pgvector/pgvector), [changelog](https://github.com/pgvector/pgvector/blob/master/CHANGELOG.md). Validate exact SQL plans on the pinned extension. |
| ParadeDB BM25/transactions/license | Maintainer repository supports BM25, ACID positioning, and AGPL-3.0 labeling | [ParadeDB](https://github.com/paradedb/paradedb). Actual Arm image/extension versions, privileges, MVCC test, and distribution obligations still need the pinned-artifact review; no blanket legal compatibility conclusion is made here. |
| Ollama candidate availability | All three named model families are listed, including Qwen3 embedding 0.6B | [Nomic](https://ollama.com/library/nomic-embed-text), [EmbeddingGemma](https://ollama.com/library/embeddinggemma), [Qwen3 embedding](https://ollama.com/library/qwen3-embedding). Availability does not verify capacity or exact dimensions/configuration. |
| Embedding preprocessing | Nomic documents query/document task prefixes; Ollama can truncate by default | [Model card](https://huggingface.co/nomic-ai/nomic-embed-text-v1.5), [embed API](https://docs.ollama.com/api/embed). Include templates and truncation policy in manifests. |
| Haiku 4.5 / Sonnet 5 pricing | $1/$5 and $2/$10 per million input/output tokens are supported; Batch halves these rates | [Anthropic pricing](https://platform.claude.com/docs/en/about-claude/pricing), [model IDs](https://platform.claude.com/docs/en/models/overview). Pin a concrete supported ID in the release. |
| Anthropic data policy | Commercial inputs/outputs are not used for training by default, with documented exceptions | [Commercial-data policy](https://privacy.claude.com/en/articles/7996868-is-my-data-used-for-model-training). Organization approval and retention review remain separate. |
| Gemini free-tier data use | Conservative prohibition on private-data routing is supported by the unpaid-service terms | [Gemini terms](https://ai.google.dev/gemini-api/terms). Account/region/billing context must be recorded before broad assertions about all usage. |
| Aggregated free LLM throughput | Not verified for the account; should not be a guaranteed capacity input | [Gemini limits](https://ai.google.dev/gemini-api/docs/rate-limits), [Groq limits](https://console.groq.com/docs/rate-limits). Record RPM, token and daily limits, plus available model IDs. |
| NVIDIA ~40 RPM | Original vendor-forum reference was reachable, but a universal current quota/entitlement was not established | [Referenced NVIDIA discussion](https://forums.developer.nvidia.com/t/request-additional-api-credits-rate-limit-increase-for-build-nvidia-com-free-tier/379569). Keep S4 open; the attempted formal API-catalog documentation path did not resolve. |
| Langfuse Hobby | Official pricing supports 50k units/month, 30-day access, two users | [Langfuse pricing](https://langfuse.com/pricing). Exact billable-unit accounting/hard-cap behavior was not established by the retrieved page text; verify in S4 and observe actual ingestion. |
| Grafana free retention | Official pricing supports 14-day retention for free logs/traces with volume limits | [Grafana pricing](https://grafana.com/pricing/). Include volume/cardinality, not retention alone. |
| Sentry | Official pricing page available; project-specific quotas/settings not verified | [Sentry pricing](https://sentry.io/pricing/). Set actual event/replay limits; content scrubbing needs tests. |
| Cloud Run fallback | Free allowances exist, but compute/network beyond them are billable | [Cloud Run pricing](https://cloud.google.com/run/pricing). Do not infer free sustained 1,000-user service. |
| Neon fallback | Pricing pages did not resolve through the available fetch route | Leave account quotas, supported extensions, and fallback cost unverified; do not treat the option as production-ready. |
| k6 SSE transport | Maintainer example demonstrates POST streaming; closed-loop throughput limitation is documented by k6 | [xk6-sse](https://github.com/phymbert/xk6-sse), [k6 workload models](https://grafana.com/docs/k6/latest/using-k6/scenarios/concepts/open-vs-closed/). Pin and test the extension version. |
| Public CI / artifacts | The project still needs measured runner time, architecture, cache footprint, and artifact limits | [Actions limits](https://docs.github.com/en/actions/reference/limits), [secure use](https://docs.github.com/en/actions/reference/security/secure-use). A public source repository does not eliminate all artifact/resource constraints. |

DuckDNS availability, domain ownership, certificate issuance on the target network, specific repository-license applicability to mined discussion data, managed fallback database features, and the illustrative AWS/GPU alternatives were not verified against an account or a final artifact. They are not necessary to validate the primary architecture; record them as deployment/legal/estimate checks rather than reusing the Appendix B heading “Checked” as if every dependency were confirmed. Review source licenses and attribution for the actual selected files/datasets; this report does not provide a license opinion.

## Requirement and section coverage

### Functional requirements

| Requirement | Disposition for v0.3 |
|---|---|
| FR-01 | Keep code/docs core; declare public-corpus acquisition; mark threads conditional (WF-19–21) |
| FR-02 | Keep AST/heading chunking; define coverage, limits, language fallback (WF-24) |
| FR-03 | Keep atomic activation; add representation identity and fencing (WF-05, 08) |
| FR-04 | Keep incremental changes; add missing-history and hostile-input paths (WF-07–08, 19) |
| FR-05 | Keep source reconciliation; distinguish six-hour repair from push freshness and shorter authorization leases (WF-01, 07) |
| FR-06 | Keep measured hybrid retrieval; fix filtered baseline and stable ranking (WF-13, 25, 28) |
| FR-07 | Keep SQL predicate; include lifecycle eligibility and independently checked current grants (WF-01–04) |
| FR-08 | Specify provisional/final citation semantics and supported answer modes (WF-09, 11) |
| FR-09 | Replace unqualified RRF answerability assumption; validate each degradation mode (WF-10) |
| FR-10 | Keep GitHub login; define anonymous ownership and lifecycle (WF-04, 23) |
| FR-11 | Synchronous negative invalidation, versioned refresh, full pagination, public metadata expiry (WF-01–02) |
| FR-12 | Classify full request; enforce policy intersections, deadlines, tokens and spend (WF-03, 12) |
| FR-13 | Canonical key plus policy/source dependencies; terminal-state cache eligibility (WF-04, 11–12) |
| FR-14 | Current authorization on historical traces; bounded storage/export (WF-04, 26) |
| FR-15 | Principal ownership, retention, abuse bounds, and private-data export policy (WF-03–04, 11) |
| FR-16 | Explicitly conditional on MCP being promoted; then full token lifecycle and same invariants (WF-23, 30) |
| FR-17 | Numeric policy, shared-IP fairness, endpoint budgets, and load-test accounting (WF-12, 16–17) |
| FR-18 | Keep harness; fix historical protocol, reference oracle, and release gates (WF-13–15, 28–29) |

### Non-functional requirements

| Requirement | Disposition for v0.3 |
|---|---|
| NFR-01 concurrency | Target until measured; publish actual request mix/cache/outcome rates (WF-16–17) |
| NFR-02 search latency | Keep target; apply absolute bound during reindex and define cache/outcome measurement (WF-17, 26) |
| NFR-03 ask latency | Separate total/stage timing and generated versus extractive/refused outcomes (WF-12, 30) |
| NFR-04 freshness | State ordinary-push target and missed-event repair bound separately; retain a continuous probe (WF-07, 22, 26) |
| NFR-05 revocation | Include visibility, lifecycle, history, and in-flight paths (WF-01–04) |
| NFR-06 leakage | Hard invariant with independent stateful tests; no probabilistic waiver (WF-15–16, 28) |
| NFR-07 availability/recovery | Capability-based availability and measured restore targets (WF-18, 26) |
| NFR-08 cost | Account-specific allowed resources plus real provider cap/budget behavior (WF-12, 27) |
| NFR-09 security | Add source ingestion, privileges, token/session lifecycle, and CI trust boundaries (WF-19, 23) |
| NFR-10 privacy | Full request and derivative classification, not repository labels alone (WF-03) |
| NFR-11 maintainability | Coverage supports, but does not replace, invariant tests; keep named ownership (WF-15, 22) |
| NFR-12 reproducibility | Full pipeline/data/artifact manifest; exact scope and tolerance (WF-29) |
| NFR-13 portability | Run actual pinned native dependencies on each claimed platform (WF-29) |
| NFR-14 accessibility | Keep browser smoke and keyboard/streaming checks; contrast alone is not full WCAG conformance (WF-22) |
| NFR-15 observability | Unsampled essential counters/audit plus sampled detail and explicit SLI math (WF-26) |

### Section-by-section review map

| Source section | Review conclusion |
|---|---|
| 1. Executive summary | Clear architecture thesis; narrow source scope and soften unmeasured/absolute guarantees (WF-09, 17, 21, 30) |
| 2. Problem | Coherent portfolio motivation; add task-based outcome evidence and avoid broad competitor claims (WF-28, 30) |
| 3. Goals/metrics | Good measurable intent; align denominators, uncertainty, modes, recovery and scope (WF-09, 17–18, 28) |
| 4. Stakeholders/RACI | Honest simulated personas; name actual decision owners and self-review status (WF-22, 30) |
| 5. Stories | Most are testable; reconcile historical rationale, artifact access, and deletion boundaries (WF-04, 06, 20–21) |
| 6. Requirements | Covered individually above; no blanket claim that security/testing requirements are absent |
| 7. Assumptions | A-1 capacity and A-3 dataset yield remain unverified; A-2 actual allocation, A-4 CPU, A-5 image behavior, A-6 quotas require spikes; A-7 is a scope decision (WF-17, 20, 22, 27) |
| 8. Architecture | Keep read/write split and one transactional store; clarify access-refresh owner and two embedding processes (WF-02, 30) |
| 9. Detailed design | Principal concentration of findings: security lifecycle, representation identity, queue semantics, deletion, generation, APIs (WF-01–12, 19–25) |
| 10. Capacity | Arithmetic checked; resource estimates and overload utility need measurements (WF-16–17) |
| 11. Cost | Per-ask math checked; account quotas, private-demo scope, token limits, and fallback costs remain conditional (WF-12, 27) |
| 12. Stack/ADRs | Reasonable bounded choices; pin exact native artifacts and resolve consequential ADRs before coding (WF-07, 23, 29) |
| 13. Security/privacy | Substantial existing controls; full request classification, retained artifacts, hostile ingestion, and administrative authority need closure (WF-01–04, 19, 23) |
| 14. Corpus/datasets | Good provenance intent; installation constraints and temporal/label validity need a concrete protocol (WF-14, 20–21, 28) |
| 15. Evaluation | Strong paired-comparison approach; fix E7 and held-out/judge/uncertainty interpretation (WF-13–15, 28) |
| 16. Testing | Broad layers already present; add independent mutable oracle, mode tests, protected triggers, and cold/open-loop cases (WF-15–16) |
| 17. Operations | Keep probes/runbook; recovery, readiness, export limits and true SLO denominators need correction (WF-18, 26) |
| 18. CI/CD | Keep exact-image release evidence, immutable artifacts, and rollback; strengthen trust and platform profiles (WF-23, 29) |
| 19. Delivery | Zero buffer and safety-test cuts are not acceptable unchanged; scope down with explicit dependent changes (WF-22) |
| 20. Risks | Add stale public visibility, refresh races, model identity, River mismatch, restore/deletion resurrection, and full-prompt disclosure; rescore security likelihood after tests |
| 21. Alternatives | No need for distributed redesign; managed fallback is a new tested option, not guaranteed free capacity (WF-27) |
| 22. Approval | Approve only concrete scope and evidence; separate prototype approval from private-data launch (protected checklist above) |
| Revision history | Credited the fixes in v0.2; some intended fixes still lack executable contracts, especially queue completion and GC |
| Appendix A | Mostly sound glossary; narrow “index snapshot at commit” to git sources and explain rule-of-three assumptions (WF-21, 28) |
| Appendix B | Primary facts rechecked in the ledger; unknown account terms remain explicitly unverified |
| Appendix C | Layout is workable; add manifest/evidence locations within existing `eval/`, `loadtest/`, `docs/`, and CI folders rather than more services |

## Recommended implementation order and next review

1. **Freeze the v1 product contract.** Code and Markdown first; explicitly identify the public upstream/mirror connector mode; define generated, refused, and extractive answers. Keep historical thread rationale out of the Must scope unless re-estimated.
2. **Prove the safety and consistency kernel before the UI.** Repository eligibility leases, atomic negative invalidation, fenced refresh, correct representation identity, actual River successor scheduling, and FK-safe GC. Use only public and synthetic data until the P0 suite passes.
3. **Build one complete vertical path.** Install/select source → index → authorized search → source citation → cache → revoke → deny → delete → restore. Include the minimal browser flow and observability from the start.
4. **Establish trustworthy measurements.** Historical data protocol, authorized exact oracle, dense/BM25/hybrid baselines, full manifests, cold/warm whole-system CPU, and mode-specific quality.
5. **Add bounded generated answers.** Full-input classification, approved provider route, complete answer state machine, deadlines/quotas, and safe streaming. Keep extractive answers when quality or provider guarantees cannot be met.
6. **Run release evidence on the exact candidate.** Mutation suite, load profiles, failure injection, migration/rollback, restore, and documented account limits. Make the final README claims match the observed result.

The next review should receive v0.3 plus five concrete artifacts: the permission state-machine tests; the pinned River/activation/GC integration results; a dataset manifest and label audit; a real capacity report with cache and degradation ratios; and a restore/deletion drill report. Those artifacts resolve the key uncertainties much more effectively than adding further diagrams or framework choices.
