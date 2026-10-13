"""Pydantic schemas for Investigation endpoints."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import PaginatedResponse


class InvestigationBase(BaseModel):
    """Base fields for investigation models."""

    title: str = Field(..., min_length=1, max_length=255, description="Investigation title")
    description: Optional[str] = Field(None, description="Detailed description of the investigation scope")
    keywords: List[str] = Field(default_factory=list, description="Target keywords and phrases")
    languages: List[str] = Field(default_factory=lambda: ["en"], description="Target ISO 639-1 language codes")
    date_range_start: Optional[datetime] = Field(None, description="Start date for data collection")
    date_range_end: Optional[datetime] = Field(None, description="End date for data collection")
    source_types: List[str] = Field(
        default_factory=lambda: ["url", "rss", "file", "text"],
        description="Allowed source types for ingestion",
    )


class InvestigationCreate(InvestigationBase):
    """Payload for creating a new investigation."""
    pass


class InvestigationUpdate(BaseModel):
    """Payload for updating an existing investigation."""

    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    keywords: Optional[List[str]] = None
    languages: Optional[List[str]] = None
    date_range_start: Optional[datetime] = None
    date_range_end: Optional[datetime] = None
    source_types: Optional[List[str]] = None
    status: Optional[str] = Field(None, description="Investigation status: active, paused, completed, archived")


class InvestigationResponse(InvestigationBase):
    """Full investigation representation returned to clients."""

    id: uuid.UUID = Field(..., description="Unique investigation UUID")
    status: str = Field("active", description="Current status")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    document_count: int = Field(0, description="Total ingested documents")
    cluster_count: int = Field(0, description="Total narrative clusters discovered")

    model_config = ConfigDict(from_attributes=True)


class InvestigationList(PaginatedResponse[InvestigationResponse]):
    """Paginated list of investigations."""
    pass


class InvestigationRunResponse(BaseModel):
    """Response returned upon launching an investigation processing run."""

    investigation_id: uuid.UUID = Field(..., description="Investigation ID")
    status: str = Field(..., description="Pipeline execution state (queued, running, completed)")
    started_at: datetime = Field(..., description="Run launch timestamp")
    message: str = Field(..., description="Descriptive status message")


class InvestigationStatusResponse(BaseModel):
    """Detailed runtime status and statistics for an investigation."""

    investigation_id: uuid.UUID
    status: str
    document_count: int = 0
    cluster_count: int = 0
    indicator_count: int = 0
    citation_count: int = 0
    last_updated: datetime
