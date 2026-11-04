"""Spike S2's reference reranker, pinned by ADR-0019 (gupta958, ruling 1).

    PYTHONPATH=eval/harness uv run python -m s2.reranker --fetch ~/wayfinder-s2/reranker

The ARM64 int8 ONNX export and four tokenizer files at one revision, each checked against its
SHA-256 (the export also by size); S2 refuses to run if any differs. They are fetched once, never
committed. `Reranker` needs the `s2` extra (`uv sync --extra dev --extra s2 --locked`).

A rerank call scores N (query, passage) pairs, each truncated to L tokens in total, longest side
first, padded to the batch's longest pair (gupta958's ruling on #104). Tokenization and inference
both run on the calling thread (§10.5), so the harness thread clock sees all of the call's CPU.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import sys
import urllib.request
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

REPO = "cross-encoder/ms-marco-MiniLM-L6-v2"
REVISION = "233902d25c440f23af6f7d6e94d2946bac0bee0a"
MODEL = "onnx/model_qint8_arm64.onnx"
PINS = {
    MODEL: "3573b6b9593cb2f75987a31815d409ca3dd8808629118fd20451bb1a5d90cec7",
    "tokenizer.json": "d241a60d5e8f04cc1b2b3e9ef7a4921b27bf526d9f6050ab90f9267a1f9e5c66",
    "tokenizer_config.json": "a5c2e5a7b1a29a0702cd28c08a399b5ecc110c263009d17f7e3b415f25905fd8",
    "vocab.txt": "07eced375cec144d27c900241f3e339478dec958f92fddbc551f295c992038a3",
    "special_tokens_map.json": "3c3507f36dff57bce437223db3b3081d1e2b52ec3e56ee55438193ecb2c94dd6",
}
SIZES = {MODEL: 23_200_716}
N_GRID = (8, 16, 32, 50)  # ADR-0015's grid
L_GRID = (128, 256)


class PinError(RuntimeError):
    """A reranker file is missing or differs from its pin. S2 refuses to run."""


def sha256(path: Path) -> str:
    with path.open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def verify(root: Path, pins: dict[str, str] = PINS, sizes: dict[str, int] = SIZES) -> None:
    """Every pinned file exists with its size and SHA-256, or `PinError` names each one that does not."""
    problems = []
    for name, digest in pins.items():
        f = root / name
        if not f.is_file():
            problems.append(f"{name}: missing")
        elif name in sizes and f.stat().st_size != sizes[name]:
            problems.append(f"{name}: {f.stat().st_size} bytes, pinned {sizes[name]}")
        elif (got := sha256(f)) != digest:
            problems.append(f"{name}: sha256 {got}, pinned {digest}")
    if problems:
        raise PinError("reranker files differ from ADR-0019's pins: " + "; ".join(problems))


def url(name: str) -> str:
    return f"https://huggingface.co/{REPO}/resolve/{REVISION}/{name}"


Download = Callable[[str, Path], None]  # url -> write the body to this path


def urllib_download(src: str, dest: Path) -> None:
    with urllib.request.urlopen(src, timeout=120) as resp, dest.open("wb") as out:
        shutil.copyfileobj(resp, out, 1 << 20)


def fetch(
    root: Path,
    download: Download = urllib_download,
    pins: dict[str, str] = PINS,
    sizes: dict[str, int] = SIZES,
) -> None:
    """All or nothing: download every pinned file into a staging directory beside `root`, verify the
    complete set there, and only then rename the staging directory to `root`. Any failure, including
    an interrupted download, removes the staging directory, so `root` either holds the full verified
    set or does not exist. An existing non-empty `root` is refused rather than mixed with."""
    if root.exists() and any(root.iterdir()):
        raise PinError(f"{root} already has files; --verify it, or remove it and fetch again")
    root.parent.mkdir(parents=True, exist_ok=True)
    staging = root.with_name(f".{root.name}.staging-{os.getpid()}")
    shutil.rmtree(staging, ignore_errors=True)
    try:
        for name in pins:
            (staging / name).parent.mkdir(parents=True, exist_ok=True)
            download(url(name), staging / name)
        verify(staging, pins, sizes)
        if root.exists():
            root.rmdir()  # empty, checked above
        staging.rename(root)
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise


@dataclass(frozen=True)
class Encoded:
    input_ids: list[list[int]]
    attention_mask: list[list[int]]
    token_type_ids: list[list[int]]


def encode(tokenizer, query: str, passages: Sequence[str], length: int) -> Encoded:
    """Each pair truncated to `length` tokens, padded to the batch's longest. Pairs are encoded one
    at a time with `encode`, never `encode_batch`, whose worker threads the harness thread clock
    cannot see (gupta958's review of #104); the padding here equals the batch call's."""
    tokenizer.enable_truncation(max_length=length, strategy="longest_first")
    tokenizer.no_padding()
    pad = tokenizer.token_to_id("[PAD]")
    enc = [tokenizer.encode(query, p) for p in passages]
    width = max(len(e.ids) for e in enc)

    def padded(rows, fill):
        return [r + [fill] * (width - len(r)) for r in rows]

    return Encoded(
        padded([e.ids for e in enc], pad),
        padded([e.attention_mask for e in enc], 0),
        padded([e.type_ids for e in enc], 0),
    )


class Reranker:
    def __init__(self, root: Path):
        verify(root)
        import onnxruntime as ort
        from tokenizers import Tokenizer

        options = ort.SessionOptions()
        options.intra_op_num_threads = 1
        options.inter_op_num_threads = 1
        options.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
        self.session = ort.InferenceSession(str(root / MODEL), options, providers=["CPUExecutionProvider"])
        self.inputs = {i.name for i in self.session.get_inputs()}
        self.tokenizer = Tokenizer.from_file(str(root / "tokenizer.json"))

    def score(self, query: str, passages: Sequence[str], length: int) -> list[float]:
        """One rerank call: a relevance logit per passage, in input order."""
        if length not in L_GRID:
            raise ValueError(f"L must be one of {L_GRID}, not {length}")
        import numpy as np

        e = encode(self.tokenizer, query, passages, length)
        feed = {k: np.array(getattr(e, k), dtype=np.int64) for k in self.inputs}
        (logits,) = self.session.run(["logits"], feed)
        return [float(x) for x in logits.reshape(-1)]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--fetch", type=Path, help="download the pinned files here, then verify them")
    ap.add_argument("--verify", type=Path, help="verify an existing directory")
    args = ap.parse_args(argv)
    root = args.fetch or args.verify
    if root is None:
        ap.error("give --fetch or --verify")
    try:
        fetch(root) if args.fetch else verify(root)
    except PinError as e:
        print(e, file=sys.stderr)
        return 1
    print(f"verified {len(PINS)} files under {os.fspath(root)} at {REPO}@{REVISION[:12]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
