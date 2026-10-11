"""
Strict Pydantic schemas for the HazardIQ API.
Enforces validation on incoming payloads, internal evaluations, and outgoing responses.
All coordinates, units, and timestamps follow explicit standards.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
import base64
import re
from pydantic import BaseModel, Field, field_validator, model_validator


# ==============================================================================
# Enumerations
# ==============================================================================

class RiskLevel(str, Enum):
    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"
    SEVERE = "SEVERE"
    UNKNOWN = "UNKNOWN"


class ShadeStatus(str, Enum):
    VERIFIED_SHADED = "VERIFIED_SHADED"
    UNSHADED = "UNSHADED"
    UNKNOWN = "UNKNOWN"


class HazardCategory(str, Enum):
    WATERLOGGING = "WATERLOGGING"
    EXTREME_HEAT = "EXTREME_HEAT"
    DAMAGED_WATER_POINT = "DAMAGED_WATER_POINT"
    FALLEN_TREE_OBSTRUCTION = "FALLEN_TREE_OBSTRUCTION"
    OTHER = "OTHER"


class ReportStatus(str, Enum):
    PENDING_REVIEW = "PENDING_REVIEW"
    AI_FLAGGED = "AI_FLAGGED"
    REVIEWED = "REVIEWED"
    REJECTED = "REJECTED"


class SafetyAction(str, Enum):
    ALLOW = "ALLOW"
    WARN = "WARN"
    AVOID = "AVOID"
    UNKNOWN = "UNKNOWN"


class VehicleType(str, Enum):
    PEDESTRIAN = "PEDESTRIAN"
    TWO_WHEELER = "TWO_WHEELER"
    THREE_WHEELER_AUTO = "THREE_WHEELER_AUTO"
    FOUR_WHEELER_CAR = "FOUR_WHEELER_CAR"
    BUS_HEAVY = "BUS_HEAVY"


class RoadType(str, Enum):
    PRIMARY = "PRIMARY"
    SECONDARY = "SECONDARY"
    ARTERIAL = "ARTERIAL"
    RESIDENTIAL = "RESIDENTIAL"
    HIGHWAY = "HIGHWAY"


# ==============================================================================
# Weather Schemas
# ==============================================================================

class WeatherSnapshot(BaseModel):
    """
    Weather data snapshot at a specific geographic location and time.
    Explicit units are documented and retained in field names.
    """
    temperature_celsius: Optional[float] = Field(
        None, description="Air temperature in degrees Celsius at 2 meters above ground"
    )
    relative_humidity_percentage: Optional[float] = Field(
        None, ge=0.0, le=100.0, description="Relative humidity percentage (0-100%)"
    )
    precipitation_mm: Optional[float] = Field(
        None, ge=0.0, description="Precipitation accumulated over preceding hour in millimeters (mm)"
    )
    wind_speed_kmh: Optional[float] = Field(
        None, ge=0.0, description="Wind speed at 10 meters in kilometers per hour (km/h)"
    )
    observation_time: Optional[str] = Field(
        None, description="ISO timestamp of weather observation/forecast"
    )
    data_freshness_seconds: Optional[int] = Field(
        None, description="Seconds elapsed since observation or cache fetch"
    )
    source: str = Field(
        "Open-Meteo API", description="Data source attribution (open-meteo.com under CC BY 4.0)"
    )
    is_live: bool = Field(
        False, description="True if fetched live from weather API; False if cached or fallback"
    )


# ==============================================================================
# Hotspot & Risk Schemas
# ==============================================================================

class HeatRiskAssessment(BaseModel):
    """
    Estimated thermal risk score and level for a hotspot or route.
    """
    score: Optional[float] = Field(
        None, ge=0.0, le=100.0, description="Normalized heat risk score (0-100); null if insufficient data"
    )
    level: RiskLevel = Field(
        RiskLevel.UNKNOWN, description="Heat risk category"
    )
    is_estimate: bool = Field(
        True, description="Always true: represents a heuristic prototype estimate, not validated forecast"
    )
    shade_status: ShadeStatus = Field(
        ShadeStatus.UNKNOWN, description="Shade data status. Never assume shaded if data is missing"
    )
    contributing_factors: List[str] = Field(
        default_factory=list, description="List of primary factors influencing heat risk score"
    )
    calculation_notes: str = Field(
        "", description="Transparent calculation rationale or limitations"
    )


class MonsoonRiskAssessment(BaseModel):
    """
    Estimated flood / waterlogging risk score and level for a hotspot or road segment.
    """
    score: Optional[float] = Field(
        None, ge=0.0, le=100.0, description="Normalized monsoon risk score (0-100); null if insufficient data"
    )
    level: RiskLevel = Field(
        RiskLevel.UNKNOWN, description="Monsoon / waterlogging risk category"
    )
    is_estimate: bool = Field(
        True, description="Always true: represents a heuristic estimate, not a ground water-depth measurement"
    )
    waterlogging_hazard: bool = Field(
        False, description="Flag indicating high likelihood of standing water or drainage failure"
    )
    contributing_factors: List[str] = Field(
        default_factory=list, description="List of primary factors influencing monsoon risk score"
    )
    calculation_notes: str = Field(
        "", description="Transparent calculation rationale or limitations"
    )


class HotspotStaticData(BaseModel):
    """
    Static environmental and infrastructural attributes of a mapped hotspot.
    All sample data is explicitly marked as demo data.
    """
    hotspot_id: str = Field(..., pattern=r"^[a-zA-Z0-9_\-]+$", description="Unique hotspot identifier")
    name: str = Field(..., min_length=2, max_length=120, description="Descriptive hotspot name")
    latitude: float = Field(..., ge=-90.0, le=90.0, description="Geographic latitude in decimal degrees")
    longitude: float = Field(..., ge=-180.0, le=180.0, description="Geographic longitude in decimal degrees")
    elevation_dip_meters: float = Field(
        ..., ge=0.0, le=20.0, description="Estimated depression depth in meters relative to surrounding grade"
    )
    impermeability_ratio: float = Field(
        ..., ge=0.0, le=1.0, description="Surface impermeability ratio (0.0 = permeable soil, 1.0 = solid concrete)"
    )
    road_type: RoadType = Field(..., description="Classification of the road segment")
    shade_ratio: Optional[float] = Field(
        None, ge=0.0, le=1.0, description="Shade coverage ratio (0-1); null if unmeasured / unknown"
    )
    drinking_water_available: Optional[bool] = Field(
        None, description="Thermal relief drinking water kiosk present; null if unverified"
    )
    hotspot_type: str = Field(
        ..., description="Type of hazard vulnerability: 'heatwave', 'waterlogging', or 'dual'"
    )
    road_segment_id: str = Field(..., description="Associated road segment ID for routing integration")
    data_source: str = Field(
        "delhi_demo_synthetic", description="Provenance of the static data record"
    )
    is_demo_data: bool = Field(
        True, description="Explicit flag indicating demonstration record; not verified surveyed field data"
    )


class HotspotResponseItem(BaseModel):
    """
    Unified hotspot record returned to frontend, including static attributes and dynamic risks.
    """
    hotspot_id: str
    name: str
    latitude: float
    longitude: float
    elevation_dip_meters: float
    impermeability_ratio: float
    road_type: RoadType
    shade_ratio: Optional[float]
    drinking_water_available: Optional[bool]
    hotspot_type: str
    road_segment_id: str
    data_source: str
    is_demo_data: bool
    heat_risk: HeatRiskAssessment
    monsoon_risk: MonsoonRiskAssessment
    weather_snapshot: Optional[WeatherSnapshot]
    last_evaluated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class HotspotListResponse(BaseModel):
    """
    Response envelope for GET /api/hotspots.
    """
    hotspots: List[HotspotResponseItem]
    total_count: int
    data_source: str
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    target_city: str
    limitations: List[str] = Field(
        default_factory=lambda: [
            "Sample coordinates and attributes are synthetic demonstration data for hackathon evaluation.",
            "Weather data is obtained from Open-Meteo under CC BY 4.0 license.",
            "Risk scores are prototype heuristics and do not represent verified ground truth."
        ]
    )


# ==============================================================================
# Citizen Hazard Reporting Schemas
# ==============================================================================

class HazardReportCreate(BaseModel):
    """
    Incoming payload for citizen hazard reporting (POST /api/report).
    """
    hazard_category: HazardCategory = Field(..., description="Observed hazard category")
    latitude: float = Field(..., ge=-90.0, le=90.0, description="Observed latitude")
    longitude: float = Field(..., ge=-180.0, le=180.0, description="Observed longitude")
    description: Optional[str] = Field(
        None, max_length=500, description="Optional brief commuter note"
    )
    road_segment_id: Optional[str] = Field(
        None, max_length=64, description="Optional road segment ID supplied by Leaflet mapping (Member 2)"
    )
    vehicle_type: Optional[VehicleType] = Field(
        VehicleType.TWO_WHEELER, description="Commuter vehicle type for clearance and safety decision"
    )
    image_base64: Optional[str] = Field(
        None, description="Optional photograph encoded as Base64 string (max 5MB)"
    )
    reporter_client_id: Optional[str] = Field(
        None, max_length=64, description="Anonymous client-generated ID; no PII"
    )

    @field_validator("image_base64")
    @classmethod
    def validate_image_base64(cls, v: Optional[str]) -> Optional[str]:
        if v is None or v.strip() == "":
            return None
        cleaned = v.strip()
        # Strip data URL prefix if supplied (e.g., 'data:image/jpeg;base64,')
        if "," in cleaned:
            cleaned = cleaned.split(",", 1)[1]
        try:
            decoded = base64.b64decode(cleaned, validate=True)
        except Exception as e:
            raise ValueError(f"Invalid Base64 encoding: {str(e)}")
        # Check size limit: 5MB
        if len(decoded) > 5 * 1024 * 1024:
            raise ValueError("Encoded image exceeds maximum allowable limit of 5 Megabytes (MB)")
        # Magic bytes validation for common image formats (JPEG, PNG, WEBP)
        if not (
            decoded.startswith(b"\xff\xd8\xff") or  # JPEG
            decoded.startswith(b"\x89PNG\r\n\x1a\n") or  # PNG
            (decoded.startswith(b"RIFF") and b"WEBP" in decoded[:16])  # WEBP
        ):
            raise ValueError("Unsupported image format. Allowed formats: JPEG, PNG, WEBP")
        return cleaned


class ImageAnalysisResult(BaseModel):
    """
    Findings produced by AI vision analysis (e.g. Amazon Bedrock with Nova Lite).
    Explicitly labelled as an AI candidate assessment, not ground truth.
    """
    model_id: str = Field(..., description="Model identifier used for analysis")
    analyzed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    hazard_detected: bool = Field(..., description="Whether a visual hazard was detected")
    detected_category: Optional[str] = Field(None, description="Identified category from image")
    confidence_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="Model confidence estimate (0-1)")
    visual_indicators: List[str] = Field(default_factory=list, description="Visible indicators observed in image")
    reasoning: str = Field(..., description="Summary explanation of visual evaluation")
    is_ai_estimate: bool = Field(
        True, description="Always true: AI output is a candidate assessment, never physical ground measurement"
    )


class SafetyDecisionResult(BaseModel):
    """
    Conservative safety decision generated for commuter guidance.
    """
    action: SafetyAction = Field(..., description="Decision outcome: ALLOW, WARN, AVOID, or UNKNOWN")
    reason: str = Field(..., description="Human-readable decision explanation")
    policy_engine: str = Field(
        ..., description="Identifier of evaluator: 'cedar_policy_engine_v1' or 'deterministic_python_safety_engine'"
    )
    rules_triggered: List[str] = Field(default_factory=list, description="List of rule IDs or policies evaluated")
    uncertainty_warning: Optional[str] = Field(
        None, description="Explicit warning if data freshness or confidence is insufficient"
    )


class RouteAvoidanceRecommendation(BaseModel):
    """
    Advisory information for Member 2's Leaflet routing component.
    """
    avoid_segment: bool = Field(..., description="True if routing system should penalize or avoid this segment")
    road_segment_id: Optional[str] = Field(None, description="Affected road segment ID")
    alternative_route_available: bool = Field(
        False, description="Always false on backend; Member 2 owns route graph generation"
    )
    guidance_notes: str = Field(..., description="Navigation advisory notes for commuter")


class HazardReportResponse(BaseModel):
    """
    Response envelope for POST /api/report.
    """
    report_id: str = Field(..., description="Unique report identifier")
    hazard_category: HazardCategory
    latitude: float
    longitude: float
    status: ReportStatus
    created_at: datetime
    vehicle_type: Optional[VehicleType] = None
    image_analyzed: bool = False
    ai_analysis: Optional[ImageAnalysisResult] = None
    risk_assessment: Optional[Dict[str, Any]] = None
    safety_evaluation: SafetyDecisionResult
    route_avoidance_recommendation: RouteAvoidanceRecommendation
    service_limitations: List[str] = Field(default_factory=list)


# ==============================================================================
# Health and Error Schemas
# ==============================================================================

class HealthResponse(BaseModel):
    """
    Response schema for GET /health.
    """
    status: str = "ok"
    app_name: str
    version: str
    environment: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    services: Dict[str, str] = Field(
        default_factory=dict, description="Status of integrated subsystems and adapters"
    )


class ErrorDetail(BaseModel):
    error_code: str
    message: str
    details: Optional[Any] = None


class ErrorResponse(BaseModel):
    error: ErrorDetail


# ==============================================================================
# HazardIQ Team API Contract Schemas (PDF Specification)
# ==============================================================================

class HotspotContractItem(BaseModel):
    """
    Contract model for GET /api/hotspots:
    Strict JSON List element returned to the React frontend.
    """
    id: str = Field(..., description="System record ID for the choke point, e.g. 'point_001'")
    name: str = Field(..., description="Human-readable location identifier")
    lat: float = Field(..., ge=-90.0, le=90.0, description="Decimal latitude coordinate")
    lng: float = Field(..., ge=-180.0, le=180.0, description="Decimal longitude coordinate")
    type: str = Field(..., description="Classification of the physical choke point: 'underpass', 'transit_hub', etc.")
    baseline_impermeability_ratio: float = Field(
        ..., ge=0.0, le=1.0, description="Environmental run-off indicator metric (0.00 to 1.00)"
    )
    elevation_dip_meters: float = Field(
        ..., description="Relative topographical dip value in meters (e.g. -3.8)"
    )
    current_risk_status: str = Field(
        ..., description="Active hazard evaluation status: 'clear', 'monsoon_warning', 'heatwave_warning', 'impassable'"
    )


class ReportContractRequest(BaseModel):
    """
    Contract model for POST /api/report (Frontend -> Backend).
    """
    lat: float = Field(..., ge=-90.0, le=90.0, description="Latitude where the photo/hazard was captured")
    lng: float = Field(..., ge=-180.0, le=180.0, description="Longitude where the photo/hazard was captured")
    hazard_mode: str = Field(..., description="Selected operational evaluation context: 'monsoon' or 'heatwave'")
    vehicle_type: str = Field(..., description="User's current mode of transit: 'two_wheeler', 'car', 'pedestrian'")
    image_base64: str = Field(..., description="Complete base64-encoded image source string (Base64 Data URI)")

    @model_validator(mode="before")
    @classmethod
    def resolve_aliases(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "lat" not in data and "latitude" in data:
                data["lat"] = data["latitude"]
            if "lng" not in data and "longitude" in data:
                data["lng"] = data["longitude"]
            if "hazard_mode" not in data and "hazard_category" in data:
                cat = str(data["hazard_category"]).lower()
                data["hazard_mode"] = "heatwave" if "heat" in cat else "monsoon"
            if "vehicle_type" in data:
                v_str = str(data["vehicle_type"]).lower()
                if "two" in v_str:
                    data["vehicle_type"] = "two_wheeler"
                elif "car" in v_str or "four" in v_str:
                    data["vehicle_type"] = "car"
                elif "pedestrian" in v_str:
                    data["vehicle_type"] = "pedestrian"
        return data

    @field_validator("hazard_mode")
    @classmethod
    def validate_hazard_mode(cls, v: str) -> str:
        clean = v.strip().lower()
        if clean not in ("monsoon", "heatwave"):
            raise ValueError("hazard_mode must be 'monsoon' or 'heatwave'")
        return clean

    @field_validator("vehicle_type")
    @classmethod
    def validate_vehicle_type(cls, v: str) -> str:
        clean = v.strip().lower()
        if clean not in ("two_wheeler", "car", "pedestrian"):
            raise ValueError("vehicle_type must be 'two_wheeler', 'car', or 'pedestrian'")
        return clean

    @field_validator("image_base64")
    @classmethod
    def validate_image_base64(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("image_base64 cannot be empty")
        raw = v.strip()
        payload = raw.split(",", 1)[1] if "," in raw else raw
        try:
            decoded = base64.b64decode(payload, validate=True)
        except Exception as e:
            raise ValueError(f"Invalid Base64 encoding: {str(e)}")
        if len(decoded) > 5 * 1024 * 1024:
            raise ValueError("Encoded image exceeds maximum allowable limit of 5 MB")
        if not (
            decoded.startswith(b"\xff\xd8\xff") or
            decoded.startswith(b"\x89PNG\r\n\x1a\n") or
            (decoded.startswith(b"RIFF") and b"WEBP" in decoded[:16])
        ):
            raise ValueError("Unsupported image format. Allowed formats: JPEG, PNG, WEBP")
        return raw


class DetectedHazardContract(BaseModel):
    water_depth_inches: int = Field(
        ..., ge=0, description="Estimated water level depth (evaluates to 0 in heatwave mode)"
    )
    shade_coverage_percent: int = Field(
        ..., ge=0, le=100, description="Measured shade percentage (evaluates to 100 in monsoon mode)"
    )


class ReportContractResponse(BaseModel):
    """
    Contract model for POST /api/report (Backend -> Frontend).
    """
    verification_status: str = Field(
        ..., description="Verification status from image evaluation engine: 'verified', 'rejected_spam', 'processing_failed'"
    )
    detected_hazard: DetectedHazardContract
    cedar_routing_decision: str = Field(
        ..., description="Output verdict calculated by Cedar policy engine: 'ALLOW_ROUTE' or 'DENY_ROUTE'"
    )
    ui_message: str = Field(
        ..., description="Explanatory routing feedback displayed on UI layer"
    )
