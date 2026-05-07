"""Smoke tests: same property checks against the running Docker stack."""

from __future__ import annotations

import os
import subprocess
import time
import uuid
from datetime import UTC, datetime

import httpx
import pytest


pytestmark = pytest.mark.skipif(
    os.environ.get("RESCUE_OIS_REAL_STACK") != "1",
    reason="Real-stack tests are opt-in; set RESCUE_OIS_REAL_STACK=1.",
)

RESP_OPS = os.environ.get("RESP_OPS", "http://ops-api.edge-resp-1:8000")
CMD_PG = "edge-cmd-postgres-1"
DB = "rescue_ois_edge"


def submit(client: httpx.Client, incident_id: str, cid: str) -> int:
    body = {
        "client_event_id": cid,
        "incident_id": incident_id,
        "event_type": "observation",
        "payload": {},
        "device_id": "real-test",
        "user_id": "u",
        "occurred_at": datetime.now(UTC).isoformat(),
    }
    response = client.post(f"{RESP_OPS}/api/events", json=body, timeout=10.0)
    return response.status_code


def journal_count(incident_id: str) -> int:
    out = subprocess.run(
        [
            "docker", "exec", CMD_PG,
            "psql", "-U", "postgres", DB, "-tAc",
            f"SELECT count(*) FROM incident.journal WHERE incident_id = '{incident_id}'",
        ],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    return int(out)


def test_real_stack_idempotent_replay() -> None:
    incident = "00000000-0000-0000-0000-000000000ee1"
    cid = str(uuid.uuid4())
    with httpx.Client() as client:
        for _ in range(10):
            assert submit(client, incident, cid) == 200
    time.sleep(2.0)
    assert journal_count(incident) == 1


def test_real_stack_distinct_cids() -> None:
    incident = "00000000-0000-0000-0000-000000000ee2"
    cids = [str(uuid.uuid4()) for _ in range(5)]
    with httpx.Client() as client:
        for cid in cids:
            assert submit(client, incident, cid) == 200
    time.sleep(2.0)
    assert journal_count(incident) == 5
