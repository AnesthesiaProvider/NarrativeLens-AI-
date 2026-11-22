"""Schemas for Civil Unrest Event Extraction and Escalation Forecasting."""

from __future__ import annotations

from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class EventType(str, Enum):
    PROTEST = "protest"
    RIOT = "riot"
    STRIKE = "strike"
    BLOCKADE = "blockade"
    MARCH = "march"
    COUNTER_PROTEST = "counter_protest"
    BOYCOTT = "boycott"
    CLASH = "clash"
    FLASHMOB = "flashmob"
    CURFEW_DEFIANCE = "curfew_defiance"
    CIVIL_DISOBEDIENCE = "civil_disobedience"
    UNKNOWN = "unknown"


class TemporalStatus(str, Enum):
    IMMINENT = "imminent"       # Scheduled within 24 hours
    SCHEDULED = "scheduled"     # Planned for future date (>24 hours)
    ACTIVE = "active"           # Currently occurring / live updates
    HISTORICAL = "historical"   # Already concluded
    UNSPECIFIED = "unspecified"


class ThreatLevel(str, Enum):
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    SEVERE = "severe"
    CRITICAL = "critical"


class MobilizationRadius(str, Enum):
    LOCAL = "local"
    CITYWIDE = "citywide"
    REGIONAL = "regional"
    NATIONWIDE = "nationwide"


class ExtractedActors(BaseModel):
    organizers: List[str] = Field(default_factory=list, description="Organizers, coalitions, factions, or key hashtags behind the call")
    targets: List[str] = Field(default_factory=list, description="Target entities, public figures, government agencies, or corporations")
    counter_actors: List[str] = Field(default_factory=list, description="Opposing groups, counter-protesters, or rival factions")
    security_forces: List[str] = Field(default_factory=list, description="Law enforcement, riot squads, or private security mentioned")
    demographics: List[str] = Field(default_factory=list, description="Targeted or participating demographics (e.g., students, workers, transit unions)")


class ExtractedLocation(BaseModel):
    raw_location: str = Field(..., description="Raw extracted text location mention")
    landmark_or_venue: Optional[str] = Field(None, description="Specific gathering point (e.g. City Hall Plaza, 5th Ave Bridge)")
    city: Optional[str] = Field(None, description="City name")
    state_region: Optional[str] = Field(None, description="State, province, or district")
    country: Optional[str] = Field(None, description="Country")
    geo_specificity: str = Field("medium", description="'high' (exact address/intersection), 'medium' (city/district), 'low' (country/general)")


class ExtractedTimeline(BaseModel):
    raw_time_expression: str = Field(..., description="Raw temporal mention e.g., 'Tomorrow at 4pm', 'This Friday noon'")
    normalized_target_time: Optional[str] = Field(None, description="Estimated target ISO or formatted timestamp")
    temporal_status: TemporalStatus = Field(TemporalStatus.UNSPECIFIED, description="Temporal urgency status")
    call_to_action: bool = Field(False, description="Whether this post contains an explicit assembly or mobilization call")
    call_to_action_text: Optional[str] = Field(None, description="Direct imperative command e.g., 'Assemble at Central Station'")


class EscalationIndicators(BaseModel):
    threat_level: ThreatLevel = Field(ThreatLevel.LOW, description="Estimated threat level")
    escalation_score: float = Field(..., ge=0.0, le=1.0, description="Escalation propensity metric (0.0=peaceful assembly, 1.0=imminent violent riot)")
    weapons_or_clash_risk: bool = Field(False, description="Mentions of weapons, projectiles, clashes, or violent intent")
    protective_gear_or_tactics: List[str] = Field(default_factory=list, description="Tactical gear: gas masks, laser pointers, umbrella shields, etc.")
    infrastructure_targeting: List[str] = Field(default_factory=list, description="Targeted physical assets e.g. highways, rail transit, government buildings")
    virality_velocity: str = Field("moderate", description="'low', 'rising', 'surging', 'explosive'")
    tactical_coordination_flags: List[str] = Field(default_factory=list, description="Coordination tactics: encrypted channels, scanner radios, scout signals")


class UnrestForecast(BaseModel):
    overall_unrest_probability: float = Field(..., ge=0.0, le=1.0, description="Overall probability of disruptive or violent unrest occurring")
    mobilization_radius: MobilizationRadius = Field(MobilizationRadius.LOCAL, description="Geographic scope of mobilization")
    predicted_peak_window: str = Field(..., description="Forecasted window of peak unrest or disruption")
    violence_propensity: float = Field(..., ge=0.0, le=1.0, description="Likelihood of physical violence or property destruction")
    recommended_interventions: List[str] = Field(default_factory=list, description="Recommended de-escalation, public safety, or monitoring actions")
    analytical_rationale: str = Field(..., description="Synthesized reasoning explaining the prediction")


class CivilUnrestPostInput(BaseModel):
    text: str = Field(..., min_length=3, description="Noisy social media post text, thread, or report")
    platform: Optional[str] = Field("generic", description="Social platform source e.g. twitter, reddit, telegram, 4chan")
    author: Optional[str] = Field(None, description="Author handle or display name")
    timestamp: Optional[str] = Field(None, description="Post publication timestamp")
    location_hint: Optional[str] = Field(None, description="Optional geographic context or user profile location")


class CivilUnrestBatchInput(BaseModel):
    posts: List[CivilUnrestPostInput] = Field(..., min_items=1, description="List of social media posts to analyze together")
    investigation_id: Optional[str] = Field(None, description="Optional associated investigation ID")
    region_filter: Optional[str] = Field(None, description="Optional region context filter")


class CivilUnrestAnalysisResult(BaseModel):
    event_id: str = Field(..., description="Unique analysis record identifier")
    primary_event_type: EventType = Field(..., description="Categorized primary event type")
    event_summary: str = Field(..., description="One-sentence structured summary of the unrest event")
    actors: ExtractedActors = Field(..., description="Extracted key actors and entities")
    location: ExtractedLocation = Field(..., description="Extracted geographical coordinates and venue")
    timeline: ExtractedTimeline = Field(..., description="Extracted temporal timeline and call-to-action")
    escalation: EscalationIndicators = Field(..., description="Escalation metrics and tactical indicators")
    forecast: UnrestForecast = Field(..., description="AI-assisted predictive unrest forecast")
    model_used: str = Field(..., description="Model powering extraction (e.g. qwen3:4b or hybrid heuristic engine)")
    prompt_technique: str = Field(..., description="Prompt engineering technique utilized")
    raw_text_snippet: str = Field(..., description="Analyzed post excerpt")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Extraction confidence score")
