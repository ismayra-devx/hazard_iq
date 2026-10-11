"""
Weather Service using Open-Meteo API.
Provides asynchronous weather fetching with in-memory caching and resilient error handling.

Attribution:
Weather data provided by Open-Meteo.com under Creative Commons Attribution 4.0 International (CC BY 4.0).
https://open-meteo.com/en/terms
"""

import logging
import time
from typing import Dict, Optional, Tuple
import httpx

from app.config import settings
from app.schemas import WeatherSnapshot

logger = logging.getLogger(__name__)


class WeatherCacheEntry:
    def __init__(self, snapshot: WeatherSnapshot, cached_at: float):
        self.snapshot = snapshot
        self.cached_at = cached_at

    def is_expired(self, ttl_seconds: int) -> bool:
        return (time.time() - self.cached_at) > ttl_seconds


class WeatherService:
    def __init__(self, base_url: Optional[str] = None, timeout: float = 5.0):
        self.base_url = base_url or settings.OPEN_METEO_BASE_URL
        self.timeout = timeout or settings.WEATHER_REQUEST_TIMEOUT_SECONDS
        self._cache: Dict[str, WeatherCacheEntry] = {}

    def _cache_key(self, latitude: float, longitude: float) -> str:
        # Round to 2 decimal places (~1.1 km grid resolution) to maximize cache hits across nearby city hotspots
        return f"{round(latitude, 2)}:{round(longitude, 2)}"

    async def get_weather(
        self,
        latitude: float,
        longitude: float,
        client: Optional[httpx.AsyncClient] = None
    ) -> WeatherSnapshot:
        """
        Fetch current weather metrics for given coordinates.
        Uses in-memory cache if available and within TTL.
        Returns a resilient WeatherSnapshot on network timeout or upstream failure.
        """
        # Validate coordinates bounds
        if not (-90.0 <= latitude <= 90.0) or not (-180.0 <= longitude <= 180.0):
            logger.error("Invalid coordinates provided to WeatherService: lat=%s, lon=%s", latitude, longitude)
            return WeatherSnapshot(
                source="Invalid Coordinates - Open-Meteo",
                is_live=False
            )

        cache_key = self._cache_key(latitude, longitude)
        now = time.time()

        # Check cache
        if cache_key in self._cache:
            entry = self._cache[cache_key]
            if not entry.is_expired(settings.WEATHER_CACHE_TTL_SECONDS):
                freshness = int(now - entry.cached_at)
                # Clone snapshot with updated freshness
                cached_data = entry.snapshot.model_copy()
                cached_data.data_freshness_seconds = freshness
                return cached_data

        params = {
            "latitude": round(latitude, 4),
            "longitude": round(longitude, 4),
            "current": "temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m",
            "timezone": "auto"
        }

        should_close_client = False
        if client is None:
            client = httpx.AsyncClient(timeout=self.timeout)
            should_close_client = True

        try:
            response = await client.get(self.base_url, params=params)
            response.raise_for_status()
            data = response.json()

            current = data.get("current", {})
            temp = current.get("temperature_2m")
            humidity = current.get("relative_humidity_2m")
            precip = current.get("precipitation")
            wind = current.get("wind_speed_10m")
            obs_time = current.get("time")

            snapshot = WeatherSnapshot(
                temperature_celsius=float(temp) if temp is not None else None,
                relative_humidity_percentage=float(humidity) if humidity is not None else None,
                precipitation_mm=float(precip) if precip is not None else None,
                wind_speed_kmh=float(wind) if wind is not None else None,
                observation_time=str(obs_time) if obs_time else None,
                data_freshness_seconds=0,
                source="Open-Meteo API (CC BY 4.0)",
                is_live=True
            )

            # Store in cache
            self._cache[cache_key] = WeatherCacheEntry(snapshot, now)
            return snapshot

        except httpx.TimeoutException:
            logger.warning("Open-Meteo weather API timed out for coords (%s, %s)", latitude, longitude)
            return WeatherSnapshot(
                source="Open-Meteo API (Timeout Fallback)",
                is_live=False
            )
        except httpx.HTTPStatusError as e:
            logger.warning("Open-Meteo HTTP status error: %s for coords (%s, %s)", e.response.status_code, latitude, longitude)
            return WeatherSnapshot(
                source=f"Open-Meteo API (HTTP {e.response.status_code} Error)",
                is_live=False
            )
        except Exception as e:
            logger.error("Unexpected error fetching weather: %s", str(e))
            return WeatherSnapshot(
                source=f"Open-Meteo API (Unavailable: {type(e).__name__})",
                is_live=False
            )
        finally:
            if should_close_client:
                await client.aclose()


# Singleton instance
weather_service = WeatherService()
