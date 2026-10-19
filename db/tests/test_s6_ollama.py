"""db/s6_ollama.py's S6-5 sequence against a fake Ollama, so the logic is tested in CI. Only the real run
(by Myan, with `ollama serve`) is evidence; this pins what that run checks."""

import pytest
import s6_identity as s6
import s6_ollama


class FakeOllama:
    """Models are name -> digest. `copy` re-points an alias exactly as Ollama does: it takes the source's
    digest. Vectors depend only on the digest, plus `noise` on each call to model a non-repeatable runtime."""

    def __init__(self, models, noise=0.0):
        self.models = dict(models)
        self.noise = noise
        self.calls = 0

    def version(self):
        return "0.0-fake"

    def digest(self, name):
        return self.models[name]

    def copy(self, source, destination):
        self.models[destination] = self.models[source]

    def delete(self, name):
        self.models.pop(name, None)

    def embed(self, model, text):
        self.calls += 1
        vector = s6.stand_in(s6.Spec(0, model, self.models[model], ""), text)
        return [v + self.noise * self.calls for v in vector]


MODELS = {s6_ollama.FIRST: "d1" * 32, s6_ollama.SECOND: "d2" * 32}


def test_s6_5_passes_when_the_alias_moves_to_another_digest(db):
    report = s6_ollama.run(FakeOllama(MODELS), db)
    assert report["passed"] and all(report["checks"].values())
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
