"""ADR-0021 rules 4 and 5: what the reviewer watcher does with a verdict. Code decides; the model advises.

Each gate is one function returning `(ok, reason)`. `decide` turns the mode, the verdict and the gates
into one action. Only `approve_and_merge` lets the watcher approve, and only when the mode is `on` and
every gate holds. `shadow` never gets further than `would_approve`.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass

from reviewbus import tier as tier_

MODES = ("off", "shadow", "on")
VERDICTS = ("approve", "changes", "needs_human")
MAX_ROUND = 3
FINDING = {"id": str, "file": str, "severity": str, "blocking": bool, "text": str}
SEVERITIES = ("high", "medium", "low")
_SHA = re.compile(r"[0-9a-f]{40}")
# actions, from least to most the watcher may do
NONE, ESCALATE, NEEDS_HUMAN, REQUEST_CHANGES, WOULD_APPROVE, APPROVE = (
    "none", "escalate", "needs_human", "request_changes", "would_approve", "approve_and_merge",
)  # fmt: skip


@dataclass(frozen=True)
class Review:
    mode: str
    round: int
    reviewed_head: str  # the full sha the model reviewed
    pr_head: str  # the PR's head now
    files: Sequence[str]
    checks: Mapping[str, str]  # required check name -> conclusion on reviewed_head
    required: Sequence[str]
    description: str
    verdict: object  # the model's parsed JSON, unchecked
    tier: Sequence[str]


def verdict_problem(v: object) -> str | None:
    """None when the verdict matches the schema in prompts/review.md."""
    if not isinstance(v, dict):
        return "the verdict is not a JSON object"
    if v.get("verdict") not in VERDICTS:
        return f"verdict {v.get('verdict')!r} is not one of {VERDICTS}"
    findings = v.get("findings")
    if not isinstance(findings, list):
        return "findings is not a list"
    for i, f in enumerate(findings):
        if not isinstance(f, dict):
            return f"finding {i} is not an object"
        for key, kind in FINDING.items():
            if type(f.get(key)) is not kind:
                return f"finding {i} has no {kind.__name__} {key!r}"
        if f["severity"] not in SEVERITIES:
            return f"finding {i} has severity {f['severity']!r}, not one of {SEVERITIES}"
        if "line" not in f or not (f["line"] is None or (type(f["line"]) is int and f["line"] >= 1)):
            return f"finding {i} needs a line that is null or a positive integer"
    return None


def blocking(v: dict) -> list[dict]:
    return [f for f in v["findings"] if f["blocking"]]


def switch(r: Review) -> tuple[bool, str]:
    return r.mode == "on", f"WAYFINDER_AGENT_APPROVAL is {r.mode}"


def canonical(path: object) -> bool:
    """A repository-relative path as git prints it: no leading ./ or /, no . or .. segment, no
    doubled or trailing slash, no backslash. Anything else could slip past a tier glob."""
    return (
        isinstance(path, str)
        and bool(path)
        and "\\" not in path
        and all(part not in ("", ".", "..") for part in path.split("/"))
    )


def no_tier_path(r: Review) -> tuple[bool, str]:
    if not isinstance(r.files, (list, tuple)) or not r.files:
        return False, "no list of changed files was given; refusing rather than treating none as safe"
    if odd := [f for f in r.files if not canonical(f)]:
        return False, f"changed paths not in canonical repository-relative form: {odd!r}"
    if not r.tier:
        return False, "no human-only tier was given; refusing rather than treating every path as safe"
    hits = tier_.human_only(r.files, r.tier)
    return not hits, f"human-only tier: {hits}" if hits else "no human-only path"


def heads_problem(r: Review) -> str | None:
    for name in ("reviewed_head", "pr_head"):
        if not isinstance(getattr(r, name), str) or not _SHA.fullmatch(getattr(r, name)):
            return f"{name} {getattr(r, name)!r} is not a full commit sha"
    return None


def checks_green(r: Review) -> tuple[bool, str]:
    if problem := heads_problem(r):
        return False, problem
    if r.pr_head != r.reviewed_head:
        return False, f"the head moved from {r.reviewed_head[:7]} to {r.pr_head[:7]} after the review"
    if not r.required:
        return False, "no required checks were given; refusing rather than treating none as green"
    bad = {c: r.checks.get(c, "missing") for c in r.required if r.checks.get(c) != "success"}
    return not bad, f"required checks not green: {bad}" if bad else "every required check is green"


def verdict_clean(r: Review) -> tuple[bool, str]:
    if problem := verdict_problem(r.verdict):
        return False, problem
    hits = blocking(r.verdict)  # type: ignore[arg-type]
    return not hits, f"{len(hits)} blocking finding(s)" if hits else "no blocking finding"


def description_current(r: Review) -> tuple[bool, str]:
    """The description names the reviewed head: at least its first 7 characters, as a whole word."""
    if problem := heads_problem(r):
        return False, problem
    short = r.reviewed_head[:7]
    named = re.search(rf"(?<![0-9a-f]){re.escape(short)}[0-9a-f]*(?![0-9a-f])", r.description)
    ok = bool(named) and r.reviewed_head.startswith(named.group(0))
    return ok, f"the description {'names' if ok else 'lacks'} {short}"


def round_ok(r: Review) -> tuple[bool, str]:
    ok = type(r.round) is int and 1 <= r.round <= MAX_ROUND
    return ok, f"round {r.round} of {MAX_ROUND}"


GATES: tuple[tuple[str, Callable[[Review], tuple[bool, str]]], ...] = (
    ("a", switch),
    ("b", no_tier_path),
    ("c", checks_green),
    ("d", verdict_clean),
    ("e", description_current),
    ("f", round_ok),
)


@dataclass(frozen=True)
class Decision:
    action: str
    gates: dict[str, tuple[bool, str]]


def decide(r: Review) -> Decision:
    if r.mode not in MODES:
        raise ValueError(f"unknown mode {r.mode!r}; the watcher treats it as off")
    gates = {name: g(r) for name, g in GATES}
    if r.mode == "off":
        return Decision(NONE, gates)
    if not gates["f"][0]:
        return Decision(ESCALATE, gates)  # rule 10: after three rounds both sides stop
    if verdict_problem(r.verdict):
        return Decision(NEEDS_HUMAN, gates)
    v: dict = r.verdict  # type: ignore[assignment]
    if v["verdict"] == "changes" or blocking(v):
        return Decision(REQUEST_CHANGES, gates)  # allowed in every mode but off (rule 4)
    if v["verdict"] == "needs_human":
        return Decision(NEEDS_HUMAN, gates)
    if r.mode == "shadow":
        return Decision(WOULD_APPROVE, gates)
    return Decision(APPROVE if all(ok for ok, _ in gates.values()) else NEEDS_HUMAN, gates)
