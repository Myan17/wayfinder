"""The size guardrail exempts exactly two paths, and nothing that merely resembles them.

The db/schema.sql exemption (reviewer ruling, 2026-09-23) is only safe if it is exact: a pattern
match would let any file named like the snapshot, anywhere, escape the limit.
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
