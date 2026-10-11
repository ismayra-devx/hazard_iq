"""
Tests for Health and Root endpoints.
"""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_health_check_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "app_name" in data
        assert "version" in data
        assert "environment" in data
        assert "services" in data
        assert "weather_service" in data["services"]
        assert "policy_engine" in data["services"]


@pytest.mark.asyncio
async def test_root_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "online"
        assert "/docs" in data["docs_url"]
