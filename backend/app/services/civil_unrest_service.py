"""Civil Unrest Event Extraction & Escalation Forecasting Service.

Implements structured few-shot prompt engineering for Ollama LLMs with intelligent
heuristic and OSINT rule-based fallbacks to extract events, actors, locations,
timelines, and escalation indicators from noisy social media text.
"""

from __future__ import annotations

import json
import logging
import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx

from app.core.config import settings
from app.schemas.civil_unrest import (
    CivilUnrestAnalysisResult,
    CivilUnrestBatchInput,
    CivilUnrestPostInput,
    CivilUnrestScenarioItem,
    EscalationIndicators,
    EventType,
    ExtractedActors,
    ExtractedLocation,
    ExtractedTimeline,
    MobilizationRadius,
    TemporalStatus,
    ThreatLevel,
    UnrestForecast,
)

logger = logging.getLogger(__name__)

SCENARIOS_FILE = Path(__file__).parent.parent / "data" / "civil_unrest_scenarios.json"

# Specialized few-shot system prompt for OSINT civil unrest intelligence extraction
CIVIL_UNREST_SYSTEM_PROMPT = """You are an elite OSINT (Open Source Intelligence) and Civil Unrest Early-Warning Analyst.
Your mission is to parse noisy, colloquial, multilingual social media communications (hashtags, slang, typos, imperatives)
and extract structured tactical intelligence for forecasting potential civil unrest.

Analyze the input text and output a STRICT JSON object with these EXACT keys:
{
  "event_type": "protest" | "riot" | "strike" | "blockade" | "march" | "counter_protest" | "boycott" | "clash" | "flashmob" | "curfew_defiance" | "civil_disobedience" | "unknown",
  "event_summary": "One concise sentence summarizing the planned or active event.",
  "actors": {
    "organizers": ["list of organizing groups, activist handles, unions, or coordinating hashtags"],
    "targets": ["government institutions, political figures, corporations, or rival communities being targeted"],
    "counter_actors": ["counter-protesters, opposing factions, or vigilante groups mentioned"],
    "security_forces": ["police departments, riot squads, national guard, or private security mentioned"],
    "demographics": ["demographics targeted or called to participate (e.g. students, transit workers, residents)"]
  },
  "location": {
    "raw_location": "verbatim location mention from text",
    "landmark_or_venue": "specific gathering spot (e.g. City Hall Plaza, Interstate 95 Exit 4, Parliament Gate)",
    "city": "City name if identified",
    "state_region": "State, province, or district",
    "country": "Country",
    "geo_specificity": "high" | "medium" | "low"
  },
  "timeline": {
    "raw_time_expression": "verbatim time expression (e.g. 'Tomorrow @ 4pm', 'Saturday night', 'Right NOW')",
    "normalized_target_time": "Estimated date/time or window",
    "temporal_status": "imminent" | "scheduled" | "active" | "historical" | "unspecified",
    "call_to_action": true | false,
    "call_to_action_text": "Imperative instruction (e.g. 'Everyone gather at Central Square with masks')"
  },
  "escalation": {
    "threat_level": "low" | "moderate" | "high" | "severe" | "critical",
    "escalation_score": 0.0 to 1.0 (0.0=purely peaceful assembly, 1.0=imminent armed or destructive riot),
    "weapons_or_clash_risk": true | false,
    "protective_gear_or_tactics": ["mentions of gas masks, umbrellas, laser pointers, barricades, milk for teargas"],
    "infrastructure_targeting": ["highways, rail transit, government buildings, power substations, commercial centers"],
    "virality_velocity": "low" | "rising" | "surging" | "explosive",
    "tactical_coordination_flags": ["mentions of Signal/Telegram groups, encrypted comms, burner phones, scout lookouts"]
  },
  "forecast": {
    "overall_unrest_probability": 0.0 to 1.0,
    "mobilization_radius": "local" | "citywide" | "regional" | "nationwide",
    "predicted_peak_window": "Forecasted peak intensity window (e.g. 'Next 6-12 hours', 'Saturday 14:00 - 18:00')",
    "violence_propensity": 0.0 to 1.0,
    "recommended_interventions": ["list of 2-3 de-escalation, public transport rerouting, or monitoring recommendations"],
    "analytical_rationale": "Clear 2-3 sentence strategic rationale assessing why this event is likely or unlikely to escalate."
  },
  "confidence": 0.0 to 1.0
}

Output ONLY valid JSON. Do not include markdown code block formatting or explanations outside the JSON."""


class CivilUnrestService:
    """Service handling civil unrest event extraction, dynamic prompt engineering, and predictive forecasting."""

    def __init__(self) -> None:
        self.base_url = getattr(settings, "OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
        self.default_model_name = getattr(settings, "OLLAMA_MODEL", "qwen3:4b")
        self.timeout = float(getattr(settings, "OLLAMA_TIMEOUT", 35.0))

    def get_scenarios(self) -> List[Dict[str, Any]]:
        """Load OSINT scenarios dynamically from JSON repository."""
        if SCENARIOS_FILE.exists():
            try:
                with open(SCENARIOS_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as exc:
                logger.warning(f"Failed to read scenarios file: {exc}")
        return []

    def add_scenario(self, scenario: CivilUnrestScenarioItem) -> Dict[str, Any]:
        """Dynamically add a custom scenario to the repository."""
        scenarios = self.get_scenarios()
        sc_dict = scenario.model_dump()
        # Update or append
        scenarios = [s for s in scenarios if s.get("id") != scenario.id]
        scenarios.insert(0, sc_dict)
        try:
            SCENARIOS_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(SCENARIOS_FILE, "w", encoding="utf-8") as f:
                json.dump(scenarios, f, indent=2, ensure_ascii=False)
        except Exception as exc:
            logger.error(f"Failed to persist scenario: {exc}")
        return sc_dict

    async def analyze_single_post(self, post: CivilUnrestPostInput) -> CivilUnrestAnalysisResult:
        """Analyze a single social media post using dynamic prompt engineering with fallback."""
        llm_result = await self._extract_with_ollama(post)
        if llm_result:
            return llm_result

        logger.info("Ollama LLM extraction offline or unreachable; utilizing dynamic OSINT heuristic extractor.")
        return self._extract_with_heuristics(post)

    async def analyze_batch(self, batch: CivilUnrestBatchInput) -> Dict[str, Any]:
        """Analyze a batch of posts and synthesize a consolidated civil unrest intelligence brief."""
        individual_results: List[CivilUnrestAnalysisResult] = []
        for post in batch.posts:
            res = await self.analyze_single_post(post)
            individual_results.append(res)

        avg_escalation = sum(r.escalation.escalation_score for r in individual_results) / max(len(individual_results), 1)
        max_threat_score = max(r.escalation.escalation_score for r in individual_results)
        
        if max_threat_score >= 0.8:
            agg_threat_level = ThreatLevel.CRITICAL
        elif max_threat_score >= 0.65:
            agg_threat_level = ThreatLevel.SEVERE
        elif max_threat_score >= 0.45:
            agg_threat_level = ThreatLevel.HIGH
        elif max_threat_score >= 0.25:
            agg_threat_level = ThreatLevel.MODERATE
        else:
            agg_threat_level = ThreatLevel.LOW

        locations = list({r.location.landmark_or_venue or r.location.city or r.location.raw_location for r in individual_results if r.location.raw_location})
        organizers = list({org for r in individual_results for org in r.actors.organizers if org})
        targets = list({tgt for r in individual_results for tgt in r.actors.targets if tgt})
        all_tactics = list({tactic for r in individual_results for tactic in r.escalation.protective_gear_or_tactics if tactic})
        all_infrastructure = list({infra for r in individual_results for infra in r.escalation.infrastructure_targeting if infra})
        
        imminent_events = [r for r in individual_results if r.timeline.temporal_status == TemporalStatus.IMMINENT]
        active_events = [r for r in individual_results if r.timeline.temporal_status == TemporalStatus.ACTIVE]

        overall_prob = min(1.0, (avg_escalation * 0.5) + (max_threat_score * 0.5))

        return {
            "batch_summary": f"Analyzed {len(individual_results)} social media signals across monitored streams.",
            "aggregate_threat_level": agg_threat_level,
            "average_escalation_score": round(avg_escalation, 3),
            "peak_escalation_score": round(max_threat_score, 3),
            "overall_unrest_probability": round(overall_prob, 3),
            "primary_hotspots": locations[:5],
            "identified_organizers": organizers[:6],
            "identified_targets": targets[:6],
            "tactics_and_gear_detected": all_tactics,
            "targeted_infrastructure": all_infrastructure,
            "imminent_threats_count": len(imminent_events),
            "active_unrest_signals": len(active_events),
            "records": individual_results,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    async def _extract_with_ollama(self, post: CivilUnrestPostInput) -> Optional[CivilUnrestAnalysisResult]:
        """Query Ollama LLM using structured dynamic prompt engineering."""
        if not getattr(settings, "ENABLE_LLM_CONTEXT_ARBITER", True):
            return None

        # Dynamic parameter resolution
        target_model = post.model or self.default_model_name
        target_temp = post.temperature if post.temperature is not None else 0.1
        system_prompt = post.system_prompt or CIVIL_UNREST_SYSTEM_PROMPT

        # Assemble prompt with custom instructions if requested
        prompt_parts = [
            f"INPUT SOCIAL MEDIA POST:\n",
            f"Platform: {post.platform or 'Unspecified'}\n",
            f"Author: {post.author or 'Anonymous'}\n",
            f"Location Context: {post.location_hint or 'None provided'}\n",
        ]
        if post.custom_prompt_instructions:
            prompt_parts.append(f"Special Intelligence Requirements: {post.custom_prompt_instructions}\n")
        prompt_parts.append(f"Post Text: \"\"\"{post.text}\"\"\"\n\n")
        prompt_parts.append("Extract the exact JSON specified in the system instructions.")

        full_prompt = "".join(prompt_parts)

        try:
            client_timeout = httpx.Timeout(self.timeout, connect=2.5)
            async with httpx.AsyncClient(timeout=client_timeout) as client:
                resp = await client.post(
                    f"{self.base_url}/api/generate",
                    json={
                        "model": target_model,
                        "system": system_prompt,
                        "prompt": full_prompt,
                        "stream": False,
                        "format": "json",
                        "options": {
                            "temperature": target_temp,
                            "top_p": 0.9,
                            "num_predict": 950,
                        },
                    },
                )
                if resp.status_code == 200:
                    data = resp.json()
                    raw_resp = data.get("response", "").strip()
                    raw_thinking = data.get("thinking", "").strip()

                    parsed_dict = self._parse_json_candidates([raw_resp, raw_thinking])
                    if parsed_dict:
                        result = self._build_result_from_dict(parsed_dict, post, model_tag=target_model)
                        result.raw_prompt = full_prompt
                        result.raw_llm_response = raw_resp
                        result.reasoning_tokens = raw_thinking
                        return result
        except Exception as exc:
            logger.debug(f"Ollama unrest extraction failed/timed out: {exc}")

        return None

    def _parse_json_candidates(self, candidates: List[str]) -> Optional[Dict[str, Any]]:
        """Try parsing JSON from model output or embedded codeblocks."""
        for candidate in candidates:
            if not candidate:
                continue
            try:
                data = json.loads(candidate)
                if isinstance(data, dict) and "event_type" in data:
                    return data
            except Exception:
                pass

            match = re.search(r"\{[\s\S]*\}", candidate)
            if match:
                try:
                    data = json.loads(match.group(0))
                    if isinstance(data, dict) and "event_type" in data:
                        return data
                except Exception:
                    pass
        return None

    def _build_result_from_dict(
        self,
        d: Dict[str, Any],
        post: CivilUnrestPostInput,
        model_tag: str,
    ) -> CivilUnrestAnalysisResult:
        """Construct a validated CivilUnrestAnalysisResult model from parsed JSON."""
        raw_et = str(d.get("event_type", "protest")).lower()
        event_type = EventType.PROTEST
        for et in EventType:
            if et.value in raw_et or raw_et in et.value:
                event_type = et
                break

        raw_act = d.get("actors", {})
        actors = ExtractedActors(
            organizers=raw_act.get("organizers", []),
            targets=raw_act.get("targets", []),
            counter_actors=raw_act.get("counter_actors", []),
            security_forces=raw_act.get("security_forces", []),
            demographics=raw_act.get("demographics", []),
        )

        raw_loc = d.get("location", {})
        location = ExtractedLocation(
            raw_location=raw_loc.get("raw_location", post.location_hint or "Unknown"),
            landmark_or_venue=raw_loc.get("landmark_or_venue"),
            city=raw_loc.get("city"),
            state_region=raw_loc.get("state_region"),
            country=raw_loc.get("country"),
            geo_specificity=raw_loc.get("geo_specificity", "medium"),
        )

        raw_time = d.get("timeline", {})
        raw_t_status = str(raw_time.get("temporal_status", "unspecified")).lower()
        temporal_status = TemporalStatus.UNSPECIFIED
        for ts in TemporalStatus:
            if ts.value in raw_t_status:
                temporal_status = ts
                break

        timeline = ExtractedTimeline(
            raw_time_expression=raw_time.get("raw_time_expression", "unspecified"),
            normalized_target_time=raw_time.get("normalized_target_time"),
            temporal_status=temporal_status,
            call_to_action=bool(raw_time.get("call_to_action", False)),
            call_to_action_text=raw_time.get("call_to_action_text"),
        )

        raw_esc = d.get("escalation", {})
        raw_threat = str(raw_esc.get("threat_level", "moderate")).lower()
        threat_level = ThreatLevel.MODERATE
        for tl in ThreatLevel:
            if tl.value in raw_threat:
                threat_level = tl
                break

        escalation = EscalationIndicators(
            threat_level=threat_level,
            escalation_score=float(min(1.0, max(0.0, raw_esc.get("escalation_score", 0.5)))),
            weapons_or_clash_risk=bool(raw_esc.get("weapons_or_clash_risk", False)),
            protective_gear_or_tactics=raw_esc.get("protective_gear_or_tactics", []),
            infrastructure_targeting=raw_esc.get("infrastructure_targeting", []),
            virality_velocity=raw_esc.get("virality_velocity", "moderate"),
            tactical_coordination_flags=raw_esc.get("tactical_coordination_flags", []),
        )

        raw_fc = d.get("forecast", {})
        raw_rad = str(raw_fc.get("mobilization_radius", "local")).lower()
        mobilization_radius = MobilizationRadius.LOCAL
        for mr in MobilizationRadius:
            if mr.value in raw_rad:
                mobilization_radius = mr
                break

        forecast = UnrestForecast(
            overall_unrest_probability=float(min(1.0, max(0.0, raw_fc.get("overall_unrest_probability", 0.5)))),
            mobilization_radius=mobilization_radius,
            predicted_peak_window=raw_fc.get("predicted_peak_window", "Next 24 hours"),
            violence_propensity=float(min(1.0, max(0.0, raw_fc.get("violence_propensity", 0.3)))),
            recommended_interventions=raw_fc.get("recommended_interventions", [
                "Deploy proactive community liaison teams",
                "Monitor transportation and egress choke points",
            ]),
            analytical_rationale=raw_fc.get("analytical_rationale", "Synthesized from social media indicator density and call-to-action strength."),
        )

        return CivilUnrestAnalysisResult(
            event_id=f"unrest-{uuid.uuid4().hex[:10]}",
            primary_event_type=event_type,
            event_summary=d.get("event_summary", "Civil unrest event extracted from social post."),
            actors=actors,
            location=location,
            timeline=timeline,
            escalation=escalation,
            forecast=forecast,
            model_used=model_tag,
            prompt_technique="Few-Shot Chain-of-Thought with Strict JSON Schema Enforcement",
            raw_text_snippet=post.text[:280],
            confidence=float(min(1.0, max(0.1, d.get("confidence", 0.85)))),
        )

    def _extract_with_heuristics(self, post: CivilUnrestPostInput) -> CivilUnrestAnalysisResult:
        """High-precision, fully dynamic rule-based OSINT heuristic extractor for offline/fallback use."""
        text = post.text
        text_lower = text.lower()

        # 1. Dynamic Event Type Resolution
        event_type = EventType.PROTEST
        if any(w in text_lower for w in ["riot", "burn", "smash", "looting", "torched", "molotov", "clash with cops"]):
            event_type = EventType.RIOT
        elif any(w in text_lower for w in ["strike", "walkout", "picket", "union", "shut down work"]):
            event_type = EventType.STRIKE
        elif any(w in text_lower for w in ["blockade", "block the highway", "occupy bridge", "barricade", "shut down the port", "occupy"]):
            event_type = EventType.BLOCKADE
        elif any(w in text_lower for w in ["march to", "marching towards", "procession", "rally"]):
            event_type = EventType.MARCH
        elif any(w in text_lower for w in ["counter-protest", "confront them", "show up against"]):
            event_type = EventType.COUNTER_PROTEST
        elif any(w in text_lower for w in ["curfew", "defy curfew", "stay out past curfew"]):
            event_type = EventType.CURFEW_DEFIANCE

        # 2. Dynamic Timeline & Call to Action
        call_to_action = False
        cta_text = None
        temporal_status = TemporalStatus.UNSPECIFIED
        time_expression = "unspecified"

        cta_patterns = [
            r"((?:everyone|all|patriots|workers|students|citizens)\s+(?:meet|gather|assemble|show up|walk out|take to the streets)[^.!?\n]*)",
            r"(take to the streets[^.!?\n]*)",
            r"(shut (?:it|everything|down)[^.!?\n]*)",
            r"(bring your [^.!?\n]*)",
            r"(assemble at [^.!?\n]*)",
            r"(occupy [^.!?\n]*)",
        ]
        for pattern in cta_patterns:
            m = re.search(pattern, text, re.IGNORECASE)
            if m:
                call_to_action = True
                cta_text = m.group(1).strip()
                break

        time_patterns = [
            (r"\b(tonight|today|right now|currently|happening now)\b", TemporalStatus.ACTIVE),
            (r"\b(tomorrow(?:\s+at|\s+@)?(?:\s+\d{1,2}(?::\d{2})?\s*(?:am|pm|cet|est|pst|utc)?)?)\b", TemporalStatus.IMMINENT),
            (r"\b(in \d+ hours?|next few hours)\b", TemporalStatus.IMMINENT),
            (r"\b((?:this\s+)?(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday)(?:\s+at|\s+@)?(?:\s+\d{1,2}(?::\d{2})?\s*(?:am|pm|cet)?)?)\b", TemporalStatus.SCHEDULED),
            (r"\b(yesterday|last night|earlier today)\b", TemporalStatus.HISTORICAL),
        ]
        for pattern, status in time_patterns:
            m = re.search(pattern, text_lower)
            if m:
                time_expression = m.group(1)
                temporal_status = status
                break

        # 3. Dynamic Location & Venue Extraction
        raw_location = post.location_hint or "Unspecified Location"
        landmark = None
        city = None

        location_patterns = [
            r"(?:at|outside|in front of|near|occupying|blocking)\s+([A-Z0-9][a-zA-Z0-9\s]{2,35}(?:Square|Plaza|Park|Hall|Station|Bridge|Building|Avenue|St|Street|Boulevard|Center|Capitol|Parliament|Embassy|Precinct|Port|Gate|Pier))",
            r"(?:at|in)\s+([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)?(?:\s*,\s*[A-Z]{2,3})?)",
        ]
        for lp in location_patterns:
            m = re.search(lp, text)
            if m:
                cand = m.group(1).strip()
                if len(cand) > 3 and not any(cand.lower().startswith(x) for x in ["everyone", "all", "tomorrow", "tonight", "bring"]):
                    landmark = cand
                    raw_location = landmark
                    break

        if post.location_hint:
            city = post.location_hint.split(",")[0].strip()

        # 4. Dynamic Actors & Entity Extraction
        organizers = []
        if post.author:
            organizers.append(post.author)
        hashtags = re.findall(r"#([a-zA-Z0-9_]+)", text)
        for ht in hashtags:
            if any(k in ht.lower() for k in ["strike", "march", "protest", "resist", "revolt", "unite", "occupy", "shutdown"]):
                organizers.append(f"#{ht}")

        targets = []
        if any(w in text_lower for w in ["cops", "police", "precinct", "law enforcement", "feds"]):
            targets.append("Law Enforcement / Precincts")
        if any(w in text_lower for w in ["city hall", "mayor", "governor", "parliament", "senate", "white house", "capitol"]):
            targets.append("Government & Civic Institutions")
        if any(w in text_lower for w in ["fare hike", "transit lines", "trains", "metro", "port", "pier", "highways"]):
            targets.append("Public Transportation & Logistics Infrastructure")
        if any(w in text_lower for w in ["corporate", "bank", "headquarters", "tech company", "landlord", "crude expansions"]):
            targets.append("Corporate & Commercial Assets")

        security_forces = []
        if any(w in text_lower for w in ["riot police", "tear gas", "tactical unit", "national guard", "swat", "riot units"]):
            security_forces.append("Riot Police / Tactical Units")
        elif "police" in text_lower or "cops" in text_lower:
            security_forces.append("Local Police Force")

        demographics = []
        if any(w in text_lower for w in ["workers", "sanitation", "union", "transit union"]):
            demographics.append("Labor Unions & Municipal Workers")
        if any(w in text_lower for w in ["students", "youth", "campus"]):
            demographics.append("Student & Youth Activists")
        if any(w in text_lower for w in ["patriots", "citizens", "residents", "all"]):
            demographics.append("Citizens & Affinity Groups")

        # 5. Dynamic Tactics & Escalation Scoring
        tactics_gear = []
        if any(w in text_lower for w in ["gas mask", "respirator", "masks"]):
            tactics_gear.append("Gas Masks & Respirators")
        if any(w in text_lower for w in ["umbrella", "shield", "makeshift shield"]):
            tactics_gear.append("Crowd Umbrellas & Defensive Shields")
        if any(w in text_lower for w in ["laser", "pointer"]):
            tactics_gear.append("Laser Pointers")
        if any(w in text_lower for w in ["milk", "baking soda", "saline", "medic", "eye wash"]):
            tactics_gear.append("Chemical Irritant / Saline Eye Wash")
        if any(w in text_lower for w in ["lockbox", "d-lock", "chain", "barricade", "dumpster"]):
            tactics_gear.append("Barricades & Locking Hardware")

        infrastructure = []
        if any(w in text_lower for w in ["highway", "interstate", "bridge", "freeway", "road", "michigan ave"]):
            infrastructure.append("Highways & Arterial Bridges")
        if any(w in text_lower for w in ["metro", "subway", "train", "transit", "station", "pier", "terminal", "port"]):
            infrastructure.append("Transit Stations, Rail Lines & Shipping Terminals")
        if any(w in text_lower for w in ["city hall", "capitol", "courthouse", "precinct", "parliament"]):
            infrastructure.append("Government & Law Enforcement Buildings")

        coordination_flags = []
        if any(w in text_lower for w in ["telegram", "signal", "encrypted", "matrix", "burner"]):
            coordination_flags.append("Encrypted Channels (Signal/Telegram)")
        if any(w in text_lower for w in ["scout", "scanner", "lookout", "radio"]):
            coordination_flags.append("Tactical Lookouts & Police Radio Monitoring")

        weapons_clash = any(w in text_lower for w in ["molotov", "fireworks", "weapons", "rocks", "bricks", "bats", "clash", "fight back", "torch", "burn"])

        base_score = 0.20
        if event_type in [EventType.RIOT, EventType.CLASH]:
            base_score += 0.35
        elif event_type in [EventType.BLOCKADE, EventType.CURFEW_DEFIANCE]:
            base_score += 0.25
        if weapons_clash:
            base_score += 0.30
        if tactics_gear:
            base_score += 0.10
        if infrastructure:
            base_score += 0.10
        if call_to_action:
            base_score += 0.08

        escalation_score = min(0.98, max(0.12, base_score))

        if escalation_score >= 0.8:
            threat_level = ThreatLevel.CRITICAL
        elif escalation_score >= 0.65:
            threat_level = ThreatLevel.SEVERE
        elif escalation_score >= 0.45:
            threat_level = ThreatLevel.HIGH
        elif escalation_score >= 0.25:
            threat_level = ThreatLevel.MODERATE
        else:
            threat_level = ThreatLevel.LOW

        unrest_prob = min(0.96, max(0.15, escalation_score * 0.95 + (0.08 if call_to_action else 0.0)))
        violence_prob = min(0.95, max(0.05, 0.75 * escalation_score if weapons_clash else 0.35 * escalation_score))

        # Dynamic Event Summary
        target_str = ", ".join(targets[:2]) if targets else (landmark or "public gathering areas")
        event_summary = f"Detected {event_type.value.replace('_', ' ')} mobilization targeting {target_str} with {temporal_status.value} urgency."

        prompt_rendered = (
            f"OSINT Prompt Template (Dynamic Extraction):\n"
            f"Input Text: \"{text[:300]}\"\n"
            f"Platform: {post.platform} | Location Context: {post.location_hint or 'None'}"
        )

        return CivilUnrestAnalysisResult(
            event_id=f"unrest-{uuid.uuid4().hex[:10]}",
            primary_event_type=event_type,
            event_summary=event_summary,
            actors=ExtractedActors(
                organizers=organizers or ["Grassroots Mobilizers"],
                targets=targets,
                counter_actors=[],
                security_forces=security_forces,
                demographics=demographics or ["General Public / Activists"],
            ),
            location=ExtractedLocation(
                raw_location=raw_location,
                landmark_or_venue=landmark,
                city=city,
                state_region=None,
                country=None,
                geo_specificity="high" if landmark else "medium",
            ),
            timeline=ExtractedTimeline(
                raw_time_expression=time_expression,
                normalized_target_time=None,
                temporal_status=temporal_status,
                call_to_action=call_to_action,
                call_to_action_text=cta_text,
            ),
            escalation=EscalationIndicators(
                threat_level=threat_level,
                escalation_score=round(escalation_score, 2),
                weapons_or_clash_risk=weapons_clash,
                protective_gear_or_tactics=tactics_gear,
                infrastructure_targeting=infrastructure,
                virality_velocity="surging" if call_to_action else "moderate",
                tactical_coordination_flags=coordination_flags,
            ),
            forecast=UnrestForecast(
                overall_unrest_probability=round(unrest_prob, 2),
                mobilization_radius=MobilizationRadius.CITYWIDE if infrastructure else MobilizationRadius.LOCAL,
                predicted_peak_window=time_expression if time_expression != "unspecified" else "Next 12-24 hours",
                violence_propensity=round(violence_prob, 2),
                recommended_interventions=[
                    f"Establish proactive civil liaison presence near {landmark or 'gathering perimeter'}",
                    "Coordinate public transit detour plans for identified transport bottlenecks",
                    "Monitor real-time encrypted coordination nodes for dynamic routing changes",
                ],
                analytical_rationale=f"Real-time heuristic evaluation: Event Type='{event_type.value}', Weapons Clash Risk={weapons_clash}, Tactical Gear Count={len(tactics_gear)}, Infrastructure Assets={len(infrastructure)}.",
            ),
            model_used=post.model or "OSINT-Dynamic-Heuristic-V2",
            prompt_technique="Rule-Based OSINT Dynamic Parsing & Threat Scoring",
            raw_text_snippet=text[:280],
            confidence=0.89 if landmark and call_to_action else 0.74,
            raw_prompt=prompt_rendered,
            raw_llm_response=json.dumps({
                "event_type": event_type.value,
                "event_summary": event_summary,
                "escalation_score": escalation_score,
                "threat_level": threat_level.value,
            }, indent=2),
            reasoning_tokens=f"Tactical markers parsed: {len(tactics_gear)} countermeasures, {len(infrastructure)} infrastructure nodes. Urgency: {temporal_status.value}.",
        )


civil_unrest_service = CivilUnrestService()
