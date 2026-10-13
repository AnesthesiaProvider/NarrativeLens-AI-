"""Common Pydantic schemas used across multiple API endpoints."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Generic, List, Optional, TypeVar
from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class HealthResponse(BaseModel):
    """Health check response schema."""

    status: str = Field(..., description="Overall service status (healthy/degraded/unhealthy)")
    db_connected: bool = Field(..., description="PostgreSQL database connectivity status")
    redis_connected: bool = Field(..., description="Redis connectivity status")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Current server timestamp in UTC",
    )
    details: Dict[str, Any] = Field(default_factory=dict, description="Additional component status details")


class ModelStatusItem(BaseModel):
    """Status details for a single machine learning model."""

    model_id: str = Field(..., description="Model identifier")
    model_type: str = Field(..., description="Model category (e.g. hate_speech, embedding)")
    status: str = Field(..., description="Model runtime status (e.g. ready, uninitialized, error)")
    device: str = Field(..., description="Device executing the model (cpu/cuda)")
    memory_mb: float = Field(0.0, description="Approximate memory footprint in MB")
    loaded_at: Optional[datetime] = Field(None, description="Timestamp when model was loaded")


class ModelStatusResponse(BaseModel):
    """Response schema summarizing status across all configured models."""

    status: str = Field(..., description="Aggregated model manager status")
    models: List[ModelStatusItem] = Field(default_factory=list, description="List of model status entries")
    total_loaded: int = Field(0, description="Total number of active models loaded in memory")
    device: str = Field(..., description="Default execution device")


class PaginatedResponse(BaseModel, Generic[T]):
    """Standard generic pagination wrapper."""

    items: List[T] = Field(..., description="List of items for the requested page")
    total: int = Field(..., description="Total items matching query")
    page: int = Field(..., ge=1, description="Current page number (1-indexed)")
    size: int = Field(..., ge=1, le=100, description="Number of items per page")
    pages: int = Field(..., ge=0, description="Total number of pages")

    model_config = ConfigDict(from_attributes=True)


class ErrorResponse(BaseModel):
    """Standardized API error response schema."""

    detail: str = Field(..., description="Human-readable error description")
    error_code: Optional[str] = Field(None, description="Optional programmatic error code")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp when error occurred",
    )
