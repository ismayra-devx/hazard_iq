"""
HazardIQ Backend - Climate-Aware Navigation Engine.
FastAPI entry point providing:
- GET /health
- GET /api/hotspots
- POST /api/report
"""

import base64
import json
import logging
import os
import uuid
from datetime import datetime, timezone
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Ensure current and parent directories are on sys.path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))
if str(BASE_DIR.parent) not in sys.path:
    sys.path.insert(1, str(BASE_DIR.parent))

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

try:
    from schemas.report import (
        DetectedHazard,
        HealthResponse,
        HotspotItem,
        ReportRequest,
        ReportResponse,
    )
    from services.bedrock_service import bedrock_service
    from services.dynamodb_service import dynamodb_service
    from services.routing_policy import routing_policy
    from services.s3_service import s3_service
except ImportError:
    from backend.schemas.report import (
        DetectedHazard,
        HealthResponse,
        HotspotItem,
        ReportRequest,
        ReportResponse,
    )
    from backend.services.bedrock_service import bedrock_service
    from backend.services.dynamodb_service import dynamodb_service
    from backend.services.routing_policy import routing_policy
    from backend.services.s3_service import s3_service

# Load .env file for local development if available
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(dotenv_path=BASE_DIR / ".env")

# Logging setup
logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO").upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("hazardiq.backend")

# Constants
MAX_IMAGE_SIZE_BYTES = int(os.getenv("MAX_IMAGE_SIZE_BYTES", 5 * 1024 * 1024))  # 5 MB

app = FastAPI(
    title="HazardIQ Backend",
    description="Advisory climate-resilient routing engine for extreme heatwave and monsoon flooding navigation.",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# ==============================================================================
# CORS Configuration
# ==============================================================================
allowed_origins_raw = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000"
)
origins = [origin.strip() for origin in allowed_origins_raw.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins if origins else ["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD"],
    allow_headers=["*"],
    expose_headers=["*"],
)


# ==============================================================================
# Consistent Error Handlers
# ==============================================================================
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Format 422 schema validation errors cleanly without leaking internals.
    """
    clean_errors = []
    for err in exc.errors():
        clean_errors.append({
            "loc": err.get("loc"),
            "msg": err.get("msg"),
            "type": err.get("type"),
        })
    status_code = getattr(status, "HTTP_422_UNPROCESSABLE_CONTENT", 422)
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "error_code": "VALIDATION_ERROR",
                "message": "Request parameter or body failed schema validation.",
                "details": clean_errors,
            }
        },
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Guard against unhandled internal server errors. Never leak tracebacks or secrets.
    """
    logger.error("Unhandled error processing %s %s: %s", request.method, request.url.path, str(exc), exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "error_code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected server error occurred. Please try again later.",
            }
        },
    )


# ==============================================================================
# Helper Functions
# ==============================================================================
def find_hotspots_file() -> Path:
    """
    Resiliently locate hotspots.json regardless of working directory.
    """
    candidates = [
        BASE_DIR / "data" / "hotspots.json",
        Path("data/hotspots.json"),
        BASE_DIR.parent / "data" / "hotspots.json",
        BASE_DIR.parent / "app" / "data" / "hotspots.json",
    ]
    for path in candidates:
        if path.exists():
            return path
    raise FileNotFoundError("Could not find hotspots.json in any standard data directory")


def decode_and_validate_image(image_payload: str) -> Tuple[bytes, str]:
    """
    Validate base64 string, size limits, and image magic bytes.
    Raises:
        HTTPException 400 for malformed base64 or unsupported image magic bytes.
        HTTPException 413 if decoded byte size exceeds MAX_IMAGE_SIZE_BYTES.
    """
    raw = image_payload.strip()
    if not raw:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Image payload is empty.",
        )

    # Strip data URL prefix if supplied
    b64_data = raw.split(",", 1)[1] if "," in raw else raw

    try:
        image_bytes = base64.b64decode(b64_data, validate=True)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Malformed Base64 image encoding: {str(e)}",
        )

    # Size verification
    if len(image_bytes) > MAX_IMAGE_SIZE_BYTES:
        raise HTTPException(
            status_code=getattr(status, "HTTP_413_CONTENT_TOO_LARGE", 413),
            detail=f"Uploaded image exceeds maximum allowable limit of {MAX_IMAGE_SIZE_BYTES // (1024 * 1024)} MB",
        )

    # Magic byte verification (JPEG, PNG, WEBP)
    is_jpeg = image_bytes.startswith(b"\xff\xd8\xff")
    is_png = image_bytes.startswith(b"\x89PNG\r\n\x1a\n")
    is_webp = image_bytes.startswith(b"RIFF") and b"WEBP" in image_bytes[:16]

    if not (is_jpeg or is_png or is_webp):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported image format. Only JPEG, PNG, and WEBP formats are accepted.",
        )

    content_type = "image/jpeg" if is_jpeg else ("image/png" if is_png else "image/webp")
    return image_bytes, b64_data


# ==============================================================================
# Endpoint: GET /health
# ==============================================================================
@app.get(
    "/health",
    response_model=HealthResponse,
    summary="Service Health Check",
    description="Returns service availability status. Operates without requiring AWS credentials.",
)
async def get_health():
    return HealthResponse(
        status="ok",
        service="hazardiq-backend",
    )


# ==============================================================================
# Endpoint: GET /api/hotspots
# ==============================================================================
@app.get(
    "/api/hotspots",
    response_model=List[HotspotItem],
    summary="Get Demo Urban Hazard Hotspots",
    description="Returns pre-seeded urban choke points for Leaflet map visualization.",
)
async def get_hotspots():
    try:
        file_path = find_hotspots_file()
        with open(file_path, "r", encoding="utf-8") as f:
            raw_data = json.load(f)
    except FileNotFoundError as fnf:
        logger.error("Hotspots data file not found: %s", str(fnf))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Hotspots demonstration data file could not be located.",
        )
    except Exception as e:
        logger.error("Failed to parse hotspots file: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to load hotspot data.",
        )

    hotspots = []
    for item in raw_data:
        try:
            hotspots.append(HotspotItem(**item))
        except Exception as val_err:
            logger.warning("Skipping malformed hotspot entry: %s", str(val_err))
            continue

    return hotspots


# ==============================================================================
# Endpoint: POST /api/report
# ==============================================================================
@app.post(
    "/api/report",
    response_model=ReportResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit Citizen Hazard Photo Report",
    description="Validates citizen photograph, evaluates Bedrock vision, applies vehicle routing policy, and persists report.",
)
async def submit_hazard_report(payload: ReportRequest):
    # 1. Validate image format, base64 integrity, and size limits
    image_bytes, clean_b64 = decode_and_validate_image(payload.image_base64)

    # 2. Generate unique identifiers and timestamps
    report_uuid = str(uuid.uuid4())
    created_timestamp = datetime.now(timezone.utc).isoformat()

    # 3. Analyze image with Bedrock (or safe fallback)
    (
        water_depth,
        shade_percent,
        analysis_status,
        confidence,
        analysis_limitations,
    ) = await bedrock_service.analyze_hazard_image(
        image_bytes=image_bytes,
        image_base64=clean_b64,
        hazard_mode=payload.hazard_mode,
    )

    # 4. Evaluate deterministic routing safety rules
    policy_result = routing_policy.evaluate(
        hazard_mode=payload.hazard_mode,
        vehicle_type=payload.vehicle_type,
        water_depth_inches=water_depth,
        shade_coverage_percent=shade_percent,
    )

    # 5. Persist image to Amazon S3 (if configured)
    s3_result = await s3_service.upload_image(
        report_uuid=report_uuid,
        image_bytes=image_bytes,
    )

    # 6. Save report record to DynamoDB (or local test store)
    report_record = {
        "report_id": report_uuid,
        "timestamp": created_timestamp,
        "lat": payload.lat,
        "lng": payload.lng,
        "hazard_mode": payload.hazard_mode,
        "vehicle_type": payload.vehicle_type,
        "water_depth_inches": water_depth,
        "shade_coverage_percent": shade_percent,
        "verification_status": "pending_review",
        "routing_decision": policy_result.decision,
        "image_storage_status": s3_result["status"],
    }
    persistence_status = await dynamodb_service.save_report(report_record)

    # 7. Aggregate transparent data limitations
    combined_limitations = list(analysis_limitations)
    for lim in policy_result.limitations:
        if lim not in combined_limitations:
            combined_limitations.append(lim)

    return ReportResponse(
        report_id=report_uuid,
        timestamp=created_timestamp,
        verification_status="pending_review",
        analysis_status=analysis_status,
        detected_hazard=DetectedHazard(
            water_depth_inches=water_depth,
            shade_coverage_percent=shade_percent,
        ),
        cedar_routing_decision=policy_result.decision,
        decision_engine=policy_result.decision_engine,
        ui_message=policy_result.ui_message,
        image_storage_status=s3_result["status"],
        persistence_status=persistence_status,
        route_alternative_status="not_available",
        data_limitations=combined_limitations,
    )


# Entry point for direct execution
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8080))
    uvicorn.run("backend.main:app", host="0.0.0.0", port=port, reload=True)
