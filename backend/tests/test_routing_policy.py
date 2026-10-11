"""
Tests for deterministic vehicle-specific safety routing rules.
"""

try:
    from services.routing_policy import routing_policy
except ImportError:
    from backend.services.routing_policy import routing_policy


# ==============================================================================
# Monsoon Waterlogging Rule Tests
# ==============================================================================

def test_monsoon_two_wheeler_over_threshold():
    """Two-wheeler at 7 inches (> 6 inches threshold) -> DENY_ROUTE."""
    result = routing_policy.evaluate(
        hazard_mode="monsoon",
        vehicle_type="two_wheeler",
        water_depth_inches=7,
    )
    assert result.decision == "DENY_ROUTE"
    assert result.decision_engine == "python_fallback"
    assert "two wheeler" in result.ui_message.lower()


def test_monsoon_two_wheeler_at_threshold():
    """Two-wheeler at exactly 6 inches (threshold is > 6) -> ALLOW_ROUTE (provisional)."""
    result = routing_policy.evaluate(
        hazard_mode="monsoon",
        vehicle_type="two_wheeler",
        water_depth_inches=6,
    )
    assert result.decision == "ALLOW_ROUTE"


def test_monsoon_car_over_threshold():
    """Car at 13 inches (> 12 inches threshold) -> DENY_ROUTE."""
    result = routing_policy.evaluate(
        hazard_mode="monsoon",
        vehicle_type="car",
        water_depth_inches=13,
    )
    assert result.decision == "DENY_ROUTE"


def test_monsoon_car_under_threshold():
    """Car at 12 inches (<= 12 inches) -> ALLOW_ROUTE."""
    result = routing_policy.evaluate(
        hazard_mode="monsoon",
        vehicle_type="car",
        water_depth_inches=12,
    )
    assert result.decision == "ALLOW_ROUTE"


def test_monsoon_pedestrian_over_threshold():
    """Pedestrian at 5 inches (> 4 inches threshold) -> DENY_ROUTE."""
    result = routing_policy.evaluate(
        hazard_mode="monsoon",
        vehicle_type="pedestrian",
        water_depth_inches=5,
    )
    assert result.decision == "DENY_ROUTE"


def test_monsoon_pedestrian_under_threshold():
    """Pedestrian at 4 inches (<= 4 inches) -> ALLOW_ROUTE."""
    result = routing_policy.evaluate(
        hazard_mode="monsoon",
        vehicle_type="pedestrian",
        water_depth_inches=4,
    )
    assert result.decision == "ALLOW_ROUTE"


def test_monsoon_missing_depth_returns_unknown():
    """CRITICAL: Missing water depth (None) must return UNKNOWN, not ALLOW_ROUTE."""
    result = routing_policy.evaluate(
        hazard_mode="monsoon",
        vehicle_type="two_wheeler",
        water_depth_inches=None,
    )
    assert result.decision == "UNKNOWN"
    assert any("missing or unverified" in lim for lim in result.limitations)


def test_monsoon_negative_depth_returns_unknown():
    """Negative water depth represents an invalid reading -> UNKNOWN."""
    result = routing_policy.evaluate(
        hazard_mode="monsoon",
        vehicle_type="car",
        water_depth_inches=-3,
    )
    assert result.decision == "UNKNOWN"


# ==============================================================================
# Heatwave Shade Coverage Rule Tests
# ==============================================================================

def test_heatwave_pedestrian_low_shade():
    """Pedestrian with 10% shade (< 20%) -> DENY_ROUTE."""
    result = routing_policy.evaluate(
        hazard_mode="heatwave",
        vehicle_type="pedestrian",
        shade_coverage_percent=10,
    )
    assert result.decision == "DENY_ROUTE"


def test_heatwave_two_wheeler_low_shade():
    """Two-wheeler with 19% shade (< 20%) -> DENY_ROUTE."""
    result = routing_policy.evaluate(
        hazard_mode="heatwave",
        vehicle_type="two_wheeler",
        shade_coverage_percent=19,
    )
    assert result.decision == "DENY_ROUTE"


def test_heatwave_pedestrian_exact_threshold():
    """Pedestrian with exactly 20% shade -> ALLOW_ROUTE (provisional)."""
    result = routing_policy.evaluate(
        hazard_mode="heatwave",
        vehicle_type="pedestrian",
        shade_coverage_percent=20,
    )
    assert result.decision == "ALLOW_ROUTE"


def test_heatwave_car_low_shade():
    """Car with 10% shade -> ALLOW_ROUTE (vehicles with cabins are sheltered from solar direct heat)."""
    result = routing_policy.evaluate(
        hazard_mode="heatwave",
        vehicle_type="car",
        shade_coverage_percent=10,
    )
    assert result.decision == "ALLOW_ROUTE"


def test_heatwave_missing_shade_returns_unknown():
    """Missing shade measurement (None) -> UNKNOWN."""
    result = routing_policy.evaluate(
        hazard_mode="heatwave",
        vehicle_type="pedestrian",
        shade_coverage_percent=None,
    )
    assert result.decision == "UNKNOWN"


def test_heatwave_invalid_shade_percent():
    """Shade percent over 100% or under 0% -> UNKNOWN."""
    assert routing_policy.evaluate("heatwave", "pedestrian", shade_coverage_percent=150).decision == "UNKNOWN"
    assert routing_policy.evaluate("heatwave", "pedestrian", shade_coverage_percent=-5).decision == "UNKNOWN"
