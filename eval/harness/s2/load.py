"""Spike S2's corpus load, part 2: run `s2.load_plan` against the database through schema's build path.

ADR-0019 Amendments 1-3. One connection holds 100 pseudo-repositories (`s2/pseudo-NN`). Each one with
windows is built in ascending id, inside a single claim of exactly `LEASE` (BCR-3): every window through
`index_chunk` with the real embedder, then its padding copies through `pad_copy`, then `finish_build`
and `activate`. A build that `activate` refuses, or that took longer than the lease, fails the load,
and nothing extends a claim. A window whose truncated retry is rejected again fails the load and is
named (Amendment 2). With `pad_to`, the live representations are checked to be exactly that many.
"""

from __future__ import annotations

import time
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field
from datetime import timedelta

from s2 import load_plan as plan
from s2.inputs import Window

s6 = plan.s6_identity


@dataclass
class Loaded:
    lease: timedelta = plan.LEASE
    repo_ids: dict[int, int] = field(default_factory=dict)  # pseudo-repository -> repository.id
    durations: dict[int, timedelta] = field(default_factory=dict)  # claim to activation
    real: dict[int, int] = field(default_factory=dict)  # distinct pre-padding representations
    padded: dict[int, int] = field(default_factory=dict)
    windows: int = 0
    accepted_tokens: list[int] = field(default_factory=list)  # per accepted window
    truncated: list[plan.Truncated] = field(default_factory=list)


def live_representations(conn, repo_ids: Iterable[int]) -> int:
    """Representations an active generation of these repositories serves."""
    return conn.execute(
        "SELECT count(DISTINCT o.representation_id) FROM occurrence o"
        " JOIN repository r ON r.active_generation_id = o.generation_id WHERE r.id = ANY(%s)",
        (list(repo_ids),),
    ).fetchone()[0]


def load(
    conn,
    embed: s6.Embedder,
    windows: Iterable[Window],
    full_names: Mapping[int, str],
    spec: s6.Spec,
    *,
    calls: list,
    context_exceeded: type[BaseException],
    pad_to: int | None = None,
    clock: Callable[[], float] = time.monotonic,
) -> Loaded:
    """`embed` must be `s6_ollama.embedder(..., record=calls, truncate_rejected=True)`, and
    `context_exceeded` its `ContextExceeded`: the loader reads `calls` and names a failed retry."""
    groups = plan.group(windows)
    srcs = {p: plan.sources(ws, full_names, spec.doc_template) for p, ws in groups.items()}
    out = Loaded(windows=sum(len(ws) for ws in groups.values()))
    out.real = {p: len(s) for p, s in srcs.items()}
    shares = plan.allocate(out.real, pad_to) if pad_to is not None else {p: 0 for p in groups}
    out.padded = dict(shares)
    copies: dict[int, list[plan.Pad]] = {p: [] for p in groups}
    for pad in plan.pads(srcs, shares):
        copies[pad.pseudo_repo].append(pad)

    connection_id = s6.seed_connection(conn)
    for p in sorted(groups):
        repo = s6.seed_repository(
            conn, connection_id=connection_id, github_repo_id=p, full_name=f"s2/pseudo-{p:02d}"
        )
        out.repo_ids[p] = repo
        if groups[p]:
            out.durations[p] = _build(
                conn, embed, repo, p, groups[p], copies[p], full_names, spec, context_exceeded, clock
            )

    by_hash: dict[bytes, list[Window]] = {}
    for ws in groups.values():
        for w in ws:
            by_hash.setdefault(
                plan.input_hash(w, full_names[w.github_repo_id], spec.doc_template), []
            ).append(w)
    out.accepted_tokens, out.truncated = plan.embed_report(calls, by_hash)
    if pad_to is not None and (live := live_representations(conn, out.repo_ids.values())) != pad_to:
        raise plan.LoadFailed(f"{live} live representations after padding, not {pad_to}")
    return out


def _build(conn, embed, repo, p, ws, copies, full_names, spec, context_exceeded, clock) -> timedelta:
    start = clock()
    desired, claim = s6.push_and_claim(conn, repo, claim_for=plan.LEASE)
    gen = s6.new_generation(conn, repo, spec, desired=desired, base=None)
    rep_at: dict[tuple[str, int], int] = {}
    for w in ws:
        try:
            rep_at[(w.path, w.first_line)] = s6.index_chunk(
                conn,
                embed,
                repo_id=repo,
                generation_id=gen,
                spec=spec,
                header=plan.header(full_names[w.github_repo_id], w.path),
                body=w.text,
                path=w.path,
                start_line=w.first_line,
            )
        except context_exceeded as e:
            raise plan.retry_failed(w, getattr(e, "error", str(e))) from e
    for pad in copies:
        source = rep_at[(pad.source.path, pad.source.first_line)]
        s6.pad_copy(conn, repo_id=repo, generation_id=gen, spec=spec, source=source, row=pad.row)
    s6.finish_build(conn, gen)
    try:
        s6.activate(conn, repo_id=repo, new=gen, base=None, desired=desired, claim=claim)
    except s6.ActivationRefused as e:
        raise plan.LoadFailed(f"pseudo-repository {p}: activation refused ({e})") from e
    elapsed = timedelta(seconds=clock() - start)
    plan.check_lease(p, elapsed)
    return elapsed
