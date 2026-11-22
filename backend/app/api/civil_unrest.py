"""API Router for Civil Unrest Event Extraction & Escalation Forecasting."""

from __future__ import annotations

import logging
from typing import Any, Dict, List
from fastapi import APIRouter, HTTPException, status

from app.schemas.civil_unrest import (
    CivilUnrestAnalysisResult,
    CivilUnrestBatchInput,
    CivilUnrestPostInput,
)
from app.services.civil_unrest_service import civil_unrest_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/civil-unrest", tags=["Civil Unrest & Escalation Forecasting"])


@router.post(
    "/extract",
    response_model=CivilUnrestAnalysisResult,
    status_code=status.HTTP_200_OK,
    summary="Extract Structured Civil Unrest Event & Forecast",
    description="Uses few-shot prompt-engineered Ollama LLM with OSINT heuristic fallback to extract events, actors, locations, timelines, and escalation indicators.",
)
async def extract_civil_unrest(post: CivilUnrestPostInput) -> CivilUnrestAnalysisResult:
    """Analyze a single social media post for civil unrest signals."""
    try:
        return await civil_unrest_service.analyze_single_post(post)
    except Exception as exc:
        logger.error(f"Error extracting civil unrest signals: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to extract civil unrest event intelligence: {str(exc)}",
        )


@router.post(
    "/batch",
    response_model=Dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Batch Social Media Stream Analysis for Unrest Signals",
    description="Aggregates and correlates multiple social media posts into a synthesized civil unrest dossier.",
)
async def analyze_batch_unrest(batch: CivilUnrestBatchInput) -> Dict[str, Any]:
    """Analyze a collection of posts for coordinated unrest mobilization."""
    try:
        return await civil_unrest_service.analyze_batch(batch)
    except Exception as exc:
        logger.error(f"Error analyzing batch civil unrest: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to analyze civil unrest batch: {str(exc)}",
        )


@router.get(
    "/scenarios",
    response_model=List[Dict[str, Any]],
    status_code=status.HTTP_200_OK,
    summary="Get Pre-Configured OSINT Scenarios",
    description="Returns pre-loaded noisy social media post scenarios for immediate live evaluation and demonstration.",
)
async def get_sample_scenarios() -> List[Dict[str, Any]]:
    """Return pre-configured realistic OSINT scenarios for live demonstration."""
    return [
        {
            "id": "scenario-1",
            "title": "Metropolitan Transit Hub Blockade & Clash Risk",
            "category": "Direct Action / Blockade",
            "platform": "telegram",
            "author": "@MetroDirectAction",
            "location_hint": "Chicago, IL",
            "text": "🚨 URGENT CALL TO ACTION: Everyone assemble at Central Station Plaza TOMORROW at 5:00 PM! We are shutting down the inbound train lines and blocking the Michigan Ave bridge. Bring umbrellas, eye wash (milk/saline), and laser pointers. No peace until the fare hikes are repealed. Cops are already mobilizing riot units, join our backup Signal group for live scout alerts! #MetroShutdown #OccupyTheTracks",
        },
        {
            "id": "scenario-2",
            "title": "General Labor Strike & Picket March",
            "category": "Labor Action / Strike",
            "platform": "twitter",
            "author": "AlliedSanitationWorkers",
            "location_hint": "Philadelphia, PA",
            "text": "Sanitation & Transit Union members: The wildcat strike is ON starting this Friday at 6:00 AM outside City Hall. All municipal workers walk out. We will march down Broad Street to the Mayor's office. Keep it completely disciplined and non-violent, wear union vests and bring whistles. Stand united! #PhillyGeneralStrike",
        },
        {
            "id": "scenario-3",
            "title": "Emergency Curfew Defiance & Nocturnal Clashes",
            "category": "Riot / Curfew Defiance",
            "platform": "reddit",
            "author": "NightOwl_88",
            "location_hint": "Atlanta, GA",
            "text": "They declared a 9 PM curfew thinking that would silence us?! Absolutely not. Defy the curfew tonight at 10 PM in front of the 4th Precinct. Bring respirators and makeshift shields, teargas canisters are already loaded on their tactical trucks. Block the exits with dumpsters and scooters. We aren't backing down tonight! 🔥",
        },
        {
            "id": "scenario-4",
            "title": "Counter-Protest Flashpoint at State Capitol",
            "category": "Counter-Protest / Flashmob",
            "platform": "telegram",
            "author": "PatriotFrontlineChannel",
            "location_hint": "Lansing, MI",
            "text": "Rumor has it opposition agitators are occupying the State Capitol steps this Saturday afternoon at 1 PM. Patriots, assemble on the opposite lawn at 12:30 PM with megaphones and flags. Do not let them intimidate our legislators. Stay in buddy pairs, record everything on video, and watch out for provocations.",
        },
    ]


@router.get(
    "/indicators",
    response_model=Dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Get Civil Unrest Indicator Taxonomy",
    description="Returns the taxonomy of tactical indicators, event types, and threat levels used in forecasting.",
)
async def get_indicators_taxonomy() -> Dict[str, Any]:
    """Return the structured indicator taxonomy and prompt engineering schema."""
    return {
        "event_types": [
            "protest",
            "riot",
            "strike",
            "blockade",
            "march",
            "counter_protest",
            "boycott",
            "clash",
            "flashmob",
            "curfew_defiance",
            "civil_disobedience",
        ],
        "threat_levels": ["low", "moderate", "high", "severe", "critical"],
        "tactical_indicators": [
            "Weapons & Projectile Propensity",
            "Protective Gear & Defensive Countermeasures (Gas Masks, Umbrellas, Shields)",
            "Critical Physical Infrastructure Targeting (Railways, Highways, Government Plazas)",
            "Encrypted Tactical Command & Control (Signal/Telegram channels, Radio Scanners)",
            "Temporal Mobilization Urgency (Active, Imminent <24h, Scheduled)",
        ],
        "prompt_architecture": "Dual-Candidate Structured JSON with Chain-of-Thought Tactical Extraction",
    }
