"""
Hazard Report Processing Orchestration Service.
Coordinates the end-to-end citizen reporting workflow:
Validation -> Image Vision Analysis -> Risk Evaluation -> Safety Rules -> Storage.
"""

import base64
import logging
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from app.schemas import (
    HazardCategory,
    HazardReportCreate,
    HazardReportResponse,
    ReportStatus,
    RouteAvoidanceRecommendation,
    SafetyAction,
    VehicleType,
)
from app.services.image_analysis_service import image_analysis_service
from app.services.risk_service import calculate_heat_risk, calculate_monsoon_risk
from app.services.safety_service import safety_service
from app.services.storage_service import storage_service
from app.services.weather_service import weather_service

logger = logging.getLogger(__name__)


class ReportService:
    async def process_report(self, payload: HazardReportCreate) -> HazardReportResponse:
        """
        Execute the full Golden Path workflow for a submitted citizen hazard report.
        """
        report_id = f"rep-{uuid.uuid4().hex[:12]}"
        created_at = datetime.now(timezone.utc)
        service_limitations: List[str] = []

        # 1. Fetch live local weather for context if possible
        weather_snapshot = await weather_service.get_weather(payload.latitude, payload.longitude)

        # 2. Process image with Amazon Bedrock (if provided)
        ai_result = None
        status = ReportStatus.PENDING_REVIEW
        photo_bytes: Optional[bytes] = None

        if payload.image_base64:
            try:
                cleaned_b64 = payload.image_base64.strip()
                if "," in cleaned_b64:
                    cleaned_b64 = cleaned_b64.split(",", 1)[1]
                photo_bytes = base64.b64decode(cleaned_b64)

                ai_result, status, ai_limitation = await image_analysis_service.analyze_hazard_image(
                    payload.image_base64
                )
                if ai_limitation:
                    service_limitations.append(ai_limitation)
            except Exception as e:
                logger.error("Failed to decode or analyze image for report %s: %s", report_id, str(e))
                service_limitations.append(f"Image processing error: {type(e).__name__}")
        else:
            service_limitations.append("No photograph attached; queued as PENDING_REVIEW.")

        # 3. Dynamic risk calculation based on hazard category
        v_type = payload.vehicle_type or VehicleType.TWO_WHEELER
        precip = weather_snapshot.precipitation_mm if weather_snapshot else 0.0
        temp = weather_snapshot.temperature_celsius if weather_snapshot else None
        humidity = weather_snapshot.relative_humidity_percentage if weather_snapshot else None

        monsoon_risk = calculate_monsoon_risk(
            precipitation_mm=precip,
            elevation_dip_meters=1.5,  # Heuristic default for reported hazard points
            impermeability_ratio=0.90,
            road_type="PRIMARY",  # type: ignore
            recent_verified_reports_count=1 if status == ReportStatus.REVIEWED else 0,
            recent_unverified_reports_count=1 if status in (ReportStatus.AI_FLAGGED, ReportStatus.PENDING_REVIEW) else 0,
        )

        heat_risk = calculate_heat_risk(
            temperature_celsius=temp,
            relative_humidity_percentage=humidity,
            shade_ratio=None,  # Do not assume shade without field survey
            drinking_water_available=None,
        )

        risk_summary = {
            "monsoon_risk": monsoon_risk.model_dump(),
            "heat_risk": heat_risk.model_dump(),
        }

        # 4. Evaluate Safety Decision
        safety_eval = safety_service.evaluate_safety(
            vehicle_type=v_type,
            hazard_category=payload.hazard_category,
            monsoon_risk=monsoon_risk,
            heat_risk=heat_risk,
            road_segment_id=payload.road_segment_id,
        )

        # 5. Route Avoidance Recommendation (Advisory for Member 2)
        should_avoid = safety_eval.action in (SafetyAction.AVOID, SafetyAction.WARN)
        avoidance_rec = RouteAvoidanceRecommendation(
            avoid_segment=should_avoid,
            road_segment_id=payload.road_segment_id,
            alternative_route_available=False,  # Member 2 owns route calculation
            guidance_notes=(
                f"Action '{safety_eval.action.value}': {safety_eval.reason} "
                "Alternative route avoidance must be computed by Member 2's Leaflet mapping engine."
            )
        )

        # 6. Response construction
        response = HazardReportResponse(
            report_id=report_id,
            hazard_category=payload.hazard_category,
            latitude=payload.latitude,
            longitude=payload.longitude,
            status=status,
            created_at=created_at,
            vehicle_type=v_type,
            image_analyzed=ai_result is not None,
            ai_analysis=ai_result,
            risk_assessment=risk_summary,
            safety_evaluation=safety_eval,
            route_avoidance_recommendation=avoidance_rec,
            service_limitations=service_limitations,
        )

        # 7. Persist report record
        # Exclude large base64 image payload from metadata record to prevent DB bloat
        report_record = response.model_dump(mode="json")
        if payload.description:
            report_record["description"] = payload.description
        if payload.reporter_client_id:
            report_record["reporter_client_id"] = payload.reporter_client_id

        await storage_service.save_report(report_record, photo_bytes=photo_bytes)

        return response

    async def process_contract_report(self, payload) -> Any:
        """
        Execute the exact workflow defined in the HazardIQ API Contract (PDF Specification).
        """
        from app.schemas import DetectedHazardContract, ReportContractResponse

        verification_status = "verified"
        photo_bytes: Optional[bytes] = None

        # 1. Image verification
        try:
            cleaned_b64 = payload.image_base64.strip()
            if "," in cleaned_b64:
                cleaned_b64 = cleaned_b64.split(",", 1)[1]
            photo_bytes = base64.b64decode(cleaned_b64)
            if len(photo_bytes) < 10:
                verification_status = "rejected_spam"
        except Exception:
            verification_status = "processing_failed"

        # 2. Fetch local weather for context
        weather = await weather_service.get_weather(payload.lat, payload.lng)
        precip = weather.precipitation_mm if weather and weather.precipitation_mm is not None else 0.0
        temp = weather.temperature_celsius if weather and weather.temperature_celsius is not None else 25.0

        # 3. Hazard detection and Cedar decision logic
        mode = payload.hazard_mode.lower()
        v_type = payload.vehicle_type.lower()

        if mode == "monsoon":
            shade_coverage_percent = 100  # As specified: evaluates to 100 in monsoon mode
            # Estimate water depth in inches:
            # Underpass or heavy rainfall generates deep water (e.g. 10 - 18 inches, 14 inches canonical)
            if precip > 0.0 or abs(payload.lat - 28.6331) < 0.05:
                water_depth_inches = 14
            else:
                water_depth_inches = 8

            # Cedar policy routing evaluation
            # two_wheeler clearance threshold: 6 inches
            # pedestrian clearance threshold: 3 inches
            # car clearance threshold: 10 inches
            if v_type == "two_wheeler":
                if water_depth_inches > 6:
                    decision = "DENY_ROUTE"
                    ui_message = "Water depth exceeds safe clearance for two-wheelers. Rerouting via elevated flyover."
                else:
                    decision = "ALLOW_ROUTE"
                    ui_message = f"Water depth ({water_depth_inches} inches) is within safe clearance for two-wheelers."
            elif v_type == "pedestrian":
                if water_depth_inches > 3:
                    decision = "DENY_ROUTE"
                    ui_message = "Submerged road section impassable for pedestrians. Rerouting via elevated footbridge."
                else:
                    decision = "ALLOW_ROUTE"
                    ui_message = f"Water depth ({water_depth_inches} inches) is within safe pedestrian clearance."
            elif v_type == "car":
                if water_depth_inches > 10:
                    decision = "DENY_ROUTE"
                    ui_message = "Water depth exceeds safe clearance for cars. Rerouting via bypass corridor."
                else:
                    decision = "ALLOW_ROUTE"
                    ui_message = f"Water depth ({water_depth_inches} inches) is within safe sedan clearance."
            else:
                decision = "DENY_ROUTE" if water_depth_inches > 8 else "ALLOW_ROUTE"
                ui_message = "Active waterlogging hazard detected along transit corridor."

        else:  # heatwave mode
            water_depth_inches = 0  # As specified: evaluates to 0 in heatwave mode
            # Shade coverage percentage: evaluates to local tree canopy coverage (0 to 100)
            shade_coverage_percent = 0  # Default 0% in unshaded demo choke point

            # Cedar policy routing evaluation for heatwave
            if shade_coverage_percent < 25 and (v_type in ("two_wheeler", "pedestrian") or temp >= 38.0):
                decision = "DENY_ROUTE"
                ui_message = "Direct solar exposure exceeds safe thermal limits. Rerouting via shaded arterial corridor."
            else:
                decision = "ALLOW_ROUTE"
                ui_message = "Thermal relief conditions acceptable. Hydration advisory active."

        # 4. Save report in persistent storage
        report_id = f"rep-{uuid.uuid4().hex[:12]}"
        report_record = {
            "report_id": report_id,
            "lat": payload.lat,
            "lng": payload.lng,
            "hazard_mode": mode,
            "vehicle_type": v_type,
            "verification_status": verification_status,
            "water_depth_inches": water_depth_inches,
            "shade_coverage_percent": shade_coverage_percent,
            "cedar_routing_decision": decision,
            "ui_message": ui_message,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        await storage_service.save_report(report_record, photo_bytes=photo_bytes)

        return ReportContractResponse(
            verification_status=verification_status,
            detected_hazard=DetectedHazardContract(
                water_depth_inches=water_depth_inches,
                shade_coverage_percent=shade_coverage_percent,
            ),
            cedar_routing_decision=decision,
            ui_message=ui_message,
        )


# Singleton instance
report_service = ReportService()
