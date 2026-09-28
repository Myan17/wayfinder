"""ADR-0016's file universe and chunk estimate: seven exclusion steps, then ceil(lines / 60)."""

from __future__ import annotations

import math
import re
from pathlib import PurePosixPath

EXTENSIONS = (".py", ".pyi", ".go", ".md")
TEST_DIRS = {"test", "tests", "testdata"}
TEST_NAMES = (re.compile(r"test_.*\.py"), re.compile(r".*_test\.py"), re.compile(r".*_test\.go"),
              re.compile(r"conftest\.py"))
VENDOR_DIRS = {"vendor", "third_party", "_vendor"}
GENERATED_NAMES = (re.compile(r".*_pb2\.pyi?"), re.compile(r".*\.pb\.go"))
GO_GENERATED = re.compile(rb"^// Code generated .* DO NOT EDIT\.$")
MARKDOWN_NAMES = (re.compile(r"CHANGELOG.*"), re.compile(r"CHANGES.*"), re.compile(r"LICENSE.*"))
CHUNK_LINES = 60


def excluded(path: str, mode: str, content: bytes | None) -> str | None:
    """The first ADR-0016 step that excludes the file, or None if it is in the universe.

    `content` is None when only the path is known (a file deleted by a pull request); the two
    content steps (Go's generated header, UTF-8) are then skipped.
    """
    p = PurePosixPath(path)
    dirs, name = set(p.parts[:-1]), p.name
    if mode not in ("100644", "100755"):
        return "not a regular file"
    if p.suffix not in EXTENSIONS:
        return "extension"
    if dirs & TEST_DIRS or any(r.fullmatch(name) for r in TEST_NAMES):
        return "test"
    if dirs & VENDOR_DIRS:
        return "vendored"
    if any(r.fullmatch(name) for r in GENERATED_NAMES):
        return "generated"
    if p.suffix == ".go" and content is not None and any(
            GO_GENERATED.match(line) for line in content.split(b"\n")[:10]):
        return "generated"
    if p.suffix == ".md" and (any(r.fullmatch(name) for r in MARKDOWN_NAMES) or ".github" in p.parts[:-1]):
        return "markdown"
    if content is not None:
        try:
            content.decode("utf-8")
        except UnicodeDecodeError:
            return "binary"
    return None


def lines(content: bytes) -> int:
    """Count of \\n bytes, plus 1 if the file is non-empty and does not end in \\n."""
    return content.count(b"\n") + (1 if content and not content.endswith(b"\n") else 0)


def chunks(content: bytes) -> int:
    return math.ceil(lines(content) / CHUNK_LINES)
