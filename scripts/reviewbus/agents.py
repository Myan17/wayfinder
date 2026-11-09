"""Run the reviewer's model, ChatGPT through the Codex CLI, and parse what it returns (ADR-0021 rules 3, 9).

One `codex exec` per review or ruling: a read-only sandbox over the PR's checkout, no session kept, its
stdin closed, its answer constrained by a JSON schema and written to a file. Its environment carries no
GitHub token and no gh config directory, so the model can never act on GitHub (rule 3). Text the PR
supplies goes inside a fence whose delimiter is random per run, so the PR cannot close it (rule 9).
Whatever comes back is parsed and checked here; anything else raises `AgentError`, which the watcher
turns into `needs_human`. Code decides what is posted; the model only advises.
"""

from __future__ import annotations

import json
import os
import re
import secrets
import subprocess
import tempfile
from collections.abc import Callable, Sequence
from pathlib import Path
from string import Template

from reviewbus import gates

PROMPTS = Path(__file__).resolve().parent / "prompts"
TIMEOUT_S = 1800
SECRETS = ("GH_TOKEN", "GITHUB_TOKEN", "GH_ENTERPRISE_TOKEN", "GITHUB_ENTERPRISE_TOKEN", "GH_CONFIG_DIR")
FINDING = {
    "type": "object",
    "additionalProperties": False,
    "required": ["id", "file", "line", "severity", "blocking", "text"],
    "properties": {
        "id": {"type": "string"},
        "file": {"type": "string"},
        "line": {"type": ["integer", "null"]},
        "severity": {"type": "string", "enum": list(gates.SEVERITIES)},
        "blocking": {"type": "boolean"},
        "text": {"type": "string"},
    },
}
SCHEMAS = {
    "review": {
        "type": "object",
        "additionalProperties": False,
        "required": ["verdict", "findings", "summary"],
        "properties": {
            "verdict": {"type": "string", "enum": list(gates.VERDICTS)},
            "findings": {"type": "array", "items": FINDING},
            "summary": {"type": "string"},
        },
    },
    "ruling": {
        "type": "object",
        "additionalProperties": False,
        "required": ["decision", "rationale"],
        "properties": {"decision": {"type": "string"}, "rationale": {"type": "string"}},
    },
}
Run = Callable[[list[str], dict[str, str]], None]  # argv, env; raises on failure


_SHA = re.compile(r"[0-9a-f]{40}")
_ID = re.compile(r"[A-Za-z0-9._-]{1,32}")


class AgentError(RuntimeError):
    """The model gave no usable answer; the watcher hands the PR to a human."""


def check_ids(pr: object, head: object, base: object) -> None:
    """The values placed outside the fence must be what they claim: a PR number and two commit shas."""
    if type(pr) is not int or pr < 1:
        raise AgentError(f"pull request number {pr!r} is not a positive integer")
    for name, sha in (("head", head), ("base", base)):
        if type(sha) is not str or not _SHA.fullmatch(sha):
            raise AgentError(f"{name} {sha!r} is not a full commit sha")


def subprocess_run(argv: list[str], env: dict[str, str]) -> None:
    subprocess.run(
        argv, env=env, stdin=subprocess.DEVNULL, capture_output=True, check=True, timeout=TIMEOUT_S
    )


def env() -> dict[str, str]:
    return {k: v for k, v in os.environ.items() if k not in SECRETS}


def fenced(data: str) -> tuple[str, str]:
    """A delimiter the data cannot contain, since it is chosen after the data is fixed."""
    while True:
        fence = f"----- PR DATA {secrets.token_hex(16)} -----"
        if fence not in data:
            return fence, data


def prompt(kind: str, fields: dict[str, str], data: str) -> str:
    fence, data = fenced(data)
    return Template((PROMPTS / f"{kind}.md").read_text()).substitute(fields, fence=fence, data=data)


def ask(kind: str, workdir: Path, text: str, model: str | None, run: Run) -> dict:
    with tempfile.TemporaryDirectory() as tmp:
        schema, out = Path(tmp) / "schema.json", Path(tmp) / "answer.json"
        schema.write_text(json.dumps(SCHEMAS[kind]))
        argv = ["codex", "exec", "--sandbox", "read-only", "--ephemeral", "--skip-git-repo-check",
                "-C", str(workdir), "--output-schema", str(schema), "-o", str(out)]  # fmt: skip
        if model:
            argv += ["-m", model]
        try:
            run([*argv, "--", text], env())
            answer = json.loads(out.read_text())
        except (subprocess.SubprocessError, OSError, ValueError) as e:
            raise AgentError(f"codex gave no usable {kind}: {type(e).__name__}: {e}") from e
    if type(answer) is not dict:
        raise AgentError(f"codex's {kind} is not a JSON object")
    return answer


def review(
    workdir: Path, pr: int, head: str, base: str, data: str, *, model=None, run=subprocess_run
) -> dict:
    """The model's verdict on the checkout at `workdir`, checked against gates' schema."""
    check_ids(pr, head, base)
    answer = ask(
        "review", workdir, prompt("review", {"pr": str(pr), "head": head, "base": base}, data), model, run
    )
    if problem := gates.verdict_problem(answer):
        raise AgentError(f"codex's verdict does not match the schema: {problem}")
    return answer


def ruling(
    workdir: Path,
    pr: int,
    head: str,
    question_id: str,
    options: Sequence[str],
    data: str,
    *,
    model=None,
    run=subprocess_run,
) -> dict:
    """The model's decision, which must be one of `options` exactly."""
    check_ids(pr, head, head)
    if type(question_id) is not str or not _ID.fullmatch(question_id):
        raise AgentError(f"question id {question_id!r} is not 1-32 of [A-Za-z0-9._-]")
    if type(options) is not list or not options or any(type(o) is not str or not o for o in options):
        raise AgentError("a ruling needs a non-empty list of options")
    listed = "\n".join(f"- {json.dumps(o)}" for o in options)
    fields = {"pr": str(pr), "head": head, "question_id": question_id, "options": listed}
    answer = ask("ruling", workdir, prompt("ruling", fields, data), model, run)
    if answer.get("decision") not in options or type(answer.get("rationale")) is not str:
        raise AgentError(f"codex's ruling {answer.get('decision')!r} is not one of the options")
    return answer
