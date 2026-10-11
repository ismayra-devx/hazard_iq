"""
Tests for Citizen Hazard Reporting endpoints, validation, and storage
adhering strictly to the HazardIQ API Contract.
"""

import base64
import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


# Minimal valid 1x1 pixel JPEG
VALID_1X1_JPEG_B64 = (
    "data:image/jpeg;base64,"
    "/9j/4AAQSkZJRgABAQEASABIAAD/2wBDAP////////////////////////////////////////////////"
    "//////////////////////////////////////wgALCAABAAEBAREA/8QAFBABAAAAAAAAAAAAAAAAAAAA"
    "AP/aAAgBAQABPxA="
)


@pytest.mark.asyncio
async def test_submit_valid_monsoon_report():
    payload = {
        "lat": 28.6331,
        "lng": 77.2252,
        "hazard_mode": "monsoon",
        "vehicle_type": "two_wheeler",
        "image_base64": VALID_1X1_JPEG_B64
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/report", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert data["verification_status"] == "verified"
        assert "detected_hazard" in data
        assert data["detected_hazard"]["water_depth_inches"] > 0
        assert data["detected_hazard"]["shade_coverage_percent"] == 100
        assert data["cedar_routing_decision"] in ("ALLOW_ROUTE", "DENY_ROUTE")
        assert "ui_message" in data


@pytest.mark.asyncio
async def test_submit_valid_heatwave_report():
    payload = {
        "lat": 28.6315,
        "lng": 77.2167,
        "hazard_mode": "heatwave",
        "vehicle_type": "pedestrian",
        "image_base64": VALID_1X1_JPEG_B64
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/report", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert data["verification_status"] == "verified"
        assert data["detected_hazard"]["water_depth_inches"] == 0
        assert 0 <= data["detected_hazard"]["shade_coverage_percent"] <= 100
        assert data["cedar_routing_decision"] in ("ALLOW_ROUTE", "DENY_ROUTE")
        assert len(data["ui_message"]) > 0


@pytest.mark.asyncio
async def test_reject_invalid_coordinates():
    payload = {
        "lat": 150.0,  # Invalid latitude (>90)
        "lng": 77.2252,
        "hazard_mode": "monsoon",
        "vehicle_type": "two_wheeler",
        "image_base64": VALID_1X1_JPEG_B64
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/report", json=payload)
        assert response.status_code == 422
        data = response.json()
        assert "error" in data
        assert data["error"]["error_code"] == "VALIDATION_ERROR"


@pytest.mark.asyncio
async def test_reject_invalid_hazard_mode():
    payload = {
        "lat": 28.6331,
        "lng": 77.2252,
        "hazard_mode": "earthquake",  # Not allowed
        "vehicle_type": "two_wheeler",
        "image_base64": VALID_1X1_JPEG_B64
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/report", json=payload)
        assert response.status_code == 422


@pytest.mark.asyncio
async def test_reject_malformed_base64_image():
    payload = {
        "lat": 28.6331,
        "lng": 77.2252,
        "hazard_mode": "monsoon",
        "vehicle_type": "two_wheeler",
        "image_base64": "data:image/jpeg;base64,NOT_A_VALID_BASE64_PAYLOAD!@#$"
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/report", json=payload)
        assert response.status_code == 422


@pytest.mark.asyncio
async def test_reject_invalid_image_magic_bytes():
    fake_image_b64 = "data:image/jpeg;base64," + base64.b64encode(b"This is just plain text, not an image!").decode("ascii")
    payload = {
        "lat": 28.6331,
        "lng": 77.2252,
        "hazard_mode": "monsoon",
        "vehicle_type": "two_wheeler",
        "image_base64": fake_image_b64
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/report", json=payload)
        assert response.status_code == 422


@pytest.mark.asyncio
async def test_list_and_get_reports_lifecycle():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Create a report
        create_res = await client.post(
            "/api/report",
            json={
                "lat": 28.5672,
                "lng": 77.2100,
                "hazard_mode": "monsoon",
                "vehicle_type": "car",
                "image_base64": VALID_1X1_JPEG_B64
            }
        )
        assert create_res.status_code == 201

        # List reports
        list_res = await client.get("/api/reports?limit=10")
        assert list_res.status_code == 200
        reports = list_res.json()
        assert len(reports) > 0
        assert "report_id" in reports[0]

        # Get first report by ID
        first_id = reports[0]["report_id"]
        get_res = await client.get(f"/api/reports/{first_id}")
        assert get_res.status_code == 200
        assert get_res.json()["report_id"] == first_id

        # Get non-existent report
        not_found_res = await client.get("/api/reports/rep-does-not-exist")
        assert not_found_res.status_code == 404
