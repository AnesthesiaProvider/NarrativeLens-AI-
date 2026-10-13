"""Endpoints for managing benchmark datasets and model evaluation runs."""

from __future__ import annotations

import math
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.db.models import Dataset, EvaluationRun
from app.schemas.common import PaginatedResponse

router = APIRouter(tags=["Evaluations & Datasets"])


class DatasetResponse(BaseModel):
    """Dataset record representation."""

    id: uuid.UUID
    name: str
    description: Optional[str]
    version: str
    record_count: int
    label_distribution: Dict[str, int]
    language_distribution: Dict[str, int]
    split_type: str
    file_path: Optional[str]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DatasetListResponse(PaginatedResponse[DatasetResponse]):
    """Paginated collection of datasets."""
    pass


class EvaluationCreate(BaseModel):
    """Payload for submitting or triggering an evaluation run."""

    dataset_id: uuid.UUID = Field(..., description="UUID of the benchmark dataset")
    model_id: str = Field(..., description="Model identifier being evaluated")
    training_run_id: Optional[uuid.UUID] = Field(None, description="Optional training run UUID")
    metrics: Dict[str, Any] = Field(
        default_factory=dict,
        description="Global metrics e.g. {'f1': 0.92, 'precision': 0.91, 'recall': 0.93, 'accuracy': 0.94}",
    )
    confusion_matrix: List[List[int]] = Field(
        default_factory=list, description="Confusion matrix rows and columns"
    )
    per_class_metrics: Dict[str, Any] = Field(
        default_factory=dict, description="Fine-grained per-class breakdown"
    )


class EvaluationResponse(BaseModel):
    """Evaluation benchmark run details."""

    id: uuid.UUID
    training_run_id: Optional[uuid.UUID]
    dataset_id: uuid.UUID
    model_id: str
    metrics: Dict[str, Any]
    confusion_matrix: List[List[int]]
    per_class_metrics: Dict[str, Any]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class EvaluationListResponse(PaginatedResponse[EvaluationResponse]):
    """Paginated evaluation run history."""
    pass


@router.get(
    "/evaluations",
    response_model=EvaluationListResponse,
    status_code=status.HTTP_200_OK,
    summary="List Evaluation Runs",
    description="Retrieve historical benchmark runs, metrics, and confusion matrices.",
)
async def list_evaluations(
    model_id: Optional[str] = Query(None, description="Filter by model ID"),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> EvaluationListResponse:
    """Retrieve evaluation benchmark history."""
    query = select(EvaluationRun)
    if model_id:
        query = query.where(EvaluationRun.model_id == model_id)

    total_q = select(func.count()).select_from(query.subquery())
    total = (await db.scalar(total_q)) or 0

    offset = (page - 1) * size
    stmt = query.order_by(EvaluationRun.created_at.desc()).offset(offset).limit(size)
    records = (await db.scalars(stmt)).all()

    items = [EvaluationResponse.model_validate(r) for r in records]
    total_pages = math.ceil(total / size) if size > 0 else 0

    return EvaluationListResponse(
        items=items,
        total=total,
        page=page,
        size=size,
        pages=total_pages,
    )


@router.post(
    "/evaluations",
    response_model=EvaluationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Record Evaluation Run",
    description="Store evaluation results and benchmark scores for a model checkpoint.",
)
async def create_evaluation(
    payload: EvaluationCreate,
    db: AsyncSession = Depends(get_db),
) -> EvaluationResponse:
    """Record an evaluation run in the database."""
    dataset = await db.scalar(select(Dataset).where(Dataset.id == payload.dataset_id))
    if not dataset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dataset with ID '{payload.dataset_id}' not found.",
        )

    eval_run = EvaluationRun(
        dataset_id=payload.dataset_id,
        training_run_id=payload.training_run_id,
        model_id=payload.model_id,
        metrics=payload.metrics,
        confusion_matrix=payload.confusion_matrix,
        per_class_metrics=payload.per_class_metrics,
    )
    db.add(eval_run)
    await db.commit()
    await db.refresh(eval_run)

    return EvaluationResponse.model_validate(eval_run)


@router.get(
    "/datasets",
    response_model=DatasetListResponse,
    status_code=status.HTTP_200_OK,
    summary="List Benchmark Datasets",
    description="Retrieve all registered benchmark and training datasets.",
)
async def list_datasets(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> DatasetListResponse:
    """Retrieve registered datasets."""
    query = select(Dataset)
    total_q = select(func.count()).select_from(query.subquery())
    total = (await db.scalar(total_q)) or 0

    offset = (page - 1) * size
    stmt = query.order_by(Dataset.created_at.desc()).offset(offset).limit(size)
    records = (await db.scalars(stmt)).all()

    items = [DatasetResponse.model_validate(r) for r in records]
    total_pages = math.ceil(total / size) if size > 0 else 0

    return DatasetListResponse(
        items=items,
        total=total,
        page=page,
        size=size,
        pages=total_pages,
    )
