# Task log — myan-platform-s3-arch-rule-correction

| Field | Value |
|---|---|
| Task | Correct S3-1's architecture observation before any S3 result is recorded |
| Module | platform |
| Branch | `myan/platform/s3-arch-rule-correction` |
| Worktree | `../wayfinder-wt/myan-platform-s3-arch-rule-correction` |
| Operator | myan |
| Agent | human |
| Session | 2026-09-21T23:58Z/a2f205b |
| Started | 2026-09-21T23:58:34Z |
| Closed when | the last entry says TASK CLOSED (the header is never edited - this file is append-only) |

**Append-only.** Corrections are new entries. Entries are written by `scripts/log.sh` and the
`post-commit` hook; CI rejects a rewritten log (`scripts/check_agent_log.py`).

## Cards read

- (listed by `new-task.sh`; add any you read later as `READ` entries)

## Timeline

### 2026-09-21T23:58:49Z · TEST · myan · claude-code/opus-5 · a2f205b
Reconnaissance before building the S3 harness, and it broke my own rule rather than the engine. ParadeDB publishes linux/arm64: buildx imagetools inspect paradedb/paradedb:0.25.9 lists it, digest sha256:c17153b8b7307734c3aede0393dfe8fa447f4a528ec028b1c3937186ab3ee242. Ran S3-1a's four points against that digest on this machine. Point 1, host uname -m, reported 'arm64'; the rule requires 'aarch64'. macOS reports arm64, Linux reports aarch64, and the A1 is Linux, so the rule is right for S3-1b and wrong for the machine S3-1a is defined to run on. Point 2, daemon Server.Arch, reported arm64 as required. Point 3, image Architecture/Variant, reported 'arm64/' with an empty variant; the rule requires 'arm64/v8'. Checked whether that is a ParadeDB defect: the raw manifest index advertises the platform object {"architecture": "arm64", "os": "linux"} with no variant key at all, while alpine:3.20 and postgres:17 both set Variant=v8 for their arm64 builds. Variant is optional and its absence is not evidence about architecture. So the rule as written FAILS a genuinely arm64 image and would have sent a working engine to the fallback.

### 2026-09-21T23:58:49Z · PLAN · myan · claude-code/opus-5 · a2f205b
Correcting the observation in ADR-0007 before recording any S3 result, in its own pull request, and not running the rest of the spike until it merges. The correction is that the rule mis-stated what to observe, not that the threshold was too strict: architecture must be arm64, and variant must be v8 only when the image declares one, because the OCI platform object makes it optional. Point 1 accepts arm64 or aarch64, which are the same architecture under two spellings, and S3-1b keeps requiring the Linux spelling since the A1 is Linux. Rejected quietly relaxing this while writing up the results - that is editing a rule after seeing a measurement, which is the exact thing this ADR exists to prevent, and it would not matter that the edit happened to be correct. Rejected pinning a different image that does set v8: choosing the artifact to fit the rule is the same error wearing a different hat.

### 2026-09-21T23:59:35Z · HANDOFF · myan · claude-code/opus-5 · a2f205b
Ready for review, and nothing from S3 has been recorded anywhere - the Decision section is still empty and I have not run S3-2 through S3-6. Two corrections to S3-1's observation table, both found by pointing it at the real image before building the harness, both failing closed. Point 3 required Architecture/Variant to read arm64/v8; ParadeDB declares no variant, so a genuinely arm64 image failed. Point 1 required aarch64; macOS spells it arm64 and S3-1a runs on a development machine, while S3-1b keeps the Linux spelling because the A1 is Linux. The reviewer should check that these read as corrections to what is observed rather than as a threshold loosened because it was inconvenient; the test I would apply is that neither makes a non-arm64 image pass. Holding the harness until this merges.

### 2026-09-21T23:59:35Z · COMMIT · myan · claude-code/opus-5 · parent:a2f205b
fix(platform): S3-1 rejected a genuinely arm64 image; correct what it observes
2 files changed, 50 insertions(+), 2 deletions(-)
