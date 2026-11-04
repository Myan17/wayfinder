"""Spike S2's services: the containers in `compose.yml`, their readiness, and ADR-0019's cold reset.

Every docker command goes through a `Run` callable and every Ollama request through an `Http`
callable, so the order of the reset and each check is tested without Docker. `subprocess_run` and
`urllib_http` are the real ones. Any check that fails raises `ServiceError`: S2 is an error.
"""

from __future__ import annotations

import json
import subprocess
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from pathlib import Path

from s2 import counters

COMPOSE = Path(__file__).with_name("compose.yml")
PROJECT = "wayfinder-s2"
OLLAMA_VERSION = "0.34.2"
MODEL = "nomic-embed-text:latest"
MODEL_DIGEST = "0a109f422b47e3a30ba2b10eca18548e944e8a23073ee3f3e947efcf3c45e59f"  # ADR-0019
OLLAMA = {"ollama-query": "http://127.0.0.1:11435", "ollama-ingest": "http://127.0.0.1:11436"}
DSN = "postgresql://wayfinder:s2_local_only_not_a_secret@127.0.0.1:55433/s2"
COLD = ("postgres", "ollama-query")  # what a cold reset restarts (ADR-0019 step 1)
READY_S = 120

Run = Callable[[list[str]], str]  # argv -> stdout; raises on a nonzero exit
Http = Callable[[str, dict | None], tuple[int, dict]]  # url, JSON body (POST) or None (GET)


class ServiceError(RuntimeError):
    """A container, version, model or readiness check failed. S2 stops as an error."""


def subprocess_run(argv: list[str]) -> str:
    return subprocess.run(argv, check=True, capture_output=True, text=True).stdout


def urllib_http(url: str, body: dict | None) -> tuple[int, dict]:
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=600) as resp:
            return resp.status, json.load(resp)
    except (urllib.error.URLError, ConnectionError):
        return 0, {}


def compose(*args: str) -> list[str]:
    return ["docker", "compose", "-p", PROJECT, "-f", str(COMPOSE), *args]


def host_pid(run: Run, service: str) -> int:
    """The host pid of a running service's main process."""
    cid = run(compose("ps", "-q", service)).strip()
    pid = int(run(["docker", "inspect", "-f", "{{.State.Pid}}", cid]).strip()) if cid else 0
    if pid <= 0:
        raise ServiceError(f"{service} is not running")
    return pid


def cgroup(run: Run, service: str, proc: Path = counters.PROC, root: Path = counters.CGROUP_ROOT) -> Path:
    return counters.cgroup_of(host_pid(run, service), proc, root)


def wait(
    probe: Callable[[], bool], what: str, timeout: float = READY_S, sleep=time.sleep, clock=time.monotonic
):
    end = clock() + timeout
    while not probe():
        if clock() > end:
            raise ServiceError(f"{what} not ready after {timeout:.0f} s")
        sleep(0.5)


def postgres_ready(run: Run) -> bool:
    try:
        run(compose("exec", "-T", "postgres", "pg_isready", "-U", "wayfinder", "-d", "s2"))
        return True
    except subprocess.CalledProcessError:
        return False


def ollama_ready(http: Http, service: str) -> bool:
    """Ready once `/api/version` answers; it must then be the pinned version."""
    status, body = http(f"{OLLAMA[service]}/api/version", None)
    if status != 200:
        return False
    if body.get("version") != OLLAMA_VERSION:
        raise ServiceError(f"{service} runs Ollama {body.get('version')}, pinned {OLLAMA_VERSION}")
    return True


def check_model(http: Http, service: str) -> None:
    """The embedding model is present at the pinned digest, read from the runtime, never the name."""
    status, body = http(f"{OLLAMA[service]}/api/tags", None)
    digests = {m.get("name"): m.get("digest") for m in body.get("models", [])} if status == 200 else {}
    if digests.get(MODEL) != MODEL_DIGEST:
        raise ServiceError(f"{service}: {MODEL} digest {digests.get(MODEL)}, pinned {MODEL_DIGEST}")


def pull_model(http: Http, service: str) -> None:
    """Pull the model by name, then refuse it unless its digest is the pinned one."""
    status, _ = http(f"{OLLAMA[service]}/api/pull", {"model": MODEL, "stream": False})
    if status != 200:
        raise ServiceError(f"{service}: pulling {MODEL} returned {status}")
    check_model(http, service)


def up(run: Run, http: Http, services=("postgres", "ollama-query")) -> None:
    run(compose("up", "-d", *services))
    for s in services:
        wait(lambda s=s: postgres_ready(run) if s == "postgres" else ollama_ready(http, s), s)


def reset(
    run: Run, http: Http, drop_caches: Path = Path("/proc/sys/vm/drop_caches"), sleep=time.sleep
) -> None:
    """ADR-0019's cold reset, steps 1 to 4, in order. Step 5 (model load) and step 6 (a new
    connection) belong to the cold pass, which measures them."""
    run(compose("stop", *COLD))  # Postgres makes its shutdown checkpoint
    run(["sync"])
    drop_caches.write_text("3\n")
    run(compose("start", *COLD))
    wait(lambda: postgres_ready(run), "postgres", sleep=sleep)
    wait(lambda: ollama_ready(http, "ollama-query"), "ollama-query", sleep=sleep)
    check_model(http, "ollama-query")


def connect(run: Run, dsn: str = DSN, proc: Path = counters.PROC, root: Path = counters.CGROUP_ROOT):
    """A new connection, so a new backend, and that backend's host pid (ADR-0019 step 6)."""
    import psycopg

    conn = psycopg.connect(dsn, autocommit=True)
    (backend,) = conn.execute("SELECT pg_backend_pid()").fetchone()
    return conn, counters.backend_host_pid(backend, cgroup(run, "postgres", proc, root), proc)
