"""
End-to-End Golden Path Demonstration Scenarios
strictly validating the HazardIQ API Contract (PDF Specification).
"""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


VALID_1X1_JPEG_B64 = (
    "data:image/jpeg;base64,"
    "/9j/4AAQSkZJRgABAQEASABIAAD/2wBDAP////////////////////////////////////////////////"
    "//////////////////////////////////////wgALCAABAAEBAREA/8QAFBABAAAAAAAAAAAAAAAAAAAA"
    "AP/aAAgBAQABPxA="
)


@pytest.mark.asyncio
async def test_golden_path_monsoon_waterlogging_flow():
    """
    Scenario 1: Monsoon Mode & Citizen Waterlogging Report Flow
    1. Frontend loads mapped choke points (GET /api/hotspots) as a direct JSON List.
    2. Hotspots return static coordinates and current_risk_status.
    3. Commuter files a waterlogging report on a low-lying road (Minto Bridge underpass).
    4. Backend validates request according to HazardIQ API Contract.
    5. Vision verification evaluates image and returns water_depth_inches & shade_coverage_percent.
    6. Cedar policy returns routing verdict (DENY_ROUTE) with user-facing ui_message.
    """
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Step 1 & 2: Frontend loads hotspots list
        hotspots_res = await client.get("/api/hotspots")
        assert hotspots_res.status_code == 200
        hotspots = hotspots_res.json()
        assert isinstance(hotspots, list), "Contract requires direct JSON List"
        assert len(hotspots) >= 20

        # Verify Minto Bridge exists with depression attribute
        minto = next(h for h in hotspots if h["id"] == "point_001")
        assert minto["name"] == "Minto Bridge Underpass"
        assert minto["elevation_dip_meters"] < 0
        assert minto["current_risk_status"] in ("clear", "monsoon_warning", "heatwave_warning", "impassable")

        # Step 3 & 4: Commuter submits photo report
        report_payload = {
            "lat": minto["lat"],
            "lng": minto["lng"],
            "hazard_mode": "monsoon",
            "vehicle_type": "two_wheeler",
            "image_base64": VALID_1X1_JPEG_B64
        }
        submit_res = await client.post("/api/report", json=report_payload)
        assert submit_res.status_code == 201
        report = submit_res.json()

        # Step 5 & 6: Verify contract response shape
        assert report["verification_status"] == "verified"
        assert "detected_hazard" in report
        assert report["detected_hazard"]["water_depth_inches"] > 0
        assert report["detected_hazard"]["shade_coverage_percent"] == 100  # Contract rule for monsoon
        assert report["cedar_routing_decision"] == "DENY_ROUTE"
        assert "Water depth exceeds safe clearance for two-wheelers" in report["ui_message"]


@pytest.mark.asyncio
async def test_golden_path_heatwave_corridor_flow():
    """
    Scenario 2: Heatwave Mode & Thermal Relief Hydration Flow
    1. Frontend loads mapped choke points for heatwave navigation.
    2. Commuter uploads hazard report with hazard_mode="heatwave".
    3. Backend returns water_depth_inches=0 and measured shade_coverage_percent.
    4. Cedar policy evaluates routing decision and user-facing advice.
    """
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Step 1: Frontend loads hotspots
        hotspots_res = await client.get("/api/hotspots?type=transit_hub")
        assert hotspots_res.status_code == 200
        transit_points = hotspots_res.json()
        assert isinstance(transit_points, list)
        cp_point = next(h for h in transit_points if h["id"] == "point_002")

        # Step 2 & 3: Submit heatwave hazard report
        heat_payload = {
            "lat": cp_point["lat"],
            "lng": cp_point["lng"],
            "hazard_mode": "heatwave",
            "vehicle_type": "pedestrian",
            "image_base64": VALID_1X1_JPEG_B64
        }
        submit_res = await client.post("/api/report", json=heat_payload)
        assert submit_res.status_code == 201
        report = submit_res.json()

        assert report["verification_status"] == "verified"
        assert report["detected_hazard"]["water_depth_inches"] == 0  # Contract rule for heatwave
        assert 0 <= report["detected_hazard"]["shade_coverage_percent"] <= 100
        assert report["cedar_routing_decision"] in ("ALLOW_ROUTE", "DENY_ROUTE")
        assert len(report["ui_message"]) > 0
