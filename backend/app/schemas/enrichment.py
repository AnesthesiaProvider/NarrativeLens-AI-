"""Pydantic schemas for multi-attribute hate speech enrichment output.

These schemas extend the base TextAnalysisResponse with structured
intelligence fields: target group, harm type, severity rating, and
recommended moderation action.
"""

from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field


class TargetGroupResult(BaseModel):
    """Detected protected demographic group being targeted."""

    label: str = Field(
        ...,
        description=(
            "High-level protected category. One of: Religion, Race/Ethnicity, "
            "Gender, Sexual Orientation, Nationality/Immigration, Disability, "
            "Political/Ideological, Socioeconomic, Multiple/Intersectional, None"
        ),
    )
    detail: Optional[str] = Field(
        None,
        description="Specific sub-group detected (e.g. 'Muslim', 'Jewish', 'LGBTQ+'), if identifiable.",
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Signal confidence score (0–1) based on identity signal density in text.",
    )


class HarmTypeResult(BaseModel):
    """Classified type of harm or hostility present in the content."""

    label: str = Field(
        ...,
        description=(
            "Harm category. One of: Slur, Dehumanization, Incitement to Violence, "
            "Harassment/Intimidation, Stereotype Reinforcement, Profanity/Aggression, None"
        ),
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Signal confidence score for the detected harm type.",
    )


class SeverityRating(BaseModel):
    """Composite severity score and recommended moderation action."""

    level: str = Field(
        ...,
        description="Severity tier: CRITICAL, SEVERE, MODERATE, LOW, MINIMAL.",
    )
    score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Normalised composite severity score (0.0 = benign, 1.0 = most extreme).",
    )
    recommended_action: str = Field(
        ...,
        description=(
            "Recommended moderation action: AUTO_REMOVE, ESCALATE_TO_HUMAN_REVIEW, "
            "FLAG_FOR_REVIEW, LOG_ONLY, NO_ACTION, MANUAL_REVIEW."
        ),
    )


class EnrichedAnalysis(BaseModel):
    """Complete multi-attribute enrichment result attached to any analysis response."""

    target_group: TargetGroupResult = Field(
        ...,
        description="Which protected demographic group is being targeted, if any.",
    )
    harm_type: HarmTypeResult = Field(
        ...,
        description="The type of harm or hostility expressed in the content.",
    )
    severity: SeverityRating = Field(
        ...,
        description="Composite severity assessment and recommended moderation action.",
    )
    is_below_threshold: bool = Field(
        False,
        description=(
            "True when the classifier confidence falls below the class-specific "
            "decision threshold, indicating the prediction is uncertain."
        ),
    )
    threshold_used: float = Field(
        0.0,
        description="The decision threshold applied to the predicted class.",
    )
