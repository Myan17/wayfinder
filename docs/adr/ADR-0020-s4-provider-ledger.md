# ADR-0020 — What spike S4 records about providers and accounts, and when it is done

- **Status:** Proposed. **The decision is deliberately empty**; spike S4 fills it.
- **Date written:** 2026-11-03, **before** any S4 lookup.
- **Decides:** how assumption A-7 (`DESIGN` §7.1) is tested, and the evidence behind the S4 rows of
  Appendix B, the provider rows of §11.1, the model IDs and prices of §11.2, and the data-terms
  approvals of §9.7.2.

## Why this document exists before the lookups

A ledger looks like transcription, but it hides choices. The choices include which source counts,
whether a documented free-tier limit counts as capacity, which quota window binds, and whether
unclear terms count as approval. Made after reading the pages, each choice can be bent to approve a
provider the routing chain already assumes. They are fixed here, so the sources decide.

S4 is a **record**, not a test the design can fail. A provider whose terms or limits cannot be
established is not "failed". It is recorded as unverified, and the consequence below applies to it.

## Scope (pinned)

The services are the ones that §11.1 and Appendix B already name. No other service is added by S4.

| Service | Tier S4 records | Used for (§11.1) |
|---|---|---|
| Anthropic API | The paid account that holds the ≤ $25 spend limit | Private-classified generation, evaluation, judging |
| Google Gemini API | Unpaid tier | Public-classified generation |
| Groq | Free tier | Public-classified generation |
| NVIDIA API catalog | Free tier | Public-classified generation |
| Langfuse Cloud | Hobby | Traces |
| Grafana Cloud | Free | Metrics |
| Sentry | Free (Developer) | Errors |

Oracle and GitHub facts stay with S3 and P1. They are not in S4.

## Fields (pinned)

**For each LLM provider, and for each model the routing chain would call:**

1. The model ID, exactly as the API accepts it.
2. Every quota window the provider enforces on this account: requests per minute, tokens per minute
   (input and output separately where the provider splits them), requests per day, tokens per day.
   A window the provider does not enforce is recorded as `none`, with the source that says so.
3. The price per million input and output tokens, and the batch price, for paid tiers only.
4. The data terms for the tier in use: whether inputs or outputs are used for training by default,
   the retention period, and whether humans may review content.
5. The spend control: whether a cap **stops** requests or only **alerts**, and the cap that is set.

**For each observability service:**

1. The unit the allowance is counted in, and the monthly allowance.
2. Retention.
3. What happens past the allowance: data is dropped, ingestion is blocked, or usage is billed.
4. The data terms for what is sent, under the same item 4 as above.

## Evidence classes

Every recorded value carries exactly one class, the date it was read, and its source.

- **`account`:** read from this project's own account. Either the provider's console page (the
  ledger names the page, and the value is typed in, never screenshotted) or the rate-limit
  headers of one live request (rule S4-4). Only this class establishes **entitlement**, as the
  Appendix B preface already requires.
- **`public`:** the provider's own primary documentation, pricing page or terms. It is recorded with
  its URL, the date it was retrieved, and the shortest sentence that states the value. It
  establishes what the provider **offers**, not what this account receives.
- **`unverified`:** anything else, such as forums, blogs, third-party aggregators, earlier versions
  of this document, or memory. Corroboration never upgrades a value from this class.

When an `account` value and a `public` value disagree, the `account` value is recorded and the
disagreement is noted. The lower of the two is used for capacity.

## Acceptance rules

- **S4-1 Completeness.** Every field above has a value and a class for every service in scope.
- **S4-2 Approval is mechanical** (§9.7.2), and is derived from item 4 with no judgement:
  - **Private-approved** only when a `public` or `account` source for the tier in use says
    inputs and outputs are not used for training by default.
  - **Public-approved** when the data terms are `public` or `account`, whatever they permit.
  - **Not approved** when the data terms are `unverified`. "Unverified terms mean not approved" is
    §9.7.2's rule. S4 applies it and does not soften it.
- **S4-3 Capacity is computed, not chosen.** For each model, capacity in asks per minute is the
  minimum, across every enforced window, of what that window allows at §11.2's ask shape (5,000
  input and 400 output tokens). A daily window is divided by 1,440 for the per-minute figure, and is
  also reported as asks per day. A field without an `account` or `public` value counts as zero.
  **Guaranteed** capacity is the part backed by a contractual commitment to this account. Documented
  free-tier limits are never a guarantee, so A-7's "guaranteed public generation capacity is zero"
  stands unless a provider's terms guarantee capacity.
- **S4-4 The live request is bounded.** A rate-limit header read sends one request per model, with
  the fixed synthetic text `Reply with the word OK.`, no repository content, and an output limit of
  16 tokens. Keys come from the environment, and only the allowlisted rate-limit header names and
  values are recorded. `myan` runs it, because the keys are his. It is optional: a console value
  is equally `account`.
- **S4-5 No secrets, no personal data.** No key, account ID, organization ID, email address or
  invoice is recorded. A console page is named by its menu path.
- **S4-6 The design moves with the ledger.** The results pull request updates, in the same revision:
  the S4 rows of Appendix B, with a class column; §11.1's provider rows; §11.2's model IDs and
  prices; §9.7.2's approved-provider sentences; and A-7. A model ID that has been retired is replaced
  in each of those, and the change is named.
- **S4-7 Values expire.** Values are dated, not permanent. P3's launch checklist re-reads every
  `account` value. Any value older than 30 days at release is re-read before it enters the release
  manifest.

## Decision

*Empty until S4 runs.* It will be completed with one of these:

- **Recorded:** the ledger table (every field, class, date and source); the approval set for private
  and public classification under S4-2; per-model capacity under S4-3; and A-7 marked **holds as
  written** or **restated**, with the restatement.
- **Incomplete:** a service could not be reached, or an account does not exist yet. Name it.
  Its fields are `unverified`, S4-2 and S4-3 apply to them as written, and S4 can still close.
  A missing account never blocks S4. It removes that provider from the chain until the account
  exists.
