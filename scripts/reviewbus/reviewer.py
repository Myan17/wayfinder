"""The reviewer's pass over one pull request (REVIEW-BUS.md §2 and §4), run as gupta958.

Read the mode, the PR and its comments; act only when the state is `requested`; check the PR out at
its head in a throwaway worktree; ask Codex; let `gates.decide` choose the action; post the
`review_result`; and approve and merge only for `approve_and_merge` in `on` mode, pinned to the
reviewed head. Shadow mode never approves or merges. If the head moves while the model works,
nothing is posted, and the next pass sees the new request. `dry_run` posts nothing at all.
"""

from __future__ import annotations

import contextlib
import subprocess
import tempfile
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from pathlib import Path

from reviewbus import agents, gates, protocol, state, tier
from reviewbus.github import GitHub

MODE = "WAYFINDER_AGENT_APPROVAL"
POSTED = {  # decide()'s action -> the verdict the review_result carries
    gates.APPROVE: "approve",
    gates.WOULD_APPROVE: "approve",
    gates.REQUEST_CHANGES: "changes",
    gates.NEEDS_HUMAN: "needs_human",
    gates.ESCALATE: "needs_human",  # rule 8 keeps `escalate` for Myan17; the round limit asks him here
}


@dataclass(frozen=True)
class Config:
    repo_dir: Path  # a local clone the watcher may fetch into and add worktrees to
    required: list[str] = field(default_factory=list)  # the required check names, from branch protection
    model: str | None = None


@contextlib.contextmanager
def checkout(repo_dir: Path, pr: int, head: str) -> Iterator[Path]:
    """The PR at `head`, detached, in a temporary worktree removed afterwards. Public repository:
    fetching needs no credentials, and git runs with none."""
    git = ["git", "-C", str(repo_dir)]
    subprocess.run([*git, "fetch", "--quiet", "origin", "main", f"pull/{pr}/head"], check=True, timeout=300)
    with tempfile.TemporaryDirectory(prefix="reviewbus-") as tmp:
        wt = Path(tmp) / "wt"
        subprocess.run(
            [*git, "worktree", "add", "--quiet", "--detach", str(wt), head], check=True, timeout=300
        )
        try:
            yield wt
        finally:
            subprocess.run([*git, "worktree", "remove", "--force", str(wt)], check=False, timeout=300)


def pr_text(pull: dict, comments: list[dict]) -> str:
    """What the model sees as data: the description, then every comment with its author."""
    lines = ["Description:", pull["body"], "", "Comments:"]
    lines += [f"--- {c['author']}:\n{c['body']}" for c in comments]
    return "\n".join(lines)


def result_text(action: str, verdict: dict, decision: gates.Decision, round_: int) -> str:
    head = {
        gates.WOULD_APPROVE: f"**Would approve** (shadow mode, round {round_}). Approve and merge are yours.",
        gates.APPROVE: f"**Approved** (round {round_}); every gate holds.",
        gates.REQUEST_CHANGES: f"**Changes requested** (round {round_}).",
        gates.NEEDS_HUMAN: f"**Needs a human** (round {round_}).",
        gates.ESCALATE: f"**Stopped after {gates.MAX_ROUND} rounds** without a pass (rule 10).",
    }[action]
    findings = [f"{i}. [{'blocking' if f['blocking'] else f['severity']}] {f['file']}"
                f"{':' + str(f['line']) if f['line'] else ''} — {f['text']}"
                for i, f in enumerate(verdict.get("findings", []), 1)]  # fmt: skip
    failed = [f"gate {k}: {why}" for k, (ok, why) in decision.gates.items() if not ok]
    return "\n".join(
        [head, "", verdict.get("summary", ""), *findings, *(["", "Gates:", *failed] if failed else [])]
    )


def review_pr(
    pr: int,
    gh: GitHub,
    cfg: Config,
    roster: str,
    *,
    dry_run: bool = False,
    ask: Callable[..., dict] = agents.review,
    open_checkout: Callable[[Path, int, str], contextlib.AbstractContextManager[Path]] = checkout,
) -> list[str]:
    """One pass; returns what it did, one line each, for the log."""
    mode = gh.variable(MODE)
    mode = mode if mode in gates.MODES else "off"
    if mode == "off":
        return [f"#{pr}: {MODE} is off; nothing done"]
    pull, comments = gh.pull(pr), gh.comments(pr)
    st = state.state(comments, pull["head"], roster)
    log = [f"#{pr}: skipped {why}" for why in st.ignored]
    if st.status != "requested":
        return [*log, f"#{pr}: state {st.status}; nothing to review"]
    try:
        with open_checkout(cfg.repo_dir, pr, pull["head"]) as wt:
            verdict = ask(wt, pr, pull["head"], pull["base"], pr_text(pull, comments),
                          visibility=gh.visibility(), model=cfg.model)  # fmt: skip
    except (agents.AgentError, subprocess.SubprocessError, OSError) as e:
        verdict = {"verdict": "needs_human", "findings": [], "summary": f"No usable review: {e}"}
        log.append(f"#{pr}: review failed: {e}")
    decision = gates.decide(gates.Review(
        mode=mode, round=st.round, reviewed_head=pull["head"], pr_head=gh.pull(pr)["head"],
        files=pull["files"], checks=pull["checks"], required=list(cfg.required), description=pull["body"],
        verdict=verdict, tier=list(tier.globs()),
    ))  # fmt: skip
    if not decision.gates["c"][0] and "moved" in decision.gates["c"][1]:
        return [*log, f"#{pr}: {decision.gates['c'][1]}; nothing posted, the next pass reviews the new head"]
    fields = {"pr": pr, "head": pull["head"][:12], "round": st.round, "verdict": POSTED[decision.action],
              "findings": verdict.get("findings", []), "model": cfg.model or "codex default",
              "gates": {k: ok for k, (ok, _) in decision.gates.items()}}  # fmt: skip
    body = protocol.build(
        "review_result", fields, result_text(decision.action, verdict, decision, st.round), roster
    )
    log.append(f"#{pr}: round {st.round} {decision.action}{' (dry run, not posted)' if dry_run else ''}")
    if dry_run:
        return log
    gh.comment(pr, body)
    if decision.action == gates.APPROVE and mode == "on":  # never in shadow: decide() cannot return it there
        gh.approve(pr, pull["head"], "Approved by the review bus: every ADR-0021 gate holds.")
        gh.merge(pr, pull["head"])
        log.append(f"#{pr}: approved and merged at {pull['head'][:12]}")
    return log
