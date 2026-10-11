"""
Tests for GET /api/hotspots endpoint.
"""

from fastapi.testclient import TestClient

try:
    import main
    from main import app
except ImportError:
    from backend import main
    from backend.main import app

client = TestClient(app)


def test_get_hotspots_returns_array():
    """Verify endpoint returns a JSON array with status 200."""
    response = client.get("/api/hotspots")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_hotspots_seed_count_and_fields():
    """Verify at least 5 demo hotspots with required field names and valid coordinates."""
    response = client.get("/api/hotspots")
    assert response.status_code == 200
    hotspots = response.json()
    assert len(hotspots) >= 5, "Must contain at least 5 demo hotspots"

    required_fields = {
        "id",
        "name",
        "lat",
        "lng",
        "type",
        "baseline_impermeability_ratio",
        "elevation_dip_meters",
        "current_risk_status",
    }

    for spot in hotspots:
        for field in required_fields:
            assert field in spot, f"Missing required field '{field}' in hotspot record {spot}"

        assert -90.0 <= spot["lat"] <= 90.0, f"Invalid latitude: {spot['lat']}"
        assert -180.0 <= spot["lng"] <= 180.0, f"Invalid longitude: {spot['lng']}"
        assert 0.0 <= spot["baseline_impermeability_ratio"] <= 1.0
        # Verification that demo data uses a recognized risk status
        assert spot["current_risk_status"] in ("unknown", "clear", "moderate_risk", "high_risk", "low_risk")


def test_hotspots_error_handling_when_file_missing(monkeypatch):
    """Verify appropriate HTTP 500 error when hotspots file cannot be loaded."""
    def mock_find_hotspots_file():
        raise FileNotFoundError("Simulated missing file")

    monkeypatch.setattr(main, "find_hotspots_file", mock_find_hotspots_file)

    response = client.get("/api/hotspots")
    assert response.status_code == 500
    assert "detail" in response.json()
