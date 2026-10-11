"""
Comprehensive tests for POST /api/report endpoint.
Covers input validation, error handling, image security, AWS-disabled mode, and service failure recovery.
"""

import base64
from fastapi.testclient import TestClient

try:
    import main
    from main import app
    from services.bedrock_service import bedrock_service
    from services.dynamodb_service import dynamodb_service
    from services.s3_service import s3_service
except ImportError:
    from backend import main
    from backend.main import app
    from backend.services.bedrock_service import bedrock_service
    from backend.services.dynamodb_service import dynamodb_service
    from backend.services.s3_service import s3_service

client = TestClient(app)

# Minimal valid JPEG bytes
VALID_JPEG_BYTES = (
    b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00"
    b"\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t"
    b"\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00\xff\xc4\x00\x1f\x00\x00\x01\x05\x01\x01\x01\x01\x01\x01\x00\x00\x00\x00\x00\x00\x00"
    b"\xff\xda\x00\x08\x01\x01\x00\x00?\x00\xbf\x80\xff\xd9"
)
VALID_JPEG_BASE64 = base64.b64encode(VALID_JPEG_BYTES).decode("utf-8")
VALID_DATA_URI = f"data:image/jpeg;base64,{VALID_JPEG_BASE64}"

# Minimal valid PNG bytes
VALID_PNG_BYTES = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01\x00"
    b"\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
)
VALID_PNG_BASE64 = base64.b64encode(VALID_PNG_BYTES).decode("utf-8")


# ==============================================================================
# Validation Tests
# ==============================================================================

def test_reject_invalid_latitude():
    """Latitude > 90 must trigger 422 Unprocessable Entity."""
    payload = {
        "lat": 95.0,
        "lng": 77.2090,
        "hazard_mode": "monsoon",
        "vehicle_type": "two_wheeler",
        "image_base64": VALID_JPEG_BASE64,
    }
    response = client.post("/api/report", json=payload)
    assert response.status_code == 422


def test_reject_invalid_longitude():
    """Longitude < -180 must trigger 422 Unprocessable Entity."""
    payload = {
        "lat": 28.6139,
        "lng": -195.0,
        "hazard_mode": "monsoon",
        "vehicle_type": "two_wheeler",
        "image_base64": VALID_JPEG_BASE64,
    }
    response = client.post("/api/report", json=payload)
    assert response.status_code == 422


def test_reject_invalid_hazard_mode():
    """Hazard mode other than monsoon/heatwave must trigger 422."""
    payload = {
        "lat": 28.6139,
        "lng": 77.2090,
        "hazard_mode": "blizzard",
        "vehicle_type": "two_wheeler",
        "image_base64": VALID_JPEG_BASE64,
    }
    response = client.post("/api/report", json=payload)
    assert response.status_code == 422


def test_reject_invalid_vehicle_type():
    """Vehicle type other than two_wheeler/car/pedestrian must trigger 422."""
    payload = {
        "lat": 28.6139,
        "lng": 77.2090,
        "hazard_mode": "monsoon",
        "vehicle_type": "helicopter",
        "image_base64": VALID_JPEG_BASE64,
    }
    response = client.post("/api/report", json=payload)
    assert response.status_code == 422


def test_reject_malformed_base64():
    """Malformed Base64 string must return 400 Bad Request."""
    payload = {
        "lat": 28.6139,
        "lng": 77.2090,
        "hazard_mode": "monsoon",
        "vehicle_type": "two_wheeler",
        "image_base64": "Not-Valid-Base-64-@#!*%",
    }
    response = client.post("/api/report", json=payload)
    assert response.status_code == 400
    assert "Base64" in response.json()["detail"]


def test_reject_unsupported_image_magic_bytes():
    """Base64 data containing plain text instead of JPEG/PNG/WEBP must return 400."""
    plain_text_b64 = base64.b64encode(b"This is just a text file disguised as an image").decode("utf-8")
    payload = {
        "lat": 28.6139,
        "lng": 77.2090,
        "hazard_mode": "monsoon",
        "vehicle_type": "two_wheeler",
        "image_base64": plain_text_b64,
    }
    response = client.post("/api/report", json=payload)
    assert response.status_code == 400
    assert "Unsupported image format" in response.json()["detail"]


def test_reject_oversized_upload(monkeypatch):
    """Uploaded image exceeding size limit must return 413 Request Entity Too Large."""
    monkeypatch.setattr(main, "MAX_IMAGE_SIZE_BYTES", 50)  # artificially low 50 bytes

    payload = {
        "lat": 28.6139,
        "lng": 77.2090,
        "hazard_mode": "monsoon",
        "vehicle_type": "two_wheeler",
        "image_base64": VALID_JPEG_BASE64,
    }
    response = client.post("/api/report", json=payload)
    assert response.status_code == 413


# ==============================================================================
# Success and Integration Tests
# ==============================================================================

def test_submit_valid_report_local_aws_disabled():
    """Submitting report with AWS disabled succeeds, returning pending_review and UNKNOWN routing."""
    payload = {
        "lat": 28.6331,
        "lng": 77.2252,
        "hazard_mode": "monsoon",
        "vehicle_type": "two_wheeler",
        "image_base64": VALID_DATA_URI,
    }
    response = client.post("/api/report", json=payload)
    assert response.status_code == 201
    data = response.json()

    assert data["verification_status"] == "pending_review"
    assert data["analysis_status"] == "analysis_unavailable"
    assert data["cedar_routing_decision"] == "UNKNOWN"
    assert data["decision_engine"] == "python_fallback"
    assert data["image_storage_status"] == "not_configured"
    assert data["persistence_status"] == "not_configured"
    assert isinstance(data["data_limitations"], list)
    assert len(data["data_limitations"]) > 0


def test_submit_valid_png_report():
    """Submitting valid PNG base64 works cleanly."""
    payload = {
        "lat": 28.6331,
        "lng": 77.2252,
        "hazard_mode": "heatwave",
        "vehicle_type": "pedestrian",
        "image_base64": f"data:image/png;base64,{VALID_PNG_BASE64}",
    }
    response = client.post("/api/report", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["verification_status"] == "pending_review"


def test_mocked_bedrock_monsoon_hazard_denies_route(monkeypatch):
    """When Bedrock estimates deep water (14 inches), two-wheeler gets DENY_ROUTE."""
    async def mock_analyze(image_bytes, image_base64, hazard_mode):
        return (14, None, "completed", 0.85, ["Visual estimation limitation."])

    monkeypatch.setattr(bedrock_service, "analyze_hazard_image", mock_analyze)

    payload = {
        "lat": 28.6331,
        "lng": 77.2252,
        "hazard_mode": "monsoon",
        "vehicle_type": "two_wheeler",
        "image_base64": VALID_JPEG_BASE64,
    }
    response = client.post("/api/report", json=payload)
    assert response.status_code == 201
    data = response.json()

    assert data["detected_hazard"]["water_depth_inches"] == 14
    assert data["cedar_routing_decision"] == "DENY_ROUTE"
    assert "exceeds safe clearance" in data["ui_message"]


def test_mocked_bedrock_failure_recovers_safely(monkeypatch):
    """When Bedrock raises an exception, the backend does not crash and returns UNKNOWN decision."""
    async def mock_analyze_fail(image_bytes, image_base64, hazard_mode):
        return (None, None, "analysis_unavailable", 0.0, ["Service connection failed."])

    monkeypatch.setattr(bedrock_service, "analyze_hazard_image", mock_analyze_fail)

    payload = {
        "lat": 28.6331,
        "lng": 77.2252,
        "hazard_mode": "monsoon",
        "vehicle_type": "car",
        "image_base64": VALID_JPEG_BASE64,
    }
    response = client.post("/api/report", json=payload)
    assert response.status_code == 201
    data = response.json()

    assert data["analysis_status"] == "analysis_unavailable"
    assert data["detected_hazard"]["water_depth_inches"] is None
    # Critical requirement: missing water depth does NOT become ALLOW_ROUTE!
    assert data["cedar_routing_decision"] == "UNKNOWN"


def test_mocked_s3_and_dynamodb_failures_recorded_accurately(monkeypatch):
    """Storage failures are accurately reflected in status fields rather than masked as success."""
    async def mock_s3_upload(report_uuid, image_bytes):
        return {"status": "failed", "object_key": "", "bucket": "test-bucket"}

    async def mock_ddb_save(report_item):
        return "failed"

    monkeypatch.setattr(s3_service, "upload_image", mock_s3_upload)
    monkeypatch.setattr(dynamodb_service, "save_report", mock_ddb_save)

    payload = {
        "lat": 28.6331,
        "lng": 77.2252,
        "hazard_mode": "heatwave",
        "vehicle_type": "two_wheeler",
        "image_base64": VALID_JPEG_BASE64,
    }
    response = client.post("/api/report", json=payload)
    assert response.status_code == 201
    data = response.json()

    assert data["image_storage_status"] == "failed"
    assert data["persistence_status"] == "failed"
