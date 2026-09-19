import os
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from src.main import app

client = TestClient(app)


def _require_integration() -> None:
    """Skip unless a migrated core Postgres is reachable.

    Every command-epoch and journal-events path touches the database, so the
    default suite can only exercise request validation. Behavioural coverage
    lives behind this flag, matching edge/syncd's convention.
    """
    if os.environ.get("RESCUE_OIS_INTEGRATION_TESTS") != "1":
        pytest.skip("set RESCUE_OIS_INTEGRATION_TESTS=1 to run DB-backed sync-api tests")


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "sync-api"}


def test_sync_events_compat() -> None:
    response = client.get("/sync/events")
    assert response.status_code == 200
    assert response.json() == {"latest_seq": 0, "events": []}


def test_empty_journal_batch_ack() -> None:
    response = client.post("/sync/journal-batch", json={"events": []})
    assert response.status_code == 200
    assert response.json() == {"accepted": 0, "duplicates": 0, "last_acked_seq": 0}


# --- request validation (no database required) -----------------------------


def test_journal_batch_accepts_optional_command_epoch() -> None:
    """command_epoch is backward-compatible: present or absent, the contract holds.

    An empty batch short-circuits before any DB access, so this exercises
    parsing of the new field without a database.
    """
    response = client.post("/sync/journal-batch", json={"events": [], "command_epoch": 7})
    assert response.status_code == 200
    assert response.json() == {"accepted": 0, "duplicates": 0, "last_acked_seq": 0}


def test_promote_rejects_incomplete_request() -> None:
    response = client.post(
        "/sync/command-epoch/promote", json={"incident_id": str(uuid4())}
    )
    assert response.status_code == 422


def test_promote_rejects_malformed_incident_id() -> None:
    response = client.post(
        "/sync/command-epoch/promote",
        json={"incident_id": "not-a-uuid", "started_by": "op", "node_id": "edge-cmd"},
    )
    assert response.status_code == 422


def test_journal_events_rejects_negative_after_seq() -> None:
    response = client.get(
        "/sync/journal-events", params={"incident_id": str(uuid4()), "after_seq": -1}
    )
    assert response.status_code == 422


def test_journal_events_rejects_oversized_limit() -> None:
    """The page limit is capped so one request cannot pull an unbounded journal."""
    response = client.get(
        "/sync/journal-events", params={"incident_id": str(uuid4()), "limit": 100000}
    )
    assert response.status_code == 422


# --- behaviour (requires a migrated core Postgres) -------------------------


@pytest.mark.integration
def test_promote_is_monotonic_and_serialized() -> None:
    """Consecutive promotions strictly increase, and the epoch is readable back.

    Concurrency itself is covered by the harness rather than here: this asserts
    the monotonic contract the promotion protocol depends on.
    """
    _require_integration()
    incident_id = str(uuid4())
    client.post(
        "/sync/journal-batch",
        json={
            "events": [
                {
                    "incident_id": incident_id,
                    "event_seq": 1,
                    "event_type": "seed",
                    "payload": {},
                    "device_id": "pytest",
                    "user_id": "pytest",
                    "client_event_id": str(uuid4()),
                    "created_at": "2026-01-01T00:00:00+00:00",
                }
            ]
        },
    )

    first = client.post(
        "/sync/command-epoch/promote",
        json={"incident_id": incident_id, "started_by": "pytest", "node_id": "edge-cmd"},
    )
    assert first.status_code == 200, first.text
    second = client.post(
        "/sync/command-epoch/promote",
        json={"incident_id": incident_id, "started_by": "pytest", "node_id": "edge-resp-1"},
    )
    assert second.status_code == 200, second.text
    assert second.json()["epoch_id"] > first.json()["epoch_id"]

    current = client.get("/sync/command-epoch", params={"incident_id": incident_id})
    assert current.status_code == 200
    assert current.json()["epoch_id"] == second.json()["epoch_id"]


@pytest.mark.integration
def test_promote_unknown_incident_is_404() -> None:
    _require_integration()
    response = client.post(
        "/sync/command-epoch/promote",
        json={"incident_id": str(uuid4()), "started_by": "pytest", "node_id": "ghost"},
    )
    assert response.status_code == 404
    assert response.json()["detail"]["reason"] == "unknown_incident"


@pytest.mark.integration
def test_stale_epoch_batch_is_rejected_before_any_write() -> None:
    """A demoted command's buffered batch must be refused, not silently taken."""
    _require_integration()
    incident_id = str(uuid4())

    def batch(epoch: int | None) -> dict:
        body: dict = {
            "events": [
                {
                    "incident_id": incident_id,
                    "event_seq": 1,
                    "event_type": "observation",
                    "payload": {},
                    "device_id": "pytest",
                    "user_id": "pytest",
                    "client_event_id": str(uuid4()),
                    "created_at": "2026-01-01T00:00:00+00:00",
                }
            ]
        }
        if epoch is not None:
            body["command_epoch"] = epoch
        return body

    assert client.post("/sync/journal-batch", json=batch(None)).status_code == 200
    client.post(
        "/sync/command-epoch/promote",
        json={"incident_id": incident_id, "started_by": "pytest", "node_id": "edge-cmd"},
    )
    client.post(
        "/sync/command-epoch/promote",
        json={"incident_id": incident_id, "started_by": "pytest", "node_id": "edge-resp-1"},
    )

    stale = client.post("/sync/journal-batch", json=batch(1))
    assert stale.status_code == 409
    assert stale.json()["detail"]["reason"] == "stale_epoch"

    future = client.post("/sync/journal-batch", json=batch(999))
    assert future.status_code == 409
    assert future.json()["detail"]["reason"] == "future_epoch"


@pytest.mark.integration
def test_journal_events_pages_in_sequence_order() -> None:
    _require_integration()
    incident_id = str(uuid4())
    events = [
        {
            "incident_id": incident_id,
            "event_seq": seq,
            "event_type": "observation",
            "payload": {"i": seq},
            "device_id": "pytest",
            "user_id": "pytest",
            "client_event_id": str(uuid4()),
            "created_at": "2026-01-01T00:00:00+00:00",
        }
        for seq in range(1, 6)
    ]
    assert client.post("/sync/journal-batch", json={"events": events}).status_code == 200

    first = client.get(
        "/sync/journal-events", params={"incident_id": incident_id, "after_seq": 0, "limit": 2}
    )
    assert first.status_code == 200, first.text
    body = first.json()
    assert [e["event_seq"] for e in body["events"]] == [1, 2]
    assert body["has_more"] is True
    assert body["next_after_seq"] == 2

    rest = client.get(
        "/sync/journal-events",
        params={"incident_id": incident_id, "after_seq": body["next_after_seq"], "limit": 500},
    )
    assert [e["event_seq"] for e in rest.json()["events"]] == [3, 4, 5]
    assert rest.json()["has_more"] is False
