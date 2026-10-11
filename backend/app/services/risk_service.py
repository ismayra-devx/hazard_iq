"""
Risk Evaluation Service.
Calculates transparent, explainable heatwave and monsoon risk scores (0-100).

IMPORTANT LIMITATIONS:
- These scores are heuristic prototype models designed for commuter decision support,
  not scientifically calibrated flood hydraulic models or clinical thermal stress forecasts.
- Missing inputs are never silently assumed to be safe.
- A road is never declared safe solely because an estimated water depth or rainfall is low.
- Locations with missing shade data are flagged as UNKNOWN rather than assuming they are shaded.
"""

from typing import List, Optional
import math

from app.schemas import (
    HeatRiskAssessment,
    MonsoonRiskAssessment,
    RiskLevel,
    RoadType,
    ShadeStatus,
)


def calculate_heat_risk(
    temperature_celsius: Optional[float],
    relative_humidity_percentage: Optional[float] = None,
    shade_ratio: Optional[float] = None,
    drinking_water_available: Optional[bool] = None,
) -> HeatRiskAssessment:
    """
    Calculate thermal risk estimate (0-100) based on temperature, humidity, and thermal relief.
    """
    contributing_factors: List[str] = []

    # 1. Missing data handling
    if temperature_celsius is None:
        return HeatRiskAssessment(
            score=None,
            level=RiskLevel.UNKNOWN,
            is_estimate=True,
            shade_status=ShadeStatus.UNKNOWN,
            contributing_factors=["Missing ambient temperature data"],
            calculation_notes="Unable to evaluate heat risk without temperature measurements."
        )

    # 2. Base thermal stress calculation
    temp = float(temperature_celsius)
    humidity = float(relative_humidity_percentage) if relative_humidity_percentage is not None else 50.0

    # Simplified apparent temperature approximation (Australian Bureau of Meteorology formula)
    # Vapor pressure (e) in hPa: e = (humidity / 100) * 6.105 * exp((17.27 * temp) / (237.7 + temp))
    # Apparent temp = temp + 0.33 * e - 4.0
    vapor_pressure = (humidity / 100.0) * 6.105 * math.exp((17.27 * temp) / (237.7 + temp))
    apparent_temp = temp + (0.33 * vapor_pressure) - 4.0

    contributing_factors.append(f"Ambient temperature {temp:.1f}°C")
    if relative_humidity_percentage is not None:
        contributing_factors.append(f"Relative humidity {humidity:.0f}% (Apparent feels-like: {apparent_temp:.1f}°C)")
    else:
        contributing_factors.append("Humidity unmeasured; defaulted to neutral 50% for thermal estimate")

    # Map apparent temperature to baseline 0-100 score
    if apparent_temp <= 25.0:
        base_score = max(0.0, (apparent_temp / 25.0) * 20.0)
    elif apparent_temp <= 35.0:
        base_score = 20.0 + ((apparent_temp - 25.0) / 10.0) * 40.0
    elif apparent_temp <= 44.0:
        base_score = 60.0 + ((apparent_temp - 35.0) / 9.0) * 25.0
    else:
        base_score = min(100.0, 85.0 + ((apparent_temp - 44.0) / 6.0) * 15.0)

    score = base_score

    # 3. Shade coverage evaluation
    if shade_ratio is None:
        shade_status = ShadeStatus.UNKNOWN
        contributing_factors.append("Shade coverage unmeasured: flagged UNKNOWN (no shade assumed)")
    else:
        clamped_shade = max(0.0, min(1.0, float(shade_ratio)))
        if clamped_shade >= 0.35:
            shade_status = ShadeStatus.VERIFIED_SHADED
            reduction = clamped_shade * 15.0
            score = max(0.0, score - reduction)
            contributing_factors.append(f"Verified tree/canopy shade ({clamped_shade*100:.0f}%) mitigated thermal stress (-{reduction:.1f} pts)")
        else:
            shade_status = ShadeStatus.UNSHADED
            penalty = 5.0 if clamped_shade < 0.15 else 2.0
            score = min(100.0, score + penalty)
            contributing_factors.append(f"Low shade coverage ({clamped_shade*100:.0f}%): exposed to solar insolation (+{penalty:.1f} pts)")

    # 4. Drinking water relief point evaluation
    if drinking_water_available is True:
        score = max(0.0, score - 5.0)
        contributing_factors.append("Verified drinking water thermal relief kiosk available nearby (-5.0 pts)")
    elif drinking_water_available is False:
        contributing_factors.append("No drinking water points verified along this segment")
    else:
        contributing_factors.append("Drinking water point status unverified")

    # Final score normalization (0.0 to 100.0)
    final_score = round(max(0.0, min(100.0, score)), 1)

    # Risk level categorization
    if final_score < 30.0:
        level = RiskLevel.LOW
    elif final_score < 60.0:
        level = RiskLevel.MODERATE
    elif final_score < 85.0:
        level = RiskLevel.HIGH
    else:
        level = RiskLevel.SEVERE

    notes = (
        f"Score {final_score}/100 ({level.value}). "
        "Estimated using apparent temperature index adjusted for local micro-climate shade and hydration relief."
    )

    return HeatRiskAssessment(
        score=final_score,
        level=level,
        is_estimate=True,
        shade_status=shade_status,
        contributing_factors=contributing_factors,
        calculation_notes=notes
    )


def calculate_monsoon_risk(
    precipitation_mm: Optional[float],
    elevation_dip_meters: float,
    impermeability_ratio: float,
    road_type: RoadType = RoadType.PRIMARY,
    recent_verified_reports_count: int = 0,
    recent_unverified_reports_count: int = 0,
) -> MonsoonRiskAssessment:
    """
    Calculate monsoon / waterlogging risk estimate (0-100) based on rainfall,
    surface runoff permeability, topographical depression, and incident reports.
    """
    contributing_factors: List[str] = []

    # 1. Missing rainfall check
    if precipitation_mm is None and (recent_verified_reports_count + recent_unverified_reports_count) == 0:
        return MonsoonRiskAssessment(
            score=None,
            level=RiskLevel.UNKNOWN,
            is_estimate=True,
            waterlogging_hazard=False,
            contributing_factors=["Precipitation data unavailable and no citizen reports filed"],
            calculation_notes="Unable to calculate monsoon risk without rainfall inputs or active field reports."
        )

    precip = float(precipitation_mm) if precipitation_mm is not None else 0.0
    elevation_dip = max(0.0, float(elevation_dip_meters))
    impermeability = max(0.0, min(1.0, float(impermeability_ratio)))

    contributing_factors.append(f"Precipitation: {precip:.1f} mm/hr accumulation")
    contributing_factors.append(f"Topographic elevation dip: {elevation_dip:.1f} meters")
    contributing_factors.append(f"Surface impermeability: {impermeability*100:.0f}% concrete/asphalt")

    # 2. Rainfall accumulation factor (0 to 50 pts)
    if precip <= 0.0:
        rainfall_pts = 0.0
    elif precip <= 5.0:
        rainfall_pts = precip * 3.0  # up to 15
    elif precip <= 20.0:
        rainfall_pts = 15.0 + ((precip - 5.0) / 15.0) * 20.0  # up to 35
    elif precip <= 50.0:
        rainfall_pts = 35.0 + ((precip - 20.0) / 30.0) * 15.0  # up to 50
    else:
        rainfall_pts = min(55.0, 50.0 + ((precip - 50.0) / 20.0) * 5.0)

    # 3. Topographic depression & drainage factor
    # Depression traps water; impermeability prevents natural absorption
    topography_multiplier = 1.0 + (elevation_dip * 0.35)
    runoff_score = rainfall_pts * impermeability * topography_multiplier

    # 4. Road classification modifier
    # Arterial / Underpass / Highway culverts carry heavy drainage basin loads
    if road_type in (RoadType.ARTERIAL, RoadType.HIGHWAY) and elevation_dip > 1.5:
        runoff_score += 10.0
        contributing_factors.append("High-capacity underpass corridor vulnerable to flash drainage overflow (+10 pts)")

    # 5. Incident reports bonus (ground truth signals)
    report_bonus = 0.0
    if recent_verified_reports_count > 0:
        bonus = min(35.0, recent_verified_reports_count * 20.0)
        report_bonus += bonus
        contributing_factors.append(f"{recent_verified_reports_count} verified citizen waterlogging report(s) (+{bonus:.0f} pts)")

    if recent_unverified_reports_count > 0:
        bonus = min(15.0, recent_unverified_reports_count * 8.0)
        report_bonus += bonus
        contributing_factors.append(f"{recent_unverified_reports_count} unverified / AI-flagged report(s) (+{bonus:.0f} pts)")

    total_score = round(max(0.0, min(100.0, runoff_score + report_bonus)), 1)

    # 6. Waterlogging hazard condition
    # Triggers if total score >= 55.0 or any verified report exists
    hazard = total_score >= 55.0 or recent_verified_reports_count > 0

    # Categorical classification
    if total_score < 25.0:
        level = RiskLevel.LOW
    elif total_score < 55.0:
        level = RiskLevel.MODERATE
    elif total_score < 80.0:
        level = RiskLevel.HIGH
    else:
        level = RiskLevel.SEVERE

    notes = (
        f"Score {total_score}/100 ({level.value}). "
        "Estimated via hydraulic runoff accumulation combining rainfall, depression depth, and citizen incident reports. "
        "Roads are never certified safe solely based on low depth."
    )

    return MonsoonRiskAssessment(
        score=total_score,
        level=level,
        is_estimate=True,
        waterlogging_hazard=hazard,
        contributing_factors=contributing_factors,
        calculation_notes=notes
    )
