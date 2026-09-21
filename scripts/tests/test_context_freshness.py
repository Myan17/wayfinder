"""Cards are verified against interface *content*, not against a commit.

A commit sha cannot survive the repository's own merge policy: squash merges discard branch commits,
so a card verified against one becomes unresolvable the moment it lands. Content hashes have no such
problem, which is the whole reason for this shape.
"""

import importlib.util
import pathlib
import re
import sys

MODULE = pathlib.Path(__file__).resolve().parents[1] / "check_context_freshness.py"
spec = importlib.util.spec_from_file_location("freshness", MODULE)
freshness = importlib.util.module_from_spec(spec)
sys.modules["freshness"] = freshness
spec.loader.exec_module(freshness)


def test_hash_changes_when_the_file_changes(tmp_path):
    f = tmp_path / "interface.py"
    f.write_text("def a(): ...\n")
    before = freshness.file_hash(f)

    f.write_text("def a(): ...\ndef b(): ...\n")

    assert freshness.file_hash(f) != before


def test_hash_is_stable_across_reads(tmp_path):
    f = tmp_path / "interface.py"
    f.write_text("def a(): ...\n")

    assert freshness.file_hash(f) == freshness.file_hash(f)


def test_front_matter_hashes_are_parsed(tmp_path):
    card = tmp_path / "card.md"
    card.write_text(
        "---\nmodule: x\ninterface_files:\n  - a.py\nverified_hashes:\n"
        '  "a.py": "abc123"\nverified_on: 2026-09-21\n---\n\n# x\n'
    )

    assert freshness.recorded_hashes(card.read_text()) == {"a.py": "abc123"}


def test_a_card_with_no_recorded_hash_for_an_existing_interface_is_stale(tmp_path, monkeypatch):
    (tmp_path / "docs" / "context" / "modules").mkdir(parents=True)
    (tmp_path / "iface.py").write_text("def a(): ...\n")
    card = tmp_path / "docs" / "context" / "modules" / "x.md"
    card.write_text("---\nmodule: x\ninterface_files:\n  - iface.py\nverified_on: 2026-09-21\n---\n\n# x\n")
    monkeypatch.chdir(tmp_path)

    assert freshness.main_with(cards_dir=tmp_path / "docs" / "context" / "modules", fix=None) == 1


def two_stale_cards(tmp_path):
    """Two modules, each with its own interface file, neither carrying a recorded hash."""
    cards = tmp_path / "docs" / "context" / "modules"
    cards.mkdir(parents=True)
    for module in ("alpha", "beta"):
        (tmp_path / f"{module}.py").write_text(f"def {module}(): ...\n")
        (cards / f"{module}.md").write_text(
            f"---\nmodule: {module}\ninterface_files:\n  - {module}.py\n"
            f"verified_on: 2026-09-21\n---\n\n# {module}\n"
        )
    return cards


def test_fixing_one_card_leaves_every_other_card_byte_for_byte_unchanged(tmp_path, monkeypatch):
    """--fix is an attestation that a human re-read *that* card. It must not touch the others.

    A --fix that refreshed every implemented card would record, on cards nobody opened, that they
    were verified. That is exactly the claim the guardrail exists to make impossible to fake.
    """
    cards = two_stale_cards(tmp_path)
    monkeypatch.chdir(tmp_path)
    untouched_before = (cards / "beta.md").read_bytes()

    assert freshness.main_with(cards_dir=cards, fix="alpha") == 0

    assert "verified_hashes" in (cards / "alpha.md").read_text()
    assert (cards / "beta.md").read_bytes() == untouched_before


def test_fix_without_a_named_card_refuses_and_changes_nothing(tmp_path, monkeypatch):
    cards = two_stale_cards(tmp_path)
    monkeypatch.chdir(tmp_path)
    before = {p.name: p.read_bytes() for p in cards.glob("*.md")}

    assert freshness.main_with(cards_dir=cards, fix="") == 2

    assert {p.name: p.read_bytes() for p in cards.glob("*.md")} == before


def test_no_message_tells_the_reader_to_run_a_bare_fix(tmp_path, monkeypatch, capsys):
    """Every instruction the tool prints must be a command that works.

    A message reading "record one with --fix" sends the reader to a command that exits 2. The
    guardrail's whole value is that its errors say what to do next, so a stale instruction is a
    defect in the guardrail, not a typo.
    """
    cards = two_stale_cards(tmp_path)
    monkeypatch.chdir(tmp_path)

    assert freshness.main_with(cards_dir=cards) == 1

    printed = capsys.readouterr().out
    assert "--fix alpha" in printed
    for line in printed.splitlines():
        if "--fix" in line:
            assert "--fix <module>" in line or re.search(r"--fix [a-z]", line), line


def test_the_command_line_cannot_express_a_bare_fix():
    """A bare `--fix` must reach main_with as "", the value it refuses, never as "fix everything"."""
    assert freshness.parse_fix([]) is None
    assert freshness.parse_fix(["--fix"]) == ""
    assert freshness.parse_fix(["--fix", "--quiet"]) == ""
    assert freshness.parse_fix(["--fix", "authz"]) == "authz"


def test_fix_on_a_module_with_no_card_refuses(tmp_path, monkeypatch):
    cards = two_stale_cards(tmp_path)
    monkeypatch.chdir(tmp_path)
    before = {p.name: p.read_bytes() for p in cards.glob("*.md")}

    assert freshness.main_with(cards_dir=cards, fix="gamma") == 2

    assert {p.name: p.read_bytes() for p in cards.glob("*.md")} == before
