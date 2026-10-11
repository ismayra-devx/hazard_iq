"""
Tests for Weather service, caching, fallback resilience, and endpoint.
"""

import pytest
import httpx
from unittest.mock import AsyncMock, patch
from httpx import ASGITransport, AsyncClient, Response

from app.main import app
from app.services.weather_service import WeatherService


@pytest.mark.asyncio
async def test_weather_service_successful_mock():
    mock_payload = {
        "current": {
            "time": "2026-10-11T12:00",
            "temperature_2m": 37.5,
            "relative_humidity_2m": 48.0,
            "precipitation": 0.0,
            "wind_speed_10m": 12.4
        }
    }

    service = WeatherService(base_url="https://api.open-meteo.com/v1/forecast")
    mock_client = AsyncMock()
    req = httpx.Request("GET", "https://api.open-meteo.com/v1/forecast")
    mock_client.get.return_value = Response(200, json=mock_payload, request=req)

    snapshot = await service.get_weather(28.6139, 77.2090, client=mock_client)
    assert snapshot.temperature_celsius == 37.5
    assert snapshot.relative_humidity_percentage == 48.0
    assert snapshot.precipitation_mm == 0.0
    assert snapshot.wind_speed_kmh == 12.4
    assert snapshot.is_live is True
    assert "Open-Meteo" in snapshot.source


@pytest.mark.asyncio
async def test_weather_service_timeout_resilience():
    service = WeatherService(base_url="https://api.open-meteo.com/v1/forecast")
    mock_client = AsyncMock()
    mock_client.get.side_effect = httpx.TimeoutException("Connection timed out")

    # Should not raise exception; must return graceful snapshot
    snapshot = await service.get_weather(28.6139, 77.2090, client=mock_client)
    assert snapshot.is_live is False
    assert "Timeout" in snapshot.source
    assert snapshot.temperature_celsius is None


@pytest.mark.asyncio
async def test_weather_service_invalid_coordinates():
    service = WeatherService()
    snapshot = await service.get_weather(999.0, 999.0)
    assert snapshot.is_live is False
    assert "Invalid Coordinates" in snapshot.source


@pytest.mark.asyncio
async def test_weather_caching_behavior():
    mock_payload = {
        "current": {
            "time": "2026-10-11T12:00",
            "temperature_2m": 32.0,
            "relative_humidity_2m": 55.0,
            "precipitation": 1.2,
            "wind_speed_10m": 8.0
        }
    }

    service = WeatherService()
    mock_client = AsyncMock()
    req = httpx.Request("GET", "https://api.open-meteo.com/v1/forecast")
    mock_client.get.return_value = Response(200, json=mock_payload, request=req)

    # First call - fetches from network
    snap1 = await service.get_weather(28.6139, 77.2090, client=mock_client)
    assert mock_client.get.call_count == 1
    assert snap1.temperature_celsius == 32.0

    # Second call for same or nearby coords - served from cache without network call
    snap2 = await service.get_weather(28.6139, 77.2090, client=mock_client)
    assert mock_client.get.call_count == 1  # No additional network call
    assert snap2.temperature_celsius == 32.0


@pytest.mark.asyncio
async def test_weather_api_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/weather/current?latitude=28.6139&longitude=77.2090")
        assert response.status_code == 200
        data = response.json()
        assert "source" in data
        assert "is_live" in data
