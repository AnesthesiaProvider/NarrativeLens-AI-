"""Layer 4: Severity scoring engine.

Computes a composite severity score (0.0–1.0) from four weighted signals:
  1. Classifier confidence (if predicted class is hate or offensive)
  2. Incitement boost (harm_type = Incitement to Violence)
  3. Target group confidence (identity targeting signal strength)
  4. Slur / Dehumanization boost (specific high-severity harm types)

Maps the composite score to a severity tier (CRITICAL / SEVERE / MODERATE /
LOW / MINIMAL) and recommends a moderation action.

Also handles calibrated confidence thresholds to flag uncertain predictions
rather than presenting them as confident labels.
"""

from __future__ import annotations

import logging
from typing import Dict, Tuple

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Class-specific decision thresholds
# Derived from the evaluation report confusion matrix analysis:
#   - hate:      49% of [0.5, 0.65) predictions were wrong  → raise threshold
#   - offensive: coin-flip precision below 0.55              → raise threshold
#   - normal:    conservative — be sure before clearing      → raise threshold
# ---------------------------------------------------------------------------
CLASS_THRESHOLDS: Dict[str, float] = {
    "hate": 0.65,
    "hatespeech": 0.65,
    "hate_speech": 0.65,
    "offensive": 0.55,
    "toxic": 0.55,
    "toxicity": 0.55,
    "normal": 0.70,
    "neutral": 0.70,
}

# Severity tier boundaries (inclusive lower bound)
_TIER_BOUNDARIES: Tuple[Tuple[float, str, str], ...] = (
    (0.85, "CRITICAL", "AUTO_REMOVE"),
    (0.65, "SEVERE",   "ESCALATE_TO_HUMAN_REVIEW"),
    (0.40, "MODERATE", "FLAG_FOR_REVIEW"),
    (0.20, "LOW",      "LOG_ONLY"),
    (0.0,  "MINIMAL",  "NO_ACTION"),
)

# Harm types that qualify for the incitement boost
_INCITEMENT_HARM_TYPES = {"Incitement to Violence"}

# Harm types that qualify for the slur/dehumanization boost
_DEHUMANIZATION_HARM_TYPES = {"Slur", "Dehumanization", "Incitement to Violence"}


class SeverityEngine:
    """Computes composite severity score and recommends a moderation action.

    Weights:
      0.40 — classifier confidence (for hate/offensive class)
      0.25 — incitement boost (binary: harm_type = Incitement to Violence)
      0.20 — target group confidence
      0.15 — slur/dehumanization boost (binary)
    """

    # Signal weights (must sum to 1.0)
    W_CLASSIFIER   = 0.40
    W_INCITEMENT   = 0.25
    W_TARGET_GROUP = 0.20
    W_SLUR_DEHUM   = 0.15

    def _get_threshold(self, raw_label: str) -> float:
        """Return the class-specific decision threshold for a label."""
        return CLASS_THRESHOLDS.get(raw_label.lower(), 0.60)

    def _severity_tier(self, score: float) -> Tuple[str, str]:
        """Map a 0–1 score to a (tier_label, recommended_action) pair."""
        for lower_bound, tier, action in _TIER_BOUNDARIES:
            if score >= lower_bound:
                return tier, action
        return "MINIMAL", "NO_ACTION"

    def score(
        self,
        raw_label: str,
        confidence: float,
        target_group_confidence: float,
        harm_type_label: str,
    ) -> Dict:
        """Compute severity score and recommended action.

        Args:
            raw_label:               Internal model label (hate / offensive / normal).
            confidence:              Classifier softmax probability for predicted class.
            target_group_confidence: Signal strength from TargetGroupDetector (0–1).
            harm_type_label:         Label from HarmClassifier.

        Returns:
            dict with keys: level, score, recommended_action,
                            is_below_threshold, threshold_used
        """
        norm_label = raw_label.lower()
        threshold = self._get_threshold(norm_label)
        is_below_threshold = confidence < threshold

        # If below threshold, downgrade action to MANUAL_REVIEW immediately
        if is_below_threshold:
            return {
                "level": "MODERATE",
                "score": round(confidence * 0.5, 4),
                "recommended_action": "MANUAL_REVIEW",
                "is_below_threshold": True,
                "threshold_used": threshold,
            }

        # Signal 1: Classifier confidence contribution
        # For normal/neutral predictions, classifier signal is very low
        is_toxic = norm_label in {"hate", "hatespeech", "hate_speech", "offensive", "toxic", "toxicity"}
        classifier_signal = confidence if is_toxic else confidence * 0.1

        # Signal 2: Incitement boost (binary 0 or 1)
        incitement_signal = 1.0 if harm_type_label in _INCITEMENT_HARM_TYPES else 0.0

        # Signal 3: Target group confidence
        target_signal = target_group_confidence

        # Signal 4: Slur / Dehumanization boost (binary 0 or 1)
        slur_dehum_signal = 1.0 if harm_type_label in _DEHUMANIZATION_HARM_TYPES else 0.0

        composite = (
            self.W_CLASSIFIER   * classifier_signal
            + self.W_INCITEMENT   * incitement_signal
            + self.W_TARGET_GROUP * target_signal
            + self.W_SLUR_DEHUM   * slur_dehum_signal
        )
        composite = round(min(max(composite, 0.0), 1.0), 4)

        tier, action = self._severity_tier(composite)

        return {
            "level": tier,
            "score": composite,
            "recommended_action": action,
            "is_below_threshold": False,
            "threshold_used": threshold,
        }
