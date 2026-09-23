# ORIENT.md — what to work on, in order

**Every agent session reads this file before its first action.** A `SessionStart` hook in
`.claude/settings.json` prints it, followed by the `scripts/orient.py` brief, into every Claude Code
session. Tools without hooks read it by hand as step 1 of `AGENTS.md` §9. It is not optional, and it
is not skimmed for ideas. It decides what the next task is.

The plan itself is `docs/DESIGN.md` §19. That section gives the phases, gates and hours. This file
gives the **order** to work them in and the **status** of each item, which DESIGN does not record.

## The rule

1. The next task is the **first item below whose status is not `done`** and that is not `blocked`.
   Start it with `scripts/new-task.sh`. Do not offer a menu of options. The order is already decided.
2. Work outside this list happens only when `myan` or `gupta958` directs it explicitly in the
   session. Log a `DECIDE` entry that quotes the direction. "It would be useful" is not a direction.
3. The pull request that completes an item also changes that item's status here to `done #<pr>`.
   A status change without a merged pull request behind it is wrong.
4. If an item is blocked, set it to `blocked: <reason>` in a pull request, then take the next item.
   Never skip an item silently.
5. If a phase runs out of contingency, apply DESIGN §19.8 the same day. The date moves; evidence is
   never cut.
6. Before a phase's gate closes, the next phase's ordered list is written into this file in its own
   pull request, reviewed before any of that phase's work starts.

## Current phase: P0 — spikes, decisions, schema, selection rules

Sep 21 – 27. Gate **G0**: every spike answered, and ADR-0013 and ADR-0015 written before any
experiment. 32 h planned, 3 h of contingency.

| # | Item | h | Why it is here in the order | Status |
|---|---|---|---|---|
| 1 | ADR-0013 (evaluation protocol), ADR-0015 (rerank selection rule), ADR-0011 (answerability) | 1 | G0 requires them written before any experiment, and ADR-0013 decides how S1 selects its corpus | in review #24 |
| 2 | Schema v1: authorization facts, three identities, generations, tombstones | 3 | The most expensive thing to change later; `gupta958`'s first P0 review focus | in review #25–#28 |
| 3 | Repo scaffold, CI skeleton, release-manifest format | 3 | Before anything that produces evidence. A spike result is only citable if the commit, image digests, schema version and dataset hashes it ran against are pinned (DESIGN §16.9), and only repeatable if CI can re-run it. Evidence produced before the manifest format exists would have to be re-run or cited without provenance. It also gives the schema tests a database in CI | open |
| 4 | S5 River scheduling proof at every crash boundary | 5 | Evidence for DESIGN §9.3.3, which P1 builds on | open |
| 5 | S1 corpus: linkable pairs, base-commit resolvability, licenses, acquisition mode | 4 | Needs ADR-0013; feeds the P2 evaluation dataset | open |
| 6 | S6 embedding identity: two specifications over identical text | 3 | Evidence for DESIGN §9.2 | open |
| 7 | S2 whole-system CPU | 6 | Replaces every estimate in DESIGN §10.3 | open |
| 8 | S4 provider and account ledger | 3 | Appendix B refresh; not needed until P3 | open |
| 9a | S3 rules S3-1a, S3-2 to S3-5 | — | Ran before item 3 existed; its evidence is ADR-0007's local run, not release evidence | done #19 |
| 9b | S3-1b: provision the A1 and run S3 on it | — | | blocked: Myan provisions the A1 |
| 9c | S3-6: two-leg hybrid query of DESIGN §9.5 (vector column, HNSW index, stand-in embeddings) | — | Follow-up to #19; runs under item 3's manifest | open |

### Done outside the order during P0 (for the record, not a precedent)

- P1 work done early: authz leases, row predicate, fenced refresh and counters (#4–#7, #10).
- Agreements tooling not in §19: line limit (#8), review handoff and its skill (#11, #13), content
  hashes for cards (#14), webhook fix (#15), `scripts/orient.py` (#20, #21).
- Platform: platform card (#2), dev dependency lock (#3, #18), S3 acceptance rules (#16, #17).

## Next phase

P1, the safety and consistency kernel (Sep 28 – Oct 11, gate G1). Its ordered list is written here
before G0 closes (rule 6). Until then, DESIGN §19.3 is the only source for it.
