"""The size guardrail exempts the task's own log and three exact paths, and nothing that merely
resembles them.

Each exemption (db/schema.sql, 2026-09-23; the S1 pairs file, #50; the S1 manifest, 2026-10-17) is
only safe if it is exact: a pattern match would let any file named like it, anywhere, escape the limit.
"""

import importlib.util
import pathlib
import subprocess
import sys

import pytest

MODULE = pathlib.Path(__file__).resolve().parents[1] / "check_pr_size.py"
spec = importlib.util.spec_from_file_location("check_pr_size", MODULE)
size = importlib.util.module_from_spec(spec)
sys.modules["check_pr_size"] = size
spec.loader.exec_module(size)

BRANCH = "myan/schema/snapshot"
LOG = "docs/agent-log/myan-schema-snapshot.md"


def numstat(*rows: tuple[int, int, str]) -> str:
    return "\n".join(f"{a}\t{d}\t{p}" for a, d, p in rows)


def test_root_schema_snapshot_is_exempt():
    rows = numstat((1104, 0, "db/schema.sql"), (40, 0, "db/dump-schema.sh"))
    counted, exempted, _ = size.tally(rows, BRANCH)
    assert (counted, exempted) == (40, 1104)


def test_task_log_is_still_exempt():
    counted, exempted, _ = size.tally(numstat((90, 0, LOG), (10, 0, "scripts/x.py")), BRANCH)
    assert (counted, exempted) == (10, 90)


@pytest.mark.parametrize("path", [
    "db/schema.sql.bak",
    "db/schema.sqlx",
    "db/Schema.sql",
    "db/schema/sql",
    "sub/db/schema.sql",
    "apps/api/db/schema.sql",
    "schema.sql",
    "db/schema.sql/extra",
    "./db/schema.sql",
    "db/{old => schema.sql}",
])
def test_lookalike_paths_still_count(path):
    counted, exempted, _ = size.tally(numstat((500, 0, path)), BRANCH)
    assert (counted, exempted) == (500, 0)


@pytest.mark.parametrize("path", ["uv.lock", ".github/CODEOWNERS", "db/views/retrieval_rows.sql"])
def test_other_generated_files_still_count(path):
    counted, exempted, _ = size.tally(numstat((450, 0, path)), BRANCH)
    assert (counted, exempted) == (450, 0)


def test_another_tasks_log_counts():
    counted, exempted, _ = size.tally(numstat((70, 0, "docs/agent-log/myan-other-task.md")), BRANCH)
    assert (counted, exempted) == (70, 0)


def test_end_to_end_rename_into_the_snapshot_path_counts_the_delete(tmp_path):
    """With --no-renames, moving a file onto db/schema.sql cannot smuggle its old path's lines out."""
    def git(*args):
        return subprocess.run(["git", "-C", str(tmp_path), *args], check=True, capture_output=True, text=True)

    git("init", "-q", "-b", "main")
    git("config", "user.email", "t@example.invalid")
    git("config", "user.name", "t")
    (tmp_path / "db").mkdir()
    (tmp_path / "db" / "big.sql").write_text("x\n" * 500)
    git("add", ".")
    git("commit", "-q", "-m", "base")
    git("checkout", "-q", "-b", "feature")
    git("mv", "db/big.sql", "db/schema.sql")
    git("commit", "-q", "-m", "move")

    out = subprocess.run(
        [sys.executable, str(MODULE), "main", "feature", "--branch", BRANCH],
        cwd=tmp_path, capture_output=True, text=True,
    )
    assert out.returncode == 1, out.stdout          # 500 deleted lines of db/big.sql still count
    assert "500 changed lines" in out.stdout


def test_the_s1_pairs_dataset_is_exempt_at_its_exact_path():
    # Reviewer ruling on #50 (2026-09-28): the generated S1 dataset is reviewed mechanically.
    rows = numstat((1200, 0, "eval/datasets/s1/pairs.jsonl"), (30, 0, "eval/datasets/manifest.schema.json"))
    counted, exempted, _ = size.tally(rows, BRANCH)
    assert (counted, exempted) == (30, 1200)                       # the schema still counts


def test_the_s1_manifest_is_exempt_at_its_exact_path():
    # Reviewer ruling, 2026-10-17: the generated S1 manifest is reviewed mechanically, like the pairs.
    rows = numstat(
        (4740, 0, "eval/datasets/s1/manifest.json"),
        (2206, 0, "eval/datasets/s1/pairs.jsonl"),
        (60, 0, "docs/adr/ADR-0016-source-modes-and-s1-acceptance.md"),
    )
    counted, exempted, _ = size.tally(rows, BRANCH)
    assert (counted, exempted) == (60, 6946)                       # the Decision's prose still counts


@pytest.mark.parametrize("path", [
    "eval/datasets/s1/pairs.json",
    "eval/datasets/s1/pairs.jsonl.bak",
    "eval/datasets/s2/pairs.jsonl",
    "eval/datasets/pairs.jsonl",
    "eval/datasets/s1/sample/pairs.jsonl",
    "./eval/datasets/s1/pairs.jsonl",
    "eval/datasets/s1/{old => pairs.jsonl}",
])
def test_dataset_lookalike_paths_still_count(path):
    counted, exempted, _ = size.tally(numstat((500, 0, path)), BRANCH)
    assert (counted, exempted) == (500, 0)


@pytest.mark.parametrize("path", [
    "eval/datasets/s1/manifest.jsonl",
    "eval/datasets/s1/manifest.json.bak",
    "eval/datasets/s1/Manifest.json",
    "eval/datasets/s2/manifest.json",
    "eval/datasets/manifest.json",
    "eval/datasets/manifest.schema.json",
    "eval/datasets/s1/sample/manifest.json",
    "./eval/datasets/s1/manifest.json",
    "eval/datasets/s1/manifest.json/extra",
    "eval/datasets/s1/{old => manifest.json}",
])
def test_manifest_lookalike_paths_still_count(path):
    counted, exempted, _ = size.tally(numstat((500, 0, path)), BRANCH)
    assert (counted, exempted) == (500, 0)


def test_end_to_end_rename_into_the_manifest_path_counts_the_delete(tmp_path):
    """With --no-renames, moving a file onto the S1 manifest path cannot smuggle its old lines out."""
    def git(*args):
        return subprocess.run(["git", "-C", str(tmp_path), *args], check=True, capture_output=True, text=True)

    git("init", "-q", "-b", "main")
    git("config", "user.email", "t@example.invalid")
    git("config", "user.name", "t")
    (tmp_path / "eval" / "datasets" / "s1").mkdir(parents=True)
    (tmp_path / "eval" / "notes.json").write_text("x\n" * 500)
    git("add", ".")
    git("commit", "-q", "-m", "base")
    git("checkout", "-q", "-b", "feature")
    git("mv", "eval/notes.json", "eval/datasets/s1/manifest.json")
    git("commit", "-q", "-m", "move")

    out = subprocess.run(
        [sys.executable, str(MODULE), "main", "feature", "--branch", BRANCH],
        cwd=tmp_path, capture_output=True, text=True,
    )
    assert out.returncode == 1, out.stdout          # 500 deleted lines of eval/notes.json still count
    assert "500 changed lines" in out.stdout
