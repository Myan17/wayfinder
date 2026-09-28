# ADR-0016 — Two source modes, and the acceptance rules for spike S1

- **Status:** Proposed. **The decision is deliberately empty**; spike S1 fills it.
- **Date written:** 2026-09-28, **before** S1 measures any candidate.
- **Decides:** the public read-only corpus of `DESIGN` §14.1, assumption A-3 (§7.1), and risks R-03
  and R-14 (§20). DESIGN §12 lists this ADR as "Two source modes: installation and public
  read-only". The modes are already designed; this ADR records the evidence that makes the public
  mode usable.
- **Builds on:** ADR-0013. Its dataset rules D-1 to D-7 decide which pairs survive. This ADR
  decides which repositories they are mined from.

## Why this document exists before the experiment

For the same reason as ADR-0004 and ADR-0007. If the candidates and thresholds are chosen after
looking at the data, S1 cannot fail: a repository that yields few pairs is quietly swapped for one
that yields many, and the criteria drift toward whatever the run produced. So the candidates, the
criteria and the selection rule merge first. The miner and its results come in later pull
requests.

## The two modes (DESIGN §14.1, unchanged)

- **`public_readonly`**: read-only clone plus GitHub REST/GraphQL metadata for upstream repositories
  whose organizations the author does not control. No App installation (WF-20). S1 tests this mode.
- **`installation`**: the GitHub App on the author's own organization, including one private and
  one synthetic repository. It is not measured by S1.

## Candidates, fixed before measurement

The list is closed. A repository not on it cannot be selected by S1. Widening it is R-03's
fallback (below) and needs a new pull request that states why.

| Language | Repositories (checked only to exist and be unarchived on 2026-09-28) |
|---|---|
| Python | `pallets/flask`, `pallets/click`, `encode/httpx`, `psf/requests`, `python-attrs/attrs` |
| Go | `spf13/cobra`, `go-chi/chi`, `urfave/cli`, `gin-gonic/gin`, `charmbracelet/bubbletea` |

**As-of time.** Every measurement uses PRs merged before **2026-09-28T00:00:00Z**, the default
branch at the last commit before that instant, and license and repository metadata as returned on
the day S1 runs. The manifest records the as-of time and each repository's commit.

## Per-candidate rules

A candidate **qualifies** only if it passes all of the following. Each result is recorded,
including failures, with the measured value.

| # | Rule | How it is measured |
|---|---|---|
| S1-1 | **Permissive license** | The repository's SPDX id, read from the license file in the clone and cross-checked against the GitHub API, is one of MIT, BSD-2-Clause, BSD-3-Clause, Apache-2.0 or ISC. A mismatch between the two sources fails the rule |
| S1-2 | **At least 100 linkable pairs** | Merged PRs (before the as-of time) with a non-empty `closingIssuesReferences` to an issue in the same repository, counted as (issue, PR) pairs **before** ADR-0013's filters |
| S1-3 | **Base commits resolve** | For every S1-2 pair, the parent of the PR's first commit (ADR-0013 D-1) exists in the clone, including commits from fork PRs through `refs/pull/*/head`. The rule passes if **at least 95%** resolve. Unresolved pairs are excluded with the reason (D-6) |
| S1-4 | **Real Markdown documentation** | At least 5 `.md` files outside `CHANGELOG*`, `LICENSE*`, `.github/` and vendored paths, with at least 2,000 words among them, at the as-of commit |
| S1-5 | **Acquisition works read-only** | Every S1 read comes from a read-only clone and REST/GraphQL as an ordinary authenticated user, with no App and no write scope. S1 records the API calls used, and the rule fails if any read needed more access |

## Selecting the corpus

Among qualifying candidates, S1 chooses **3 or 4** repositories:

1. At least one Python and one Go repository.
2. The estimated total size is **no more than 60,000 chunks**. The chunker does not exist yet, so the
   estimate is fixed now: for each source and Markdown file at the as-of commit, `ceil(lines / 60)`,
   summed. Tests, vendored and generated paths are excluded, matching D-2's exclusions.
3. Within 1 and 2, maximise the **surviving pairs**, meaning pairs that pass ADR-0013 D-1, D-2 and
   D-3's strong set. Ties go to more repositories, then to the smaller total chunk estimate, then
   to the smaller sum of `github_repo_id`. It is an exhaustive search over the 3- and 4-subsets of
   qualifying candidates.

## The aggregate bar

**A-3 passes** if the selected corpus has **at least 300 surviving strong pairs** under ADR-0013
D-1 to D-3, before the temporal split (D-5).

**If it has fewer, R-03's fallbacks apply in this order, each only if the previous one still falls
short:**

1. Relax D-2's upper file count from 10 to 15 (R-03). The decision records how many pairs this adds.
2. Widen the candidate list. That is a new pull request that names the added candidates **before**
   measuring them, for the same reason as this document.

Neither fallback lowers the bar. If both are used and the corpus still falls short, S1 reports the
shortfall and A-3 fails. DESIGN §14.2's intervals are then published at the achieved size, which
ADR-0013 already allows.

## What S1 must deliver (the manifest)

A source manifest, **not a candidate list** (DESIGN §19.2), that satisfies ADR-0013's
consequences:

- Per candidate: S1-1 to S1-5 with the measured value and PASS or FAIL, and the chunk estimate.
- Per selected repository: `github_repo_id`, the as-of commit and the SPDX id.
- Per pair: issue and PR numbers, base commit, gold files, strong or weak, `group_id`, `t(g)` and
  split (D-5).
- Exclusion counts by reason (D-6), the API-call tally (S1-5), the as-of time, the miner's commit,
  and the file's SHA-256 (§14.5).

## Decision

*Empty until S1 runs.* It will be completed with one of:

- **Accept the corpus:** name the 3–4 repositories, quote each candidate's S1-1 to S1-5 results,
  the chunk estimate and the surviving-pair count, and state A-3 as passed.
- **Accept with fallback:** the same, naming which R-03 fallback was used and what it added.
- **A-3 fails:** quote the shortfall, and record the consequence for §14.2's intervals.
