try:
    from schemas.report import (
        DetectedHazard,
        HazardMode,
        HealthResponse,
        HeatwaveBedrockAnalysis,
        HotspotItem,
        MonsoonBedrockAnalysis,
        ReportRequest,
        ReportResponse,
        RoutingDecision,
        VehicleType,
    )
except ImportError:
    from backend.schemas.report import (
        DetectedHazard,
        HazardMode,
        HealthResponse,
        HeatwaveBedrockAnalysis,
        HotspotItem,
        MonsoonBedrockAnalysis,
        ReportRequest,
        ReportResponse,
        RoutingDecision,
        VehicleType,
    )

__all__ = [
    "DetectedHazard",
    "HazardMode",
    "HealthResponse",
    "HeatwaveBedrockAnalysis",
    "HotspotItem",
    "MonsoonBedrockAnalysis",
    "ReportRequest",
    "ReportResponse",
    "RoutingDecision",
    "VehicleType",
]
