# Task log — myan-platform-s3-acceptance-rules

| Field | Value |
|---|---|
| Task | Write S3's acceptance rules for pg_search on arm64 before running the spike |
| Module | platform |
| Branch | `myan/platform/s3-acceptance-rules` |
| Worktree | `../wayfinder-wt/myan-platform-s3-acceptance-rules` |
| Operator | myan |
| Agent | human |
| Session | 2026-09-21T23:07Z/07154fa |
| Started | 2026-09-21T23:07:55Z |
| Closed when | the last entry says TASK CLOSED (the header is never edited - this file is append-only) |

**Append-only.** Corrections are new entries. Entries are written by `scripts/log.sh` and the
`post-commit` hook; CI rejects a rewritten log (`scripts/check_agent_log.py`).

## Cards read

- (listed by `new-task.sh`; add any you read later as `READ` entries)

## Timeline

### 2026-09-21T23:08:08Z · READ · myan · claude-code/opus-5 · 07154fa
DESIGN A-5 (ParadeDB image runs on arm64 and pg_search honours MVCC snapshot visibility, owned by S3), R-06 (pg_search on arm64 or its MVCC behaviour disappoints: likelihood L, impact H, mitigation built-in FTS measured in E1, decision at G0), ADR-0002 (pg_search accepted with AGPL-3.0, built-in FTS as the named fallback), 19.2 (S3 is 4 h, output 'deployment decision or ADR-0007 option B'), 12.1 line 843 (exact BM25 DDL comes from the pinned pg_search version, key_field = 'id'), 16.3 RETR-03. Also read docs/context/modules/platform.md. docs/adr/ exists and is empty: no ADR has been written yet, although DESIGN cites 0002, 0007, 0011, 0013 and 0015.

### 2026-09-21T23:08:08Z · PLAN · myan · claude-code/opus-5 · 07154fa
Writing S3's acceptance rules as ADR-0007 before running anything, and landing them in their own pull request. The rules have to be falsifiable and fixed in advance or the spike cannot fail: with the measurement in the same pull request I could set the threshold to whatever the run produced, and neither I nor the reviewer could tell afterwards. Separate pull requests make the ordering checkable from the merge order rather than from my word for it. The ADR states the question, the fallback R-06 already names, and one pass/fail rule per claim in A-5; the Decision section stays empty until S3 runs. Rejected writing rules and results together to save a review cycle, which is the whole thing B said to watch for at P0. Rejected inventing a latency threshold: nothing in DESIGN sets one for BM25 alone, and a number I made up today would look like evidence later.

### 2026-09-21T23:23:25Z · TEST · myan · claude-code/opus-5 · 07154fa
No code in this pull request, so the check that matters is whether its claims are true. Wrote the ADR with section references from memory first, then verified them and found most were wrong: I had cited 12.1 for the schema (it is ADRs), 9.4 for deletion closure (it is chunking; the right one is 9.3.6), and 5.3, 12.3, 12.4 and 20.1, none of which exist. Corrected against the real headings: A-5 is 7.1, the BM25 DDL is 9.2, fenced activation is 9.3.5, the retrieval pipeline and RRF are 9.5, the comparison table is 12, E1 is 15.4, R-06 is 20. Also corrected a metric claim: I had written that E1 compares the two engines on Recall@5; E1's stated question is whether lexical and dense complement each other, scored on Recall@10, so the ADR now says only what R-06 says, that the fallback is measured there. Verified with a script that extracts every section token from the ADR and every numbered heading from DESIGN.md and reports tokens that resolve to no heading: 12 cited, 0 unresolvable. A-5, R-06, Q-3, ADR-0002, RRF and key_field all confirmed present in DESIGN.md.

### 2026-09-21T23:23:25Z · HANDOFF · myan · claude-code/opus-5 · 07154fa
Ready for review. One file: docs/adr/ADR-0007-lexical-search-engine-acceptance.md, six falsifiable acceptance rules for pg_search on arm64, Decision section deliberately empty. The spike harness and the measured results come in a separate pull request so the ordering is checkable from the merge order rather than from my word. Two things for the reviewer: docs/adr/ matches no module in OWNERSHIP.md, which the guardrail reports as a warning - it is the reviewer's file to change under the standing ruling, so it is a proposal in the pull request body rather than a change in the diff. And a guardrail that checks ADR section references against DESIGN.md headings would have caught my errors mechanically; scripts/ is joint, so I am raising it rather than adding it.

### 2026-09-21T23:23:35Z · COMMIT · myan · claude-code/opus-5 · parent:07154fa
docs(platform): write S3's acceptance rules before running S3
2 files changed, 126 insertions(+)

### 2026-09-21T23:38:01Z · TEST · myan · claude-code/opus-5 · 400415d
Checked the reviewer's S3-1 objection against Docker rather than taking it on trust, and it is worse than the wording suggested. On this arm64 host, 'docker run --platform linux/amd64 alpine:3.20 uname -m' reports x86_64, so uname does catch that direction - but uname reports what the binary sees, so an arm64 image emulated on an amd64 host reports aarch64 and my rule would have passed. That is the real false pass: a CI runner with binfmt installed would satisfy the old S3-1. What does distinguish them: 'docker image inspect --format {{.Architecture}}/{{.Variant}}' reports arm64/v8 for an arm64 pull and amd64 for an amd64 pull of the same tag, and 'docker version --format {{.Server.Arch}}' reports the daemon's architecture independently. S3-1 now requires both to read arm64 and to agree, pinned by digest, and S3-1b requires no qemu-aarch64 interpreter in /proc/sys/fs/binfmt_misc on the A1 itself, which is the definitive check and only available on a real Linux host. Re-verified after the rewrite: 12 section references cited, 0 unresolvable; rule ids consistent as S3-1a, S3-1b, S3-2..S3-6; no bare S3-1 or uname left in the file.

### 2026-09-21T23:38:01Z · DECIDE · myan · claude-code/opus-5 · 400415d
S3-1b cannot be settled until the Oracle A1 exists, so ADR-0007 stays Proposed even if every other rule passes locally. Considered marking S3-1 satisfied by a local aarch64 machine and noting the A1 as follow-up; rejected it. A-5 is a claim about the deployment target, 19.2 puts A1 provisioning inside S3 for exactly this reason, and 'passed on my laptop' recorded as acceptance is the same category of error the reviewer just caught twice. A partial result is recorded as 'measured locally, S3-1b outstanding', never as an acceptance.

### 2026-09-21T23:38:14Z · COMMIT · myan · claude-code/opus-5 · parent:400415d
docs(platform): close three ways an S3 rule could pass falsely
2 files changed, 58 insertions(+), 7 deletions(-)

### 2026-09-21T23:51:47Z · EDIT · myan · claude-code/opus-5 · 2af703c
Both reviewer corrections accepted. S3-1b: my binfmt check was reasoning backwards. A qemu-aarch64 handler is what lets an amd64 host run arm64 binaries; on an aarch64 A1 it is irrelevant, and its registration would not mean Docker used it for this container - absence was neither necessary nor sufficient. Replaced with the reviewer's four points, all in one run against one digest: host uname -m outside any container is aarch64, docker version Server.Arch is arm64, docker image inspect Architecture/Variant is arm64/v8, and the container runs with Postgres accepting a connection. Emulation is how Docker executes a format the host cannot run, so three matching architectures plus a successful run means there is no foreign format and the question does not arise. S3-1a is now the same four points on a development machine, labelled precondition only, and removed from the acceptance list entirely - passing locally is not evidence about the deployment target. S3-4: the heading said four-step over a five-row table; corrected to five, and step 5 is the one that stops a uniformly stale implementation passing, which is why the count mattered. Recorded both superseded drafts inside the ADR rather than deleting them, since the reasoning errors are the useful part for anyone re-opening this.

### 2026-09-21T23:51:47Z · TEST · myan · claude-code/opus-5 · 2af703c
Re-verified after the edits: no 'four-step' or 'all four' left; the S3-4 table has exactly 5 numbered rows against a rule that says five steps; the only qemu and binfmt mentions are the explicit record of the superseded draft; 12 section references cited, 0 unresolvable. make guardrails clean apart from the known docs/adr ownership warning.

### 2026-09-21T23:51:48Z · COMMIT · myan · claude-code/opus-5 · parent:2af703c
docs(platform): prove native execution by matching architectures, not by absent QEMU
2 files changed, 37 insertions(+), 5 deletions(-)
