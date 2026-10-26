"""Multi-attribute enrichment pipeline for hate speech analysis.

Wraps the existing XLM-RoBERTa classifier output with structured intelligence:
- Target group detection (protected demographic categories)
- Harm type classification (dehumanization, slur, incitement, etc.)
- Severity scoring with recommended moderation action
- Calibrated confidence thresholds to reduce false certainty

No retraining required — enrichment runs as a post-processing layer.
"""

from .enrichment_pipeline import EnrichmentPipeline, enrich_prediction
from .harm_classifier import HarmClassifier
from .severity_engine import SeverityEngine
from .target_detector import TargetGroupDetector

__all__ = [
    "EnrichmentPipeline",
    "enrich_prediction",
    "HarmClassifier",
    "SeverityEngine",
    "TargetGroupDetector",
]
