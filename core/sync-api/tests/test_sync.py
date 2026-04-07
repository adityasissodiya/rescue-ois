from fastapi.testclient import TestClient

from src.main import app

client = TestClient(app)


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "sync-api"}


def test_sync_events_stub() -> None:
    response = client.get("/sync/events")
    assert response.status_code == 501


def test_sync_bootstrap_stub() -> None:
    response = client.get("/sync/bootstrap", params={"incident_id": "abc"})
    assert response.status_code == 501
