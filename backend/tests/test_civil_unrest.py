"""Unit and integration tests for Civil Unrest Event Extraction & Forecasting."""

import pytest
from httpx import AsyncClient

from app.schemas.civil_unrest import (
    CivilUnrestPostInput,
    EventType,
    TemporalStatus,
    ThreatLevel,
)
from app.services.civil_unrest_service import civil_unrest_service


@pytest.mark.asyncio
async def test_heuristic_event_extraction_protest_and_tactics():
    """Verify that noisy social media text correctly extracts landmarks, gear, and escalation markers."""
    post = CivilUnrestPostInput(
        text="🚨 URGENT: Everyone assemble at Central Station Plaza TOMORROW at 5:00 PM! We are shutting down the train lines and blocking the bridge. Bring umbrellas and laser pointers! #MetroShutdown",
        platform="telegram",
        location_hint="Chicago, IL",
    )
    result = civil_unrest_service._extract_with_heuristics(post)

    assert result.primary_event_type in [EventType.PROTEST, EventType.BLOCKADE]
    assert result.timeline.call_to_action is True
    assert "assemble at Central Station Plaza" in (result.timeline.call_to_action_text or "")
    assert result.timeline.temporal_status == TemporalStatus.IMMINENT
    assert any("Umbrellas" in t for t in result.escalation.protective_gear_or_tactics)
    assert any("Laser" in t for t in result.escalation.protective_gear_or_tactics)
    assert result.escalation.escalation_score >= 0.4
    assert result.forecast.overall_unrest_probability >= 0.45


@pytest.mark.asyncio
async def test_heuristic_event_extraction_riot_curfew():
    """Verify that violent riot and curfew defiance markers trigger severe/critical threat levels."""
    post = CivilUnrestPostInput(
        text="Defy the curfew tonight at 10 PM in front of the 4th Precinct. Bring respirators and makeshift shields, teargas canisters are already loaded. Block the exits with dumpsters and Molotovs! 🔥",
        platform="reddit",
    )
    result = civil_unrest_service._extract_with_heuristics(post)

    assert result.primary_event_type in [EventType.RIOT, EventType.CURFEW_DEFIANCE]
    assert result.escalation.weapons_or_clash_risk is True
    assert result.escalation.threat_level in [ThreatLevel.SEVERE, ThreatLevel.CRITICAL]
    assert result.escalation.escalation_score >= 0.65
    assert result.forecast.violence_propensity >= 0.5


@pytest.mark.asyncio
async def test_api_scenarios_endpoint(client: AsyncClient):
    """Verify GET /api/civil-unrest/scenarios returns pre-loaded OSINT scenarios."""
    response = await client.get("/api/civil-unrest/scenarios")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 3
    assert "title" in data[0]
    assert "text" in data[0]


@pytest.mark.asyncio
async def test_api_indicators_endpoint(client: AsyncClient):
    """Verify GET /api/civil-unrest/indicators returns taxonomy and schema info."""
    response = await client.get("/api/civil-unrest/indicators")
    assert response.status_code == 200
    data = response.json()
    assert "event_types" in data
    assert "threat_levels" in data
    assert "protest" in data["event_types"]
    assert "critical" in data["threat_levels"]


@pytest.mark.asyncio
async def test_api_extract_endpoint(client: AsyncClient):
    """Verify POST /api/civil-unrest/extract executes analysis and returns structured schema."""
    payload = {
        "text": "Everyone meet at Parliament Square on Saturday at noon to protest the austerity budget. Bring banners and megaphones.",
        "platform": "twitter",
        "location_hint": "London, UK",
    }
    response = await client.post("/api/civil-unrest/extract", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "event_id" in data
    assert "primary_event_type" in data
    assert "actors" in data
    assert "location" in data
    assert "timeline" in data
    assert "escalation" in data
    assert "forecast" in data
    assert data["timeline"]["call_to_action"] is True
