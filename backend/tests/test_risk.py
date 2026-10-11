"""
Unit tests for Heat and Monsoon risk calculations.
Covers low, moderate, high, severe, missing data, shade handling, and boundary conditions.
"""

from app.schemas import RiskLevel, RoadType, ShadeStatus
from app.services.risk_service import calculate_heat_risk, calculate_monsoon_risk


# ==============================================================================
# Heat Risk Tests
# ==============================================================================

def test_heat_risk_low_condition():
    # Mild temperature (20°C, 45% humidity)
    assessment = calculate_heat_risk(
        temperature_celsius=20.0,
        relative_humidity_percentage=45.0,
        shade_ratio=0.5,
        drinking_water_available=True
    )
    assert assessment.level == RiskLevel.LOW
    assert assessment.score is not None
    assert assessment.score < 30.0
    assert assessment.is_estimate is True
    assert assessment.shade_status == ShadeStatus.VERIFIED_SHADED


def test_heat_risk_moderate_condition():
    # Warm conditions (32°C, 50% humidity)
    assessment = calculate_heat_risk(
        temperature_celsius=32.0,
        relative_humidity_percentage=50.0,
        shade_ratio=0.2,
        drinking_water_available=False
    )
    assert assessment.level in (RiskLevel.MODERATE, RiskLevel.HIGH)
    assert assessment.score is not None
    assert 30.0 <= assessment.score <= 75.0


def test_heat_risk_severe_condition():
    # Extreme heatwave (44°C, 55% humidity)
    assessment = calculate_heat_risk(
        temperature_celsius=44.0,
        relative_humidity_percentage=55.0,
        shade_ratio=0.05,
        drinking_water_available=False
    )
    assert assessment.level in (RiskLevel.HIGH, RiskLevel.SEVERE)
    assert assessment.score is not None
    assert assessment.score >= 70.0
    assert assessment.shade_status == ShadeStatus.UNSHADED


def test_heat_risk_missing_temperature():
    # Missing temperature input must return UNKNOWN, not assume safe
    assessment = calculate_heat_risk(
        temperature_celsius=None,
        relative_humidity_percentage=60.0
    )
    assert assessment.level == RiskLevel.UNKNOWN
    assert assessment.score is None
    assert assessment.shade_status == ShadeStatus.UNKNOWN
    assert any("Missing" in f for f in assessment.contributing_factors)


def test_heat_risk_unmeasured_shade_flagged_unknown():
    # Critical requirement: Missing shade data MUST NOT assume shaded
    assessment = calculate_heat_risk(
        temperature_celsius=35.0,
        relative_humidity_percentage=50.0,
        shade_ratio=None,
        drinking_water_available=False
    )
    assert assessment.shade_status == ShadeStatus.UNKNOWN
    assert any("unmeasured" in f.lower() for f in assessment.contributing_factors)


def test_heat_risk_shade_mitigation_benefit():
    # Compare identical temperature with and without verified shade
    without_shade = calculate_heat_risk(38.0, 50.0, shade_ratio=0.0)
    with_shade = calculate_heat_risk(38.0, 50.0, shade_ratio=0.8)
    assert with_shade.score is not None and without_shade.score is not None
    assert with_shade.score < without_shade.score
    assert with_shade.shade_status == ShadeStatus.VERIFIED_SHADED


def test_heat_risk_drinking_water_mitigation():
    no_water = calculate_heat_risk(38.0, 50.0, drinking_water_available=False)
    with_water = calculate_heat_risk(38.0, 50.0, drinking_water_available=True)
    assert with_water.score is not None and no_water.score is not None
    assert with_water.score < no_water.score


# ==============================================================================
# Monsoon Risk Tests
# ==============================================================================

def test_monsoon_risk_dry_conditions():
    # Zero rainfall
    assessment = calculate_monsoon_risk(
        precipitation_mm=0.0,
        elevation_dip_meters=0.2,
        impermeability_ratio=0.85,
        road_type=RoadType.PRIMARY
    )
    assert assessment.level == RiskLevel.LOW
    assert assessment.score is not None
    assert assessment.score < 25.0
    assert assessment.waterlogging_hazard is False


def test_monsoon_risk_moderate_rainfall():
    # 12 mm rainfall in slight depression
    assessment = calculate_monsoon_risk(
        precipitation_mm=12.0,
        elevation_dip_meters=1.0,
        impermeability_ratio=0.90,
        road_type=RoadType.PRIMARY
    )
    assert assessment.level in (RiskLevel.MODERATE, RiskLevel.HIGH)
    assert assessment.score is not None
    assert 25.0 <= assessment.score <= 65.0


def test_monsoon_risk_severe_flash_flood_conditions():
    # Heavy downpour (45mm/hr) in deep underpass (elevation dip 2.8m, impermeability 0.95)
    assessment = calculate_monsoon_risk(
        precipitation_mm=45.0,
        elevation_dip_meters=2.8,
        impermeability_ratio=0.95,
        road_type=RoadType.ARTERIAL
    )
    assert assessment.level in (RiskLevel.HIGH, RiskLevel.SEVERE)
    assert assessment.score is not None
    assert assessment.score >= 60.0
    assert assessment.waterlogging_hazard is True


def test_monsoon_risk_missing_rainfall():
    # Missing rainfall and zero reports must return UNKNOWN, not safe
    assessment = calculate_monsoon_risk(
        precipitation_mm=None,
        elevation_dip_meters=2.0,
        impermeability_ratio=0.90,
        recent_verified_reports_count=0
    )
    assert assessment.level == RiskLevel.UNKNOWN
    assert assessment.score is None
    assert assessment.waterlogging_hazard is False


def test_monsoon_risk_citizen_report_elevates_hazard():
    # Even with low rainfall, a verified citizen waterlogging report elevates hazard
    assessment = calculate_monsoon_risk(
        precipitation_mm=2.0,
        elevation_dip_meters=0.5,
        impermeability_ratio=0.85,
        recent_verified_reports_count=1
    )
    assert assessment.waterlogging_hazard is True
    assert assessment.score is not None
    assert assessment.score >= 20.0
