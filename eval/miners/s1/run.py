"""S1's runner: measure ADR-0016's ten candidates, select the corpus, write the pairs file and manifest.

`measure` is the only part that touches the network (GraphQL through `github.Client`, a mirror clone
through `repo.mirror`). Everything after it is `s1.corpus`, which is pure.

usage: WAYFINDER_S1_TOKEN=<classic token with no scopes> python -m s1.run [out_dir]
"""

from __future__ import annotations

import datetime as dt
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from . import corpus, github, license, pairs, repo

ADR_0016 = (
    ("pallets/flask", "py"),
    ("pallets/click", "py"),
    ("encode/httpx", "py"),
    ("psf/requests", "py"),
    ("python-attrs/attrs", "py"),
    ("spf13/cobra", "go"),
    ("go-chi/chi", "go"),
    ("urfave/cli", "go"),
    ("gin-gonic/gin", "go"),
    ("charmbracelet/bubbletea", "go"),
)
# R-03 step 1 appends here, in a pull request that names the new candidates before they are measured.
CANDIDATES = ADR_0016


def widened(candidates: tuple[tuple[str, str], ...]) -> bool:
    """False for ADR-0016's list, True for it with new candidates appended after it (R-03 step 1).

    Any other change (a reordering, removal, replacement or a repeated candidate) is not a widening
    and fails closed (review of #66), since ADR-0016's list is closed and only grows by appending.
    """
    slugs = [slug for slug, _ in candidates]
    if tuple(candidates[: len(ADR_0016)]) != ADR_0016 or len(set(slugs)) != len(slugs):
        raise ValueError("CANDIDATES must be ADR-0016's ten, in order, with any new candidates appended")
    return len(candidates) > len(ADR_0016)


MIN_LINKED, MIN_RESOLVED = 100, 0.95  # S1-2, S1-3
MIN_MD_FILES, MIN_MD_WORDS = 5, 2000  # S1-4


def measure(
    client: github.Client, slug: str, lang: str, workdir: Path, as_of: dt.datetime = corpus.AS_OF
) -> dict:
    """One candidate's S1-1 to S1-5 and chunk estimate, and its linked pairs with gold files."""
    owner, name = slug.split("/")
    first_response = len(client.scopes_seen)
    meta = github.repo(client, owner, name)
    git_dir = repo.mirror(f"https://github.com/{slug}.git", workdir / f"{owner}__{name}.git")
    commit = repo.as_of_commit(git_dir, meta.default_branch, as_of)
    if commit is None:
        raise RuntimeError(f"{slug}: no commit on {meta.default_branch} before {as_of.isoformat()}")
    file_id, file_reason = license.file_spdx(git_dir, commit)
    size = repo.measure(git_dir, commit)
    linked = list(github.linked_pairs(client, owner, name, meta.github_repo_id, as_of))
    found, gold_by_pr = [], {}
    for p in linked:
        base, reason = repo.resolve(git_dir, p.first_commit, p.head)
        gold = []
        if reason is None:
            if p.pr not in gold_by_pr:
                gold_by_pr[p.pr] = pairs.gold_files(repo.changed(git_dir, base, p.head))
            gold = gold_by_pr[p.pr]
        strong = not pairs.weak(p.issue_updated_at, p.merged_at)
        found.append(
            {
                "repo_id": meta.github_repo_id,
                "issue": p.issue,
                "pr": p.pr,
                "base": base,
                "reason": reason,
                "gold": gold,
                "strong": strong,
                "merged_at": p.merged_at,
            }
        )
    seen = client.scopes_seen[first_response:]
    s1_1 = license.s1_1(file_id, meta.api_spdx)
    s1_1["value"]["file_reason"] = file_reason  # why the clone gave no id (review of #66)
    resolved = sum(f["base"] is not None for f in found)
    rate = resolved / len(found) if found else 0.0
    rules = {
        "S1-1": s1_1,
        "S1-2": {"value": len(found), "pass": len(found) >= MIN_LINKED},
        "S1-3": {
            "value": {"resolved": resolved, "of": len(found)},
            "pass": bool(found) and rate >= MIN_RESOLVED,
        },
        "S1-4": {
            "value": {"md_files": size.md_files, "md_words": size.md_words},
            "pass": size.md_files >= MIN_MD_FILES and size.md_words >= MIN_MD_WORDS,
        },
        # What was observed (review of #66): every response's scope header, and how many were checked.
        "S1-5": {
            "value": {"x_oauth_scopes": sorted(set(seen)), "responses_checked": len(seen), "clone": "https"},
            "pass": bool(seen) and set(seen) == {""},
        },
    }
    entry = {
        "repo": slug,
        "github_repo_id": meta.github_repo_id,
        "lang": lang,
        "as_of_commit": commit,
        "spdx": file_id,
        "rules": rules,
        "file_count": size.file_count,
        "chunk_estimate": size.chunk_estimate,
    }
    return {"entry": entry, "pairs": found}


# The miner and the schema that validates its output (review of #66), relative to eval/.
INPUTS = ("miners", "datasets/manifest.schema.json")


def _miner_commit() -> str:
    """HEAD, refused if any input has uncommitted changes, since the manifest pins the miner by commit."""
    here = Path(__file__).parents[2]  # eval
    if subprocess.run(
        ["git", "status", "--porcelain", "--", *INPUTS], cwd=here, capture_output=True, text=True
    ).stdout:
        raise RuntimeError("uncommitted changes in eval/miners or the manifest schema; commit before running")
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=here, capture_output=True, text=True, check=True
    ).stdout.strip()


def main(argv: list[str]) -> int:
    out = Path(argv[0]) if argv else Path(__file__).parents[2] / "datasets" / "s1"
    token = os.environ.get("WAYFINDER_S1_TOKEN")
    if not token:
        print(
            "WAYFINDER_S1_TOKEN is not set (a classic token with no scopes, ADR-0016 S1-5)", file=sys.stderr
        )
        return 2
    wide = widened(CANDIDATES)  # before any network call
    commit = _miner_commit()
    client = github.Client(github.urllib_transport(token))
    with tempfile.TemporaryDirectory(prefix="s1-") as tmp:  # the clones never outlive the run
        measured = []
        for slug, lang in CANDIDATES:
            measured.append(measure(client, slug, lang, Path(tmp)))
            e = measured[-1]["entry"]
            print(f"{slug}: {json.dumps({k: v['pass'] for k, v in e['rules'].items()})}", file=sys.stderr)
    data, manifest = corpus.build(measured, commit, client.calls, widened=wide)
    out.mkdir(parents=True, exist_ok=True)
    (out / "pairs.jsonl").write_bytes(data)
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    last = manifest["selection_rounds"][-1]
    print(
        f"selected {manifest['selected']} at max_files {last['max_files']}; "
        f"strong {manifest['pairs_file']['strong_count']} (A-3 bar {corpus.A3_BAR}); calls {client.calls}",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
