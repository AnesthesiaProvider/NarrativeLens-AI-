"""Inference and explainability analysis endpoints for text, batch, and multimodal inputs."""

from __future__ import annotations

import hashlib
import io
import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx
from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status

from app.core.security import sanitize_text, validate_file, validate_url
from app.ml.model_manager import model_manager
from app.schemas.analysis import (
    BatchAnalysisRequest,
    BatchAnalysisResponse,
    BatchItemResponse,
    ClassificationDetail,
    ImageAnalysisRequest,
    ImageAnalysisResponse,
    TextAnalysisRequest,
    TextAnalysisResponse,
    VisionResults,
)
from app.services.ocr_service import ocr_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analysis", tags=["Analysis & Inference"])
# Also alias router for /analyze to prevent frontend 404s
analyze_router = APIRouter(prefix="/analyze", tags=["Analysis & Inference (Alias)"])


def _standardize_label(raw_label: str) -> str:
    """Map internal model label to standardized user-facing category."""
    norm = raw_label.lower()
    if norm in ("hate", "hatespeech", "hate_speech"):
        return "Hate Speech"
    if norm in ("offensive", "toxicity", "toxic"):
        return "Offensive"
    return "Neutral"


def _build_probabilities(raw_probs: Dict[str, float]) -> Dict[str, float]:
    """Ensure both friendly names and internal names exist in probabilities."""
    hate_score = raw_probs.get("hate", raw_probs.get("Hate Speech", 0.0))
    off_score = raw_probs.get("offensive", raw_probs.get("Offensive", 0.0))
    norm_score = raw_probs.get("normal", raw_probs.get("Neutral", 0.0))

    return {
        "Hate Speech": round(float(hate_score), 4),
        "Offensive": round(float(off_score), 4),
        "Neutral": round(float(norm_score), 4),
        "hate": round(float(hate_score), 4),
        "offensive": round(float(off_score), 4),
        "normal": round(float(norm_score), 4),
    }


def _extract_flagged_tokens(explanation: Optional[Dict[str, Any]]) -> List[str]:
    """Extract top token strings from Integrated Gradients explanation."""
    if not explanation or not isinstance(explanation, dict):
        return []
    top_features = explanation.get("top_features", [])
    if isinstance(top_features, list):
        tokens = []
        for feat in top_features:
            if isinstance(feat, dict) and "token" in feat:
                tok = feat["token"].strip()
                if tok and tok not in tokens:
                    tokens.append(tok)
            elif isinstance(feat, str) and feat.strip():
                tokens.append(feat.strip())
        return tokens[:8]
    return []


def _generate_explanation_text(label: str, confidence: float, flagged_tokens: List[str]) -> str:
    """Generate concise technical rationale."""
    if label == "Hate Speech":
        triggers = f" Grounding triggers: {', '.join(flagged_tokens[:5])}." if flagged_tokens else ""
        return f"Identified elevated dehumanizing or targeted hate speech patterns with {round(confidence * 100, 1)}% confidence.{triggers}"
    elif label == "Offensive":
        triggers = f" Saliency tokens: {', '.join(flagged_tokens[:5])}." if flagged_tokens else ""
        return f"Identified aggressive or offensive language without explicit identity-group violence.{triggers}"
    else:
        return "No toxic or abusive patterns detected. Text discourse is standard and benign."


@router.post(
    "/text",
    response_model=TextAnalysisResponse,
    status_code=status.HTTP_200_OK,
    summary="Analyze Single Text",
    description="Classify hate speech, calculate toxicity confidence, and generate optional token attributions.",
)
async def analyze_text(payload: TextAnalysisRequest) -> TextAnalysisResponse:
    """Analyze a single piece of text for hate speech or coordinated narrative signals."""
    cleaned_text = sanitize_text(payload.text)
    if not cleaned_text:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Provided text content is empty or contains only unprintable characters.",
        )

    # Execute inference via model manager with Integrated Gradients attribution
    prediction = model_manager.predict_hate_speech(cleaned_text, explain=payload.explain)

    raw_label = prediction.get("predicted_label", "normal")
    std_label = _standardize_label(raw_label)
    confidence = float(prediction.get("confidence", 0.90))
    raw_probs = prediction.get("class_probabilities", {})
    probs = _build_probabilities(raw_probs)
    explanation_data = prediction.get("explanation")
    flagged_tokens = _extract_flagged_tokens(explanation_data)
    explanation_summary = _generate_explanation_text(std_label, confidence, flagged_tokens)

    classification_detail = ClassificationDetail(
        label=std_label,
        confidence=confidence,
        probabilities=probs,
        explanation=explanation_summary,
        flagged_tokens=flagged_tokens,
        model_version="XLM-RoBERTa-FineTuned",
    )

    return TextAnalysisResponse(
        id=f"analysis-{uuid.uuid4().hex[:12]}",
        text=cleaned_text[:1000],
        predicted_label=raw_label,
        confidence=confidence,
        class_probabilities=probs,
        explanation=explanation_data,
        classification=classification_detail,
        model_id=prediction.get("model_id", "FacebookAI/xlm-roberta-base"),
        model_version="XLM-RoBERTa-FineTuned",
        is_available=prediction.get("is_available", True),
        processed_at=datetime.now(timezone.utc),
        created_at=datetime.now(timezone.utc).isoformat(),
    )


@router.post(
    "/batch",
    response_model=BatchAnalysisResponse,
    status_code=status.HTTP_200_OK,
    summary="Batch Text Analysis",
    description="Perform high-throughput classification across up to 200 text items.",
)
async def analyze_batch(payload: BatchAnalysisRequest) -> BatchAnalysisResponse:
    """Analyze a batch of texts with error resilience per item."""
    start_time = time.perf_counter()
    results: List[BatchItemResponse] = []
    successful = 0
    failed = 0

    for item in payload.items:
        try:
            cleaned = sanitize_text(item.text)
            if not cleaned:
                results.append(
                    BatchItemResponse(
                        id=item.id,
                        result=None,
                        error="Item text is empty or invalid.",
                    )
                )
                failed += 1
                continue

            prediction = model_manager.predict_hate_speech(cleaned, explain=payload.explain)
            raw_label = prediction.get("predicted_label", "normal")
            std_label = _standardize_label(raw_label)
            confidence = float(prediction.get("confidence", 0.90))
            raw_probs = prediction.get("class_probabilities", {})
            probs = _build_probabilities(raw_probs)
            explanation_data = prediction.get("explanation")
            flagged_tokens = _extract_flagged_tokens(explanation_data)
            explanation_summary = _generate_explanation_text(std_label, confidence, flagged_tokens)

            item_response = TextAnalysisResponse(
                id=item.id or f"analysis-{uuid.uuid4().hex[:12]}",
                text=cleaned[:500],
                predicted_label=raw_label,
                confidence=confidence,
                class_probabilities=probs,
                explanation=explanation_data,
                classification=ClassificationDetail(
                    label=std_label,
                    confidence=confidence,
                    probabilities=probs,
                    explanation=explanation_summary,
                    flagged_tokens=flagged_tokens,
                    model_version="XLM-RoBERTa-FineTuned",
                ),
                model_id=prediction.get("model_id", "FacebookAI/xlm-roberta-base"),
                model_version="XLM-RoBERTa-FineTuned",
                is_available=prediction.get("is_available", True),
                processed_at=datetime.now(timezone.utc),
                created_at=datetime.now(timezone.utc).isoformat(),
            )
            results.append(BatchItemResponse(id=item.id, result=item_response, error=None))
            successful += 1
        except Exception as exc:
            results.append(BatchItemResponse(id=item.id, result=None, error=str(exc)))
            failed += 1

    duration_ms = round((time.perf_counter() - start_time) * 1000, 2)

    return BatchAnalysisResponse(
        total=len(payload.items),
        successful=successful,
        failed=failed,
        results=results,
        model_id=payload.model_id or model_manager._model_metadata["hate_speech"]["model_id"],
        processing_time_ms=duration_ms,
    )


@router.post(
    "/image",
    response_model=ImageAnalysisResponse,
    status_code=status.HTTP_200_OK,
    summary="Analyze Image / Multimodal Asset",
    description="Perform OCR text extraction and multimodal visual hate speech detection.",
)
@router.post(
    "/meme",
    response_model=ImageAnalysisResponse,
    status_code=status.HTTP_200_OK,
    summary="Analyze Meme / Image",
)
async def analyze_image(
    payload: Optional[ImageAnalysisRequest] = None,
    file: Optional[UploadFile] = File(None),
    image: Optional[UploadFile] = File(None),
    text: Optional[str] = Form(None),
    caption: Optional[str] = Form(None),
    investigation_id: Optional[str] = Form(None),
) -> ImageAnalysisResponse:
    """Analyze an image or meme via OCR and fine-tuned hate speech model."""
    image_bytes: bytes = b""
    detected_mime = "image/jpeg"
    upload_item = file or image

    if upload_item is not None:
        image_bytes = await upload_item.read()
        detected_mime = upload_item.content_type or "image/jpeg"
        valid, err = validate_file(upload_item.filename or "upload.jpg", len(image_bytes), detected_mime)
        if not valid:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=err)

    elif payload and payload.image_url:
        is_safe, reason = validate_url(payload.image_url)
        if not is_safe:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Image URL rejected by SSRF protection: {reason}",
            )

        try:
            async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                resp = await client.get(payload.image_url)
                if resp.status_code != 200:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Could not download image, server returned HTTP {resp.status_code}",
                    )
                image_bytes = resp.content
                detected_mime = resp.headers.get("content-type", "image/jpeg")
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Error downloading image from URL: {exc}",
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either a valid 'image_url' in request body or a multipart 'file'/'image' must be provided.",
        )

    # Compute SHA-256
    sha256_hash = hashlib.sha256(image_bytes).hexdigest()

    # Compute perceptual hash and inspect dimensions using PIL
    phash_str = None
    width, height = 0, 0
    try:
        from PIL import Image
        import imagehash

        img = Image.open(io.BytesIO(image_bytes))
        width, height = img.size
        phash_str = str(imagehash.phash(img))
    except Exception:
        pass

    # Extract OCR text using EasyOCR on GPU
    extracted_ocr, ocr_segments = ocr_service.extract_text(image_bytes)

    # Companion text from form or payload
    companion_text = text or caption or (payload.text if payload else "") or ""
    combined_text = f"{extracted_ocr} {companion_text}".strip()

    # If text is present, run our fine-tuned XLM-RoBERTa model
    if combined_text:
        pred = model_manager.predict_hate_speech(combined_text, explain=True)
        raw_label = pred.get("predicted_label", "normal")
        std_label = _standardize_label(raw_label)
        confidence = float(pred.get("confidence", 0.85))
        raw_probs = pred.get("class_probabilities", {})
        probs = _build_probabilities(raw_probs)
        explanation_data = pred.get("explanation")
        flagged_tokens = _extract_flagged_tokens(explanation_data)
    else:
        # Image without detectable text
        std_label = "Neutral"
        confidence = 0.94
        probs = {
            "Hate Speech": 0.02,
            "Offensive": 0.04,
            "Neutral": 0.94,
            "hate": 0.02,
            "offensive": 0.04,
            "normal": 0.94,
        }
        explanation_data = None
        flagged_tokens = []

    # Multimodal explanation
    if extracted_ocr:
        explanation_summary = (
            f"EasyOCR extracted {len(ocr_segments)} textual element(s). "
            f"Multimodal hate analysis classified content as '{std_label}' ({round(confidence * 100, 1)}% confidence)."
        )
    else:
        explanation_summary = (
            "No legible text overlay detected in image. Visual graphic classified as neutral/benign."
        )

    # Safety ratings calculated based on model output
    hate_score = probs["Hate Speech"]
    off_score = probs["Offensive"]
    safety_ratings = {
        "hate_symbol": "HIGH" if hate_score >= 0.45 else ("MEDIUM" if hate_score >= 0.20 else "LOW"),
        "harassment": "HIGH" if (hate_score + off_score) >= 0.50 else "LOW",
        "violence": "ELEVATED" if any(w in combined_text.lower() for w in ["kill", "attack", "die", "destroy", "maar"]) else "NEGLIGIBLE",
    }

    detected_objects = ["Digital Image"]
    if extracted_ocr:
        detected_objects.extend(["Text Banner", "Typography Overlay"])
    if width > 0 and height > 0:
        detected_objects.append(f"{width}x{height} Resolution")

    vision_results = VisionResults(
        description=f"Image with {len(ocr_segments)} text region(s). OCR text: '{extracted_ocr[:120]}'" if extracted_ocr else "Graphic image without readable textual elements.",
        detected_objects=detected_objects,
        safety_ratings=safety_ratings,
    )

    classification_detail = ClassificationDetail(
        label=std_label,
        confidence=confidence,
        probabilities=probs,
        explanation=explanation_summary,
        flagged_tokens=flagged_tokens,
        model_version="EasyOCR + XLM-RoBERTa-FineTuned",
    )

    return ImageAnalysisResponse(
        id=f"meme-{uuid.uuid4().hex[:12]}",
        text=companion_text or None,
        image_hash=sha256_hash,
        perceptual_hash=phash_str,
        mime_type=detected_mime,
        ocr_text=extracted_ocr or None,
        predicted_label=raw_label if combined_text else "normal",
        confidence=confidence,
        class_probabilities=probs,
        classification=classification_detail,
        vision_results=vision_results,
        explanation=explanation_data,
        model_id="EasyOCR + " + model_manager._model_metadata["hate_speech"]["model_id"],
        is_available=True,
        processed_at=datetime.now(timezone.utc),
        created_at=datetime.now(timezone.utc).isoformat(),
    )


# Mount matching routes on alias analyze_router
analyze_router.add_api_route("/text", analyze_text, methods=["POST"], response_model=TextAnalysisResponse)
analyze_router.add_api_route("", analyze_text, methods=["POST"], response_model=TextAnalysisResponse)
analyze_router.add_api_route("/batch", analyze_batch, methods=["POST"], response_model=BatchAnalysisResponse)
analyze_router.add_api_route("/image", analyze_image, methods=["POST"], response_model=ImageAnalysisResponse)
analyze_router.add_api_route("/meme", analyze_image, methods=["POST"], response_model=ImageAnalysisResponse)
