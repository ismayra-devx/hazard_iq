"""
Tests for GET /health endpoint.
"""

from fastapi.testclient import TestClient

try:
    from main import app
except ImportError:
    from backend.main import app

client = TestClient(app)


def test_health_check_success():
    """Verify health endpoint returns status 200, status ok, and service name."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "hazardiq-backend"


def test_health_check_without_aws_credentials(monkeypatch):
    """Ensure health endpoint functions when AWS credentials and env flags are absent."""
    monkeypatch.delenv("AWS_ACCESS_KEY_ID", raising=False)
    monkeypatch.delenv("AWS_SECRET_ACCESS_KEY", raising=False)
    monkeypatch.setenv("AWS_INTEGRATION_ENABLED", "false")

    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
