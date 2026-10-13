"""Health check and model status endpoints."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from fastapi import APIRouter, status

from app.core.config import settings
from app.core.database import check_db_connection
from app.ml.model_manager import model_manager
from app.schemas.common import HealthResponse, ModelStatusResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Health & Status"])


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Application Health Check",
    description="Check connectivity to database, redis, and overall service health.",
)
async def get_health() -> HealthResponse:
    """Check application health, including database and redis availability."""
    db_connected = await check_db_connection()
    redis_connected = False

    try:
        import redis.asyncio as aioredis
        if settings.REDIS_URL:
            r = aioredis.from_url(
                settings.REDIS_URL,
                socket_connect_timeout=1.0,
                socket_timeout=1.0,
            )
            await r.ping()
            await r.aclose()
            redis_connected = True
    except Exception as exc:
        logger.debug(f"Redis ping unsuccessful: {exc}")
        redis_connected = False

    if db_connected and redis_connected:
        app_status = "healthy"
    elif db_connected:
        app_status = "degraded"
    else:
        app_status = "unhealthy"

    return HealthResponse(
        status=app_status,
        db_connected=db_connected,
        redis_connected=redis_connected,
        timestamp=datetime.now(timezone.utc),
        details={
            "environment": settings.ENVIRONMENT,
            "version": "0.1.0",
            "debug": settings.DEBUG,
            "device": settings.DEVICE,
        },
    )


@router.get(
    "/models/status",
    response_model=ModelStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="ML Models Status",
    description="Inspect runtime readiness and device placement of configured machine learning models.",
)
async def get_models_status() -> ModelStatusResponse:
    """Return status of all registered machine learning models."""
    return model_manager.get_status_summary()
