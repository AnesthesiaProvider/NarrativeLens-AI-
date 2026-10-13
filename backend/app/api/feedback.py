"""Human-in-the-loop analyst feedback and review task endpoints."""

from __future__ import annotations

import math
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.db.models import HumanFeedback, ReviewTask
from app.schemas.common import PaginatedResponse

router = APIRouter(prefix="/feedback", tags=["Human Review & Feedback"])


class FeedbackCreate(BaseModel):
    """Payload for submitting human feedback or label correction."""

    review_task_id: Optional[uuid.UUID] = Field(None, description="Optional associated review task UUID")
    classification_id: Optional[uuid.UUID] = Field(None, description="Optional classification result UUID being corrected")
    corrected_label: str = Field(..., min_length=1, max_length=100, description="Corrected label by human reviewer")
    is_ambiguous: bool = Field(False, description="Whether the sample is inherently ambiguous or context-dependent")
    explanation: Optional[str] = Field(None, description="Analyst rationale or notes for the correction")
    reviewer: str = Field(..., min_length=1, max_length=255, description="Analyst username or reviewer identity")


class FeedbackResponse(BaseModel):
    """Human feedback record representation."""

    id: uuid.UUID
    review_task_id: Optional[uuid.UUID]
    classification_id: Optional[uuid.UUID]
    corrected_label: str
    is_ambiguous: bool
    explanation: Optional[str]
    reviewer: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FeedbackListResponse(PaginatedResponse[FeedbackResponse]):
    """Paginated feedback records."""
    pass


@router.post(
    "",
    response_model=FeedbackResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit Human Feedback",
    description="Record analyst label corrections and update linked review tasks.",
)
async def create_feedback(
    payload: FeedbackCreate,
    db: AsyncSession = Depends(get_db),
) -> FeedbackResponse:
    """Submit human feedback for model fine-tuning and active learning."""
    feedback = HumanFeedback(
        review_task_id=payload.review_task_id,
        classification_id=payload.classification_id,
        corrected_label=payload.corrected_label,
        is_ambiguous=payload.is_ambiguous,
        explanation=payload.explanation,
        reviewer=payload.reviewer,
    )
    db.add(feedback)

    # If linked to a review task, close the review task
    if payload.review_task_id:
        task = await db.scalar(
            select(ReviewTask).where(ReviewTask.id == payload.review_task_id)
        )
        if task:
            task.status = "completed"
            task.completed_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(feedback)

    return FeedbackResponse.model_validate(feedback)


@router.get(
    "",
    response_model=FeedbackListResponse,
    status_code=status.HTTP_200_OK,
    summary="List Human Feedback Records",
    description="Retrieve paginated feedback submitted by human reviewers.",
)
async def list_feedback(
    reviewer: Optional[str] = Query(None, description="Filter by reviewer identity"),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> FeedbackListResponse:
    """Retrieve human feedback items."""
    query = select(HumanFeedback)
    if reviewer:
        query = query.where(HumanFeedback.reviewer == reviewer)

    count_q = select(func.count()).select_from(query.subquery())
    total = (await db.scalar(count_q)) or 0

    offset = (page - 1) * size
    stmt = query.order_by(HumanFeedback.created_at.desc()).offset(offset).limit(size)
    records = (await db.scalars(stmt)).all()

    items = [FeedbackResponse.model_validate(r) for r in records]
    total_pages = math.ceil(total / size) if size > 0 else 0

    return FeedbackListResponse(
        items=items,
        total=total,
        page=page,
        size=size,
        pages=total_pages,
    )
