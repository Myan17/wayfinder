"""Tests for the code map. Pure text handling; `git ls-files` and file reads are the inputs."""

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import codemap

OWNERSHIP = """
```yaml
modules:
  authz:         {owner: myan, paths: ["apps/api/wayfinder/authz/**", "docs/context/modules/authz.md"]}
  web:           {owner: myan, paths: ["apps/web/**", "docs/context/modules/web.md"]}
  platform:      {owner: myan, paths: ["apps/ingestd/go.sum", "apps/ingestd/cmd/**", "Makefile"]}
```
"""


def test_modules_come_from_the_ownership_block():
    mods = codemap.modules(OWNERSHIP)
    assert [m["name"] for m in mods] == ["authz", "web", "platform"]
    assert mods[0] == {"name": "authz", "owner": "myan",
                       "paths": ["apps/api/wayfinder/authz/**", "docs/context/modules/authz.md"]}


def test_globs_match_like_ownership_means_them():
    assert codemap.matches("apps/api/wayfinder/authz/x/y.py", "apps/api/wayfinder/authz/**")
    assert not codemap.matches("apps/api/wayfinder/authzz/y.py", "apps/api/wayfinder/authz/**")
    assert codemap.matches("Makefile", "Makefile") and not codemap.matches("Makefile.bak", "Makefile")


def test_a_module_counts_code_but_not_its_card_or_lock_files():
    files = {"apps/api/wayfinder/authz/a.py": 10, "docs/context/modules/authz.md": 99,
             "apps/ingestd/go.sum": 50, "apps/ingestd/cmd/s/main.go": 7, "README.md": 3}
    mods = codemap.modules(OWNERSHIP)
    assert codemap.footprint(mods[0], files) == (1, 10)
    assert codemap.footprint(mods[1], files) == (0, 0)           # web: nothing but its card
    assert codemap.footprint(mods[2], files) == (1, 7)           # go.sum is a lock file
    assert codemap.without_module(mods, files) == ["README.md"]


def test_a_scripts_purpose_is_its_first_header_line():
    assert codemap.purpose('#!/usr/bin/env python3\n"""Guardrail: stay small.\n\nMore."""\n') == \
        "Guardrail: stay small."
    assert codemap.purpose("#!/usr/bin/env bash\n# Start a task: do things.\n# usage: x\n") == \
        "Start a task: do things."
    assert codemap.purpose("print(1)\n") == ""


def test_ci_jobs_are_the_top_level_keys_under_jobs():
    yml = "on: [push]\njobs:\n  unit:\n    runs-on: x\n    steps:\n  db:\n    needs: unit\n"
    assert codemap.ci_jobs(yml) == ["unit", "db"]


def test_the_map_renders_on_the_real_repository():
    script = Path(codemap.__file__)
    out = subprocess.run([sys.executable, script.name], cwd=script.parent,
                         capture_output=True, text=True, timeout=60)
    assert out.returncode == 0, out.stderr
    for section in ("MODULES", "SCRIPTS", "MIGRATIONS", "ADRS", "CI", "DOCS"):
        assert section in out.stdout
    assert len(out.stdout) < 6000
    # Review of #37 (gupta958): a file with no module still has a reviewer, through CODEOWNERS' `*`
    assert "no OWNERSHIP module (review still routed by CODEOWNERS' catch-all *)" in out.stdout
    assert "nobody" not in out.stdout and "unowned" not in out.stdout                               # the point is to be cheap to read
