"""
Pydantic schemas and data contracts for HazardIQ backend.
Validates coordinates, units, hazard modes, and payload structures.
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

class HazardMode(str, Enum):
    MONSOON = "monsoon"
    HEATWAVE = "heatwave"


class VehicleType(str, Enum):
    TWO_WHEELER = "two_wheeler"
    CAR = "car"
    PEDESTRIAN = "pedestrian"


class RoutingDecision(str, Enum):
    ALLOW_ROUTE = "ALLOW_ROUTE"
    DENY_ROUTE = "DENY_ROUTE"
    UNKNOWN = "UNKNOWN"


# ==============================================================================
# Health & Status Schemas
# ==============================================================================

class HealthResponse(BaseModel):
    status: str = "ok"
    service: str = "hazardiq-backend"


# ==============================================================================
# Hotspot Schemas
# ==============================================================================

class HotspotItem(BaseModel):
    id: str = Field(..., description="Unique hotspot identifier")
    name: str = Field(..., description="Location name or description")
    lat: float = Field(..., ge=-90.0, le=90.0, description="Latitude coordinate (-90 to 90)")
    lng: float = Field(..., ge=-180.0, le=180.0, description="Longitude coordinate (-180 to 180)")
    type: str = Field(..., description="Choke point type: underpass, transit_hub, intersection")
    baseline_impermeability_ratio: float = Field(
        ..., ge=0.0, le=1.0, description="Run-off impermeability indicator (0.0 to 1.0)"
    )
    elevation_dip_meters: float = Field(..., description="Relative topographical dip in meters")
    current_risk_status: str = Field(
        "unknown",
        description="Hazard evaluation status. 'unknown' when real-time verified evidence is missing."
    )
    is_demo_data: bool = Field(
        True, description="Indicates whether this is synthetic demonstration data"
    )
    notes: Optional[str] = Field(None, description="Operational or synthetic data notes")


# ==============================================================================
# Report Schemas
# ==============================================================================

class ReportRequest(BaseModel):
    lat: float = Field(..., ge=-90.0, le=90.0, description="Latitude where report was captured")
    lng: float = Field(..., ge=-180.0, le=180.0, description="Longitude where report was captured")
    hazard_mode: str = Field(..., description="Hazard context: 'monsoon' or 'heatwave'")
    vehicle_type: str = Field(..., description="Transit mode: 'two_wheeler', 'car', or 'pedestrian'")
    image_base64: str = Field(..., description="Base64 encoded JPEG/PNG/WEBP image or Data URI")

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
    def validate_image_payload_non_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("image_base64 must not be empty")
        return v.strip()


class DetectedHazard(BaseModel):
    water_depth_inches: Optional[int] = Field(
        None, ge=0, description="Estimated water depth in inches (null if unavailable or heatwave)"
    )
    shade_coverage_percent: Optional[int] = Field(
        None, ge=0, le=100, description="Estimated tree/canopy shade percentage (0-100, null if monsoon)"
    )


class ReportResponse(BaseModel):
    report_id: str = Field(..., description="Generated UUID identifier for the report")
    timestamp: str = Field(..., description="UTC ISO-8601 creation timestamp")
    verification_status: str = Field(
        ..., description="Verification status: 'pending_review', 'rejected_spam', 'processing_failed'"
    )
    analysis_status: str = Field(
        ..., description="Vision analysis outcome: 'completed', 'analysis_unavailable', 'uncertain'"
    )
    detected_hazard: DetectedHazard
    cedar_routing_decision: str = Field(
        ..., description="Provisional routing policy verdict: 'ALLOW_ROUTE', 'DENY_ROUTE', or 'UNKNOWN'"
    )
    decision_engine: str = Field(
        "python_fallback",
        description="Policy execution engine: 'python_fallback' or 'cedar'"
    )
    ui_message: str = Field(..., description="Human-readable routing and safety advisory")
    image_storage_status: str = Field(
        "not_configured",
        description="S3 storage outcome: 'stored', 'not_configured', or 'failed'"
    )
    persistence_status: str = Field(
        "not_configured",
        description="Database outcome: 'stored', 'local_stored', 'not_configured', or 'failed'"
    )
    route_alternative_status: str = Field(
        "not_available",
        description="Alternative path availability (managed by Member 2 mapping module)"
    )
    data_limitations: List[str] = Field(
        default_factory=list,
        description="Explicit disclaimers regarding unverified estimates and decision limits"
    )


# ==============================================================================
# Bedrock Vision Model Schemas
# ==============================================================================

class MonsoonBedrockAnalysis(BaseModel):
    water_depth_inches: Optional[int] = None
    visual_hazard_indicators: List[str] = Field(default_factory=list)
    confidence: float = 0.0
    analysis_status: str = "uncertain"
    limitations: List[str] = Field(default_factory=list)


class HeatwaveBedrockAnalysis(BaseModel):
    shade_coverage_percent: Optional[int] = None
    heat_vulnerability_indicators: List[str] = Field(default_factory=list)
    confidence: float = 0.0
    analysis_status: str = "uncertain"
    limitations: List[str] = Field(default_factory=list)
