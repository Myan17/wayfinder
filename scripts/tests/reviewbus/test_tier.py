import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # scripts/, for the reviewbus package
from reviewbus import tier

OWNERSHIP = """
```yaml
modules:
  authz:         {owner: myan, paths: ["apps/api/wayfinder/authz/**", "docs/context/modules/authz.md"]}
  egress:        {owner: myan, paths: ["apps/api/wayfinder/egress/**"]}
  webhooks:      {owner: myan, paths: ["apps/ingestd/internal/webhook/**"]}
  schema:        {owner: joint, paths: ["db/**", "docs/context/modules/schema.md"]}
  eval-harness:  {owner: myan, paths: ["eval/harness/**"]}
```
"""


@pytest.mark.parametrize(
    "path",
    [
        "db/migrations/0001.sql",
        "apps/api/wayfinder/authz/predicate.py",
        "docs/context/modules/schema.md",
        "AGENTS.md",
        "docs/adr/ADR-0021-review-bus.md",
        ".github/workflows/ci.yml",
        ".githooks/pre-push",
        "scripts/check_pr_size.py",
        "scripts/gen_codeowners.py",
        "scripts/reviewbus/gates.py",
        "scripts/tests/reviewbus/test_gates.py",
    ],
)
def test_each_rule_6_path_is_human_only(path):
    assert tier.human_only([path], tier.globs(OWNERSHIP)) == [path]


@pytest.mark.parametrize(
    "path",
    ["eval/harness/s2/passes.py", "scripts/orient.py", "dbx/x.py", "docs/context/modules/eval-harness.md"],
)
def test_other_paths_are_not(path):
    assert tier.human_only([path], tier.globs(OWNERSHIP)) == []


def test_a_path_added_to_a_security_module_joins_the_tier():
    added = OWNERSHIP.replace(
        '"apps/api/wayfinder/egress/**"', '"apps/api/wayfinder/egress/**", "infra/egress/**"'
    )
    assert tier.human_only(["infra/egress/proxy.conf"], tier.globs(added)) == ["infra/egress/proxy.conf"]


def test_a_missing_security_module_fails_closed():
    with pytest.raises(ValueError, match=r"\['webhooks'\]"):
        tier.globs(OWNERSHIP.replace("  webhooks:", "  hooks:"))
    with pytest.raises(ValueError, match="no yaml block"):
        tier.globs("no block")


def test_the_real_ownership_file_reads():
    g = tier.globs()
    assert "db/**" in g and "scripts/reviewbus/**" in g
