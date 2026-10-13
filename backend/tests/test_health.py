"""Tests for health probe, root metadata, and ML model status endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_root_endpoint(client: AsyncClient):
    """Test service root endpoint metadata."""
    response = await client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "online"
    assert "NarrativeLens" in data["service"]


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    """Test health check status returns valid response."""
    response = await client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "db_connected" in data
    assert "redis_connected" in data
    assert "timestamp" in data


@pytest.mark.asyncio
async def test_models_status(client: AsyncClient):
    """Test model manager status endpoint."""
    response = await client.get("/api/models/status")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "models" in data
    assert isinstance(data["models"], list)
    assert len(data["models"]) >= 3
    model_ids = [m["model_id"] for m in data["models"]]
    assert any("hate-speech" in mid for mid in model_ids)
