# ADR-0016 — Two source modes, and the acceptance rules for spike S1

- **Status:** Accepted 2026-10-19 (#79). Spike S1's run 4 filled the Decision below; until then it
  was deliberately empty.
- **Date written:** 2026-09-28, **before** S1 measures any candidate. **Amended** 2026-10-04, still
  before any measurement (Amendment 1, below), and 2026-10-13 after round 1 fell short, before
  the added candidates are measured (Amendment 2, below).
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

## Amendment 1 — pull requests with a merge commit in their history (2026-10-04)

Ruled by gupta958 on #59, before the miner's runner exists and before any candidate is measured.

A pair's gold files come from the diff between its D-1 base and the PR's head commit
(`refs/pull/<n>/head`). If the PR merged another branch partway through, that diff also contains
other people's changes, and the gold labels would be wrong. Reconstructing "the PR's own" changes
is ambiguous, because merges, conflict resolutions, cherry-picks and rebases all blur it. So the
rule is conservative and deterministic:

- **The PR's commit history** is the set of commits reachable from its head commit and not from its
  D-1 base (`git rev-list <base>..<head>`).
- If that history contains **any commit with more than one parent**, the pair is **excluded** with
  reason **`merge_commit_in_pr_history`**.
- The check runs after D-1's base resolves and before D-2. A pair whose base did not resolve keeps
  S1-3's unresolved reason instead.
- The pair still counts toward **S1-2**'s linkable-pair total, which is taken before ADR-0013's
  filters, and toward **S1-3**'s base-resolution rate.
- It never enters the pairs file, gold labels, the D-5 split, the strong or weak counts, or A-3's
  300-pair bar. Its exclusion is counted under D-6 in the manifest's `exclusions`.

A linear PR, with no multi-parent commit in its history, is unaffected.

## Amendment 2 — R-03 step 1: ten added candidates (2026-10-13)

Written after S1's first run and before any added candidate is measured.

**Why (round 1).** S1 ran on 2026-10-13 at miner commit `331abcc`, over the ten candidates above.
At D-2's 10 files, 14 subsets were feasible. The winner was `urfave/cli`, `gin-gonic/gin`,
`python-attrs/attrs` and `encode/httpx`, with a chunk estimate of 997. It had **156 surviving strong
pairs, 144 short of A-3's 300** (urfave/cli 38, gin 11, attrs 19, httpx 88), plus 240 weak pairs,
which are never counted. R-03 step 1 therefore applies. Step 2 (D-2 at 15 files) does not apply
yet.

Two observations from round 1 shaped the choice. Neither is a measurement of the new candidates.

- **Size does not bind.** The winner uses 997 of the 60,000-chunk bound. Larger repositories fit.
- **Strong yield binds.** More pairs were weak than strong (240 against 156, D-3). A subset holds at
  most 4 repositories, so it needs about 75 strong pairs per repository. The added candidates are
  large, permissively licensed projects with long histories of pull requests that close issues.

**Added candidates.** As before, each was checked only to exist and be unarchived, on 2026-10-13.

| Language | Repositories |
|---|---|
| Python | `pytest-dev/pytest`, `pydantic/pydantic`, `psf/black`, `Textualize/rich`, `tox-dev/tox` |
| Go | `cli/cli`, `stretchr/testify`, `gofiber/fiber`, `prometheus/prometheus`, `spf13/viper` |

**Unchanged:**
- the as-of time (2026-09-28T00:00:00Z);
- S1-1 to S1-5;
- the chunk estimate;
- feasibility, the selection order, and A-3's 300 bar.

The runner appends these ten to its candidate list, after the original ten and in this order. That
is the only widening it accepts. Selection then re-runs from scratch over every qualifying
candidate, old and new. If that round is still short, R-03 step 2 runs over the same widened list.
The Decision records round 1 above together with every later round.

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

1. More **surviving strong pairs**: pairs that pass ADR-0013 D-1 and D-2, are not excluded by
   Amendment 1 (`merge_commit_in_pr_history`), and are in D-3's strong set.
2. More repositories.
3. A smaller chunk estimate.
4. The lexicographically smaller **sorted tuple of `github_repo_id`s**. IDs are unique, so no two
   distinct subsets tie here. A sum of IDs would not guarantee that.

## The aggregate bar

**A-3 passes** if the selected corpus has **at least 300 surviving strong pairs** under ADR-0013
D-1 to D-3 and Amendment 1, before the temporal split (D-5). The weak set is always reported separately and never
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

**Accept with fallback.** R-03 step 1 was used; step 2 was not needed. A-3 passes with **1,723
surviving strong pairs** against the bar of 300.

**The corpus.** It is `pydantic/pydantic` and `psf/black` (Python), and `cli/cli` and `gofiber/fiber` (Go).
Its chunk estimate is 7,175, against the bound of 60,000. All four come from Amendment 2's widened
list, so none of the original ten is selected.

| Repository | `github_repo_id` | As-of commit | SPDX | Strong | Weak | Strong by split (dev / test / held-out) |
|---|---|---|---|---|---|---|
| `pydantic/pydantic` | 90194616 | `bb6da4cf` | MIT | 667 | 229 | 326 / 194 / 147 |
| `psf/black` | 125266328 | `8d5a2d9f` | MIT | 215 | 46 | 107 / 64 / 44 |
| `cli/cli` | 212613049 | `9b031151` | MIT | 670 | 244 | 349 / 203 / 118 |
| `gofiber/fiber` | 234231371 | `e10bca73` | MIT | 171 | 86 | 95 / 51 / 25 |
| **Total** | | | | **1,723** | **605** | **877 / 512 / 334** |

The weak set (D-3, with ADR-0013 Amendment 1's 60 s window) is reported here and never counted.

**The run of record.** Run 4 was made on 2026-10-18 at miner commit `1eaf94a`, the first commit
carrying ADR-0013 Amendment 1's window (#78). It covered all twenty candidates: ADR-0016's ten
followed by Amendment 2's ten. It used 859 GraphQL calls and 0 REST calls, all with a classic token
with no scopes. The files are committed unchanged:

- `eval/datasets/s1/pairs.jsonl`, SHA-256 `8ac8212dd39770daaf3833f0885b0cc521367efdd67ea8b9d34ede1d039c8231`,
  with 2,328 pairs (1,723 strong, 605 weak);
- `eval/datasets/s1/manifest.json`, SHA-256 `5cdde3400193009bdd8e9a87e5d14df44f30a2f986c5eff9fec051d0c51614c3`.

Both pass `s1.dataset` and `s1.landing`.

**Per-candidate results (run 4).** Twelve of twenty qualify. S1-2's value is its linkable pairs, S1-3's
is resolved over linkable, S1-4's is the `.md` files and words in the file universe, and S1-5's is
the responses checked for that candidate.

| Repository | id | Lang | S1-1 | S1-2 | S1-3 | S1-4 | S1-5 | Chunks | Qualifies |
|---|---|---|---|---|---|---|---|---|---|
| `pallets/flask` | 596892 | Python | PASS BSD-3-Clause | PASS 223 | PASS 223/223 | **FAIL** 3 files, 392 words | PASS 34 | 189 | no |
| `pallets/click` | 19103692 | Python | PASS BSD-3-Clause | PASS 360 | PASS 360/360 | PASS 38 files, 29,000 words | PASS 23 | 382 | yes |
| `encode/httpx` | 179492861 | Python | PASS BSD-3-Clause | PASS 286 | PASS 286/286 | PASS 24 files, 16,434 words | PASS 27 | 237 | yes |
| `psf/requests` | 1362490 | Python | PASS Apache-2.0 | PASS 130 | PASS 130/130 | **FAIL** 2 files, 8,702 words | PASS 35 | 164 | no |
| `python-attrs/attrs` | 29918975 | Python | PASS MIT | PASS 117 | PASS 117/117 | PASS 24 files, 16,219 words | PASS 15 | 236 | yes |
| `spf13/cobra` | 12574344 | Go | PASS Apache-2.0 | **FAIL** 95 | PASS 95/95 | PASS 17 files, 13,154 words | PASS 14 | 176 | no |
| `go-chi/chi` | 44344606 | Go | PASS MIT | **FAIL** 30 | PASS 30/30 | PASS 5 files, 3,285 words | PASS 8 | 138 | no |
| `urfave/cli` | 11393110 | Go | PASS MIT | PASS 278 | PASS 278/278 | PASS 56 files, 21,262 words | PASS 24 | 306 | yes |
| `gin-gonic/gin` | 20904437 | Go | PASS MIT | PASS 132 | PASS 132/132 | PASS 7 files, 11,923 words | PASS 27 | 218 | yes |
| `charmbracelet/bubbletea` | 233130089 | Go | PASS MIT | **FAIL** 84 | PASS 84/84 | PASS 42 files, 7,958 words | PASS 16 | 339 | no |
| `pytest-dev/pytest` | 37489525 | Python | PASS MIT | PASS 938 | PASS 938/938 | **FAIL** 2 files, 529 words | PASS 125 | 1,015 | no |
| `pydantic/pydantic` | 90194616 | Python | PASS MIT | PASS 1403 | PASS 1403/1403 | PASS 98 files, 116,215 words | PASS 86 | 1,633 | yes |
| `psf/black` | 125266328 | Python | PASS MIT | PASS 620 | PASS 620/620 | PASS 32 files, 22,736 words | PASS 41 | 1,872 | yes |
| `Textualize/rich` | 220809393 | Python | PASS MIT | PASS 169 | PASS 169/169 | PASS 41 files, 34,469 words | PASS 19 | 925 | yes |
| `tox-dev/tox` | 68465360 | Python | PASS MIT | PASS 428 | PASS 428/428 | **FAIL** 2 files, 581 words | PASS 38 | 362 | no |
| `cli/cli` | 212613049 | Go | PASS MIT | PASS 1366 | PASS 1365/1366 | PASS 35 files, 28,411 words | PASS 67 | 2,298 | yes |
| `stretchr/testify` | 6247705 | Go | PASS MIT | PASS 109 | PASS 108/109 | PASS 5 files, 2,060 words | PASS 12 | 172 | yes |
| `gofiber/fiber` | 234231371 | Go | PASS MIT | PASS 470 | PASS 470/470 | PASS 77 files, 117,468 words | PASS 52 | 1,372 | yes |
| `prometheus/prometheus` | 6838921 | Go | PASS Apache-2.0 | PASS 933 | PASS 933/933 | PASS 65 files, 95,370 words | PASS 184 | 3,064 | yes |
| `spf13/viper` | 18369373 | Go | PASS MIT | **FAIL** 66 | PASS 66/66 | **FAIL** 3 files, 3,345 words | PASS 12 | 90 | no |

**Exclusions (D-6, every candidate):** `merge_commit_in_pr_history` 1,661 (Amendment 1); D-2 no
source files 1,240; D-2 more than 10 source files 89; D-1 first commit has no parent 1; D-1 PR
lists no commits 1.

**Every selection round.**

| Round | Miner commit | Candidates | D-2 files | Feasible subsets | Winner | Strong | Outcome |
|---|---|---|---|---|---|---|---|
| 1 (Amendment 2) | `331abcc` | ADR-0016's ten | 10 | 14 | `urfave/cli`, `gin-gonic/gin`, `python-attrs/attrs`, `encode/httpx` | 156 | Short by 144, so R-03 step 1 |
| Run 4 | `1eaf94a` | all twenty | 10 | 645 | `pydantic/pydantic`, `psf/black`, `cli/cli`, `gofiber/fiber` | 1,723 | A-3 passes, so step 2 does not run |

Two runs between these are not rounds of record.

- **Run 2** at `5330f34` stopped before selection, in `stretchr/testify`, on one of GitHub's
  transient GraphQL failures. #71 added bounded retries. An earlier attempt had stopped on
  `cli/cli`#7228, a merged PR that lists no commits; that was fixed before `5330f34`.
- **Run 3** at `af7685e` completed with 699 strong pairs. Only 22 of them were in held-out, and the
  D-3 probe (#75, #76) found merge-adjacent updates in about half of the sampled weak class.
  ADR-0013 Amendment 1 (#77) added the 60 s window and ordered a re-run, and its dataset was never
  committed.

Round 1 was measured before Amendment 1. It is recorded as the evidence that triggered R-03 step 1,
not as a round under the final rules.

Before this Decision was written, this section allowed one of four outcomes:

- **Accept the corpus:** name the 3–4 repositories, quote each candidate's S1-1 to S1-5 results,
  the chunk estimate and the surviving-pair count, and state A-3 as passed.
- **Accept with fallback:** the same, naming which R-03 step was used, what it added, and every
  selection round.
- **A-3 fails, short:** a feasible corpus exists but has fewer than 300 surviving strong pairs
  after both R-03 steps. Quote the shortfall and every selection round. §14.2's intervals are
  published at the achieved size.
- **A-3 fails, no feasible corpus:** name the constraint that failed, and record R-14 if the cause
  is acquisition.
