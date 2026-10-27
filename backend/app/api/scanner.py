"""Universal web scraping API endpoints.

Accepts any URL (Reddit, Twitter/X, 4chan, news articles, blogs, forums)
and routes it to the appropriate platform scraper. All scraped content
is then classified through the XLM-RoBERTa + Ollama LLM + CLIP pipeline.
"""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.ml.model_manager import model_manager
from app.services.comment_hate_detector_service import CommentHateDetectorService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/scanner", tags=["Universal Scanner"])


# ---------------------------------------------------------------------------
# Request / Response Schemas
# ---------------------------------------------------------------------------

class UniversalScanRequest(BaseModel):
    """Payload for the universal scanner endpoint."""
    target: str = Field(..., description="URL, subreddit, hashtag, or search query to scan.")
    max_items: int = Field(50, ge=1, le=200, description="Maximum items to scrape and analyze.")
    platform: Optional[str] = Field(None, description="Override auto-detection: reddit, twitter, 4chan, web, youtube")
    download_images: bool = Field(True, description="Whether to download and analyze attached images via CLIP.")


class ScannedItemResult(BaseModel):
    """Analysis result for a single scraped document."""
    doc_id: str
    doc_type: str
    source_platform: str
    source_url: str
    author: str
    text: str
    title: str = ""
    score: int = 0
    published_at: Optional[str] = None

    # Classification
    label: str
    confidence: float
    is_hate: bool
    is_offensive: bool
    explanation_tokens: List[Dict[str, Any]] = []

    # Multi-attribute enrichment
    target_group: Optional[Dict[str, Any]] = None
    harm_type: Optional[Dict[str, Any]] = None
    severity: Optional[Dict[str, Any]] = None
    is_below_threshold: bool = False
    recommended_action: Optional[str] = None

    # LLM reasoning (if available)
    llm_reasoning: Optional[Dict[str, Any]] = None

    # Image analysis (if images attached)
    has_images: bool = False
    image_classification: Optional[Dict[str, Any]] = None

    # Platform-specific
    subreddit: str = ""
    board: str = ""
    hashtags: List[str] = []
    reply_count: int = 0


class UniversalScanResponse(BaseModel):
    """Full response from the universal scanner."""
    target: str
    detected_platform: str
    target_type: str

    # Source metadata
    source_metadata: Dict[str, Any] = {}

    # Aggregate metrics
    total_scanned: int
    hate_count: int
    offensive_count: int
    neutral_count: int
    toxicity_rate: float
    hate_rate: float

    # Advisory
    risk_level: str
    risk_label: str
    risk_color: str
    advisories: List[str]

    # LLM info
    llm_active: bool = False
    llm_model: Optional[str] = None
    executive_explanation: Optional[Dict[str, Any]] = None

    # Results
    flagged_items: List[ScannedItemResult]
    all_items: List[ScannedItemResult]

    # Timing
    scrape_duration_seconds: float
    analysis_duration_seconds: float
    scanned_at: str

    # Available scrapers
    available_platforms: List[str]

    # Errors
    errors: List[str] = []


class PlatformStatusResponse(BaseModel):
    """Status of all available platform scrapers."""
    available_platforms: List[str]
    platform_details: Dict[str, Dict[str, Any]]


# ---------------------------------------------------------------------------
# Helper: classify + LLM enrich
# ---------------------------------------------------------------------------

_detector = CommentHateDetectorService()


def _classify_text(text: str) -> Dict[str, Any]:
    """Classify a text segment using enriched hate speech detection pipeline."""
    result = _detector._classify_text(text)
    # Attach enrichment via model manager's enriched prediction
    try:
        from app.ml.enrichment.enrichment_pipeline import enrich_prediction
        raw_pred = {
            "predicted_label": result.get("raw_label", "normal"),
            "confidence": result.get("confidence", 0.0),
        }
        enriched = enrich_prediction(text, raw_pred)
        result["enriched"] = enriched
    except Exception:
        result["enriched"] = None
    return result


async def _llm_enrich(title: str, text: str, label: str) -> Optional[Dict[str, Any]]:
    """Call Ollama LLM for contextual reasoning on flagged items."""
    return await _detector.explain_with_local_llm(title, text, label)


async def _explain_page_with_llm(
    title: str,
    text: str,
    total_items: int,
    hate_count: int,
    offensive_count: int,
) -> Optional[Dict[str, Any]]:
    """Generate an executive summary and rhetorical breakdown of the extracted page using Ollama LLaMA."""
    from app.core.config import settings

    if not getattr(settings, "ENABLE_LLM_CONTEXT_ARBITER", True):
        return None

    base_url = getattr(settings, "OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
    model_name = getattr(settings, "OLLAMA_MODEL", "qwen3:4b")
    req_timeout = float(getattr(settings, "OLLAMA_TIMEOUT", 30.0))

    prompt = (
        f"You are an expert NLP safety and narrative intelligence analyst.\n"
        f"Title / Context: \"{title}\"\n"
        f"Extracted Page Content: \"{text[:1800]}\"\n"
        f"Metrics: Scanned {total_items} segments, detected {hate_count} hate speech flags and {offensive_count} offensive flags.\n\n"
        "Task: Conduct deep analytical reasoning on this content. Return a JSON object with this exact structure:\n"
        "{\n"
        "  \"summary\": \"2-3 clear sentences summarizing the core message or topic of the extracted page.\",\n"
        "  \"narrative_stance\": \"Analysis of the author's narrative, tone, and rhetorical framing.\",\n"
        "  \"targeted_groups\": \"Identity or demographic groups discussed, criticized, or targeted (or 'None').\",\n"
        "  \"hate_speech_verdict\": \"Final assessment on whether this page contains targeted hate speech, general profanity, or safe free expression.\"\n"
        "}"
    )

    try:
        import httpx
        import re
        async with httpx.AsyncClient(timeout=req_timeout) as client:
            resp = await client.post(
                f"{base_url}/api/generate",
                json={
                    "model": model_name,
                    "prompt": prompt,
                    "stream": False,
                    "format": "json",
                    "options": {"temperature": 0.1, "num_predict": 700},
                },
            )
            if resp.status_code == 200:
                data = resp.json()
                raw_response = data.get("response", "").strip()
                raw_thinking = data.get("thinking", "").strip()

                parsed = {}
                for candidate in (raw_response, raw_thinking):
                    if not candidate:
                        continue
                    try:
                        parsed = json.loads(candidate)
                        if isinstance(parsed, dict) and "summary" in parsed:
                            break
                    except Exception:
                        pass
                    match = re.search(r"\{[\s\S]*?\}", candidate)
                    if match:
                        try:
                            candidate_obj = json.loads(match.group(0))
                            if isinstance(candidate_obj, dict) and "summary" in candidate_obj:
                                parsed = candidate_obj
                                break
                        except Exception:
                            pass

                if parsed:
                    parsed["model"] = model_name
                    return parsed
    except Exception as exc:
        logger.debug(f"Page-level Ollama explanation skipped: {exc}")
    return None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get(
    "/platforms",
    response_model=PlatformStatusResponse,
    summary="List Available Scrapers",
    description="Returns which platform scrapers are available and their status.",
)
async def list_platforms() -> PlatformStatusResponse:
    """List all registered platform scrapers."""
    try:
        from app.services.scrapers.router import universal_scraper
        platforms = universal_scraper.available_platforms
    except Exception:
        platforms = []

    details = {}
    for p in platforms:
        details[p] = {
            "status": "available",
            "requires_credentials": p in ("reddit", "telegram"),
        }

    return PlatformStatusResponse(
        available_platforms=platforms,
        platform_details=details,
    )


@router.post(
    "/scan",
    response_model=UniversalScanResponse,
    status_code=status.HTTP_200_OK,
    summary="Universal Scan",
    description="Scrape any URL or target and run full hate speech analysis pipeline.",
)
async def universal_scan(payload: UniversalScanRequest) -> UniversalScanResponse:
    """Scrape content from any supported platform and classify every item."""
    target = payload.target.strip()
    if not target:
        raise HTTPException(status_code=400, detail="Target cannot be empty.")

    # 1. Import and run the universal scraper
    try:
        from app.services.scrapers.router import universal_scraper
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Universal scraper module not available: {exc}",
        )

    detected_platform = payload.platform or universal_scraper.detect_platform(target)

    # Scrape
    scrape_start = time.perf_counter()
    try:
        scraped = await universal_scraper.scrape(
            target,
            max_items=payload.max_items,
            platform=payload.platform,
            download_images=payload.download_images,
        )
    except Exception as exc:
        logger.error(f"Scrape failed for '{target}': {exc}")
        raise HTTPException(
            status_code=502,
            detail=f"Scraping failed for '{target}': {exc}",
        )
    scrape_duration = time.perf_counter() - scrape_start

    if not scraped.documents and not scraped.main_document:
        raise HTTPException(
            status_code=404,
            detail=f"No content scraped from '{target}'. Errors: {scraped.errors}",
        )

    # 2. Classify every document
    analysis_start = time.perf_counter()

    all_docs = []
    if scraped.main_document:
        all_docs.append(scraped.main_document)
    all_docs.extend(scraped.documents)

    # Determine the "title" context for LLM (from main doc or first doc)
    context_title = ""
    if scraped.main_document and scraped.main_document.title:
        context_title = scraped.main_document.title
    elif all_docs and all_docs[0].title:
        context_title = all_docs[0].title

    results: List[ScannedItemResult] = []
    hate_count = 0
    offensive_count = 0
    neutral_count = 0

    for doc in all_docs:
        text_to_classify = f"{doc.title} {doc.text}".strip() if doc.title else doc.text
        if not text_to_classify or len(text_to_classify.strip()) < 3:
            continue

        # Run XLM-RoBERTa classification in thread pool
        try:
            eval_res = await asyncio.to_thread(_classify_text, text_to_classify[:512])
        except Exception as exc:
            logger.warning(f"Classification failed for doc {doc.doc_id}: {exc}")
            eval_res = {
                "label": "Neutral", "raw_label": "normal", "confidence": 0.5,
                "is_hate": False, "is_offensive": False, "explanation_tokens": [],
            }

        if eval_res["is_hate"]:
            hate_count += 1
        elif eval_res["is_offensive"]:
            offensive_count += 1
        else:
            neutral_count += 1

        # Image analysis via CLIP (if images available)
        image_result = None
        has_images = bool(doc.image_bytes_list)
        if has_images and payload.download_images:
            try:
                clip_probs = await asyncio.to_thread(
                    model_manager.predict_multimodal, doc.image_bytes_list[0]
                )
                image_result = {"clip_categories": clip_probs}
            except Exception as exc:
                logger.debug(f"CLIP analysis skipped for doc {doc.doc_id}: {exc}")

        item = ScannedItemResult(
            doc_id=doc.doc_id,
            doc_type=doc.doc_type,
            source_platform=doc.source_platform,
            source_url=doc.source_url,
            author=doc.author,
            text=doc.text[:2000],
            title=doc.title,
            score=doc.score,
            published_at=doc.published_at.isoformat() if doc.published_at else None,
            label=eval_res["label"],
            confidence=eval_res["confidence"],
            is_hate=eval_res["is_hate"],
            is_offensive=eval_res["is_offensive"],
            explanation_tokens=eval_res.get("explanation_tokens", []),
            # Multi-attribute enrichment fields
            target_group=eval_res.get("enriched", {}).get("target_group") if eval_res.get("enriched") else None,
            harm_type=eval_res.get("enriched", {}).get("harm_type") if eval_res.get("enriched") else None,
            severity=eval_res.get("enriched", {}).get("severity") if eval_res.get("enriched") else None,
            is_below_threshold=eval_res.get("enriched", {}).get("is_below_threshold", False) if eval_res.get("enriched") else False,
            recommended_action=(
                eval_res.get("enriched", {}).get("severity", {}).get("recommended_action")
                if eval_res.get("enriched") else None
            ),
            has_images=has_images,
            image_classification=image_result,
            subreddit=doc.subreddit,
            board=doc.board,
            hashtags=doc.hashtags,
            reply_count=doc.reply_count,
        )
        results.append(item)

    # 3. LLM enrichment on top flagged items
    flagged = [r for r in results if r.is_hate or r.is_offensive]
    flagged.sort(key=lambda x: (1 if x.is_hate else 0, x.confidence, x.score), reverse=True)

    llm_active = False
    for item in flagged[:5]:
        try:
            llm_res = await _llm_enrich(context_title, item.text, item.label)
            if llm_res:
                item.llm_reasoning = llm_res
                llm_active = True
        except Exception:
            pass

    # 3b. Page-level executive LLaMA explanation
    page_text_sample = "\n\n".join(
        f"[{d.doc_type.upper()}] {d.title + ': ' if d.title else ''}{d.text}"
        for d in scraped.documents[:6]
    )
    exec_explanation = None
    try:
        exec_explanation = await _explain_page_with_llm(
            title=context_title,
            text=page_text_sample,
            total_items=len(results),
            hate_count=hate_count,
            offensive_count=offensive_count,
        )
        if exec_explanation:
            llm_active = True
    except Exception as exc:
        logger.debug(f"Executive page explanation error: {exc}")

    analysis_duration = time.perf_counter() - analysis_start

    # 4. Build advisory
    total_scanned = len(results)
    toxic_count = hate_count + offensive_count
    toxicity_rate = round(toxic_count / total_scanned, 4) if total_scanned > 0 else 0.0
    hate_rate = round(hate_count / total_scanned, 4) if total_scanned > 0 else 0.0

    if hate_rate >= 0.20 or hate_count >= 5:
        risk_level, risk_label, color = "CRITICAL_HARASSMENT", "Critical Harassment & High Hate Density", "red"
    elif toxicity_rate >= 0.30 or hate_count >= 2:
        risk_level, risk_label, color = "HIGH_TOXICITY", "High Toxicity & Hostile Content", "orange"
    elif toxicity_rate >= 0.12 or offensive_count >= 3:
        risk_level, risk_label, color = "MODERATE_TENSION", "Moderate Flaming / Divisive Rhetoric", "amber"
    else:
        risk_level, risk_label, color = "LOW_RISK", "Constructive / Low Risk Discussion", "emerald"

    advisories: List[str] = []
    if llm_active:
        from app.core.config import settings
        advisories.append(
            f"🤖 Local LLM Context Arbiter Active ({getattr(settings, 'OLLAMA_MODEL', 'qwen3:4b')}): "
            f"Contextual nuance analyzed via Ollama."
        )
    advisories.append(f"📊 Scanned {total_scanned} items from {detected_platform} in {scrape_duration:.1f}s scrape + {analysis_duration:.1f}s analysis.")

    if hate_count > 0:
        advisories.append(
            f"⚠️ Active Hate Speech: {hate_count} item(s) ({hate_rate*100:.1f}%) contain direct hate speech."
        )
    else:
        advisories.append("✅ Zero direct hate speech detected in scanned content.")

    if toxicity_rate > 0.25:
        advisories.append(f"🔥 High Hostility Index: {toxicity_rate*100:.1f}% of content is toxic or offensive.")
    elif toxicity_rate > 0.10:
        advisories.append(f"⚖️ Polarized Discourse: {toxicity_rate*100:.1f}% of content involves aggressive language.")

    if flagged:
        top = flagged[0]
        advisories.append(
            f"📌 Most flagged item by @{top.author} (score: {top.score}): "
            f"\"{top.text[:100]}...\" — {top.label}"
        )

    return UniversalScanResponse(
        target=target,
        detected_platform=detected_platform,
        target_type=scraped.target_type,
        source_metadata=scraped.source_metadata,
        total_scanned=total_scanned,
        hate_count=hate_count,
        offensive_count=offensive_count,
        neutral_count=neutral_count,
        toxicity_rate=toxicity_rate,
        hate_rate=hate_rate,
        risk_level=risk_level,
        risk_label=risk_label,
        risk_color=color,
        advisories=advisories,
        llm_active=llm_active,
        llm_model=getattr(settings, "OLLAMA_MODEL", None) if llm_active else None,
        executive_explanation=exec_explanation,
        flagged_items=flagged,
        all_items=results,
        scrape_duration_seconds=round(scrape_duration, 2),
        analysis_duration_seconds=round(analysis_duration, 2),
        scanned_at=datetime.now(timezone.utc).isoformat(),
        available_platforms=universal_scraper.available_platforms,
        errors=scraped.errors,
    )
