from fastapi.testclient import TestClient

from src.main import app

client = TestClient(app)


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
