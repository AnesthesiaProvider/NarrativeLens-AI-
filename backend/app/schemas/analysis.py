"""Pydantic schemas for text, batch, and multimodal image analysis."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.schemas.enrichment import EnrichedAnalysis


class TokenAttribution(BaseModel):
    """Token or feature importance score from model explanation."""

    token: str = Field(..., description="Token, phrase, or feature name")
    score: float = Field(..., description="Attribution / SHAP importance weight")


class ClassificationDetail(BaseModel):
    """Nested classification details matching frontend specifications."""

    label: str = Field(..., description="Standardized label (e.g. Hate Speech, Offensive, Neutral)")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score")
    probabilities: Dict[str, float] = Field(
        default_factory=dict, description="Probabilities across classes"
    )
    explanation: Optional[str] = Field(None, description="Human-readable rationale")
    flagged_tokens: List[str] = Field(default_factory=list, description="Salient tokens or triggers")
    model_version: Optional[str] = Field("XLM-RoBERTa-FineTuned", description="Model version tag")


class VisionResults(BaseModel):
    """Multimodal vision reasoning results."""

    description: Optional[str] = Field(None, description="Visual description of the content")
    detected_objects: List[str] = Field(default_factory=list, description="Detected objects and themes")
    safety_ratings: Dict[str, str] = Field(default_factory=dict, description="Safety category ratings")


class TextAnalysisRequest(BaseModel):
    """Request payload for analyzing a single piece of text."""

    text: str = Field(..., min_length=1, description="Content to analyze")
    model_id: Optional[str] = Field(None, description="Specific model ID to use")
    model_type: Optional[str] = Field(None, description="Model type identifier")
    investigation_id: Optional[str] = Field(None, description="Associated investigation ID")
    explain: bool = Field(True, description="Whether to compute explainability/feature attributions")
    language: Optional[str] = Field("en", description="Optional text language code")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Custom metadata to associate")


class TextAnalysisResponse(BaseModel):
    """Analysis result for a single text document."""

    id: str = Field(default_factory=lambda: f"analysis-{uuid.uuid4().hex[:12]}")
    text: str = Field(..., description="Analyzed input text or snippet")
    predicted_label: str = Field(..., description="Predicted hate speech category or safe/neutral")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score")
    class_probabilities: Dict[str, float] = Field(
        default_factory=dict, description="Probabilities across all candidate classes"
    )
    explanation: Optional[Any] = Field(
        None, description="Integrated Gradients or token attribution explanation details"
    )
    classification: Optional[ClassificationDetail] = Field(
        None, description="Nested classification container for frontend compatibility"
    )
    model_id: str = Field(..., description="Identifier of the model used")
    model_version: Optional[str] = Field("XLM-RoBERTa-FineTuned", description="Model version")
    is_available: bool = Field(True, description="Indicates whether ML inference was performed")
    processed_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp of inference",
    )
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO formatted timestamp",
    )
    enriched: Optional[EnrichedAnalysis] = Field(
        None,
        description=(
            "Multi-attribute enrichment: target group, harm type, severity rating, "
            "and calibrated confidence threshold result."
        ),
    )
    llm_reasoning: Optional[Dict[str, Any]] = Field(
        None,
        description="Qualitative contextual rationale and identity analysis from local Ollama LLM arbiter.",
    )


class BatchItemRequest(BaseModel):
    """Single item within a batch request."""

    id: Optional[str] = Field(None, description="Client-supplied correlation identifier")
    text: str = Field(..., min_length=1, description="Text snippet to analyze")
    language: Optional[str] = Field("en", description="Language code")


class BatchAnalysisRequest(BaseModel):
    """Request payload for processing multiple texts in a single batch."""

    items: List[BatchItemRequest] = Field(..., min_length=1, max_length=200, description="Items to analyze")
    model_id: Optional[str] = Field(None, description="Optional override model ID")
    explain: bool = Field(False, description="Whether to include explanations for each item")


class BatchItemResponse(BaseModel):
    """Result for an individual item inside a batch response."""

    id: Optional[str] = None
    result: Optional[TextAnalysisResponse] = None
    error: Optional[str] = None


class BatchAnalysisResponse(BaseModel):
    """Response payload containing results for a batch analysis request."""

    total: int = Field(..., description="Total items submitted")
    successful: int = Field(..., description="Successfully processed count")
    failed: int = Field(..., description="Failed items count")
    results: List[BatchItemResponse] = Field(..., description="Item-level analysis results")
    model_id: str = Field(..., description="Model ID used")
    processing_time_ms: float = Field(0.0, description="Total batch processing latency in milliseconds")


class ImageAnalysisRequest(BaseModel):
    """Request payload for image and multimodal analysis."""

    image_url: Optional[str] = Field(None, description="Publicly accessible HTTP/HTTPS image URL")
    text: Optional[str] = Field(None, description="Companion text, caption, or context")
    investigation_id: Optional[str] = Field(None, description="Associated investigation ID")
    model_id: Optional[str] = Field(None, description="Optional multimodal model ID")
    ocr_enabled: bool = Field(True, description="Whether to execute OCR text extraction on the image")


class ImageAnalysisResponse(BaseModel):
    """Response payload for image and multimodal analysis."""

    id: str = Field(default_factory=lambda: f"meme-{uuid.uuid4().hex[:12]}")
    text: Optional[str] = Field(None, description="Analyzed or companion text")
    image_hash: str = Field(..., description="SHA-256 hash of the analyzed image")
    perceptual_hash: Optional[str] = Field(None, description="Perceptual pHash for near-duplicate matching")
    mime_type: str = Field(..., description="Detected image MIME type")
    ocr_text: Optional[str] = Field(None, description="Extracted OCR text if enabled and found")
    predicted_label: str = Field(..., description="Predicted label")
    confidence: float = Field(..., description="Model classification confidence")
    class_probabilities: Dict[str, float] = Field(default_factory=dict)
    classification: Optional[ClassificationDetail] = Field(None, description="Nested classification container")
    vision_results: Optional[VisionResults] = Field(None, description="Multimodal visual reasoning")
    explanation: Optional[Any] = Field(None, description="Explanation or token attribution")
    model_id: str = Field(...)
    is_available: bool = Field(True, description="Whether ML models are loaded")
    processed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
