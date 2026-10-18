"""Tests for narrative web scraping, social media analysis, and truth verification endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_scrape_narrative_endpoint(client: AsyncClient):
    """Test live multi-platform narrative scraper and fact verification."""
    payload = {
        "query": "artificial intelligence safety regulations",
        "max_items_per_source": 3,
    }
    response = await client.post("/api/narratives/scrape-narrative", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert "query" in data
    assert "sources_searched" in data
    assert "verdict_summary" in data
    assert "overall_status" in data["verdict_summary"]
    assert "truth_score" in data["verdict_summary"]
    assert "claims" in data
    assert len(data["claims"]) > 0
    assert "collected_documents" in data
    assert "toxicity_overview" in data


@pytest.mark.asyncio
async def test_scrape_narrative_validation_empty(client: AsyncClient):
    """Test validation when neither query nor url is provided."""
    payload = {"query": "   ", "article_url": ""}
    response = await client.post("/api/narratives/scrape-narrative", json=payload)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_list_evidence_citations(client: AsyncClient):
    """Test listing evidence citations with pagination."""
    response = await client.get("/api/evidence")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
