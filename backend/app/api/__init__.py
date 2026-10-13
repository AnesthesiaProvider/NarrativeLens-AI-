"""API Router aggregation module."""

from fastapi import APIRouter

from app.api.analysis import router as analysis_router
from app.api.coordination import router as coordination_router
from app.api.evaluations import router as evaluations_router
from app.api.feedback import router as feedback_router
from app.api.health import router as health_router
from app.api.ingestion import router as ingestion_router
from app.api.investigations import router as investigations_router
from app.api.narratives import router as narratives_router

api_router = APIRouter()

# Include all sub-routers
api_router.include_router(health_router)
api_router.include_router(investigations_router)
api_router.include_router(analysis_router)
api_router.include_router(ingestion_router)
api_router.include_router(narratives_router)
api_router.include_router(coordination_router)
api_router.include_router(feedback_router)
api_router.include_router(evaluations_router)

__all__ = ["api_router"]
