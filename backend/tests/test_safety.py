"""
Tests for Safety Decisions and Policy Engine alignment.
Validates conservative safety rules across vehicle types and hazard conditions.
"""

import os
from app.config import settings
from app.schemas import (
    HazardCategory,
    HeatRiskAssessment,
    MonsoonRiskAssessment,
    RiskLevel,
    SafetyAction,
    ShadeStatus,
    VehicleType,
)
from app.services.safety_service import safety_service


def test_cedar_policy_file_exists_and_contains_rules():
    assert os.path.exists(settings.CEDAR_POLICY_PATH), "Cedar policy file must exist"
    with open(settings.CEDAR_POLICY_PATH, "r", encoding="utf-8") as f:
        content = f.read().lower()
    assert "forbid" in content
    assert "permit" in content
    assert "pedestrian" in content
    assert "two_wheeler" in content


def test_pedestrian_waterlogging_triggers_avoid():
    # Pedestrian on waterlogged road (Cedar Policy 1)
    monsoon = MonsoonRiskAssessment(
        score=50.0,
        level=RiskLevel.MODERATE,
        is_estimate=True,
        waterlogging_hazard=True,
        contributing_factors=[]
    )
    decision = safety_service.evaluate_safety(
        vehicle_type=VehicleType.PEDESTRIAN,
        hazard_category=HazardCategory.WATERLOGGING,
        monsoon_risk=monsoon
    )
    assert decision.action == SafetyAction.AVOID
    assert any("PEDESTRIAN" in r for r in decision.rules_triggered)


def test_two_wheeler_waterlogging_triggers_avoid():
    # Two-wheeler on waterlogged segment (Cedar Policy 2)
    monsoon = MonsoonRiskAssessment(
        score=48.0,
        level=RiskLevel.MODERATE,
        is_estimate=True,
        waterlogging_hazard=True,
        contributing_factors=[]
    )
    decision = safety_service.evaluate_safety(
        vehicle_type=VehicleType.TWO_WHEELER,
        hazard_category=HazardCategory.WATERLOGGING,
        monsoon_risk=monsoon
    )
    assert decision.action == SafetyAction.AVOID
    assert any("TWO_WHEELER" in r for r in decision.rules_triggered)


def test_four_wheeler_deep_waterlogging_triggers_avoid():
    # Sedan car in deep waterlogging (score >= 70) (Cedar Policy 4)
    monsoon = MonsoonRiskAssessment(
        score=75.0,
        level=RiskLevel.HIGH,
        is_estimate=True,
        waterlogging_hazard=True,
        contributing_factors=[]
    )
    decision = safety_service.evaluate_safety(
        vehicle_type=VehicleType.FOUR_WHEELER_CAR,
        monsoon_risk=monsoon
    )
    assert decision.action == SafetyAction.AVOID
    assert any("FOUR_WHEELER" in r for r in decision.rules_triggered)


def test_four_wheeler_moderate_waterlogging_triggers_warn():
    # Sedan car in moderate water (score = 50)
    monsoon = MonsoonRiskAssessment(
        score=50.0,
        level=RiskLevel.MODERATE,
        is_estimate=True,
        waterlogging_hazard=False,
        contributing_factors=[]
    )
    decision = safety_service.evaluate_safety(
        vehicle_type=VehicleType.FOUR_WHEELER_CAR,
        monsoon_risk=monsoon
    )
    assert decision.action == SafetyAction.WARN


def test_bus_heavy_vehicle_clearance():
    # Bus tolerates moderate waterlogging (score = 50)
    monsoon = MonsoonRiskAssessment(
        score=50.0,
        level=RiskLevel.MODERATE,
        is_estimate=True,
        waterlogging_hazard=False,
        contributing_factors=[]
    )
    decision = safety_service.evaluate_safety(
        vehicle_type=VehicleType.BUS_HEAVY,
        monsoon_risk=monsoon
    )
    assert decision.action == SafetyAction.ALLOW

    # But catastrophic flooding (score = 90) triggers AVOID (Cedar Policy 5)
    monsoon_extreme = MonsoonRiskAssessment(
        score=90.0,
        level=RiskLevel.SEVERE,
        is_estimate=True,
        waterlogging_hazard=True,
        contributing_factors=[]
    )
    decision_extreme = safety_service.evaluate_safety(
        vehicle_type=VehicleType.BUS_HEAVY,
        monsoon_risk=monsoon_extreme
    )
    assert decision_extreme.action == SafetyAction.AVOID


def test_safe_conditions_permit_transit():
    # Clear weather and low risks (Cedar Policy 6)
    monsoon = MonsoonRiskAssessment(
        score=10.0,
        level=RiskLevel.LOW,
        is_estimate=True,
        waterlogging_hazard=False,
        contributing_factors=[]
    )
    heat = HeatRiskAssessment(
        score=25.0,
        level=RiskLevel.LOW,
        is_estimate=True,
        shade_status=ShadeStatus.VERIFIED_SHADED,
        contributing_factors=[]
    )
    decision = safety_service.evaluate_safety(
        vehicle_type=VehicleType.TWO_WHEELER,
        monsoon_risk=monsoon,
        heat_risk=heat
    )
    assert decision.action == SafetyAction.ALLOW


def test_uncertain_conditions_never_marked_safe():
    # Crucial rule: Unknown conditions MUST NEVER be marked verified safe
    decision = safety_service.evaluate_safety(
        vehicle_type=VehicleType.FOUR_WHEELER_CAR,
        hazard_category=HazardCategory.WATERLOGGING,
        monsoon_risk=None,
        heat_risk=None
    )
    assert decision.action != SafetyAction.ALLOW
    assert decision.uncertainty_warning is not None
    assert "cannot be certified safe" in decision.uncertainty_warning
