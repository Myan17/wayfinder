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

### 2026-10-13T17:08:34Z · HANDOFF · myan · claude-code/opus-5.5 · b241d99
Paused for gupta958's re-review after the Apache and dual-license fix (code at b241d99, rebased onto main 960ef5e after #64 merged). This replaces the previous HANDOFF: its step (2), the dispatcher PR, merged as #64. Next, in order: (1) this PR merges; (2) #65 (s1/corpus.py) and then #66 (s1/run.py) are each rebased onto main, retargeted to main, closed and reopened, and their bodies refreshed; (3) after #66 merges, the live run with Myan's no-scope classic PAT; (4) the results PR. Test: PYTHONDONTWRITEBYTECODE=1 uv run --extra dev pytest; guardrails with B=$(git merge-base origin/main HEAD), GITHUB_HEAD_REF set.

### 2026-10-13T17:08:34Z · COMMIT · myan · claude-code/opus-5.5 · parent:b241d99
docs(agents): handoff for the S1-1 license re-review
1 file changed, 3 insertions(+)

### 2026-10-13T17:56:11Z · DECIDE · myan · claude-code/opus-5.5 · 5d7287a
Second review from gupta958, relayed by Myan on 2026-10-13: "The Apache fix is good, but dual-license rejection is still incomplete. Against the exact branch: MIT or BSD-2-Clause + MIT text gives MIT; MIT or Apache-2.0 + MIT text gives MIT; MIT or Zlib license + MIT text gives MIT. The OTHER tuple is only a partial denylist, so it cannot support the claim that any dual license fails closed. A should use stricter whole-license/template matching or comprehensively detect alternate licenses and add these regression cases." Choice: whole-license template matching, using SPDX's own templates. A list of other licenses can never be complete. spdx() now fullmatches the normalized text against each allowed license's template from spdx/license-list-data v3.29.0 (2026-09-16, the last release before the as-of time). The templates are committed under eval/miners/s1/spdx/ and pinned by SHA-256, and a changed file stops the miner. The only text allowed outside the template is a leading block of blank lines, copyright lines that do not contain "licen", and one plain MIT, ISC or BSD title (Apache-2.0's template carries its own). Normalization follows the SPDX matching guidelines in part: case, quote and dash forms, the copyright sign, http and https, and whitespace. Template variables: the leading copyright variable (.{0,5000}) matches nothing, because that block is stripped line by line under the stricter rule; bullets (.{0,20}) cannot contain spaces, which also stops catastrophic backtracking on a near-miss Apache text (a 5 s timeout before this change); .+ and .* are capped at 200 characters, and no variable may contain "licen". OTHER is removed. Known cost: a file with any extra text, such as zstd's "For Zstandard software" line, gives no id. That is a false fail, never a false pass. Rejected: a comprehensive list of alternate licenses, which cannot be complete.

### 2026-10-13T17:56:11Z · TEST · myan · claude-code/opus-5.5 · 5d7287a
PYTHONDONTWRITEBYTECODE=1 uv run --extra dev pytest gives 271 passed (test_s1_license 20). The fixtures are the templates rendered at their original values, plus a hand-written MIT file (title, two holders, curly quotes) that does not depend on the templates. Regression tests cover B's three cases and GPL-2.0, each in four shapes: a bare "MIT or X" line, a sentence before the text, an alternative after it, and the offer inside the copyright line. Real files checked by hand and not committed: the SPDX v3.29.0 texts of all five licenses, apache.org's LICENSE-2.0.txt, and the LICENSE files of kubernetes (Apache-2.0), django (BSD-3-Clause), express (MIT) and serde's LICENSE-MIT are each named correctly; zstd (extra line) and node-glob (Blue Oak) give None. No candidate's file was read. Mutation check used 13 mutants: the variable licen check, fullmatch replaced by match, the copyright-line licen lookahead, the hash check, the .+ cap, the .* cap, the bullet pattern (killed by timeout, through the near-miss Apache test), quote normalization, the copyright sign, the optional-group join, and the title strip. All 11 of those were killed. The one-hit rule (len(hits) == 1 replaced by any hit) survived. It is equivalent in practice, because no text can fullmatch two of these templates, but it is kept as a guard. ruff is clean.

### 2026-10-13T17:56:11Z · COMMIT · myan · claude-code/opus-5.5 · parent:5d7287a
fix(eval-data): S1-1 matches the whole license text against SPDX templates
9 files changed, 277 insertions(+), 102 deletions(-)

### 2026-10-13T17:56:22Z · HANDOFF · myan · claude-code/opus-5.5 · cc420ee
Paused for gupta958's third review: S1-1 is now a whole-text SPDX template match (code at the commit before this one). Correction to the last TEST entry: 12 mutants were run, not 13. 11 were killed and 1, the one-hit rule, is equivalent. Next, in order: (1) this PR merges; (2) #65 and then #66 are each rebased onto main, retargeted, closed and reopened, and their bodies refreshed (#66's measure test uses a full MIT text, since a partial one is no longer MIT); (3) after #66 merges, the live run with Myan's no-scope classic PAT; (4) the results PR. Test: PYTHONDONTWRITEBYTECODE=1 uv run --extra dev pytest; guardrails with B=$(git merge-base origin/main HEAD), GITHUB_HEAD_REF set.

### 2026-10-13T17:56:23Z · COMMIT · myan · claude-code/opus-5.5 · parent:cc420ee
docs(agents): handoff for the S1-1 template-match review
1 file changed, 3 insertions(+)

### 2026-10-13T18:16:52Z · DECIDE · myan · claude-code/opus-5.5 · 880071c
Third review from gupta958, relayed by Myan on 2026-10-13: "_lead() removes dual-license evidence before matching: two leading titles (MIT License followed by BSD 2-Clause License) plus the MIT template returns MIT; Copyright (c) 2026 X, MIT or Zlib plus the MIT template also returns MIT. A should strip at most one title, and only when it identifies the license currently being tested; stop treating arbitrary copyright lines as harmless metadata; add both cases as regression tests. Secondary: git diff --check reports whitespace errors in the vendored SPDX templates. If those bytes intentionally match upstream, that exception should be explicit; otherwise normalize them and update the hashes." Fixes: (1) _lead(text, sid) now runs per license under test and strips at most one title, from a per-license title pattern (MIT, ISC, BSD-2, BSD-3; Apache-2.0's template carries its own). (2) A copyright line is "copyright" or "(c)" followed by at most 120 characters, and the line is not stripped if that text contains an offer word (or, licen*, dual*, under, terms, alternativ*, spdx). "and/or" is covered by "or". Such a line stays in the text and fails the template. This is a grammar restriction, not a list of license names, but it cannot prove a holder string is a name: "Copyright 2026 X, Zlib", with no offer word, is still stripped. (3) The templates stay byte-identical to upstream, so their hashes are upstream's. eval/miners/s1/spdx/.gitattributes marks *.template.txt -whitespace with a comment saying why, and git diff --check is now clean.

### 2026-10-13T18:16:52Z · TEST · myan · claude-code/opus-5.5 · 880071c
PYTHONDONTWRITEBYTECODE=1 uv run --extra dev pytest gives 282 passed (test_s1_license 31). New tests: B's two cases and their variants (titles reversed, another license's title, a holder line plus "All rights reserved." plus a title still MIT, a BSD-3 title on BSD-3); one copyright line per offer word plus an over-long line, each refused while a plain line passes; at most one title. Rechecked by hand: the same twelve real files give the same ids as before. The template SHA-256s are re-verified against the upstream download. Mutation check used 11 mutants: the one-title flag, the offer check, the sid passed to _lead, the 120-character bound, and each offer word removed in turn. All were killed except and/or, which is equivalent to "or" and was dropped from the list. ruff is clean, and git diff --check against the base is clean.

### 2026-10-13T18:16:52Z · COMMIT · myan · claude-code/opus-5.5 · parent:880071c
fix(eval-data): S1-1's leading block cannot hide a second license
5 files changed, 80 insertions(+), 18 deletions(-)

### 2026-10-13T18:17:48Z · HANDOFF · myan · claude-code/opus-5.5 · 44aa7e3
Paused for gupta958's fourth review (the leading-block fix, 44aa7e3). This PR is now stacked on myan/eval-data/spdx-templates, the vendored templates split out to stay under 400 lines, because it was 445 with them. Next, in order: (1) the templates PR merges; (2) this PR is rebased onto main, retargeted, closed and reopened, and its body refreshed; (3) it merges; (4) #65, then #66, the same way; (5) the live run with Myan's no-scope classic PAT; (6) the results PR. Test: PYTHONDONTWRITEBYTECODE=1 uv run --extra dev pytest; guardrails with B=<parent head> while stacked, GITHUB_HEAD_REF set.

### 2026-10-13T18:17:48Z · COMMIT · myan · claude-code/opus-5.5 · parent:44aa7e3
docs(agents): handoff for the S1-1 leading-block review
1 file changed, 3 insertions(+)
