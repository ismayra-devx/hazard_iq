"""
Hotspots API Endpoints.
Returns urban choke points (underpasses, transit hubs) with active risk statuses
conforming to the strict HazardIQ API Contract (JSON List format).
"""

import json
import logging
import os
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, status
import httpx

from app.config import settings
from app.schemas import HotspotContractItem
from app.services.risk_service import calculate_heat_risk, calculate_monsoon_risk
from app.services.weather_service import weather_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/hotspots", tags=["Hotspots & Risk Scoring"])


def load_raw_hotspots() -> List[dict]:
    """
    Load raw hotspot records from hotspots.json.
    """
    path = settings.HOTSPOTS_FILE_PATH
    if not os.path.exists(path):
        alt_path = "data/hotspots.json"
        if os.path.exists(alt_path):
            path = alt_path
        else:
            raise FileNotFoundError(f"Hotspot records file not found at '{path}' or '{alt_path}'")

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def evaluate_risk_status(
    elevation_dip_meters: float,
    baseline_impermeability_ratio: float,
    weather_temp: Optional[float],
    weather_humidity: Optional[float],
    weather_precip: Optional[float],
    choke_type: str,
) -> str:
    """
    Evaluate active hazard evaluation status:
    Allowed values: 'clear', 'monsoon_warning', 'heatwave_warning', 'impassable'
    """
    # 1. Evaluate Monsoon / Waterlogging Risk
    precip = weather_precip if weather_precip is not None else 0.0
    abs_dip = abs(elevation_dip_meters)

    monsoon_eval = calculate_monsoon_risk(
        precipitation_mm=precip,
        elevation_dip_meters=abs_dip,
        impermeability_ratio=baseline_impermeability_ratio,
    )
    m_score = monsoon_eval.score if monsoon_eval and monsoon_eval.score is not None else 0.0

    # Underpasses with deep depression and significant rain become impassable
    if (choke_type == "underpass" and abs_dip >= 2.5 and precip >= 15.0) or m_score >= 75.0:
        return "impassable"

    if m_score >= 45.0 or precip >= 5.0:
        return "monsoon_warning"

    # 2. Evaluate Heatwave Risk
    temp = weather_temp if weather_temp is not None else 25.0
    heat_eval = calculate_heat_risk(
        temperature_celsius=temp,
        relative_humidity_percentage=weather_humidity,
    )
    h_score = heat_eval.score if heat_eval and heat_eval.score is not None else 0.0

    if h_score >= 65.0 or (temp >= 40.0):
        return "heatwave_warning"

    return "clear"


@router.get(
    "",
    response_model=List[HotspotContractItem],
    summary="Get all mapped choke points with active risk status",
    description=(
        "Fetches the pre-seeded urban choke points (underpasses, unshaded transit hubs) "
        "and their current risk attributes. The frontend uses this to plot markers on the Leaflet map."
    ),
)
async def get_all_hotspots(
    type: Optional[str] = Query(None, description="Filter by choke point type, e.g. 'underpass', 'transit_hub'")
) -> List[HotspotContractItem]:
    try:
        raw_items = load_raw_hotspots()
    except Exception as e:
        logger.error("Unable to load static hotspot data: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to load hotspot database configuration."
        )

    if type:
        raw_items = [h for h in raw_items if h.get("type", "").lower() == type.lower()]

    # Concurrently fetch weather snapshots with bounded concurrency (max 3 parallel requests)
    async with httpx.AsyncClient(timeout=settings.WEATHER_REQUEST_TIMEOUT_SECONDS) as client:
        import asyncio

        city_weather = await weather_service.get_weather(
            settings.DEFAULT_LATITUDE,
            settings.DEFAULT_LONGITUDE,
            client=client
        )

        semaphore = asyncio.Semaphore(3)

        async def fetch_point_weather(lat: float, lon: float):
            async with semaphore:
                snap = await weather_service.get_weather(lat, lon, client=client)
                if snap.temperature_celsius is None and city_weather.temperature_celsius is not None:
                    fallback_snap = city_weather.model_copy()
                    fallback_snap.source = f"{city_weather.source} (Regional Delhi Fallback)"
                    return fallback_snap
                return snap

        weather_tasks = [
            fetch_point_weather(h.get("lat", 28.6139), h.get("lng", 77.2090))
            for h in raw_items
        ]
        weather_snapshots = await asyncio.gather(*weather_tasks)

    contract_hotspots: List[HotspotContractItem] = []
    for h, weather in zip(raw_items, weather_snapshots):
        dip = float(h.get("elevation_dip_meters", 0.0))
        imp = float(h.get("baseline_impermeability_ratio", 0.90))
        choke_type = h.get("type", "underpass")

        temp = weather.temperature_celsius if weather else None
        humidity = weather.relative_humidity_percentage if weather else None
        precip = weather.precipitation_mm if weather else None

        active_status = evaluate_risk_status(
            elevation_dip_meters=dip,
            baseline_impermeability_ratio=imp,
            weather_temp=temp,
            weather_humidity=humidity,
            weather_precip=precip,
            choke_type=choke_type,
        )

        item = HotspotContractItem(
            id=h.get("id") or h.get("hotspot_id", "point_001"),
            name=h.get("name", "Unknown Choke Point"),
            lat=float(h.get("lat") or h.get("latitude", 28.6139)),
            lng=float(h.get("lng") or h.get("longitude", 77.2090)),
            type=choke_type,
            baseline_impermeability_ratio=imp,
            elevation_dip_meters=dip,
            current_risk_status=active_status,
        )
        contract_hotspots.append(item)

    return contract_hotspots


@router.get(
    "/{hotspot_id}",
    response_model=HotspotContractItem,
    summary="Get single choke point by ID",
)
async def get_hotspot_by_id(hotspot_id: str) -> HotspotContractItem:
    raw_items = load_raw_hotspots()
    matched = next((h for h in raw_items if (h.get("id") == hotspot_id or h.get("hotspot_id") == hotspot_id)), None)
    if not matched:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Hotspot with ID '{hotspot_id}' not found."
        )

    lat = float(matched.get("lat") or matched.get("latitude", 28.6139))
    lng = float(matched.get("lng") or matched.get("longitude", 77.2090))
    weather = await weather_service.get_weather(lat, lng)

    dip = float(matched.get("elevation_dip_meters", 0.0))
    imp = float(matched.get("baseline_impermeability_ratio", 0.90))
    choke_type = matched.get("type", "underpass")

    active_status = evaluate_risk_status(
        elevation_dip_meters=dip,
        baseline_impermeability_ratio=imp,
        weather_temp=weather.temperature_celsius if weather else None,
        weather_humidity=weather.relative_humidity_percentage if weather else None,
        weather_precip=weather.precipitation_mm if weather else None,
        choke_type=choke_type,
    )

    return HotspotContractItem(
        id=matched.get("id") or matched.get("hotspot_id", hotspot_id),
        name=matched.get("name", "Unknown Choke Point"),
        lat=lat,
        lng=lng,
        type=choke_type,
        baseline_impermeability_ratio=imp,
        elevation_dip_meters=dip,
        current_risk_status=active_status,
    )
