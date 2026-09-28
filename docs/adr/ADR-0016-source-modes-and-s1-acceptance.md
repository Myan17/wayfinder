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
| S1-4 | **Real Markdown documentation** | At least 5 files in the chunk estimate's file universe (below) restricted to `.md`, meaning after all seven of its steps, test and generated exclusions included, with at least 2,000 whitespace-separated words among them, at the as-of commit |
| S1-5 | **Acquisition works read-only** | Every S1 read comes from a read-only clone and REST/GraphQL as an ordinary authenticated user, with no App and no write scope. S1 records the API calls used, and the rule fails if any read needed more access |

## The chunk estimate

The chunker does not exist yet, so the size estimate is fixed now. It is computed per candidate at
its as-of commit, over exactly this file universe:

1. **Tracked regular files.** Every path in `git ls-tree -r <as-of commit>` with mode `100644` or
   `100755`. Symlinks (`120000`) and submodules (`160000`) are excluded.
2. **Extensions.** Keep only `.py`, `.pyi`, `.go` and `.md`.
3. **Tests.** Exclude a path with a directory component `test`, `tests` or `testdata`, and a
   filename matching `test_*.py`, `*_test.py`, `*_test.go` or `conftest.py`.
4. **Vendored.** Exclude a path with a directory component `vendor`, `third_party` or `_vendor`.
5. **Generated.** Exclude `*_pb2.py`, `*_pb2.pyi` and `*.pb.go`, and any `.go` file whose first 10
   lines contain a line matching `^// Code generated .* DO NOT EDIT\.$` (Go's convention).
6. **Markdown.** Exclude files named `CHANGELOG*`, `CHANGES*` or `LICENSE*`, and anything under
   `.github/`. S1-4 counts exactly this universe's `.md` files, with no exception.
7. **Binary.** Exclude a file that is not valid UTF-8.

A file's lines are its count of `\n` bytes, plus 1 if it is non-empty and does not end in `\n`. The
file contributes `ceil(lines / 60)` chunks, and an empty file contributes 0. A candidate's estimate
is the sum over its files, and a corpus's estimate is the sum over its repositories. The manifest
records each candidate's file count and estimate.

## Selecting the corpus

Among qualifying candidates, S1 chooses **3 or 4** repositories. A subset is **feasible** if:

1. it has at least one Python and one Go repository, and
2. its chunk estimate is **at most 60,000**.

Among feasible subsets, S1 chooses by an exhaustive search over every 3- and 4-subset of qualifying
candidates. The comparison is a **total order**, applied key by key:

1. More **surviving strong pairs**: pairs that pass ADR-0013 D-1 and D-2 and are in D-3's strong
   set.
2. More repositories.
3. A smaller chunk estimate.
4. The lexicographically smaller **sorted tuple of `github_repo_id`s**. IDs are unique, so no two
   distinct subsets tie here. A sum of IDs would not guarantee that.

## The aggregate bar

**A-3 passes** if the selected corpus has **at least 300 surviving strong pairs** under ADR-0013
D-1 to D-3, before the temporal split (D-5). The weak set is always reported separately and never
counted (D-3, and R-03's last clause).

### When the corpus falls short: R-03, in DESIGN's order

Each step applies only if the previous one still falls short. Neither lowers the 300 bar.

1. **Widen the candidate list.** A new pull request names the added candidates **before** measuring
   them, for the same reason as this document. The new candidates are measured under S1-1 to S1-5.
   Selection then **re-runs from scratch** over every qualifying candidate, old and new.
2. **Relax D-2's upper file count from 10 to 15**, for every candidate. Surviving pairs are
   recomputed, and selection re-runs from scratch over every qualifying candidate. Qualification
   (S1-2 counts pairs before ADR-0013's filters) and the chunk estimates do not change.

The Decision records every selection round: its candidate set, its feasible subsets and the
winner.

### When no subset is feasible

This happens if fewer than 3 candidates qualify, or if no 3- or 4-subset of qualifying candidates
meets both feasibility conditions. S1 then records **"no feasible corpus"**, naming the constraint
that failed: the qualification count, the language mix or the chunk bound.

Relaxing D-2 cannot help, since it changes neither qualification nor size, so only step 1 (widen)
applies. If a widened list still has no feasible subset, **A-3 fails** with that reason. If the
cause is S1-5 (read-only acquisition), R-14's mitigation is recorded as well. In either failing
case, S1 still delivers the per-candidate measurements, and DESIGN §14.2's evaluation cannot start
until the corpus exists.

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
- **Accept with fallback:** the same, naming which R-03 step was used, what it added, and every
  selection round.
- **A-3 fails, short:** a feasible corpus exists but has fewer than 300 surviving strong pairs
  after both R-03 steps. Quote the shortfall and every selection round. §14.2's intervals are
  published at the achieved size.
- **A-3 fails, no feasible corpus:** name the constraint that failed, and record R-14 if the cause
  is acquisition.
