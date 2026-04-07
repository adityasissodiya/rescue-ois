from fastapi.testclient import TestClient

from src.main import app

client = TestClient(app)


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "ops-api"}


def test_bootstrap_stub() -> None:
    response = client.get("/api/bootstrap")
    assert response.status_code == 501
