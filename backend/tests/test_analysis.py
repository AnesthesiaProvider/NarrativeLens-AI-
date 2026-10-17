"""Tests for text analysis, batch analysis, and image analysis endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_analyze_text_single(client: AsyncClient):
    """Test single text analysis classification and token explanation."""
    payload = {
        "text": "This is a completely normal and friendly message.",
        "explain": True,
    }
    response = await client.post("/api/analysis/text", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "predicted_label" in data
    assert "confidence" in data
    assert "class_probabilities" in data
    assert data["predicted_label"] in ("normal", "offensive", "hate", "neutral", "safe", "nothate")
    assert "explanation" in data


@pytest.mark.asyncio
async def test_analyze_batch(client: AsyncClient):
    """Test batch text analysis."""
    payload = {
        "items": [
            {"id": "msg-1", "text": "Hello world!"},
            {"id": "msg-2", "text": "This is another sample sentence."},
        ],
        "explain": False,
    }
    response = await client.post("/api/analysis/batch", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert data["successful"] == 2
    assert data["failed"] == 0
    assert len(data["results"]) == 2
    assert data["results"][0]["id"] == "msg-1"
    assert data["results"][0]["result"]["predicted_label"] is not None


@pytest.mark.asyncio
async def test_analyze_empty_text_validation(client: AsyncClient):
    """Test 422 error when submitting empty text."""
    payload = {"text": "   "}
    response = await client.post("/api/analysis/text", json=payload)
    assert response.status_code == 422
