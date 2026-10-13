"""Endpoints for detecting coordinated behavior, temporal bursts, and campaign patterns."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.db.models import CoordinationIndicator, Investigation

router = APIRouter(prefix="/coordination", tags=["Coordinated Behavior"])


class CoordinationIndicatorItem(BaseModel):
    """Signal of coordinated campaign activity."""

    id: uuid.UUID
    investigation_id: uuid.UUID
    indicator_type: str
    description: str
    evidence: Dict[str, Any]
    confidence: float
    involved_documents: List[str]
    requires_review: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CoordinationSummaryResponse(BaseModel):
    """Summary of coordinated campaign signals detected in an investigation."""

    investigation_id: uuid.UUID
    indicators: List[CoordinationIndicatorItem]
    total_indicators: int
    risk_level: str = Field("low", description="Overall coordination risk: low, moderate, elevated, severe")
    has_unreviewed_indicators: bool


@router.get(
    "/{investigation_id}",
    response_model=CoordinationSummaryResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Coordination Indicators",
    description="Retrieve all coordinated inauthentic behavior indicators discovered for an investigation.",
)
async def get_coordination(
    investigation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> CoordinationSummaryResponse:
    """Fetch coordination signals and campaign indicators."""
    inv = await db.scalar(select(Investigation).where(Investigation.id == investigation_id))
    if not inv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Investigation '{investigation_id}' does not exist.",
        )

    stmt = (
        select(CoordinationIndicator)
        .where(CoordinationIndicator.investigation_id == investigation_id)
        .order_by(CoordinationIndicator.confidence.desc())
    )
    records = (await db.scalars(stmt)).all()

    items = [CoordinationIndicatorItem.model_validate(r) for r in records]
    unreviewed = any(item.requires_review for item in items)

    # Compute risk level
    if not items:
        risk = "low"
    elif len(items) >= 5 or any(i.confidence > 0.85 for i in items):
        risk = "severe"
    elif len(items) >= 2 or any(i.confidence > 0.65 for i in items):
        risk = "elevated"
    else:
        risk = "moderate"

    return CoordinationSummaryResponse(
        investigation_id=investigation_id,
        indicators=items,
        total_indicators=len(items),
        risk_level=risk,
        has_unreviewed_indicators=unreviewed,
    )
