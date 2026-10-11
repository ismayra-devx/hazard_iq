"""
HazardIQ FastAPI Application Entry Point.
Provides climate-aware routing decision support for extreme heat and monsoon hazards.
"""

from datetime import datetime, timezone
import logging
from typing import Any, Dict
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.hotspots import router as hotspots_router
from app.api.reports import router as reports_router
from app.api.weather import router as weather_router
from app.config import settings
from app.schemas import ErrorDetail, ErrorResponse, HealthResponse

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("hazardiq.app")

app = FastAPI(
    title="HazardIQ API - Climate-Aware Navigation",
    description=(
        "Decision support backend for extreme heat and heavy rainfall navigation. "
        "Provides dynamic heat and monsoon risk scores, Open-Meteo weather integration, "
        "conservative safety evaluations, and citizen hazard reporting with optional "
        "Amazon Bedrock (Nova Lite) vision analysis."
    ),
    version=settings.APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# ==============================================================================
# CORS Configuration
# ==============================================================================
origins = settings.cors_origins_list
logger.info("Configuring CORS with allowed origins: %s", origins)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
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
    Ensure predictable, structured 422 JSON errors for the frontend.
    Sanitizes Pydantic error details so exception objects in ctx are stringified.
    """
    clean_errors = []
    for err in exc.errors():
        clean_err = {
            "loc": err.get("loc"),
            "msg": err.get("msg"),
            "type": err.get("type"),
        }
        if "ctx" in err and isinstance(err["ctx"], dict):
            clean_err["ctx"] = {k: str(v) for k, v in err["ctx"].items()}
        clean_errors.append(clean_err)

    logger.warning("Validation error on %s %s: %s", request.method, request.url.path, clean_errors)
    error_payload = ErrorResponse(
        error=ErrorDetail(
            error_code="VALIDATION_ERROR",
            message="Request body or query parameter failed schema validation.",
            details=clean_errors
        )
    )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content=error_payload.model_dump()
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Top-level exception guard. Never leaks internal tracebacks or secrets.
    """
    logger.error("Unhandled exception processing %s %s: %s", request.method, request.url.path, str(exc), exc_info=True)
    error_payload = ErrorResponse(
        error=ErrorDetail(
            error_code="INTERNAL_SERVER_ERROR",
            message="An unexpected server error occurred. Please try again later.",
            details=None
        )
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_payload.model_dump()
    )


# ==============================================================================
# Health Check Endpoint
# ==============================================================================
@app.get(
    "/health",
    response_model=HealthResponse,
    tags=["System & Health"],
    summary="Application Health & Subsystem Status",
)
async def health_check() -> HealthResponse:
    services: Dict[str, str] = {
        "weather_service": f"online (Open-Meteo, cache={settings.WEATHER_CACHE_TTL_SECONDS}s)",
        "storage_backend": "DynamoDB (active)" if settings.ENABLE_DYNAMODB else f"local_json ({settings.LOCAL_STORAGE_PATH})",
        "bedrock_vision": f"enabled (model={settings.BEDROCK_MODEL_ID})" if settings.ENABLE_BEDROCK else "disabled (fallback to PENDING_REVIEW)",
        "s3_photo_storage": f"enabled ({settings.S3_BUCKET_PHOTOS})" if settings.ENABLE_S3 else "disabled",
        "policy_engine": "cedar_spec_v1 (deterministic_python_evaluator)",
    }
    return HealthResponse(
        status="ok",
        app_name=settings.APP_NAME,
        version=settings.APP_VERSION,
        environment=settings.ENVIRONMENT,
        timestamp=datetime.now(timezone.utc),
        services=services,
    )


# ==============================================================================
# Route Registrations
# ==============================================================================
app.include_router(hotspots_router)
app.include_router(reports_router)
app.include_router(weather_router)


@app.get("/", tags=["System & Health"], include_in_schema=False)
async def root_redirect():
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "online",
        "docs_url": "/docs",
        "health_url": "/health"
    }


# ==============================================================================
# AWS Lambda Handler (Serverless Deployment via API Gateway / Lambda Function URL)
# ==============================================================================
try:
    from mangum import Mangum
    handler = Mangum(app, lifespan="off")
except ImportError:
    handler = None
