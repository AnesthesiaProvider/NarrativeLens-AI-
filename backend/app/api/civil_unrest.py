"""API Router for Civil Unrest Event Extraction & Escalation Forecasting."""

from __future__ import annotations

import logging
from typing import Any, Dict, List
import httpx
from fastapi import APIRouter, HTTPException, status

from app.core.config import settings
from app.schemas.civil_unrest import (
    CivilUnrestAnalysisResult,
    CivilUnrestBatchInput,
    CivilUnrestPostInput,
    CivilUnrestScenarioItem,
)
from app.services.civil_unrest_service import civil_unrest_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/civil-unrest", tags=["Civil Unrest & Escalation Forecasting"])


@router.post(
    "/extract",
    response_model=CivilUnrestAnalysisResult,
    status_code=status.HTTP_200_OK,
    summary="Extract Structured Civil Unrest Event & Forecast",
    description="Uses dynamic prompt-engineered LLM (Ollama) with OSINT heuristic fallback to extract events, actors, locations, timelines, and escalation indicators.",
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
    summary="Get Configured OSINT Scenarios",
    description="Returns pre-loaded and user-added noisy social media post scenarios from the dynamic repository.",
)
async def get_sample_scenarios() -> List[Dict[str, Any]]:
    """Return scenarios dynamically loaded from JSON file."""
    return civil_unrest_service.get_scenarios()


@router.post(
    "/scenarios",
    response_model=Dict[str, Any],
    status_code=status.HTTP_201_CREATED,
    summary="Add a Custom OSINT Scenario",
    description="Dynamically adds a new scenario to the monitored intelligence library.",
)
async def add_custom_scenario(scenario: CivilUnrestScenarioItem) -> Dict[str, Any]:
    """Save a custom scenario into the dynamic scenario catalog."""
    try:
        return civil_unrest_service.add_scenario(scenario)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save scenario: {str(exc)}",
        )


@router.get(
    "/models",
    response_model=List[str],
    status_code=status.HTTP_200_OK,
    summary="List Available Ollama Models",
    description="Discovers locally available LLM models installed in Ollama.",
)
async def list_available_models() -> List[str]:
    """Query Ollama daemon for available local models."""
    base_url = getattr(settings, "OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            resp = await client.get(f"{base_url}/api/tags")
            if resp.status_code == 200:
                data = resp.json()
                models = [m.get("name") for m in data.get("models", []) if m.get("name")]
                if models:
                    return models
    except Exception:
        pass
    # Default fallback models
    return ["qwen3:4b", "llama3.1:8b", "mistral:7b", "gemma2:9b", "OSINT-Dynamic-Heuristic-V2"]


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
        "prompt_architecture": "Few-Shot Chain-of-Thought with Strict JSON Schema Enforcement",
    }
