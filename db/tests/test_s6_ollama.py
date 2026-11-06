"""db/s6_ollama.py's S6-5 sequence against a fake Ollama, so the logic is tested in CI. Only the real run
(by Myan, with `ollama serve`) is evidence; this pins what that run checks."""

import json
import threading
import urllib.error
from http.server import BaseHTTPRequestHandler, HTTPServer

import psycopg
import pytest
import s6_identity as s6
import s6_ollama
from conftest import DSN


class FakeOllama:
    """Models are name -> digest. `copy` re-points an alias exactly as Ollama does: it takes the source's
    digest. Vectors depend only on the digest, plus `noise` on each call to model a non-repeatable runtime."""

    def __init__(self, models, noise=0.0):
        self.models = dict(models)
        self.noise = noise
        self.calls = 0
        self.deleted = []
        self.requests = []  # (text, truncate) per embed_counted request
        self.reject = set()  # texts refused with ContextExceeded unless truncate is true
        self.reject_truncated = set()  # texts refused even with truncate true
        self.before_retry = None  # called as a rejection is raised, to move an alias before the retry

    def version(self):
        return "0.0-fake"

    def digest(self, name):
        return self.models[name]

    def exists(self, name):
        return name in self.models

    def copy(self, source, destination):
        self.models[destination] = self.models[source]

    def delete(self, name):
        self.deleted.append(name)
        self.models.pop(name, None)

    def embed(self, model, text):
        self.calls += 1
        vector = s6.stand_in(s6.Spec(0, model, self.models[model], ""), text)
        return [v + self.noise * self.calls for v in vector]

    def embed_counted(self, model, text, *, truncate=False):
        self.requests.append((text, truncate))
        if (text in self.reject and not truncate) or text in self.reject_truncated:
            if self.before_retry:
                self.before_retry()
            raise s6_ollama.ContextExceeded(model, s6_ollama.CONTEXT_EXCEEDED)
        return s6_ollama.Embedded(self.embed(model, text), 2048 if truncate else len(text))


MODELS = {s6_ollama.FIRST: "d1" * 32, s6_ollama.SECOND: "d2" * 32}


def test_s6_5_passes_when_the_alias_moves_to_another_digest(db):
    client = FakeOllama(MODELS)
    report = s6_ollama.run(client, db)
    assert report["passed"] and all(report["checks"].values())
    assert report["alias"].startswith(s6_ollama.ALIAS_PREFIX)
    assert client.deleted == [report["alias"]] and client.models == MODELS
    assert report["models"] == MODELS
    assert report["repeatability"]["byte_identical"] is True
    assert report["repeatability"]["max_abs_difference"] == 0
    assert report["repeatability"]["cosine_distance"] == pytest.approx(0, abs=1e-12)


def test_s6_5_fails_when_both_models_share_a_digest(db):
    """A re-pointed alias with an unchanged digest must not count as a new specification."""
    report = s6_ollama.run(FakeOllama({s6_ollama.FIRST: "d1" * 32, s6_ollama.SECOND: "d1" * 32}), db)
    assert not report["passed"]
    assert not report["checks"]["alias_now_names_another_digest"]


def test_repeatability_reports_a_difference_without_failing_s6_5(db):
    report = s6_ollama.run(FakeOllama(MODELS, noise=1e-3), db)
    assert report["passed"]
    rep = report["repeatability"]
    assert rep["byte_identical"] is False
    assert rep["max_abs_difference"] == pytest.approx(1e-3)
    assert rep["cosine_distance"] > 0


def test_the_embedder_refuses_once_the_alias_names_another_digest():
    client = FakeOllama({**MODELS, "alias": MODELS[s6_ollama.FIRST]})
    embed = s6_ollama.embedder(client, {"calls": 0})
    spec = s6.Spec(1, "alias", MODELS[s6_ollama.FIRST], "")
    assert len(embed(spec, "x")) == s6.DIMENSION
    client.copy(s6_ollama.SECOND, "alias")
    with pytest.raises(RuntimeError, match="no longer names"):
        embed(spec, "x")


def test_s6_5_fails_when_capture_ignores_the_digest(db, monkeypatch):
    """The check is live: a capture that keyed on the alias would return A's row for the new model."""
    real, first = s6.capture_spec, {}

    def by_alias(conn, **fields):
        return first.setdefault(fields["model_ref"], real(conn, **fields))

    monkeypatch.setattr(s6_ollama.s6, "capture_spec", by_alias)
    report = s6_ollama.run(FakeOllama(MODELS), db)
    assert not report["passed"]
    assert not report["checks"]["repointed_alias_is_a_new_spec"]


def test_a_pre_existing_alias_is_refused_and_left_alone(db):
    client = FakeOllama({**MODELS, "taken": "d9" * 32})
    with pytest.raises(RuntimeError, match="already exists"):
        s6_ollama.run(client, db, alias="taken")
    assert client.models["taken"] == "d9" * 32 and client.deleted == [] and client.calls == 0


def test_a_failed_initial_copy_deletes_nothing(db):
    class CopyFails(FakeOllama):
        def copy(self, source, destination):
            raise OSError("copy refused")

    client = CopyFails(MODELS)
    with pytest.raises(OSError, match="copy refused"):
        s6_ollama.run(client, db, alias="fresh")
    assert client.deleted == [] and client.models == MODELS


def test_the_alias_is_deleted_when_the_run_fails_midway(db):
    client = FakeOllama({s6_ollama.FIRST: MODELS[s6_ollama.FIRST]})  # SECOND not pulled
    with pytest.raises(KeyError):
        s6_ollama.run(client, db, alias="fresh")
    assert client.deleted == ["fresh"] and "fresh" not in client.models


def test_the_database_is_dropped_when_alias_cleanup_fails():
    if not DSN:
        pytest.skip("WAYFINDER_TEST_DSN not set")

    class DeleteFails(FakeOllama):
        def delete(self, name):
            raise OSError("delete refused")

    def runs():
        with psycopg.connect(DSN) as admin:
            sql = "SELECT count(*) FROM pg_database WHERE datname LIKE 'wf_s6_%'"
            return admin.execute(sql).fetchone()[0]

    before = runs()
    with pytest.raises(OSError, match="delete refused"):
        s6_ollama.on_temporary_database(DSN, DeleteFails(MODELS))
    assert runs() == before


# BCR-2: Ollama.embed_counted against a real local HTTP server, and the embedder's count and retry.


class Server:
    """A one-route Ollama on 127.0.0.1: it records each /api/embed body and answers with `reply`."""

    def __init__(self):
        self.bodies, self.reply = [], (200, {"embeddings": [[0.0] * s6.DIMENSION], "prompt_eval_count": 7})
        outer = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                outer.bodies.append(json.loads(self.rfile.read(int(self.headers["Content-Length"]))))
                status, body = outer.reply
                raw = json.dumps(body).encode()
                self.send_response(status)
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)

            def log_message(self, *args):
                pass

        self.http = HTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=self.http.serve_forever, daemon=True).start()
        self.client = s6_ollama.Ollama(f"http://127.0.0.1:{self.http.server_port}")


@pytest.fixture
def server():
    srv = Server()
    yield srv
    srv.http.shutdown()


def test_truncate_is_false_by_default_and_must_be_a_bool(server):
    server.client.embed("m", "a")
    server.client.embed_counted("m", "b")
    server.client.embed_counted("m", "c", truncate=True)
    assert [(b["input"], b["truncate"]) for b in server.bodies] == [("a", False), ("b", False), ("c", True)]
    for bad in ("false", 1, None):
        with pytest.raises(TypeError, match="truncate must be a bool"):
            server.client.embed_counted("m", "d", truncate=bad)
    assert len(server.bodies) == 3  # refused before any request


def test_embed_counted_returns_the_count_and_refuses_a_bad_one(server):
    got = server.client.embed_counted("m", "a")
    assert got.prompt_eval_count == 7 and len(got.vector) == s6.DIMENSION
    for count in (None, 0, -1, True, 7.0):
        body = {"embeddings": [[0.0]]} | ({} if count is None else {"prompt_eval_count": count})
        server.reply = (200, body)
        with pytest.raises(RuntimeError, match="prompt_eval_count"):
            server.client.embed_counted("m", "a")
    for embeddings in ([], [[0.0], [0.0]], None):
        server.reply = (200, {"embeddings": embeddings, "prompt_eval_count": 7})
        with pytest.raises(RuntimeError, match="embeddings for one input"):
            server.client.embed_counted("m", "a")


def test_only_the_pinned_context_error_is_context_exceeded(server):
    server.reply = (400, {"error": s6_ollama.CONTEXT_EXCEEDED})
    with pytest.raises(s6_ollama.ContextExceeded) as caught:
        server.client.embed_counted("m", "long")
    assert caught.value.error == "the input length exceeds the context length" and caught.value.model == "m"
    for status, body in (
        (400, {"error": "the input length exceeds the context length."}),
        (400, {}),
        (500, {"error": s6_ollama.CONTEXT_EXCEEDED}),
    ):
        server.reply = (status, body)
        with pytest.raises(urllib.error.HTTPError) as other:
            server.client.embed_counted("m", "long")
        assert not isinstance(other.value, s6_ollama.ContextExceeded) and other.value.code == status
        # re-raised unchanged: the original error, its cause untouched and its body still readable
        assert other.value.__cause__ is None and other.value.msg and other.value.headers is not None
        assert other.value.read() == json.dumps(body).encode()
    assert caught.value.__cause__.read() == json.dumps({"error": s6_ollama.CONTEXT_EXCEEDED}).encode()


SPEC = s6.Spec(1, s6_ollama.FIRST, MODELS[s6_ollama.FIRST], "")


def test_by_default_a_rejection_propagates_and_nothing_is_recorded():
    client, record, counter = FakeOllama(MODELS), [], {"calls": 0}
    client.reject = {"long"}
    with pytest.raises(s6_ollama.ContextExceeded):
        s6_ollama.embedder(client, counter, record=record)(SPEC, "long")
    assert client.requests == [("long", False)] and record == [] and counter == {"calls": 1}


def test_truncate_rejected_retries_once_and_records_the_full_inputs_hash():
    client, record, counter = FakeOllama(MODELS), [], {"calls": 0}
    client.reject = {"long"}
    embed = s6_ollama.embedder(client, counter, record=record, truncate_rejected=True)
    assert len(embed(SPEC, "long")) == len(embed(SPEC, "ok")) == s6.DIMENSION
    assert client.requests == [("long", False), ("long", True), ("ok", False)]
    assert record == [
        s6_ollama.Call(s6.input_hash("long"), 2048, True, "the input length exceeds the context length"),
        s6_ollama.Call(s6.input_hash("ok"), 2, False, None),
    ]
    assert counter == {"calls": 2}  # embedder calls, not HTTP requests

    client.reject_truncated = {"never"}
    with pytest.raises(s6_ollama.ContextExceeded):  # a rejected retry propagates
        embed(SPEC, "never")
    assert client.requests[-2:] == [("never", False), ("never", True)] and len(record) == 2

    class Fails(FakeOllama):
        def embed_counted(self, model, text, *, truncate=False):
            self.requests.append((text, truncate))
            raise urllib.error.HTTPError("u", 500, "boom", {}, None)

    failing = Fails(MODELS)
    with pytest.raises(urllib.error.HTTPError):
        s6_ollama.embedder(failing, {"calls": 0}, truncate_rejected=True)(SPEC, "x")
    assert failing.requests == [("x", False)]  # never retried


def test_the_digest_is_checked_again_before_the_retry():
    client = FakeOllama({**MODELS, "alias": MODELS[s6_ollama.FIRST]})
    client.reject = {"long"}
    client.before_retry = lambda: client.copy(s6_ollama.SECOND, "alias")
    spec = s6.Spec(1, "alias", MODELS[s6_ollama.FIRST], "")
    with pytest.raises(RuntimeError, match="no longer names"):
        s6_ollama.embedder(client, {"calls": 0}, truncate_rejected=True)(spec, "long")
    assert client.requests == [("long", False)]  # no retry request was sent
