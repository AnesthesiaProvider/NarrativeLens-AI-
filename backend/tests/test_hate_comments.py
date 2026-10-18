"""Tests for YouTube title and comment hate speech detection service and endpoint."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_scan_hate_comments_endpoint(client: AsyncClient):
    """Test POST /api/analysis/scan-hate-comments with a sample topic."""
    payload = {
        "target": "peace and unity speech",
        "max_comments": 3,
    }
    response = await client.post("/api/analysis/scan-hate-comments", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert "target" in data
    assert "metadata" in data
    assert "title_analysis" in data
    assert "metrics" in data
    assert "advisory" in data
    assert "what_you_need_to_know" in data["advisory"]
    assert len(data["advisory"]["what_you_need_to_know"]) > 0
    assert "flagged_comments" in data
    assert "all_comments" in data


@pytest.mark.asyncio
async def test_scan_hate_comments_validation_error(client: AsyncClient):
    """Test validation when target is empty."""
    payload = {"target": "   "}
    response = await client.post("/api/analysis/scan-hate-comments", json=payload)
    assert response.status_code == 400
