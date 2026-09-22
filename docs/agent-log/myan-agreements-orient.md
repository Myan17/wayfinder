# Task log — myan-agreements-orient

| Field | Value |
|---|---|
| Task | Session orientation brief: make orient prints volatile project state so a new session stops re-reading eight files |
| Module | agreements |
| Branch | `myan/agreements/orient` |
| Worktree | `../wayfinder-wt/myan-agreements-orient` |
| Operator | myan |
| Agent | claude-code/opus-5 |
| Session | 2026-09-22T18:18Z/18506 |
| Started | 2026-09-22T18:41:55Z |
| Closed when | the last entry says TASK CLOSED (the header is never edited - this file is append-only) |

**Append-only.** Corrections are new entries. Entries are written by `scripts/log.sh` and the
`post-commit` hook; CI rejects a rewritten log (`scripts/check_agent_log.py`).

## Cards read

- (listed by `new-task.sh`; add any you read later as `READ` entries)

## Timeline

### 2026-09-22T18:42:08Z · PLAN · myan · claude-code/opus-5 · d4a5535
make orient prints a session brief to stdout and writes nothing. Sources are all already-authoritative: DESIGN 19.1/19.x for the phase and its task table, git worktree list for what is in flight, each task log's last HANDOFF for where it stopped, docs/context/INDEX.md for card status, gh pr list for review state. Nothing is committed, so it cannot go stale, cannot land in a diff, cannot conflict on a rebase and costs nothing against the 400-line limit. Rejected a committed generated docs/context/ORIENT.md refreshed by the post-commit hook: it would change on nearly every commit, so every branch would carry it and every rebase would conflict on it, and it would need its own size exception on top of the task log's. Also rejected printing the stack and the five rules: CLAUDE.md is loaded automatically at session start already, so duplicating it into orient output would be paying twice. The split is CLAUDE.md for what is durable, make orient for what is volatile. The brief states no fact it cannot source - in particular it lists the phase's task table verbatim and the recent merges next to it rather than computing a done/open column, because a guessed 'done' is worse than no column.

### 2026-09-22T18:47:19Z · EDIT · myan · claude-code/opus-5 · d4a5535
scripts/orient.py (new, the brief), scripts/tests/test_orient.py (new, 11 tests over the pure parsers), Makefile (orient target - platform module, declared as Scope), CLAUDE.md (startup block now runs make orient; a seventh row in the temptation table for reconstructing state by re-reading the design).

### 2026-09-22T18:47:19Z · TEST · myan · claude-code/opus-5 · d4a5535
uv run pytest -q -> 78 passed (11 new). uv run ruff check on both new files -> All checks passed; the 17 errors elsewhere under scripts/ are the pre-existing debt the platform card already records, untouched here. Two bugs the first run found and the tests now pin: main was listed as an in-flight worktree (git worktree list puts the main checkout first, now dropped), and every task log read as closed because the TEMPLATE header explains the TASK CLOSED marker in prose - only the Timeline section is searched now. Handoffs were also printing in full at roughly 200 words each, so they clip at a sentence boundary near 220 characters. Ran python3 scripts/orient.py --no-network to confirm the brief still renders with no GitHub call.

### 2026-09-22T18:47:36Z · HANDOFF · myan · claude-code/opus-5 · d4a5535
Ready for review. make orient replaces the eight-file read a new session otherwise does to work out where the project is. It writes nothing, so it cannot go stale, cannot land in a diff and cannot conflict on a rebase - that is the whole design choice and the alternative (a committed docs/context/ORIENT.md refreshed by the post-commit hook) was rejected for the opposite reasons. Two things for the reviewer to weigh rather than just diff. First, CLAUDE.md now tells every future agent session to run one command instead of reading the design: that is a behavioural change to how work starts here, and it is agreements, so it needs sign-off on the decision and not only on the text. Second, the brief prints the phase task table with no done column, because nothing in the repository records task completion and a guessed done is worse than none; if you want one, the honest way is a field in the task log that end-task.sh writes, which is a separate change.

### 2026-09-22T18:47:36Z · COMMIT · myan · claude-code/opus-5 · parent:d4a5535
feat(agreements): make orient, so a session stops reconstructing its own context
5 files changed, 458 insertions(+), 4 deletions(-)

### 2026-09-22T18:49:02Z · DECIDE · myan · claude-code/opus-5 · 10999ae
Correction to the EDIT and HANDOFF entries above: the Makefile target and the CLAUDE.md rewrite are both out of this pull request. Three reasons, in order of how much they cost. The Makefile is the platform module, so a three-line target widened this to two modules, and it changed a platform interface file, which made the platform card's Makefile hash stale - a card edit that would then conflict with the same card's edit on #18. Removing it makes this pure agreements with no card change. Second, even without the Makefile the branch measured 413 lines against the 400 limit, and CLAUDE.md is 16 of them. Third and the real reason: the CLAUDE.md change is the part that needs a decision rather than a diff, because it tells every future session to run a command instead of reading the design. It gets its own pull request, so it can be accepted or refused without holding the tool hostage. Entry point is therefore 'python3 scripts/orient.py' until both follow-ups land.

### 2026-09-22T18:49:02Z · COMMIT · myan · claude-code/opus-5 · parent:d4a5535
feat(agreements): scripts/orient.py, so a session stops reconstructing its own context
3 files changed, 438 insertions(+)
