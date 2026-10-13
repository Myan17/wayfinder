# Task log — myan-eval-data-s1-license

| Field | Value |
|---|---|
| Task | S1-1: the clone's license file mapped to an SPDX id and cross-checked against the API (ORIENT item 5) |
| Module | eval-data |
| Branch | `myan/eval-data/s1-license` |
| Worktree | `../wayfinder-wt/myan-eval-data-s1-license` |
| Operator | myan |
| Agent | claude-code/opus-5.5 |
| Session | 2026-10-08T06:00Z/9685 |
| Started | 2026-10-08T17:14:13Z |
| Closed when | the last entry says TASK CLOSED (the header is never edited - this file is append-only) |

**Append-only.** Corrections are new entries. Entries are written by `scripts/log.sh` and the
`post-commit` hook; CI rejects a rewritten log (`scripts/check_agent_log.py`).

## Cards read

- (listed by `new-task.sh`; add any you read later as `READ` entries)

## Timeline

### 2026-10-08T17:14:13Z · PLAN · myan · claude-code/opus-5.5 · 2e86468
New s1/license.py. file_spdx(git_dir, commit): the root-level license file at the as-of commit (a regular file whose name, case-insensitive, is LICENSE, LICENCE or COPYING with an optional extension); none or more than one gives None. spdx(text): lower-case, whitespace collapsed, then each allowed license is recognised by phrases from its SPDX standard text; exactly one match gives that id, zero or several give None. s1_1(file, api): passes only when both are the same id and it is in {MIT, BSD-2-Clause, BSD-3-Clause, Apache-2.0, ISC}. The phrases are written from the SPDX texts, before the candidates' files are read, so the rule cannot be tuned to them. Rejected: trusting GitHub's licenseInfo alone (it is licensee run on the same file, so it is not a cross-check), and vendoring licensee's full-text similarity (heavy, and a threshold is one more tunable).

### 2026-10-08T17:15:47Z · TEST · myan · claude-code/opus-5.5 · 2e86468
PYTHONDONTWRITEBYTECODE=1 uv run --extra dev pytest → 263 passed (test_s1_license 12). Mutation check on s1/license.py, 9 mutants (single-match rule, both BSD forbid lists, license-file count, regular-file mode, agreement, allowed set, forbid check, case folding): all killed, the mode mutant only after the fixture gained a root directory named license. ruff check and ruff format --check clean on both new files. No candidate's license file was read: the phrases come from the SPDX standard texts.

### 2026-10-08T17:15:48Z · COMMIT · myan · claude-code/opus-5.5 · parent:2e86468
feat(eval-data): S1-1 license cross-check — the clone's license file as an SPDX id
4 files changed, 198 insertions(+), 2 deletions(-)

### 2026-10-08T17:15:56Z · HANDOFF · myan · claude-code/opus-5.5 · f8df812
Paused for gupta958's review of this PR (s1/license.py, code at f8df812). Next, in order: (1) it merges; (2) an agreements PR removing the dispatcher line from ORIENT's Owner actions (Myan made dispatcher required on 2026-10-08); (3) the S1 runner, a new eval-data task: per candidate github.repo, repo.mirror, repo.as_of_commit on the default branch, license.file_spdx and s1_1 (S1-1), repo.measure (S1-4), github.linked_pairs (S1-2), repo.resolve per pair (S1-3, at least 95% of bases), repo.changed, pairs.gold_files and keep, pairs.weak, then split.assign and select.best, writing eval/datasets/s1/{pairs.jsonl,manifest.json} with Client.calls as api_calls, checked by python -m s1.dataset; the run needs Myan's no-scope classic PAT; (4) the results PR with the ADR-0016 Decision and ORIENT item 5 done. Test: PYTHONDONTWRITEBYTECODE=1 uv run --extra dev pytest; guardrails with B=$(git merge-base origin/main HEAD), GITHUB_HEAD_REF set for check_ownership.

### 2026-10-08T17:15:57Z · COMMIT · myan · claude-code/opus-5.5 · parent:f8df812
docs(agents): handoff for the S1-1 license review pause
1 file changed, 3 insertions(+)

### 2026-10-13T17:05:09Z · DECIDE · myan · claude-code/opus-5.5 · 9552da2
Review from gupta958, relayed by Myan on 2026-10-13: "#63: Do not approve. It is unchanged at 9552da2; the previously reported Apache and dual-license bugs remain." The earlier report never reached this branch: there is no GitHub review or comment, and no session transcript holds it. Both bugs were reproduced here before the fix. First, spdx() named a bare Apache-2.0 file header, and a GPL text that mentions "Apache License Version 2.0", as Apache-2.0. Second, "MIT or GPL-2.0" followed by the MIT text was named MIT, because GPL has no rule and so never counted as a second match. The fix: Apache-2.0 now needs its title line ("apache license version 2.0, january 2004") and two of its own sections ("terms and conditions for use, reproduction, and distribution" and "grant of patent license"). A new OTHER list (general public license, gpl, mozilla public license, eclipse public license, CDDL, creative commons, dual licen, dual-licen) makes any text that names another license, or offers a dual license, unrecognised, so S1-1 fails closed. An allowed license with an appended third-party permissive notice, such as an Apache file with an MIT appendix, stays None. That is a false fail, not a false pass, and the manifest records both ids. Rejected: adding rules for GPL and the other licenses so they count as second matches, because that list of texts is open-ended while a list of names fails closed.

### 2026-10-13T17:05:09Z · TEST · myan · claude-code/opus-5.5 · 9552da2
PYTHONDONTWRITEBYTECODE=1 uv run --extra dev pytest gives 268 passed (test_s1_license now 18, up from 12). Mutation check on the fix used 6 mutants: the OTHER check removed, each Apache section phrase removed, and the gpl, dual licen and mozilla entries removed. All 6 were killed. The patent-grant mutant was killed only after a test was added for the title plus the terms heading without section 3. ruff check and ruff format --check are clean on both files.

### 2026-10-13T17:05:09Z · COMMIT · myan · claude-code/opus-5.5 · parent:9552da2
fix(eval-data): S1-1 refuses Apache headers, mentions and dual-license texts
4 files changed, 59 insertions(+), 5 deletions(-)
