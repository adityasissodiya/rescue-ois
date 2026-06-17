"""Integration and xfail tests for partition and durability boundaries.

The Docker integration test is opt-in because it starts/uses the full local
Compose stack. The xfail tests intentionally keep unimplemented service-level
promotion and crash-boundary claims visible in normal test reports.
"""

from __future__ import annotations

import json
import os
import subprocess
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import pytest


ROOT = Path(__file__).resolve().parents[3]
NETWORK_NAME = "rescue-ois-net"
RESP_OPS = os.environ.get("RESP_OPS", "http://127.0.0.1:18101")
CMD_SYNCD = os.environ.get("CMD_SYNCD", "http://127.0.0.1:18081")
EDGE_DB = "rescue_ois_edge"


def _run(
    args: list[str],
    *,
    check: bool = True,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=ROOT,
        env=env,
        check=check,
        capture_output=True,
        text=True,
    )


def _docker_exec(container: str, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return _run(["docker", "exec", container, *args], check=check)


def _psql(container: str, db: str, sql: str, *, check: bool = True) -> str:
    proc = _docker_exec(container, "psql", "-U", "postgres", db, "-tAc", sql, check=check)
    return proc.stdout.strip()


def _http_json(method: str, url: str, body: dict | None = None, timeout_s: float = 10.0) -> tuple[int, dict]:
    data = json.dumps(body).encode("utf-8") if body is not None else None
    request = Request(url, data=data, headers={"Content-Type": "application/json"}, method=method)
    try:
        with urlopen(request, timeout=timeout_s) as response:
            raw = response.read().decode("utf-8")
            return response.status, json.loads(raw) if raw else {}
    except HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        return exc.code, json.loads(raw) if raw.startswith("{") else {}


def _wait_for_http(url: str, timeout_s: float = 90.0) -> None:
    deadline = time.monotonic() + timeout_s
    last = ""
    while time.monotonic() < deadline:
        try:
            status, _ = _http_json("GET", url, timeout_s=3.0)
            if status == 200:
                return
        except (URLError, TimeoutError, OSError) as exc:
            last = str(exc)
        time.sleep(1.0)
    raise TimeoutError(f"{url} did not become healthy: {last}")


def _wait_for_psql(container: str, db: str, timeout_s: float = 90.0) -> None:
    deadline = time.monotonic() + timeout_s
    last = ""
    while time.monotonic() < deadline:
        proc = _docker_exec(container, "psql", "-U", "postgres", db, "-tAc", "SELECT 1", check=False)
        if proc.returncode == 0 and proc.stdout.strip() == "1":
            return
        last = proc.stderr.strip() or proc.stdout.strip()
        time.sleep(1.0)
    raise TimeoutError(f"{container}/{db} did not become ready: {last}")


def _container_names() -> list[str]:
    proc = _run(["docker", "ps", "--format", "{{.Names}}"])
    return [line for line in proc.stdout.splitlines() if line]


def _edge_schema_present(container: str) -> bool:
    sql = """
        SELECT EXISTS (
            SELECT 1
            FROM information_schema.columns
            WHERE table_schema = 'incident'
              AND table_name = 'journal'
              AND column_name = 'client_event_id'
        )
    """
    return _psql(container, "rescue_ois_edge", sql, check=False) == "t"


def _core_schema_present() -> bool:
    sql = """
        SELECT EXISTS (
            SELECT 1
            FROM information_schema.columns
            WHERE table_schema = 'master'
              AND table_name = 'incident_events'
              AND column_name = 'client_event_id'
        )
    """
    return _psql("core-postgres-1", "rescue_ois", sql, check=False) == "t"


def _ensure_stack_and_schema() -> None:
    _run(["./scripts/dev-up.sh"], env={**os.environ, "RESPONDERS": "1"})
    _wait_for_http(f"{RESP_OPS}/health")
    _wait_for_psql("core-postgres-1", "rescue_ois")
    for name in _container_names():
        if name.startswith("edge-") and name.endswith("-postgres-1"):
            _wait_for_psql(name, "rescue_ois_edge")
    if not _core_schema_present():
        _run(["./scripts/run-migrations.sh", "core"])
    if any(
        not _edge_schema_present(name)
        for name in _container_names()
        if name.startswith("edge-") and name.endswith("-postgres-1")
    ):
        _run(["./scripts/run-migrations.sh", "edge"])


def _reset_tables() -> None:
    _psql(
        "edge-cmd-postgres-1",
        "rescue_ois_edge",
        "TRUNCATE incident.journal, incident.state, outbox.device_outbox CASCADE; DELETE FROM sync.state;",
    )
    _psql(
        "edge-resp-1-postgres-1",
        "rescue_ois_edge",
        "TRUNCATE incident.journal, incident.state, outbox.device_outbox CASCADE; DELETE FROM sync.state;",
    )
    _psql(
        "core-postgres-1",
        "rescue_ois",
        "TRUNCATE master.incident_events, master.incidents CASCADE;",
    )


def _container_connected(container: str) -> bool:
    proc = _run(["docker", "inspect", container], check=False)
    if proc.returncode != 0:
        return False
    info = json.loads(proc.stdout)[0]
    return NETWORK_NAME in info["NetworkSettings"]["Networks"]


def _network_aliases(container: str) -> list[str]:
    proc = _run(["docker", "inspect", container])
    info = json.loads(proc.stdout)[0]
    network = info["NetworkSettings"]["Networks"].get(NETWORK_NAME)
    return list(network.get("Aliases") or []) if network else []


def _reconnect_if_needed(container: str, aliases: list[str]) -> None:
    if _container_connected(container):
        return
    args = ["docker", "network", "connect"]
    for alias in aliases:
        args.extend(["--alias", alias])
    args.extend([NETWORK_NAME, container])
    _run(args)


def _count(container: str, sql: str, db: str = "rescue_ois_edge") -> int:
    return int(_psql(container, db, sql) or "0")


def _wait_for_count(container: str, sql: str, expected: int, timeout_s: float = 45.0) -> None:
    deadline = time.monotonic() + timeout_s
    last = -1
    while time.monotonic() < deadline:
        last = _count(container, sql)
        if last == expected:
            return
        time.sleep(0.25)
    raise AssertionError(f"expected count {expected}, got {last}: {sql}")


@pytest.mark.integration
def test_responder_partition_outbox_accumulates_then_replays() -> None:
    if os.environ.get("RESCUE_OIS_INTEGRATION_TESTS") != "1":
        pytest.skip("set RESCUE_OIS_INTEGRATION_TESTS=1 to run Docker partition test")

    _ensure_stack_and_schema()
    _reset_tables()

    incident_id = str(uuid.uuid4())
    event_count = 5
    responder_syncd = "edge-resp-1-syncd-1"
    aliases = _network_aliases(responder_syncd)
    audit_path = ROOT / "artifacts" / "data" / "responder_partition_outbox.audit.jsonl"
    partition_proc: subprocess.Popen[str] | None = None

    try:
        partition_proc = subprocess.Popen(
            ["./scripts/inject-partition.sh", "mesh", "5"],
            cwd=ROOT,
            env={
                **os.environ,
                "RESPONDER_INDEX": "1",
                "RESCUE_OIS_RUN_ID": f"pytest-{uuid.uuid4()}",
                "RESCUE_OIS_PARTITION_AUDIT_PATH": str(audit_path),
            },
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        deadline = time.monotonic() + 15.0
        while time.monotonic() < deadline and _container_connected(responder_syncd):
            if partition_proc.poll() is not None:
                stdout, stderr = partition_proc.communicate()
                raise AssertionError(f"partition exited early: {stderr.strip() or stdout.strip()}")
            time.sleep(0.1)
        assert not _container_connected(responder_syncd)

        bodies = []
        for index in range(event_count):
            body = {
                "client_event_id": str(uuid.uuid4()),
                "incident_id": incident_id,
                "event_type": "observation",
                "payload": {"partition_index": index},
                "device_id": "tab-partition-test",
                "user_id": "pytest",
                "occurred_at": datetime.now(UTC).isoformat(),
            }
            status, response = _http_json("POST", f"{RESP_OPS}/api/events", body)
            assert status == 200
            assert response["status"] == "accepted"
            bodies.append(body)

        assert _count(
            "edge-resp-1-postgres-1",
            f"SELECT count(*) FROM outbox.device_outbox WHERE incident_id = '{incident_id}' AND forwarded_at IS NULL",
        ) == event_count
        assert _count(
            "edge-cmd-postgres-1",
            f"SELECT count(*) FROM incident.journal WHERE incident_id = '{incident_id}'",
        ) == 0

        stdout, stderr = partition_proc.communicate(timeout=30)
        assert partition_proc.returncode == 0, stderr.strip() or stdout.strip()

        _wait_for_count(
            "edge-cmd-postgres-1",
            f"SELECT count(*) FROM incident.journal WHERE incident_id = '{incident_id}'",
            event_count,
        )
        _wait_for_count(
            "edge-resp-1-postgres-1",
            f"SELECT count(*) FROM outbox.device_outbox WHERE incident_id = '{incident_id}' AND forwarded_at IS NOT NULL",
            event_count,
        )

        seqs_raw = _psql(
            "edge-cmd-postgres-1",
            "rescue_ois_edge",
            f"SELECT COALESCE(string_agg(event_seq::text, ',' ORDER BY event_seq), '') FROM incident.journal WHERE incident_id = '{incident_id}'",
        )
        assert [int(value) for value in seqs_raw.split(",") if value] == list(range(1, event_count + 1))

        for body in bodies:
            status, _ = _http_json("POST", f"{RESP_OPS}/api/events", body)
            assert status == 200
        time.sleep(2.0)
        assert _count(
            "edge-cmd-postgres-1",
            f"SELECT count(*) FROM incident.journal WHERE incident_id = '{incident_id}'",
        ) == event_count
    finally:
        _reconnect_if_needed(responder_syncd, aliases)
        if partition_proc is not None and partition_proc.poll() is None:
            partition_proc.kill()


def _require_integration() -> None:
    if os.environ.get("RESCUE_OIS_INTEGRATION_TESTS") != "1":
        pytest.skip("set RESCUE_OIS_INTEGRATION_TESTS=1 to run Docker integration tests")


def _current_epoch() -> int:
    return int(_psql("edge-cmd-postgres-1", EDGE_DB, "SELECT epoch_id FROM incident.current_epoch") or "0")


def _post_accept(incident_id: str, epoch_header: int | None, n: int = 1) -> tuple[int, dict]:
    events = [
        {
            "id": str(uuid.uuid4()),
            "incident_id": incident_id,
            "client_event_id": str(uuid.uuid4()),
            "device_id": "pytest",
            "user_id": "u",
            "event_type": "observation",
            "payload": {"i": i},
            "created_at": datetime.now(UTC).isoformat(),
        }
        for i in range(n)
    ]
    data = json.dumps({"events": events}).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if epoch_header is not None:
        headers["X-Command-Epoch"] = str(epoch_header)
    request = Request(f"{CMD_SYNCD}/accept/event-batch", data=data, headers=headers, method="POST")
    try:
        with urlopen(request, timeout=10.0) as response:
            raw = response.read().decode("utf-8")
            return response.status, (json.loads(raw) if raw else {})
    except HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        return exc.code, (json.loads(raw) if raw.startswith("{") else {})


@pytest.mark.integration
def test_stale_command_epoch_rejected_after_promotion() -> None:
    """Durable command_epoch fencing on the service accept path: a request at
    the current epoch commits, a stale epoch is rejected 409 before any journal
    write, and a missing header is rejected 409. Implemented by migration
    005_command_epoch.sql + edge/syncd/src/accept.py; unit-covered in
    test_accept_epoch.py."""
    _require_integration()
    epoch = _current_epoch()
    assert epoch >= 1
    incident = str(uuid.uuid4())

    status, body = _post_accept(incident, epoch, n=1)
    assert status == 200, body
    assert body.get("accepted") == 1

    status, body = _post_accept(incident, epoch - 1, n=1)
    assert status == 409
    assert body.get("detail", {}).get("reason") == "stale_epoch"

    status, body = _post_accept(incident, None, n=1)
    assert status == 409
    assert body.get("detail", {}).get("reason") == "missing_epoch"


@pytest.mark.integration
def test_promotion_record_required_before_new_command_accepts_events() -> None:
    """Acceptance is gated by the durable command_epoch record: a future epoch
    with no command_epoch row is rejected 409, so a writer cannot claim an epoch
    that the promotion procedure (scripts/promote-responder.sh inserts the row)
    never recorded."""
    _require_integration()
    epoch = _current_epoch()
    incident = str(uuid.uuid4())
    status, body = _post_accept(incident, epoch + 1, n=1)
    assert status == 409
    assert body.get("detail", {}).get("reason") == "future_epoch"


@pytest.mark.xfail(
    reason="cross-edge SingleCommand is established by the strict TLA+ model (Sec V); the "
    "single-edge service harness cannot run two command-role writers for the same incident, "
    "so this property has no service-path witness",
    strict=True,
)
def test_no_two_command_writers_for_same_incident_epoch() -> None:
    raise AssertionError("cross-edge two-writer race is model-only; see strict TLA+ SingleCommand")


@pytest.mark.integration
def test_crash_after_local_outbox_insert_before_forward_preserves_event() -> None:
    """R2: an event accepted into the responder outbox survives a vehicle
    (Postgres) power-cycle and forwards to the command journal exactly once.
    Driven by scripts/evaluate-outbox-crash-restart.py, which exits non-zero on
    any loss, duplicate, or non-contiguous sequence."""
    _require_integration()
    proc = _run(
        [
            "python3", "scripts/evaluate-outbox-crash-restart.py",
            "--events", "20",
            "--artifact", "/tmp/eval_outbox_crash_restart.pytest.jsonl",
        ],
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + "\n" + proc.stderr


@pytest.mark.xfail(
    reason="mid-flight crash injection (command append committed but ack lost before the "
    "outbox forwarded_at mark) is not automated; the idempotent-retry guarantee itself is "
    "covered by client_event_id dedup (test_accept dedup path + duplicate_replay scenario)",
    strict=True,
)
def test_crash_after_command_append_before_ack_does_not_duplicate_on_retry() -> None:
    raise AssertionError("mid-flight ack-loss crash harness not implemented; dedup path covered elsewhere")


@pytest.mark.xfail(
    reason="mid-flight crash injection before the forwarded_at mark is not automated; "
    "post-restart re-forward de-duplication is exercised indirectly by the R2 outbox "
    "durability test above",
    strict=True,
)
def test_crash_before_forwarded_mark_retries_without_duplicate_journal_row() -> None:
    raise AssertionError("mid-flight forwarded-mark crash harness not implemented; see R2 durability test")
