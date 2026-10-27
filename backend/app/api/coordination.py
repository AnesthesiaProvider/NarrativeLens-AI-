"""Endpoints for detecting coordinated behavior, temporal bursts, and campaign patterns."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.coordination.detector import CoordinationDetector
from app.core.database import get_db
from app.db.models import CoordinationIndicator, Document, Investigation

router = APIRouter(prefix="/coordination", tags=["Coordinated Behavior"])


class CoordinationIndicatorItem(BaseModel):
    """Signal of coordinated campaign activity."""

    id: uuid.UUID
    investigation_id: uuid.UUID
    name: Optional[str] = None
    indicator_type: str
    description: str
    evidence: Dict[str, Any]
    confidence: float
    score: Optional[float] = None
    uncertainty: Optional[str] = None
    detected_patterns: Optional[List[str]] = None
    involved_documents: List[str]
    requires_review: bool
    created_at: datetime
    timestamp: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class CoordinationSummaryResponse(BaseModel):
    """Summary of coordinated campaign signals detected in an investigation."""

    investigation_id: uuid.UUID
    indicators: List[CoordinationIndicatorItem]
    total_indicators: int
    overall_coordination_index: float = 0.0
    cluster_core_count: int = 0
    uncertainty_level: str = "medium"
    risk_level: str = Field("low", description="Overall coordination risk: low, moderate, elevated, severe")
    has_unreviewed_indicators: bool
    graph: Optional[Dict[str, Any]] = None


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

    # If no indicators are stored yet, run the detector automatically
    if not records:
        detector = CoordinationDetector(db)
        summary = await detector.analyze_investigation(investigation_id, persist=True)
        # Format indicators to match response schema
        items = []
        for ind in summary["indicators"]:
            items.append(
                CoordinationIndicatorItem(
                    id=uuid.UUID(str(ind["id"])),
                    investigation_id=investigation_id,
                    name=ind.get("name", ind["indicator_type"].replace("_", " ").title()),
                    indicator_type=ind["indicator_type"],
                    description=ind["description"],
                    evidence=ind["evidence"] if isinstance(ind["evidence"], dict) else {"details": ind["evidence"]},
                    confidence=ind["confidence"],
                    score=ind.get("score", ind["confidence"]),
                    uncertainty=ind.get("uncertainty", "medium"),
                    detected_patterns=ind.get("detected_patterns", [ind["indicator_type"]]),
                    involved_documents=ind.get("involved_documents", []),
                    requires_review=ind.get("requires_review", False),
                    created_at=datetime.utcnow(),
                    timestamp=ind.get("timestamp", datetime.utcnow().isoformat()),
                )
            )

        return CoordinationSummaryResponse(
            investigation_id=investigation_id,
            indicators=items,
            total_indicators=len(items),
            overall_coordination_index=summary["overall_coordination_index"],
            cluster_core_count=summary["cluster_core_count"],
            uncertainty_level=summary["uncertainty_level"],
            risk_level=summary["risk_level"],
            has_unreviewed_indicators=summary["has_unreviewed_indicators"],
            graph=summary.get("graph"),
        )

    # Convert existing records
    items = []
    for r in records:
        ev = r.evidence if isinstance(r.evidence, dict) else {}
        name = ev.get("name") or r.indicator_type.replace("_", " ").title()
        uncertainty = "low" if r.confidence >= 0.8 else "medium" if r.confidence >= 0.5 else "high"
        patterns = [r.indicator_type]
        if "detected_patterns" in ev:
            patterns = ev["detected_patterns"]

        items.append(
            CoordinationIndicatorItem(
                id=r.id,
                investigation_id=r.investigation_id,
                name=name,
                indicator_type=r.indicator_type,
                description=r.description,
                evidence=r.evidence,
                confidence=r.confidence,
                score=r.confidence,
                uncertainty=uncertainty,
                detected_patterns=patterns,
                involved_documents=r.involved_documents or [],
                requires_review=r.requires_review,
                created_at=r.created_at,
                timestamp=r.created_at.isoformat() if r.created_at else None,
            )
        )

    unreviewed = any(item.requires_review for item in items)
    avg_score = round(sum(i.confidence for i in items) / len(items), 2) if items else 0.0

    # Retrieve docs to build live network topology
    doc_res = await db.execute(
        select(Document).where(Document.investigation_id == investigation_id)
    )
    docs = list(doc_res.scalars().all())
    detector = CoordinationDetector(db)
    graph = detector._build_network_topology(docs)
    unique_authors = {d.author for d in docs if d.author and d.author not in ("Unknown", "Reddit", "Social Media")}
    core_count = max(len(unique_authors), len(docs) if len(docs) < 5 else int(len(docs) * 0.6))

    if not items:
        risk = "low"
    elif len(items) >= 4 or any(i.confidence > 0.85 for i in items):
        risk = "severe"
    elif len(items) >= 2 or any(i.confidence > 0.65 for i in items):
        risk = "elevated"
    else:
        risk = "moderate"

    return CoordinationSummaryResponse(
        investigation_id=investigation_id,
        indicators=items,
        total_indicators=len(items),
        overall_coordination_index=avg_score,
        cluster_core_count=core_count,
        uncertainty_level="low" if len(docs) >= 10 else "medium",
        risk_level=risk,
        has_unreviewed_indicators=unreviewed,
        graph=graph,
    )


@router.post(
    "/{investigation_id}/reanalyze",
    response_model=CoordinationSummaryResponse,
    status_code=status.HTTP_200_OK,
    summary="Re-analyze Coordination Behavior",
    description="Forces a live re-execution of temporal burst, cross-platform mirroring, and graph topology detection.",
)
async def reanalyze_coordination(
    investigation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> CoordinationSummaryResponse:
    """Force re-run coordination detection algorithms and update database indicators."""
    inv = await db.scalar(select(Investigation).where(Investigation.id == investigation_id))
    if not inv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Investigation '{investigation_id}' does not exist.",
        )

    detector = CoordinationDetector(db)
    summary = await detector.analyze_investigation(investigation_id, persist=True)

    items = []
    for ind in summary["indicators"]:
        items.append(
            CoordinationIndicatorItem(
                id=uuid.UUID(str(ind["id"])),
                investigation_id=investigation_id,
                name=ind.get("name", ind["indicator_type"].replace("_", " ").title()),
                indicator_type=ind["indicator_type"],
                description=ind["description"],
                evidence=ind["evidence"] if isinstance(ind["evidence"], dict) else {"details": ind["evidence"]},
                confidence=ind["confidence"],
                score=ind.get("score", ind["confidence"]),
                uncertainty=ind.get("uncertainty", "medium"),
                detected_patterns=ind.get("detected_patterns", [ind["indicator_type"]]),
                involved_documents=ind.get("involved_documents", []),
                requires_review=ind.get("requires_review", False),
                created_at=datetime.utcnow(),
                timestamp=ind.get("timestamp", datetime.utcnow().isoformat()),
            )
        )

    return CoordinationSummaryResponse(
        investigation_id=investigation_id,
        indicators=items,
        total_indicators=len(items),
        overall_coordination_index=summary["overall_coordination_index"],
        cluster_core_count=summary["cluster_core_count"],
        uncertainty_level=summary["uncertainty_level"],
        risk_level=summary["risk_level"],
        has_unreviewed_indicators=summary["has_unreviewed_indicators"],
        graph=summary.get("graph"),
    )
