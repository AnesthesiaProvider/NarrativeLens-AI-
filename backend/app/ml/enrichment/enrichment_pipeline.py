"""Enrichment pipeline orchestrator.

Runs all three enrichment layers (target detection, harm classification,
severity scoring) on a raw classifier prediction and returns a unified
EnrichedAnalysis result.

Usage:
    from app.ml.enrichment import enrich_prediction

    raw_pred = model_manager.predict_hate_speech(text)
    enriched = enrich_prediction(text, raw_pred)
    # enriched is a dict matching the EnrichedAnalysis schema
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from .harm_classifier import HarmClassifier
from .severity_engine import SeverityEngine
from .target_detector import TargetGroupDetector

logger = logging.getLogger(__name__)

# Module-level singletons — instantiated once, reused across all requests.
# All three classes are stateless (no model weights, pure CPU regex logic).
_target_detector = TargetGroupDetector()
_harm_classifier = HarmClassifier()
_severity_engine = SeverityEngine()


def enrich_prediction(text: str, raw_prediction: Dict[str, Any]) -> Dict[str, Any]:
    """Run the full enrichment pipeline on a raw hate speech prediction.

    Args:
        text:           The original input text (sanitized, ≤512 chars recommended).
        raw_prediction: Output dict from model_manager.predict_hate_speech().
                        Expected keys: predicted_label, confidence.

    Returns:
        A dict matching the EnrichedAnalysis Pydantic schema with keys:
            target_group, harm_type, severity,
            is_below_threshold, threshold_used
    """
    raw_label = raw_prediction.get("predicted_label", "normal")
    confidence = float(raw_prediction.get("confidence", 0.0))

    # Layer 2: Target group detection
    try:
        target_result = _target_detector.detect(text)
    except Exception as exc:
        logger.warning(f"Target group detection failed: {exc}")
        target_result = {"label": "None", "detail": None, "confidence": 0.0}

    # Layer 3: Harm type classification
    try:
        harm_result = _harm_classifier.classify(text)
    except Exception as exc:
        logger.warning(f"Harm classification failed: {exc}")
        harm_result = {"label": "None", "confidence": 0.0}

    # Layer 4: Severity scoring
    try:
        severity_result = _severity_engine.score(
            raw_label=raw_label,
            confidence=confidence,
            target_group_confidence=target_result["confidence"],
            harm_type_label=harm_result["label"],
        )
    except Exception as exc:
        logger.warning(f"Severity scoring failed: {exc}")
        severity_result = {
            "level": "MINIMAL",
            "score": 0.0,
            "recommended_action": "NO_ACTION",
            "is_below_threshold": False,
            "threshold_used": 0.0,
        }

    return {
        "target_group": target_result,
        "harm_type": harm_result,
        "severity": {
            "level": severity_result["level"],
            "score": severity_result["score"],
            "recommended_action": severity_result["recommended_action"],
        },
        "is_below_threshold": severity_result.get("is_below_threshold", False),
        "threshold_used": severity_result.get("threshold_used", 0.0),
    }


class EnrichmentPipeline:
    """Object-oriented wrapper around enrich_prediction() for dependency injection."""

    def enrich(self, text: str, raw_prediction: Dict[str, Any]) -> Dict[str, Any]:
        """Enrich a raw classifier prediction with multi-attribute metadata."""
        return enrich_prediction(text, raw_prediction)
