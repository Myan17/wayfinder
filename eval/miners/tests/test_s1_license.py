"""S1-1: SPDX ids from license texts, the root license file of a real repository, and the cross-check."""

import os
import subprocess

import pytest
from s1 import license

MIT = """Copyright (c) 2026 Someone

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights...

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software."""
ISC = """Permission to use, copy, modify, and/or distribute this software for any
purpose with or without fee is hereby granted, provided that the above
copyright notice and this permission notice appear in all copies."""
APACHE = """                                 Apache License
                           Version 2.0, January 2004
                        http://www.apache.org/licenses/"""
BSD2 = """Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:
1. Redistributions of source code must retain the above copyright notice."""
BSD3 = (
    BSD2
    + """
3. Neither the name of the copyright holder nor the names of its contributors may be used
   to endorse or promote products derived from this software without specific prior written permission."""
)
BSD4 = (
    BSD3
    + """
4. All advertising materials mentioning features or use of this software must display ..."""
)


@pytest.mark.parametrize(
    ("text", "want"),
    [(MIT, "MIT"), (ISC, "ISC"), (APACHE, "Apache-2.0"), (BSD2, "BSD-2-Clause"), (BSD3, "BSD-3-Clause")],
)
def test_each_allowed_license_is_recognised_across_line_wrapping_and_case(text, want):
    assert license.spdx(text) == want
    assert license.spdx(text.upper().replace(" ", "\n  ")) == want


def test_anything_but_exactly_one_allowed_license_is_unrecognised():
    assert license.spdx(BSD4) is None  # 4-clause BSD is not BSD-3-Clause
    assert license.spdx(MIT + "\n\n" + APACHE) is None  # dual licensed: two matches
    assert license.spdx("GNU GENERAL PUBLIC LICENSE Version 3") is None
    assert license.spdx(MIT.split("The above")[0]) is None  # half an MIT text


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
    assert license.file_spdx(git_dir, "HEAD") == ("BSD-3-Clause", None)


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
    assert license.file_spdx(_repo(tmp_path, files), "HEAD") == (None, reason)
