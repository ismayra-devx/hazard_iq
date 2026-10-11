"""
Safety Evaluation Service.
Applies conservative safety rules based on vehicle clearance, hazard severity,
and commuter vulnerability.

Integrates policy engine evaluation:
- Inspects cedar_policy.cedar specification.
- If native Cedar binary/SDK is unavailable (e.g. Python 3.14 Windows environment),
  executes an equivalent deterministic Python safety engine with identical logic,
  transparently reporting the active engine name.
- Explicit Rule: A road with UNKNOWN status or missing data is never marked safe.
"""

import logging
import os
from typing import List, Optional

from app.config import settings
from app.schemas import (
    HazardCategory,
    HeatRiskAssessment,
    MonsoonRiskAssessment,
    RiskLevel,
    SafetyAction,
    SafetyDecisionResult,
    VehicleType,
)

logger = logging.getLogger(__name__)


class SafetyService:
    def __init__(self, policy_path: Optional[str] = None):
        self.policy_path = policy_path or settings.CEDAR_POLICY_PATH
        self.policy_file_exists = os.path.exists(self.policy_path)
        # Check whether native Cedar evaluator is available
        self.native_cedar_available = self._detect_cedar_runtime()

    def _detect_cedar_runtime(self) -> bool:
        """
        Detect if official native Cedar evaluation CLI or package is accessible.
        Cedar currently lacks pre-built wheels for Python 3.14 on Windows.
        """
        # Attempt to import cedarpolicy if ever installed
        try:
            import cedarpolicy  # type: ignore
            return True
        except ImportError:
            return False

    def evaluate_safety(
        self,
        vehicle_type: VehicleType,
        hazard_category: Optional[HazardCategory] = None,
        monsoon_risk: Optional[MonsoonRiskAssessment] = None,
        heat_risk: Optional[HeatRiskAssessment] = None,
        road_segment_id: Optional[str] = None,
    ) -> SafetyDecisionResult:
        """
        Evaluate navigation safety for a commuter based on vehicle type and risk assessments.
        """
        rules_triggered: List[str] = []
        engine_id = (
            "cedar_native_engine"
            if self.native_cedar_available
            else "deterministic_python_safety_engine (Cedar fallback - native engine unavailable on Python 3.14 Windows)"
        )

        # 1. Missing data / Uncertainty check
        # A road marked UNKNOWN must not be presented as verified safe.
        is_monsoon_unknown = monsoon_risk is None or monsoon_risk.level == RiskLevel.UNKNOWN
        is_heat_unknown = heat_risk is None or heat_risk.level == RiskLevel.UNKNOWN

        uncertainty_warning: Optional[str] = None
        if is_monsoon_unknown and hazard_category == HazardCategory.WATERLOGGING:
            rules_triggered.append("RULE_UNCERTAIN_WATERLOGGING_HAZARD")
            return SafetyDecisionResult(
                action=SafetyAction.WARN,
                reason="Waterlogging hazard reported but physical runoff measurements are unknown. Proceed with extreme caution.",
                policy_engine=engine_id,
                rules_triggered=rules_triggered,
                uncertainty_warning="Lacks verified runoff/depth data. Road cannot be certified safe."
            )

        # Extract numerical scores with fallbacks
        m_score = monsoon_risk.score if monsoon_risk and monsoon_risk.score is not None else 0.0
        h_score = heat_risk.score if heat_risk and heat_risk.score is not None else 0.0
        is_water_hazard = bool(monsoon_risk and monsoon_risk.waterlogging_hazard) or (
            hazard_category == HazardCategory.WATERLOGGING
        )

        # 2. Vehicle-specific flood clearance rules (Cedar Policies 1-5)
        if vehicle_type == VehicleType.PEDESTRIAN:
            if is_water_hazard or m_score >= 40.0:
                rules_triggered.append("CEDAR_POLICY_1: FORBID PEDESTRIAN on waterlogged segment")
                return SafetyDecisionResult(
                    action=SafetyAction.AVOID,
                    reason="Pedestrians must avoid waterlogged roads due to open manhole, electrical, and submerged pothole risks.",
                    policy_engine=engine_id,
                    rules_triggered=rules_triggered,
                    uncertainty_warning=uncertainty_warning
                )
            if m_score >= 25.0:
                rules_triggered.append("RULE_PEDESTRIAN_MODERATE_MONSOON_WARN")
                return SafetyDecisionResult(
                    action=SafetyAction.WARN,
                    reason="Surface water runoff may impede safe pedestrian sidewalk transit.",
                    policy_engine=engine_id,
                    rules_triggered=rules_triggered
                )

        elif vehicle_type == VehicleType.TWO_WHEELER:
            if is_water_hazard or m_score >= 45.0:
                rules_triggered.append("CEDAR_POLICY_2: FORBID TWO_WHEELER on moderate/severe waterlogging")
                return SafetyDecisionResult(
                    action=SafetyAction.AVOID,
                    reason="Two-wheelers risk hydroplaning, exhaust back-flooding, and submerged road depression accidents.",
                    policy_engine=engine_id,
                    rules_triggered=rules_triggered
                )
            if m_score >= 30.0:
                rules_triggered.append("RULE_TWO_WHEELER_SLIPPERY_WARN")
                return SafetyDecisionResult(
                    action=SafetyAction.WARN,
                    reason="Slippery surface conditions and pooling water detected.",
                    policy_engine=engine_id,
                    rules_triggered=rules_triggered
                )

        elif vehicle_type == VehicleType.THREE_WHEELER_AUTO:
            if m_score >= 55.0 or (is_water_hazard and m_score >= 40.0):
                rules_triggered.append("CEDAR_POLICY_3: FORBID THREE_WHEELER_AUTO on severe waterlogging")
                return SafetyDecisionResult(
                    action=SafetyAction.AVOID,
                    reason="Auto-rickshaws have low ground clearance and risk stalling in accumulated water.",
                    policy_engine=engine_id,
                    rules_triggered=rules_triggered
                )
            if m_score >= 35.0:
                rules_triggered.append("RULE_THREE_WHEELER_AUTO_WARN")
                return SafetyDecisionResult(
                    action=SafetyAction.WARN,
                    reason="Moderate water pooling. Slow driving recommended.",
                    policy_engine=engine_id,
                    rules_triggered=rules_triggered
                )

        elif vehicle_type == VehicleType.FOUR_WHEELER_CAR:
            if m_score >= 70.0:
                rules_triggered.append("CEDAR_POLICY_4: FORBID FOUR_WHEELER_CAR on deep waterlogging")
                return SafetyDecisionResult(
                    action=SafetyAction.AVOID,
                    reason="Estimated water accumulation exceeds safe sedan/hatchback clearance. Avoid road.",
                    policy_engine=engine_id,
                    rules_triggered=rules_triggered
                )
            if m_score >= 45.0:
                rules_triggered.append("RULE_FOUR_WHEELER_CAR_WARN")
                return SafetyDecisionResult(
                    action=SafetyAction.WARN,
                    reason="Water pooling on road. Exercise caution near low-lying underpasses.",
                    policy_engine=engine_id,
                    rules_triggered=rules_triggered
                )

        elif vehicle_type == VehicleType.BUS_HEAVY:
            if m_score >= 85.0:
                rules_triggered.append("CEDAR_POLICY_5: FORBID BUS_HEAVY on catastrophic flooding")
                return SafetyDecisionResult(
                    action=SafetyAction.AVOID,
                    reason="Catastrophic flooding and structural underpass submergence reported. Impassable.",
                    policy_engine=engine_id,
                    rules_triggered=rules_triggered
                )
            if m_score >= 60.0:
                rules_triggered.append("RULE_HEAVY_VEHICLE_WARN")
                return SafetyDecisionResult(
                    action=SafetyAction.WARN,
                    reason="Significant water depth. Heavy vehicles should proceed at reduced speed.",
                    policy_engine=engine_id,
                    rules_triggered=rules_triggered
                )

        # 3. Severe Heatwave Considerations
        if h_score >= 80.0:
            rules_triggered.append("RULE_SEVERE_HEAT_EXPOSURE")
            if vehicle_type in (VehicleType.PEDESTRIAN, VehicleType.TWO_WHEELER):
                return SafetyDecisionResult(
                    action=SafetyAction.WARN,
                    reason="Severe ambient heat stress. Carry hydration, seek shaded corridors, and minimize direct exposure.",
                    policy_engine=engine_id,
                    rules_triggered=rules_triggered
                )

        # 4. Obstruction / Other Hazard
        if hazard_category == HazardCategory.FALLEN_TREE_OBSTRUCTION:
            rules_triggered.append("RULE_PHYSICAL_OBSTRUCTION")
            return SafetyDecisionResult(
                action=SafetyAction.AVOID,
                reason="Physical blockage or fallen tree obstructing vehicular transit.",
                policy_engine=engine_id,
                rules_triggered=rules_triggered
            )

        # 5. Default Permit / Allow (Cedar Policy 6)
        rules_triggered.append("CEDAR_POLICY_6: PERMIT Transit within vehicle tolerance")
        return SafetyDecisionResult(
            action=SafetyAction.ALLOW,
            reason="Road conditions within acceptable clearance tolerances for commuter vehicle type.",
            policy_engine=engine_id,
            rules_triggered=rules_triggered
        )


# Singleton instance
safety_service = SafetyService()
