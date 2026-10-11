"""
Weather API Router.
Provides current localized weather observations and forecasts from Open-Meteo.
"""

from fastapi import APIRouter, HTTPException, Query, status

from app.schemas import WeatherSnapshot
from app.services.weather_service import weather_service

router = APIRouter(prefix="/api/weather", tags=["Weather Integration"])


@router.get(
    "/current",
    response_model=WeatherSnapshot,
    summary="Get current weather for coordinates",
    description="Retrieves current temperature, humidity, hourly precipitation accumulation, and wind speed from Open-Meteo.",
)
async def get_current_weather(
    latitude: float = Query(..., ge=-90.0, le=90.0, description="Latitude in decimal degrees"),
    longitude: float = Query(..., ge=-180.0, le=180.0, description="Longitude in decimal degrees"),
) -> WeatherSnapshot:
    snapshot = await weather_service.get_weather(latitude, longitude)
    return snapshot
