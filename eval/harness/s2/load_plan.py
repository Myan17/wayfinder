"""Spike S2's corpus load, part 1: the plan, exactly as ADR-0019 Amendments 1-3 pin it.

- Amendment 1 section 1: one window is one occurrence; identical embedded inputs in one
  pseudo-repository share a representation (BCR-1). The header is `{owner/name} · {path}`.
- Amendment 2: only a window Ollama rejects for exceeding the 2,048-token context is retried, once,
  truncated. Every truncated window is listed; a retry above 2,048 fails the load. The token-length
  distribution is over the accepted windows only.
- Amendment 3: each pseudo-repository is built within one 60-minute claim, and a longer build fails
  the load. Padding to 60,000 is split by largest remainder over distinct pre-padding
  representations, ties to the lower id; ascending id; sources cycle in path, then start-line
  order; one global row sequence from 0.

Everything here is pure. Part 2 runs the plan against the database through `db/s6_identity.py`.
"""

from __future__ import annotations

import sys
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import timedelta
from fractions import Fraction
from pathlib import Path

from s2.inputs import PSEUDO_REPOS, Window

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "db"))
import s6_identity

LEASE = timedelta(minutes=60)  # Amendment 3 section 1, through BCR-3
PADDED_TOTAL = 60_000  # Amendment 3 section 2
CONTEXT_TOKENS = 2048  # Amendment 2: nomic-embed-text's context


class LoadFailed(RuntimeError):
    """The load stops; nothing is retried with different choices."""


def header(full_name: str, path: str) -> str:
    return f"{full_name} · {path}"


def input_hash(w: Window, full_name: str, template: str) -> bytes:
    """The representation key's hash, computed as `index_chunk` computes it."""
    return s6_identity.input_hash(s6_identity.embedded_input(template, header(full_name, w.path), w.text))


def group(windows: Iterable[Window]) -> dict[int, list[Window]]:
    """Every pseudo-repository id, ascending, with its windows in path, then start-line order."""
    out: dict[int, list[Window]] = {p: [] for p in range(PSEUDO_REPOS)}
    for w in windows:
        out[w.pseudo_repo].append(w)
    for ws in out.values():
        ws.sort(key=lambda w: (w.path, w.first_line))
    return out


def sources(ws: Sequence[Window], full_names: Mapping[int, str], template: str) -> list[Window]:
    """A pseudo-repository's distinct representations, each at its first occurrence, in path, then
    start-line order. `ws` must already be in that order (as `group` returns it)."""
    seen: set[bytes] = set()
    out = []
    for w in ws:
        h = input_hash(w, full_names[w.github_repo_id], template)
        if h not in seen:
            seen.add(h)
            out.append(w)
    return out


def allocate(real: Mapping[int, int], total: int = PADDED_TOTAL) -> dict[int, int]:
    """Amendment 3 section 2: `total - sum(real)` copies, shared in proportion to `real` by largest
    remainder, equal remainders to the lower pseudo-repository id first."""
    have = sum(real.values())
    need = total - have
    if have <= 0 or need < 0:
        raise LoadFailed(f"cannot pad {have} representations to {total}")
    quotas = {p: Fraction(need * n, have) for p, n in sorted(real.items())}
    shares = {p: q.numerator // q.denominator for p, q in quotas.items()}
    left = need - sum(shares.values())
    for p in sorted(quotas, key=lambda p: (-(quotas[p] - shares[p]), p))[:left]:
        shares[p] += 1
    if sum(shares.values()) != need:
        raise AssertionError("largest remainder lost a copy")
    return shares


@dataclass(frozen=True)
class Pad:
    pseudo_repo: int
    source: Window  # the representation copied, at its first occurrence
    row: int  # pad_copy's row: unique across the run, from 0


def pads(per_repo_sources: Mapping[int, Sequence[Window]], shares: Mapping[int, int]) -> list[Pad]:
    """Ascending pseudo-repository id; within one, sources cycle in their given order."""
    out: list[Pad] = []
    for p in sorted(shares):
        srcs = per_repo_sources.get(p, [])
        if shares[p] and not srcs:
            raise LoadFailed(f"pseudo-repository {p} has {shares[p]} copies to make and no source")
        base = len(out)
        out.extend(Pad(p, srcs[i % len(srcs)], base + i) for i in range(shares[p]))
    return out


def check_lease(pseudo_repo: int, elapsed: timedelta) -> None:
    """Amendment 3 section 1: a build that outlived its claim fails the load; nothing extends it."""
    if elapsed > LEASE:
        raise LoadFailed(f"pseudo-repository {pseudo_repo}: build took {elapsed}, over the {LEASE} lease")


@dataclass(frozen=True)
class Truncated:
    github_repo_id: int
    pseudo_repo: int
    path: str
    start_line: int
    end_line: int
    prompt_eval_count: int  # the retry's
    error: str  # Ollama's raw rejection


def end_line(w: Window) -> int:
    return w.first_line + s6_identity.line_count(w.text) - 1


def retry_failed(w: Window, error: str) -> LoadFailed:
    """Amendment 2: the failure names the repository, path, start line, the context and the raw error."""
    return LoadFailed(f"{w.github_repo_id} {w.path}:{w.first_line} exceeds {CONTEXT_TOKENS:,}: {error}")


def embed_report(
    calls: Iterable, by_hash: Mapping[bytes, Sequence[Window]]
) -> tuple[list[int], list[Truncated]]:
    """From `s6_ollama.Call` records: the accepted windows' token counts (one per window, for the
    distribution) and every truncated window. A truncated retry above the context fails the load."""
    accepted: list[int] = []
    truncated: list[Truncated] = []
    for c in calls:
        ws = by_hash.get(c.input_hash)
        if not ws:
            raise AssertionError(f"embedded an input no window has: {c.input_hash.hex()}")
        if not c.truncated:
            accepted.extend(c.prompt_eval_count for _ in ws)
            continue
        if c.prompt_eval_count > CONTEXT_TOKENS:
            raise retry_failed(ws[0], f"retry counted {c.prompt_eval_count} tokens after: {c.error}")
        truncated.extend(
            Truncated(
                w.github_repo_id,
                w.pseudo_repo,
                w.path,
                w.first_line,
                end_line(w),
                c.prompt_eval_count,
                c.error,
            )
            for w in ws
        )
    return accepted, truncated
