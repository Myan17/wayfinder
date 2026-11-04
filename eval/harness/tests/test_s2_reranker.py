import hashlib
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest
from s2 import reranker
from s2.reranker import PinError

REAL = os.environ.get("WAYFINDER_S2_RERANKER")
real = pytest.mark.skipif(not REAL, reason="set WAYFINDER_S2_RERANKER to a fetched reranker directory")


def pinned(tmp_path, files):
    for name, body in files.items():
        (tmp_path / name).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / name).write_bytes(body)
    return {name: hashlib.sha256(body).hexdigest() for name, body in files.items()}


def test_the_pins_are_adr_0019s():
    assert reranker.REPO == "cross-encoder/ms-marco-MiniLM-L6-v2"
    assert reranker.REVISION == "233902d25c440f23af6f7d6e94d2946bac0bee0a"
    assert reranker.SIZES == {reranker.MODEL: 23_200_716} and len(reranker.PINS) == 5
    assert reranker.PINS[reranker.MODEL].startswith("3573b6b9") and "vocab.txt" in reranker.PINS
    assert (
        reranker.url("vocab.txt")
        == f"https://huggingface.co/{reranker.REPO}/resolve/{reranker.REVISION}/vocab.txt"
    )


def test_verify_names_every_missing_resized_or_changed_file(tmp_path):
    pins = pinned(tmp_path, {"onnx/m.onnx": b"model", "a.json": b"a", "b.txt": b"b"})
    sizes = {"onnx/m.onnx": 5}
    reranker.verify(tmp_path, pins, sizes)
    (tmp_path / "a.json").write_bytes(b"A")
    (tmp_path / "b.txt").unlink()
    (tmp_path / "onnx/m.onnx").write_bytes(b"model!")
    with pytest.raises(PinError) as e:
        reranker.verify(tmp_path, pins, sizes)
    assert "a.json: sha256" in str(e.value) and "b.txt: missing" in str(e.value)
    assert "onnx/m.onnx: 6 bytes, pinned 5" in str(e.value)


BODIES = {"onnx/m.onnx": b"model", "t.json": b"tok"}
PINS = {n: hashlib.sha256(b).hexdigest() for n, b in BODIES.items()}


def downloader(bodies, fail_on=None, seen=None):
    def download(src, dest: Path):
        name = src.rsplit(f"{reranker.REVISION}/", 1)[1]
        if seen is not None:
            seen.append(src)
        if name == fail_on:
            dest.write_bytes(b"half")
            raise ConnectionError("reset")
        dest.write_bytes(bodies[name])

    return download


def files_under(path):
    return sorted(str(p.relative_to(path)) for p in path.rglob("*") if p.is_file())


def test_fetch_downloads_the_pinned_revision_and_promotes_the_verified_set(tmp_path):
    seen = []
    reranker.fetch(tmp_path / "ok", downloader(BODIES, seen=seen), PINS, {})
    assert seen == [reranker.url("onnx/m.onnx"), reranker.url("t.json")]
    assert (tmp_path / "ok/t.json").read_bytes() == b"tok"
    assert files_under(tmp_path) == ["ok/onnx/m.onnx", "ok/t.json"]  # no staging left
    (tmp_path / "empty").mkdir()
    reranker.fetch(tmp_path / "empty", downloader(BODIES), PINS, {})  # an empty root is fine
    assert files_under(tmp_path / "empty") == ["onnx/m.onnx", "t.json"]


def test_a_failure_after_an_earlier_file_succeeded_leaves_nothing(tmp_path):
    # file 1 downloads, file 2 is interrupted: neither the root nor any staging file survives
    with pytest.raises(ConnectionError):
        reranker.fetch(tmp_path / "r", downloader(BODIES, fail_on="t.json"), PINS, {})
    assert not (tmp_path / "r").exists() and files_under(tmp_path) == []
    # every file downloads but one is tampered: the same
    with pytest.raises(PinError, match=r"t\.json: sha256"):
        reranker.fetch(tmp_path / "r", downloader({**BODIES, "t.json": b"tampered"}), PINS, {})
    assert not (tmp_path / "r").exists() and files_under(tmp_path) == []


def test_fetch_never_mixes_into_a_directory_that_has_files(tmp_path):
    (tmp_path / "r").mkdir()
    (tmp_path / "r/t.json").write_bytes(b"old")
    with pytest.raises(PinError, match="already has files"):
        reranker.fetch(tmp_path / "r", downloader(BODIES), PINS, {})
    assert files_under(tmp_path) == ["r/t.json"]


def test_the_cli_refuses_a_directory_that_fails_verification(tmp_path, capsys):
    assert reranker.main(["--verify", str(tmp_path)]) == 1
    assert "missing" in capsys.readouterr().err


def test_a_reranker_is_never_built_from_unverified_files(tmp_path):
    with pytest.raises(PinError):
        reranker.Reranker(tmp_path)


@pytest.fixture
def tiny_tokenizer():
    tk = pytest.importorskip("tokenizers")
    vocab = {t: i for i, t in enumerate(["[PAD]", "[UNK]", "[CLS]", "[SEP]", "q", "p"])}
    t = tk.Tokenizer(tk.models.WordPiece(vocab, unk_token="[UNK]"))
    t.pre_tokenizer = tk.pre_tokenizers.Whitespace()
    t.post_processor = tk.processors.BertProcessing(("[SEP]", 3), ("[CLS]", 2))
    return t


def test_pairs_are_truncated_to_l_tokens_in_total_longest_side_first(tiny_tokenizer):
    e = reranker.encode(tiny_tokenizer, "q " * 4, ["p " * 50, "p " * 2], 16)
    long, short = e.input_ids
    assert len(long) == 16 and long.count(4) == 4 and long.count(5) == 9  # 16 - 3 special tokens
    assert e.attention_mask[1] == [1] * 9 + [0] * 7  # [CLS] q*4 [SEP] p*2 [SEP], padded to the batch
    assert short[9:] == [0] * 7 and e.token_type_ids[0][:6] == [0] * 6 and e.token_type_ids[0][6] == 1
    # a query longer than L is cut too, rather than failing the call
    over = reranker.encode(tiny_tokenizer, "q " * 40, ["p " * 40], 16)
    assert len(over.input_ids[0]) == 16 and over.input_ids[0].count(5) >= 6


def test_per_pair_encoding_matches_the_batch_calls_padding(tiny_tokenizer):
    passages = ["p " * 50, "p " * 2, "", "p q " * 3]
    got = reranker.encode(tiny_tokenizer, "q " * 4, passages, 16)
    tiny_tokenizer.enable_truncation(max_length=16, strategy="longest_first")
    tiny_tokenizer.enable_padding(pad_id=0, pad_token="[PAD]")
    want = tiny_tokenizer.encode_batch([("q " * 4, p) for p in passages])
    assert got.input_ids == [e.ids for e in want]
    assert got.attention_mask == [e.attention_mask for e in want]
    assert got.token_type_ids == [e.type_ids for e in want]


CONFINED = """
import sys, time
from pathlib import Path
sys.path.insert(0, sys.argv[1])
from s2 import reranker
from tokenizers import Tokenizer
t = Tokenizer.from_file(sys.argv[2])
q, p = "q " * 20, "p q " * 400
reranker.encode(t, q, [p], 256)  # warm
proc, thread = time.process_time_ns(), time.thread_time_ns()
for _ in range(15):
    reranker.encode(t, q, [p] * 50, 256)
print(time.process_time_ns() - proc, time.thread_time_ns() - thread)
"""


def confined(tokenizer_file):
    """Process and calling-thread CPU of 15 encodes of 50 long pairs, in a fresh interpreter, so no
    tokenizer worker pool from another test is running."""
    harness = str(Path(reranker.__file__).parents[1])
    out = subprocess.check_output([sys.executable, "-c", CONFINED, harness, str(tokenizer_file)], text=True)
    return tuple(map(int, out.split()))


def test_tokenization_runs_only_on_the_calling_thread(tiny_tokenizer, tmp_path):
    tiny_tokenizer.save(str(tmp_path / "tokenizer.json"))
    proc, thread = confined(tmp_path / "tokenizer.json")
    assert thread > 0 and thread >= 0.95 * proc, (proc, thread)


def test_only_the_grids_l_values_are_accepted():
    r = object.__new__(reranker.Reranker)
    with pytest.raises(ValueError, match="L must be one of"):
        r.score("q", ["p"], 512)


@real
def test_the_real_reranker_ranks_the_relevant_passage_first_on_one_thread():
    r = reranker.Reranker(Path(REAL))
    opts = r.session.get_session_options()
    assert (opts.intra_op_num_threads, opts.inter_op_num_threads) == (1, 1)
    assert r.session.get_providers() == ["CPUExecutionProvider"]
    q = "How many people live in Berlin?"
    good = "Berlin has a population of 3,520,031 registered inhabitants in an area of 891.82 square km."
    bad = "New York City is famous for the Metropolitan Museum of Art."
    for length in reranker.L_GRID:
        s_good, s_bad = r.score(q, [good, bad], length)
        assert s_good > 5 > -5 > s_bad
    assert len(r.score(q, ["x " * 1000] * 50, 256)) == 50
    proc, thread = confined(Path(REAL) / "tokenizer.json")
    assert thread >= 0.95 * proc, (proc, thread)


@real
def test_a_real_rerank_call_spends_its_cpu_on_the_calling_thread():
    r = reranker.Reranker(Path(REAL))
    r.score("warm", ["up"], 128)
    proc, thread = time.process_time_ns(), time.thread_time_ns()
    for _ in range(3):
        r.score("how do I configure the validator", ["def f(x):\n    return x + 1 " * 60] * 50, 256)
    proc, thread = time.process_time_ns() - proc, time.thread_time_ns() - thread
    assert thread >= 0.95 * proc, (proc, thread)
