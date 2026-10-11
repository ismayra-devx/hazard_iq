"""
Tests for Hotspots database, schema validation, and API endpoints
adhering to the HazardIQ API Contract (JSON List format).
"""

import json
import pytest
from httpx import ASGITransport, AsyncClient

from app.config import settings
from app.main import app
from app.schemas import HotspotContractItem


def test_hotspot_json_loading_and_schema():
    with open(settings.HOTSPOTS_FILE_PATH, "r", encoding="utf-8") as f:
        records = json.load(f)

    assert len(records) >= 20, f"Expected at least 20 sample records, found {len(records)}"

    for record in records:
        validated = HotspotContractItem(**record)
        assert validated.id
        assert -90.0 <= validated.lat <= 90.0
        assert -180.0 <= validated.lng <= 180.0
        assert 0.0 <= validated.baseline_impermeability_ratio <= 1.0
        assert validated.current_risk_status in ("clear", "monsoon_warning", "heatwave_warning", "impassable")


@pytest.mark.asyncio
async def test_get_all_hotspots_api():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/hotspots")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list), "Response must be a direct JSON List"
        assert len(data) >= 20

        first = data[0]
        assert "id" in first
        assert "name" in first
        assert "lat" in first
        assert "lng" in first
        assert "type" in first
        assert "baseline_impermeability_ratio" in first
        assert "elevation_dip_meters" in first
        assert "current_risk_status" in first
        assert first["current_risk_status"] in ("clear", "monsoon_warning", "heatwave_warning", "impassable")


@pytest.mark.asyncio
async def test_filter_hotspots_by_type():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/hotspots?type=underpass")
        assert response.status_code == 200
        data = response.json()
        assert len(data) > 0
        for item in data:
            assert item["type"] == "underpass"


@pytest.mark.asyncio
async def test_get_hotspot_by_valid_id():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/hotspots/point_001")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "point_001"
        assert "Minto Bridge" in data["name"]


@pytest.mark.asyncio
async def test_get_hotspot_by_invalid_id():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/hotspots/point_non_existent_999")
        assert response.status_code == 404
