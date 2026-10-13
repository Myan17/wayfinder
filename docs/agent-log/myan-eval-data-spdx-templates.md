# Task log — myan-eval-data-spdx-templates

| Field | Value |
|---|---|
| Task | S1-1's SPDX license templates, vendored from license-list-data v3.29.0 (ORIENT item 5) |
| Module | eval-data |
| Branch | `myan/eval-data/spdx-templates` |
| Worktree | `../wayfinder-wt/myan-eval-data-spdx-templates` |
| Operator | myan |
| Agent | claude-code/opus-5.5 |
| Session | 2026-10-13T18:17Z/960ef5e |
| Started | 2026-10-13T18:17:07Z |
| Closed when | the last entry says TASK CLOSED (the header is never edited - this file is append-only) |

**Append-only.** Corrections are new entries. Entries are written by `scripts/log.sh` and the
`post-commit` hook; CI rejects a rewritten log (`scripts/check_agent_log.py`).

## Cards read

- (listed by `new-task.sh`; add any you read later as `READ` entries)

## Timeline

### 2026-10-13T18:17:27Z · DECIDE · myan · claude-code/opus-5.5 · 960ef5e
Split from #63 by function, because the line limit was exceeded: #63 counted 445 lines with the vendored templates. Myan relayed gupta958's third review on 2026-10-13, which needs #63 to grow. This PR carries only the data: SPDX's own templates for the five licenses S1-1 allows (MIT, ISC, BSD-2-Clause, BSD-3-Clause and Apache-2.0), byte-identical to spdx/license-list-data tag v3.29.0 (2026-09-16, the last release before the as-of time), template/<id>.template.txt. A nested .gitattributes marks them -whitespace, because upstream has trailing spaces and blank lines at end of file, and normalizing them would break the upstream hashes that #63 pins. #63 (s1/license.py) stacks on this PR.

### 2026-10-13T18:17:27Z · TEST · myan · claude-code/opus-5.5 · 960ef5e
Each file was downloaded again from raw.githubusercontent.com/spdx/license-list-data/v3.29.0/template/ and compared with cmp: all five are identical. SHA-256: Apache-2.0 5567209d3a634ebd6ed122a7302563b9668ab141941149a4e30d9c7b887f41b9, BSD-2-Clause 922ac644c79e7c2aa31bacac531a5d4d5b9d183853a3dc44a253fd9267c3c890, BSD-3-Clause c42368b683ceef1ad41b6f17999adf3b7534e3c47fbdd51449ed6690edb1fc5f, ISC a382ee687364e5fa6361f299be089d79ded228a7ccbf1d4352a30fa22bfddb8f, MIT 9b91e12dfe57d42e91ea96d2acb7624040bffc54182bd164d39d0fae33e77794. git diff --check is clean with the .gitattributes in place. No code changes, so the test suite is unchanged.

### 2026-10-13T18:17:28Z · COMMIT · myan · claude-code/opus-5.5 · parent:960ef5e
build(eval-data): vendor SPDX templates for S1-1's whole-text license match
7 files changed, 126 insertions(+)

### 2026-10-13T18:17:28Z · HANDOFF · myan · claude-code/opus-5.5 · 1ea0446
Paused for gupta958's review. This is data only, and #63 stacks on it. Next, in order: (1) this PR merges; (2) #63 is rebased onto main, retargeted, closed and reopened; (3) #65, then #66, the same way. Check: for each file, curl -fsSL https://raw.githubusercontent.com/spdx/license-list-data/v3.29.0/template/<id>.template.txt | cmp - eval/miners/s1/spdx/<id>.template.txt

### 2026-10-13T18:17:28Z · COMMIT · myan · claude-code/opus-5.5 · parent:1ea0446
docs(agents): handoff for the SPDX templates review
1 file changed, 3 insertions(+)
