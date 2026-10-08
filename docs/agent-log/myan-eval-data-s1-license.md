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
