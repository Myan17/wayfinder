# Task log — myan-eval-data-s1-git-acquire

| Field | Value |
|---|---|
| Task | S1 acquisition, git side: mirror clone with refs/pull, as-of commit, universe and S1-4 measurement, D-1 base commits, changed files at the base (ORIENT item 5) |
| Module | eval-data |
| Branch | `myan/eval-data/s1-git-acquire` |
| Worktree | `../wayfinder-wt/myan-eval-data-s1-git-acquire` |
| Operator | myan |
| Agent | claude-code/opus-5.5 |
| Session | 2026-10-05T03:20Z/9d28c1f |
| Started | 2026-10-05T03:20:59Z |
| Closed when | the last entry says TASK CLOSED (the header is never edited - this file is append-only) |

**Append-only.** Corrections are new entries. Entries are written by `scripts/log.sh` and the
`post-commit` hook; CI rejects a rewritten log (`scripts/check_agent_log.py`).

## Cards read

- (listed by `new-task.sh`; add any you read later as `READ` entries)

## Timeline

### 2026-10-05T03:21:33Z · PLAN · myan · claude-code/opus-5.5 · 9d28c1f
New eval/miners/s1/repo.py, the git half of acquisition. It is read-only against a mirror clone (S1-5), which carries refs/pull/*/head so fork commits resolve (S1-3). Functions: mirror(url, dest); as_of_commit (the last first-parent commit on the default branch before as_of); measure(commit), which gives ADR-0016's seven-step universe file count, chunk estimate and S1-4's .md file and word counts, applying universe.excluded first by path and then with content; base_commit(first_commit), D-1's parent or the reason it did not resolve (not in the clone, or root commit); changed(base, head), the base..head name-status with -M as pairs.Changed carrying base mode and bytes; has_merges(base, head). Blobs are read with one cat-file --batch per call. Tests build a real git repo in tmp_path, add a refs/pull ref and mirror-clone it through file://, so there is no network. The GitHub API half (GraphQL pairs, license cross-check, call tally) and the runner are the next two PRs. Rejected: REST pulls/N/files for the changed files, which costs one call per PR and still needs the clone for base bytes. Open for review: base..head includes others' changes when a PR merged its base branch mid-way, so has_merges exposes it rather than this PR inventing an exclusion rule ADR-0013 does not name.

### 2026-10-05T03:23:22Z · TEST · myan · claude-code/opus-5.5 · 9d28c1f
uv run --extra dev pytest: 242 passed (8 new in test_s1_repo.py, all against a real repository mirror-cloned through file://). Mutation check on repo.py, 10 mutants, all killed: no --mirror (7 tests fail), no --first-parent, no content-based exclusion (two survived the first run, so the as-of merge test and the gen.go and blob.py fixtures were added), word count by spaces, --no-renames, root commit as its own base, chunks fixed at 1, and no --merges filter. ruff check and ruff format --check are clean on both files.

### 2026-10-05T03:23:23Z · COMMIT · myan · claude-code/opus-5.5 · parent:9d28c1f
feat(eval-data): S1 acquisition, git side — mirror, as-of, universe, D-1 bases
4 files changed, 294 insertions(+), 2 deletions(-)
