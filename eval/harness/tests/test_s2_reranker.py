import hashlib
import os
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
    assert reranker.SIZES == {"onnx/model_qint8_arm64.onnx": 23_200_716}
    assert sorted(reranker.PINS) == sorted(
        [
            "onnx/model_qint8_arm64.onnx",
            "tokenizer.json",
            "tokenizer_config.json",
            "vocab.txt",
            "special_tokens_map.json",
        ]
    )
    assert reranker.PINS["onnx/model_qint8_arm64.onnx"].startswith("3573b6b9")
    assert reranker.url("vocab.txt") == (
        "https://huggingface.co/cross-encoder/ms-marco-MiniLM-L6-v2/resolve/"
        "233902d25c440f23af6f7d6e94d2946bac0bee0a/vocab.txt"
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


def test_fetch_downloads_the_pinned_revision_and_keeps_only_verified_files(tmp_path):
    bodies = {"onnx/m.onnx": b"model", "t.json": b"tok"}
    pins = {n: hashlib.sha256(b).hexdigest() for n, b in bodies.items()}
    seen = []

    def download(src, dest: Path):
        seen.append(src)
        dest.write_bytes(bodies[src.rsplit(f"{reranker.REVISION}/", 1)[1]])

    reranker.fetch(tmp_path / "ok", download, pins, {})
    assert seen == [reranker.url("onnx/m.onnx"), reranker.url("t.json")]
    assert (tmp_path / "ok/t.json").read_bytes() == b"tok"
    assert not list((tmp_path / "ok").rglob("*.part"))

    bodies["t.json"] = b"tampered"
    with pytest.raises(PinError, match=r"t\.json: sha256"):
        reranker.fetch(tmp_path / "bad", download, pins, {})
    assert not [p for p in (tmp_path / "bad").rglob("*") if p.is_file()]


def test_an_interrupted_download_leaves_no_partial_file(tmp_path):
    def download(src, dest: Path):
        dest.write_bytes(b"half")
        raise ConnectionError("reset")

    with pytest.raises(ConnectionError):
        reranker.fetch(tmp_path, download, {"onnx/m.onnx": "0" * 64}, {})
    assert not [p for p in tmp_path.rglob("*") if p.is_file()]


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
