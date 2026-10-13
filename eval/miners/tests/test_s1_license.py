"""S1-1: SPDX ids from license texts, the root license file of a real repository, and the cross-check."""

import os
import re
import subprocess

import pytest
from s1 import license


def _render(sid):
    """The SPDX template with every variable at its original value and every optional part kept."""
    raw = (license.SPDX_TEMPLATES / f"{sid}.template.txt").read_text()
    return re.sub(r"<<(begin|end)Optional>>", "", license._MARK.sub(lambda m: m.group(1) or "", raw))


MIT, ISC, APACHE, BSD2, BSD3 = map(_render, ("MIT", "ISC", "Apache-2.0", "BSD-2-Clause", "BSD-3-Clause"))
# A slice of SPDX's license list; the run uses the whole pinned list (`load_identifiers`).
IDS = license.identifiers(
    ["MIT", "ISC", "BSD-2-Clause", "BSD-3-Clause", "Apache-2.0", "Zlib", "GPL-2.0-only"]
)


def spdx(text):
    return license.spdx(text, IDS)


# A real-world shape written by hand, independent of the templates: title, two holders, curly quotes.
EXPRESS = """(The MIT License)

Copyright (c) 2009-2014 A. Person <a@example.com>
Copyright (c) 2014-2015 B. Person <b@example.com>

Permission is hereby granted, free of charge, to any person obtaining
a copy of this software and associated documentation files (the
\u2018Software\u2019), to deal in the Software without restriction, including
without limitation the rights to use, copy, modify, merge, publish,
distribute, sublicense, and/or sell copies of the Software, and to
permit persons to whom the Software is furnished to do so, subject to
the following conditions:

The above copyright notice and this permission notice shall be
included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED \u2018AS IS\u2019, WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""


@pytest.mark.parametrize(
    ("text", "want"),
    [(MIT, "MIT"), (ISC, "ISC"), (APACHE, "Apache-2.0"), (BSD2, "BSD-2-Clause"), (BSD3, "BSD-3-Clause")],
)
def test_each_allowed_license_is_recognised_across_line_wrapping_and_case(text, want):
    assert spdx(text) == want
    i = text.find("Copyright")  # a leading title and copyright line stay whole; the license is rewrapped
    cut = text.index("\n\n", i) if i < 200 else 0
    assert spdx(text[:cut] + text[cut:].upper().replace(" ", "\n  ")) == want
    assert spdx("Copyright (c) 2026 Someone\nAll rights reserved.\n\n" + text) == want


def test_a_hand_written_mit_file_with_title_holders_and_curly_quotes_is_mit():
    assert spdx(EXPRESS) == "MIT"


@pytest.mark.parametrize("other", ["BSD-2-Clause", "Apache-2.0", "Zlib license", "GPL-2.0"])
def test_a_dual_license_offer_is_unrecognised_whatever_the_other_license(other):
    # Review of #63: each of these was named MIT. Text outside the template is never ignored.
    assert spdx(f"MIT or {other}\n\n{MIT}") is None
    assert spdx(f"This project is offered under MIT or the {other}.\n\n{MIT}") is None
    assert spdx(f"{MIT}\n\nAlternatively, you may use it under the {other}.") is None
    assert spdx(f"Copyright (c) 2026 X, dual-licensed under MIT or {other}\n\n{MIT}") is None


def test_the_leading_block_cannot_hide_a_second_license():
    # Review of #63: both were named MIT while every leading title and copyright line was stripped.
    body = MIT.split("\n", 1)[1]  # the MIT template without its own title line
    assert spdx("MIT License\nBSD 2-Clause License\n" + MIT) is None  # two titles
    assert spdx("BSD 2-Clause License\nMIT License\n" + body) is None
    assert spdx("ISC License\n\n" + body) is None  # a title for another license
    assert spdx("Copyright (c) 2026 X, MIT or Zlib\n\n" + body) is None
    assert spdx("Copyright (c) 2026 X; use under the Zlib terms\n\n" + body) is None
    assert spdx("Copyright (c) 2026 Y\nAll rights reserved.\nMIT License\n\n" + body) == "MIT"
    assert spdx("BSD 3-Clause License\n\n" + BSD3) == "BSD-3-Clause"


@pytest.mark.parametrize(
    "line",
    [
        "Copyright (c) 2026 X, or Zlib",
        "Copyright (c) 2026 X and/or Zlib",
        "Copyright (c) 2026 X, licensed as Zlib",
        "Copyright (c) 2026 X, dual Zlib",
        "Copyright (c) 2026 X, under Zlib",
        "Copyright (c) 2026 X, Zlib terms",
        "Copyright (c) 2026 X, alternatively Zlib",
        "Copyright (c) 2026 X, SPDX: Zlib",
        "Copyright (c) 2026 " + "X" * 130,  # longer than a copyright line may be
    ],
)
def test_a_copyright_line_that_makes_an_offer_is_not_metadata(line):
    assert spdx(line + "\n\n" + MIT.split("\n", 1)[1]) is None
    assert spdx("Copyright (c) 2026 X\n\n" + MIT.split("\n", 1)[1]) == "MIT"


@pytest.mark.parametrize(
    "holder",
    ["MIT and BSD-2-Clause", "MIT/BSD-2-Clause", "MIT + Apache-2.0", "Zlib", "GPLv2", "GPL", "apache"],
)
def test_a_copyright_line_naming_any_license_is_not_metadata(holder):
    # Review of #63: these named no offer word and were stripped, so the MIT text alone was matched.
    assert spdx(f"Copyright (c) 2026 X, {holder}\n\n" + MIT.split("\n", 1)[1]) is None


def test_the_license_list_is_the_pinned_spdx_file():
    with pytest.raises(RuntimeError, match="does not match its pinned SHA-256"):
        license.load_identifiers(b'{"licenses": [{"licenseId": "MIT"}]}')
    words = license.identifiers(["0BSD", "BSD-3-Clause", "LGPL-2.1-only", "CC-BY-4.0"])
    assert [bool(words.search(s)) for s in ("0bsd", "lgplv2.1", "cc-by-4.0", "bsd", "lgpl", "cc")] == [
        True
    ] * 6
    assert not words.search("ccc lgplx abstract")  # whole words only


def test_at_most_one_leading_title_is_stripped():
    body = MIT.split("\n", 1)[1]
    assert spdx("MIT License\n" + body) == "MIT"
    assert spdx("MIT License\nMIT License\nMIT License\n" + body) is None


def test_anything_but_exactly_one_whole_allowed_license_is_unrecognised():
    bsd4 = BSD3.replace(
        "3. Neither", "4. All advertising materials mentioning features must display it.\n3. Neither"
    )
    assert spdx(bsd4) is None  # 4-clause BSD is neither BSD-2 nor BSD-3
    assert spdx(MIT + "\n\n" + APACHE) is None  # two licenses
    assert spdx("GNU GENERAL PUBLIC LICENSE Version 3") is None
    assert spdx(MIT.split("The above")[0]) is None  # half an MIT text
    assert spdx(APACHE + "\n\nThis product bundles code under other terms.") is None
    header = 'Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file'
    assert spdx(header) is None


def test_no_template_variable_can_carry_a_license():
    holder = "BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS"
    assert spdx(BSD3.replace(holder, "BY X, OR UNDER THE GPL LICENSE AT YOUR OPTION,")) is None
    assert spdx(BSD3.replace(holder, "BY X")) == "BSD-3-Clause"


def test_template_wildcards_are_bounded_and_the_copyright_sign_is_a_copyright_line():
    holder = "BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS"
    liable = "THE COPYRIGHT HOLDER OR CONTRIBUTORS"
    assert spdx(BSD3.replace(holder, "BY " + "X" * 250)) is None  # a variable holds at most 200
    assert spdx(BSD3.replace(liable, "X" * 250)) is None
    assert spdx(BSD3.replace(liable, "X" * 150)) == "BSD-3-Clause"
    assert spdx("\u00a9 2026 Someone\n\n" + MIT) == "MIT"


def test_a_changed_template_file_stops_the_miner(monkeypatch):
    monkeypatch.setitem(license.SHA256, "MIT", "0" * 64)
    with pytest.raises(RuntimeError, match="MIT does not match its pinned SHA-256"):
        license._load()


def test_s1_1_needs_both_sources_to_agree_on_an_allowed_id():
    assert license.s1_1("MIT", "MIT") == {"value": {"file": "MIT", "api": "MIT"}, "pass": True}
    assert not license.s1_1("MIT", "Apache-2.0")["pass"]
    assert not license.s1_1(None, "MIT")["pass"]
    assert not license.s1_1(None, None)["pass"]
    assert not license.s1_1("GPL-3.0", "GPL-3.0")["pass"]


def _repo(tmp_path, files):
    work = tmp_path / "w"
    work.mkdir()
    env = os.environ | {"GIT_CONFIG_GLOBAL": os.devnull}
    git = ["git", "-c", "user.name=t", "-c", "user.email=t@example.com", "-c", "commit.gpgsign=false"]
    subprocess.run([*git, "init", "-q", "-b", "main"], cwd=work, env=env, check=True)
    for path, content in files.items():
        (work / path).parent.mkdir(parents=True, exist_ok=True)
        (work / path).write_bytes(content)
    subprocess.run([*git, "add", "-A"], cwd=work, env=env, check=True)
    subprocess.run([*git, "commit", "-q", "-m", "c"], cwd=work, env=env, check=True)
    return work / ".git"


def test_file_spdx_reads_the_one_root_license_file(tmp_path):
    # Only root-level regular files count: not docs/LICENSE, and not a directory named license.
    files = {"LICENSE.txt": BSD3.encode(), "docs/LICENSE": MIT.encode(), "license/x.md": b"x", "a.py": b""}
    git_dir = _repo(tmp_path, files)
    assert license.file_spdx(git_dir, "HEAD", IDS) == ("BSD-3-Clause", None)


@pytest.mark.parametrize(
    ("files", "reason"),
    [
        ({"README.md": b"x"}, "0 license files at the root"),
        ({"LICENSE": MIT.encode(), "COPYING.md": MIT.encode()}, "2 license files at the root"),
        ({"Licence.md": b"\xff\xfe"}, "Licence.md is not UTF-8"),
        ({"license": b"All rights reserved."}, "license matches no single allowed license"),
    ],
)
def test_file_spdx_gives_a_reason_when_it_cannot_name_one_license(tmp_path, files, reason):
    assert license.file_spdx(_repo(tmp_path, files), "HEAD", IDS) == (None, reason)
