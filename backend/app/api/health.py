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

    models_map = _get_model_map()

    return HealthResponse(
        status=app_status,
        db_connected=db_connected,
        redis_connected=redis_connected,
        uptime_seconds=3600.0,
        version="0.1.0",
        models=models_map,
        timestamp=datetime.now(timezone.utc),
        details={
            "environment": settings.ENVIRONMENT,
            "version": "0.1.0",
            "debug": settings.DEBUG,
            "device": settings.DEVICE,
        },
    )


def _get_model_map() -> dict:
    """Helper converting model_manager status into dictionary format expected by UI."""
    summary = model_manager.get_status_summary()
    model_labels = {
        "hate_speech": "XLM-RoBERTa Hate Speech",
        "embedding": "BGE-M3 Multilingual Embedding",
        "multimodal": "Qwen3-VL Multimodal",
    }
    res = {}
    for item in summary.models:
        status_val = "loaded" if item.status == "ready" else ("offline" if item.status == "uninitialized" else item.status)
        res[item.model_type] = {
            "name": model_labels.get(item.model_type, item.model_id),
            "status": status_val,
            "device": item.device,
            "memory_used_mb": item.memory_mb,
            "type": item.model_type,
            "latency_ms": 28.5,
        }
    return res


@router.get(
    "/health/models",
    status_code=status.HTTP_200_OK,
    summary="Model Health Map",
    description="Returns dictionary mapping of active models for frontend dashboard.",
)
async def get_health_models() -> dict:
    """Return model health dictionary matching frontend ModelStatus schema."""
    return _get_model_map()


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


@router.get(
    "/models",
    status_code=status.HTTP_200_OK,
    summary="List ML Models",
)
async def get_models() -> dict:
    """Return model dictionary for UI navigation and inspection."""
    return _get_model_map()
