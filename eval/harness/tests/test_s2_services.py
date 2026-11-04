import os
import re
import subprocess

import pytest
from s2 import services
from s2.services import ServiceError

DOCKER = os.environ.get("WAYFINDER_S2_DOCKER") == "1"


class FakeDocker:
    """Records every argv. `ps -q` answers a container id, `inspect` a pid, `pg_isready` fails
    `not_ready` times first."""

    def __init__(self, pids=None, not_ready=0):
        self.calls: list[list[str]] = []
        self.pids = pids or {"postgres": 4100, "ollama-query": 4200}
        self.not_ready = not_ready

    def __call__(self, argv):
        self.calls.append(argv)
        if argv[:2] == ["docker", "compose"]:
            sub = argv[6:]
            if sub[:2] == ["ps", "-q"]:
                return f"cid-{sub[2]}\n" if sub[2] in self.pids else ""
            if "pg_isready" in sub and self.not_ready:
                self.not_ready -= 1
                raise subprocess.CalledProcessError(2, argv)
        if argv[:2] == ["docker", "inspect"]:
            return f"{self.pids[argv[-1].removeprefix('cid-')]}\n"
        return ""

    def verbs(self):
        return [" ".join(c[6:]) if c[:2] == ["docker", "compose"] else " ".join(c) for c in self.calls]


def ollama(version="0.34.2", digest=services.MODEL_DIGEST, down=0):
    state = {"down": down, "urls": []}

    def http(url, body):
        state["urls"].append(url)
        if url.endswith("/api/version"):
            if state["down"]:
                state["down"] -= 1
                return 0, {}
            return 200, {"version": version}
        if url.endswith("/api/tags"):
            return 200, {"models": [{"name": services.MODEL, "digest": digest}]}
        if url.endswith("/api/pull"):
            assert body == {"model": services.MODEL, "stream": False}
            return 200, {"status": "success"}
        raise AssertionError(url)

    http.state = state
    return http


def test_the_compose_file_pins_every_image_by_arm64_digest_and_keeps_data_on_volumes():
    text = services.COMPOSE.read_text()
    body = "\n".join(line.split("#")[0] for line in text.splitlines())  # comments may mention tmpfs
    assert f"name: {services.PROJECT}" in body
    images = re.findall(r"image: (\S+)", body)
    assert len(images) == 3 and all(re.fullmatch(r"[\w/]+@sha256:[0-9a-f]{64}", i) for i in images)
    assert images[0].endswith("c17153b8b7307734c3aede0393dfe8fa447f4a528ec028b1c3937186ab3ee242")
    assert images[1] == images[2] and "max_parallel_workers_per_gather=0" in body
    assert "tmpfs" not in body  # drop_caches cannot evict tmpfs
    assert re.findall(r"- (\w[\w-]*):/", body) == ["pgdata", "query-models", "ingest-models"]
    ports = re.findall(r'- "127\.0\.0\.1:(\d+):(?:5432|11434)"', body)
    assert ports == [services.DSN.split(":")[-1].split("/")[0], "11435", "11436"]
    assert [services.OLLAMA[s][-5:] for s in ("ollama-query", "ollama-ingest")] == ports[1:]
    assert "@127.0.0.1:" in services.DSN
    assert all(u.startswith("http://127.0.0.1:") for u in services.OLLAMA.values())


def test_every_published_port_is_bound_to_loopback():
    """A port without a host IP is published on every interface: the fixed password and an
    unauthenticated Ollama would be reachable from the network."""
    body = "\n".join(line.split("#")[0] for line in services.COMPOSE.read_text().splitlines())
    published = re.findall(r"ports:\n((?:\s+- .+\n)+)", body + "\n")
    entries = [e.strip().removeprefix("- ").strip('"') for block in published for e in block.splitlines()]
    assert len(entries) == 3 and all(e.startswith("127.0.0.1:") for e in entries), entries


def test_a_services_host_pid_and_cgroup_come_from_its_running_container(tmp_path):
    run = FakeDocker()
    (tmp_path / "4100").mkdir()
    (tmp_path / "4100/cgroup").write_text("0::/system.slice/docker-pg.scope\n")
    assert (
        services.cgroup(run, "postgres", tmp_path, tmp_path / "cg")
        == tmp_path / "cg/system.slice/docker-pg.scope"
    )
    assert run.verbs() == ["ps -q postgres", "docker inspect -f {{.State.Pid}} cid-postgres"]
    with pytest.raises(ServiceError, match="ollama-ingest is not running"):
        services.host_pid(run, "ollama-ingest")
    with pytest.raises(ServiceError, match="not running"):
        services.host_pid(FakeDocker(pids={"postgres": 0}), "postgres")  # a stopped container's pid is 0


def test_the_reset_is_adr_0019s_steps_1_to_4_in_order(tmp_path):
    run, http = FakeDocker(not_ready=2), ollama(down=1)
    drop = tmp_path / "drop_caches"
    services.reset(run, http, drop, sleep=lambda s: None)
    assert drop.read_text() == "3\n"
    v = run.verbs()
    assert v[:3] == ["stop postgres ollama-query", "sync", "start postgres ollama-query"]
    assert v[3:] == ["exec -T postgres pg_isready -U wayfinder -d s2"] * 3  # two failures, then ready
    assert [u.rsplit("/", 1)[1] for u in http.state["urls"]] == ["version", "version", "tags"]
    assert all(u.startswith("http://127.0.0.1:11435/") for u in http.state["urls"])


def test_drop_caches_is_written_between_sync_and_start(tmp_path):
    order = []
    run = FakeDocker()

    class Drop:
        def write_text(self, text):
            order.append(("drop", text, run.verbs()[-1]))

    services.reset(run, ollama(), Drop(), sleep=lambda s: None)
    assert order == [("drop", "3\n", "sync")]
    assert run.verbs()[2] == "start postgres ollama-query"


def test_a_wrong_version_or_model_digest_is_an_error():
    with pytest.raises(ServiceError, match=r"runs Ollama 0\.34\.3, pinned 0\.34\.2"):
        services.ollama_ready(ollama(version="0.34.3"), "ollama-query")
    with pytest.raises(ServiceError, match="digest beef, pinned 0a109f42"):
        services.check_model(ollama(digest="beef"), "ollama-ingest")
    with pytest.raises(ServiceError, match="digest beef"):
        services.pull_model(ollama(digest="beef"), "ollama-query")
    services.pull_model(ollama(), "ollama-query")


def test_readiness_gives_up_after_its_timeout():
    t = iter(range(0, 1000, 10))
    with pytest.raises(ServiceError, match="postgres not ready after 30 s"):
        services.wait(lambda: False, "postgres", 30, sleep=lambda s: None, clock=lambda: next(t))


@pytest.mark.skipif(not DOCKER, reason="set WAYFINDER_S2_DOCKER=1 on a Linux host with Docker, as root")
def test_the_real_services_reset_and_connect():
    run, http = services.subprocess_run, services.urllib_http
    services.up(run, http)
    services.pull_model(http, "ollama-query")
    services.reset(run, http)
    conn, pid = services.connect(run)
    assert pid > 0 and conn.execute("SHOW max_parallel_workers_per_gather").fetchone() == ("0",)
    _other, other_pid = services.connect(run)
    assert other_pid != pid  # a new connection is a new backend
