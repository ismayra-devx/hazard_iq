"""
Deterministic Routing Safety Policy Engine.
Implements vehicle-specific clearance thresholds for monsoon waterlogging and heatwave shade conditions.

Cedar Integration Status:
- The Cedar policy engine requires the Rust/C extension `cedarpolicy`.
- Under the current Python runtime (Python 3.14 on Windows), `cedarpolicy` has no compatible wheel.
- Therefore, this module provides an isolated, deterministic Python fallback (`python_fallback`)
  faithfully mirroring the Cedar specification rules.
"""

import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

try:
    from schemas.report import RoutingDecision, VehicleType
except ImportError:
    from backend.schemas.report import RoutingDecision, VehicleType

logger = logging.getLogger(__name__)

# ==============================================================================
# Centralized Provisional Clearance Thresholds (Inches of Water Depth)
# NOTE: Provisional hackathon thresholds; not certified physical safety guarantees.
# ==============================================================================
PROVISIONAL_MONSOON_THRESHOLDS: Dict[str, int] = {
    "two_wheeler": 6,   # > 6 inches triggers DENY_ROUTE
    "car": 12,          # > 12 inches triggers DENY_ROUTE
    "pedestrian": 4,    # > 4 inches triggers DENY_ROUTE
}

# Heatwave minimum acceptable tree/canopy shade percentage for exposed commuters
PROVISIONAL_HEATWAVE_MIN_SHADE_PERCENT: int = 20


@dataclass
class PolicyEvaluationResult:
    decision: str
    decision_engine: str
    ui_message: str
    limitations: List[str]


class RoutingPolicyEngine:
    """
    Evaluates road segment transit safety against vehicle clearance parameters.
    """

    def __init__(self, use_cedar_if_available: bool = False):
        self.use_cedar_if_available = use_cedar_if_available
        self.engine_name = "python_fallback"

    def evaluate_monsoon(
        self,
        vehicle_type: str,
        water_depth_inches: Optional[int],
    ) -> PolicyEvaluationResult:
        """
        Evaluate monsoon waterlogging safety.

        Rules:
        - If water_depth_inches is None (missing or unmeasurable), return UNKNOWN.
          CRITICAL: Never convert null/None to 0.
        - two_wheeler: depth > 6 inches -> DENY_ROUTE
        - car: depth > 12 inches -> DENY_ROUTE
        - pedestrian: depth > 4 inches -> DENY_ROUTE
        - depth <= threshold -> ALLOW_ROUTE (provisional rule only)
        """
        v_clean = vehicle_type.lower().strip()
        threshold = PROVISIONAL_MONSOON_THRESHOLDS.get(v_clean)

        # Unsupported vehicle type guard
        if threshold is None:
            return PolicyEvaluationResult(
                decision=RoutingDecision.UNKNOWN.value,
                decision_engine=self.engine_name,
                ui_message=f"Unsupported vehicle type '{vehicle_type}'. Cannot determine safe clearance.",
                limitations=["Vehicle type is not recognized in safety policy table."]
            )

        # Missing or unverified measurement
        if water_depth_inches is None:
            return PolicyEvaluationResult(
                decision=RoutingDecision.UNKNOWN.value,
                decision_engine=self.engine_name,
                ui_message="Water depth is unmeasured or uncertain. Exercise extreme caution or seek an alternate route.",
                limitations=[
                    "Water depth measurement is missing or unverified.",
                    "Route cannot be marked safe without ground measurement."
                ]
            )

        if water_depth_inches < 0:
            return PolicyEvaluationResult(
                decision=RoutingDecision.UNKNOWN.value,
                decision_engine=self.engine_name,
                ui_message="Invalid water depth measurement. Routing status is unknown.",
                limitations=["Negative water depth provided; data integrity issue."]
            )

        # Evaluation against threshold
        if water_depth_inches > threshold:
            ui_message = (
                f"Estimated water depth ({water_depth_inches} inches) exceeds safe clearance "
                f"({threshold} inches) for {v_clean.replace('_', ' ')}s. Avoid entering this flooded section."
            )
            return PolicyEvaluationResult(
                decision=RoutingDecision.DENY_ROUTE.value,
                decision_engine=self.engine_name,
                ui_message=ui_message,
                limitations=[
                    "Depth estimate based on visual/heuristic model; actual ground depth may vary.",
                    "Submerged obstacles, potholes, and open drains cannot be detected visually."
                ]
            )
        else:
            ui_message = (
                f"Estimated water depth ({water_depth_inches} inches) is within the provisional clearance limit "
                f"({threshold} inches) for {v_clean.replace('_', ' ')}s. Proceed cautiously."
            )
            return PolicyEvaluationResult(
                decision=RoutingDecision.ALLOW_ROUTE.value,
                decision_engine=self.engine_name,
                ui_message=ui_message,
                limitations=[
                    "Provisional allowance only. Does not guarantee absolute road safety or engine clearance.",
                    "Flowing water current and hidden road hazards remain severe risks even in shallow water."
                ]
            )

    def evaluate_heatwave(
        self,
        vehicle_type: str,
        shade_coverage_percent: Optional[int],
    ) -> PolicyEvaluationResult:
        """
        Evaluate heatwave solar exposure safety.

        Rules:
        - If shade_coverage_percent is None, return UNKNOWN.
        - If shade_coverage_percent < 20 and vehicle is pedestrian or two_wheeler -> DENY_ROUTE.
        - Otherwise, ALLOW_ROUTE under provisional rule if measurement is valid.
        """
        v_clean = vehicle_type.lower().strip()

        if shade_coverage_percent is None:
            return PolicyEvaluationResult(
                decision=RoutingDecision.UNKNOWN.value,
                decision_engine=self.engine_name,
                ui_message="Shade coverage is unmeasured. Maintain active hydration and avoid direct sunlight.",
                limitations=[
                    "Canopy shade measurement is missing or unverified.",
                    "Thermal safety cannot be determined solely from visual estimation."
                ]
            )

        if not (0 <= shade_coverage_percent <= 100):
            return PolicyEvaluationResult(
                decision=RoutingDecision.UNKNOWN.value,
                decision_engine=self.engine_name,
                ui_message="Invalid shade percentage reading. Routing status unknown.",
                limitations=["Shade coverage percentage must be between 0 and 100."]
            )

        if shade_coverage_percent < PROVISIONAL_HEATWAVE_MIN_SHADE_PERCENT and v_clean in ("pedestrian", "two_wheeler"):
            ui_message = (
                f"Low shade coverage ({shade_coverage_percent}%) poses acute solar exposure hazard "
                f"for {v_clean.replace('_', ' ')}s. Reroute through shaded or tree-lined corridors."
            )
            return PolicyEvaluationResult(
                decision=RoutingDecision.DENY_ROUTE.value,
                decision_engine=self.engine_name,
                ui_message=ui_message,
                limitations=[
                    "Shade percentage is an image-based estimate and does not measure wet-bulb globe temperature (WBGT).",
                    "Hydration availability along this route is unverified."
                ]
            )
        else:
            ui_message = (
                f"Shade coverage ({shade_coverage_percent}%) satisfies minimum provisional exposure threshold. "
                "Stay hydrated and monitor local heat indices."
            )
            return PolicyEvaluationResult(
                decision=RoutingDecision.ALLOW_ROUTE.value,
                decision_engine=self.engine_name,
                ui_message=ui_message,
                limitations=[
                    "Shade coverage alone does not ensure thermal safety during extreme temperature spikes.",
                    "Vulnerable individuals should avoid outdoor transit during peak afternoon hours."
                ]
            )

    def evaluate(
        self,
        hazard_mode: str,
        vehicle_type: str,
        water_depth_inches: Optional[int] = None,
        shade_coverage_percent: Optional[int] = None,
    ) -> PolicyEvaluationResult:
        """
        Route to appropriate hazard evaluation handler.
        """
        mode = hazard_mode.lower().strip()
        if mode == "monsoon":
            return self.evaluate_monsoon(vehicle_type, water_depth_inches)
        elif mode == "heatwave":
            return self.evaluate_heatwave(vehicle_type, shade_coverage_percent)
        else:
            return PolicyEvaluationResult(
                decision=RoutingDecision.UNKNOWN.value,
                decision_engine=self.engine_name,
                ui_message=f"Unknown hazard mode '{hazard_mode}'. Cannot evaluate safety policy.",
                limitations=["Hazard mode is unsupported."]
            )


# Default singleton instance
routing_policy = RoutingPolicyEngine()
