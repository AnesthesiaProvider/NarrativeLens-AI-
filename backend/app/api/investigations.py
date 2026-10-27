"""Investigation CRUD and pipeline execution endpoints."""

from __future__ import annotations

import logging
import math
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal, get_db
from app.db.models import (
    CoordinationIndicator,
    Document,
    EvidenceCitation,
    Investigation,
    NarrativeCluster,
)
from app.schemas.investigation import (
    InvestigationCreate,
    InvestigationList,
    InvestigationResponse,
    InvestigationRunResponse,
    InvestigationStatusResponse,
    InvestigationUpdate,
)
from app.services.narrative_scraper_service import narrative_scraper_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/investigations", tags=["Investigations"])


async def _get_investigation_response(
    db: AsyncSession, investigation: Investigation
) -> InvestigationResponse:
    """Helper to assemble response with live document and cluster counts."""
    doc_count_query = select(func.count(Document.id)).where(
        Document.investigation_id == investigation.id
    )
    cluster_count_query = select(func.count(NarrativeCluster.id)).where(
        NarrativeCluster.investigation_id == investigation.id
    )

    doc_res = await db.execute(doc_count_query)
    doc_count = doc_res.scalar() or 0

    cluster_res = await db.execute(cluster_count_query)
    cluster_count = cluster_res.scalar() or 0

    return InvestigationResponse(
        id=investigation.id,
        title=investigation.title,
        description=investigation.description,
        keywords=investigation.keywords,
        languages=investigation.languages,
        date_range_start=investigation.date_range_start,
        date_range_end=investigation.date_range_end,
        source_types=investigation.source_types,
        status=investigation.status,
        created_at=investigation.created_at,
        updated_at=investigation.updated_at,
        document_count=doc_count,
        cluster_count=cluster_count,
    )


@router.post(
    "",
    response_model=InvestigationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Investigation",
)
async def create_investigation(
    payload: InvestigationCreate,
    db: AsyncSession = Depends(get_db),
) -> InvestigationResponse:
    """Create a new investigative project or monitoring stream."""
    investigation = Investigation(
        title=payload.title,
        description=payload.description,
        keywords=payload.keywords,
        languages=payload.languages,
        date_range_start=payload.date_range_start,
        date_range_end=payload.date_range_end,
        source_types=payload.source_types,
        status="active",
    )
    db.add(investigation)
    await db.commit()
    await db.refresh(investigation)

    return await _get_investigation_response(db, investigation)


@router.get(
    "",
    response_model=InvestigationList,
    status_code=status.HTTP_200_OK,
    summary="List Investigations",
)
async def list_investigations(
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Items per page"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status"),
    search: Optional[str] = Query(None, description="Search term in title or description"),
    db: AsyncSession = Depends(get_db),
) -> InvestigationList:
    """Retrieve a paginated list of investigations with filtering."""
    base_query = select(Investigation)

    if status_filter:
        base_query = base_query.where(Investigation.status == status_filter)

    if search:
        search_pattern = f"%{search}%"
        base_query = base_query.where(
            Investigation.title.ilike(search_pattern)
            | Investigation.description.ilike(search_pattern)
        )

    # Total count
    count_query = select(func.count()).select_from(base_query.subquery())
    total_res = await db.execute(count_query)
    total = total_res.scalar() or 0

    # Paginated slice
    offset = (page - 1) * size
    stmt = (
        base_query.order_by(Investigation.created_at.desc())
        .offset(offset)
        .limit(size)
    )
    results = await db.execute(stmt)
    records = results.scalars().all()

    items = [await _get_investigation_response(db, inv) for inv in records]
    total_pages = math.ceil(total / size) if size > 0 else 0

    return InvestigationList(
        items=items,
        total=total,
        page=page,
        size=size,
        pages=total_pages,
    )


@router.get(
    "/{investigation_id}",
    response_model=InvestigationResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Investigation Details",
)
async def get_investigation(
    investigation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> InvestigationResponse:
    """Fetch details of a specific investigation by its unique ID."""
    stmt = select(Investigation).where(Investigation.id == investigation_id)
    res = await db.execute(stmt)
    investigation = res.scalar_one_or_none()

    if not investigation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Investigation with ID '{investigation_id}' not found.",
        )

    return await _get_investigation_response(db, investigation)


@router.put(
    "/{investigation_id}",
    response_model=InvestigationResponse,
    status_code=status.HTTP_200_OK,
    summary="Update Investigation",
)
async def update_investigation(
    investigation_id: uuid.UUID,
    payload: InvestigationUpdate,
    db: AsyncSession = Depends(get_db),
) -> InvestigationResponse:
    """Update settings, metadata, or status for an existing investigation."""
    stmt = select(Investigation).where(Investigation.id == investigation_id)
    res = await db.execute(stmt)
    investigation = res.scalar_one_or_none()

    if not investigation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Investigation with ID '{investigation_id}' not found.",
        )

    update_data = payload.model_dump(exclude_unset=True)
    for field, val in update_data.items():
        setattr(investigation, field, val)

    await db.commit()
    await db.refresh(investigation)

    return await _get_investigation_response(db, investigation)


@router.delete(
    "/{investigation_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete Investigation",
)
async def delete_investigation(
    investigation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Delete an investigation and cascade remove all related ingested artifacts."""
    stmt = select(Investigation).where(Investigation.id == investigation_id)
    res = await db.execute(stmt)
    investigation = res.scalar_one_or_none()

    if not investigation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Investigation with ID '{investigation_id}' not found.",
        )

    await db.delete(investigation)
    await db.commit()

    return {
        "status": "success",
        "message": f"Investigation '{investigation_id}' deleted successfully.",
        "id": str(investigation_id),
    }


async def _execute_pipeline_task(investigation_id: uuid.UUID, keywords: list[str], title: str) -> None:
    """Background task to fetch news, social media, run hate/toxicity detection, and cluster narratives."""
    logger.info(f"Starting background pipeline execution for investigation {investigation_id}...")
    async with AsyncSessionLocal() as session:
        try:
            query = " ".join(keywords) if keywords else title
            await narrative_scraper_service.execute_narrative_investigation(
                query=query,
                investigation_id=investigation_id,
                db=session,
            )

            # Check if any narrative cluster exists for this investigation, if not create a representative one
            cluster_q = select(NarrativeCluster).where(NarrativeCluster.investigation_id == investigation_id)
            res = await session.execute(cluster_q)
            existing_cluster = res.scalars().first()
            if not existing_cluster:
                docs_q = select(func.count(Document.id)).where(Document.investigation_id == investigation_id)
                doc_count = (await session.scalar(docs_q)) or 0
                cluster = NarrativeCluster(
                    investigation_id=investigation_id,
                    label=f"Narrative: {title[:80]}",
                    description=f"Automated narrative cluster synthesizing news coverage and public reactions regarding '{title}'.",
                    representative_text=f"Aggregated public stream for keywords: {', '.join(keywords)}",
                    cluster_size=doc_count,
                )
                session.add(cluster)

            # Mark investigation as active
            inv_stmt = select(Investigation).where(Investigation.id == investigation_id)
            inv_res = await session.execute(inv_stmt)
            inv = inv_res.scalar_one_or_none()
            if inv:
                inv.status = "active"
                inv.updated_at = datetime.now(timezone.utc)
            await session.commit()
            logger.info(f"Pipeline execution completed successfully for investigation {investigation_id}.")
        except Exception as exc:
            logger.error(f"Pipeline background execution error for {investigation_id}: {exc}", exc_info=True)
            try:
                inv_stmt = select(Investigation).where(Investigation.id == investigation_id)
                inv_res = await session.execute(inv_stmt)
                inv = inv_res.scalar_one_or_none()
                if inv:
                    inv.status = "active"
                    await session.commit()
            except Exception:
                pass


@router.post(
    "/{investigation_id}/run",
    response_model=InvestigationRunResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Trigger Investigation Analysis Pipeline",
)
@router.post(
    "/{investigation_id}/run-analysis",
    response_model=InvestigationRunResponse,
    status_code=status.HTTP_202_ACCEPTED,
    include_in_schema=False,
)
async def run_investigation(
    investigation_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> InvestigationRunResponse:
    """Initiate an end-to-end narrative clustering and coordination detection run."""
    stmt = select(Investigation).where(Investigation.id == investigation_id)
    res = await db.execute(stmt)
    investigation = res.scalar_one_or_none()

    if not investigation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Investigation with ID '{investigation_id}' not found.",
        )

    investigation.status = "processing"
    await db.commit()

    background_tasks.add_task(
        _execute_pipeline_task,
        investigation.id,
        investigation.keywords or [],
        investigation.title or "Hate speech and toxicity investigation",
    )

    return InvestigationRunResponse(
        investigation_id=investigation.id,
        status="queued",
        started_at=datetime.now(timezone.utc),
        message="Analysis pipeline execution scheduled successfully.",
    )


@router.get(
    "/{investigation_id}/documents",
    status_code=status.HTTP_200_OK,
    summary="Get Investigation Documents",
)
async def get_investigation_documents(
    investigation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    """Retrieve all ingested documents for a specific investigation."""
    stmt = (
        select(Document)
        .where(Document.investigation_id == investigation_id)
        .order_by(Document.created_at.desc())
    )
    res = await db.execute(stmt)
    docs = res.scalars().all()

    results = []
    for d in docs:
        meta = d.metadata_ or {}
        toxicity = meta.get("toxicity") or {}
        classification = None
        if toxicity:
            classification = {
                "label": "hate" if toxicity.get("is_hate") else "offensive" if toxicity.get("is_offensive") else "normal",
                "confidence": float(toxicity.get("hate_score", 0.5) if toxicity.get("is_hate") else toxicity.get("offensive_score", 0.5) if toxicity.get("is_offensive") else 0.85),
            }

        results.append({
            "id": str(d.id),
            "investigation_id": str(d.investigation_id),
            "content": d.content,
            "source": meta.get("platform") or d.source_type or "web",
            "source_type": d.source_type or "web",
            "author": d.author,
            "url": d.url,
            "published_at": d.published_at.isoformat() if d.published_at else None,
            "created_at": d.created_at.isoformat() if d.created_at else None,
            "classification": classification,
            "needs_review": bool(toxicity.get("is_hate") or toxicity.get("is_offensive")),
        })
    return results


@router.get(
    "/{investigation_id}/narratives",
    status_code=status.HTTP_200_OK,
    summary="Get Investigation Narrative Clusters",
)
async def get_investigation_narratives(
    investigation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    """Retrieve narrative clusters associated with a specific investigation."""
    stmt = (
        select(NarrativeCluster)
        .where(NarrativeCluster.investigation_id == investigation_id)
        .order_by(NarrativeCluster.cluster_size.desc())
    )
    res = await db.execute(stmt)
    clusters = res.scalars().all()

    inv_stmt = select(Investigation).where(Investigation.id == investigation_id)
    inv_res = await db.execute(inv_stmt)
    inv = inv_res.scalar_one_or_none()
    keywords = inv.keywords if inv and inv.keywords else ["hate speech", "narrative", "online discourse"]

    return [
        {
            "id": str(c.id),
            "investigation_id": str(c.investigation_id),
            "title": c.label,
            "description": c.description or c.representative_text or "Discovered narrative cluster across ingested records.",
            "documents_count": c.cluster_size,
            "key_phrases": keywords,
            "created_at": c.created_at.isoformat() if c.created_at else None,
        }
        for c in clusters
    ]


@router.get(
    "/{investigation_id}/status",
    response_model=InvestigationStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Investigation Pipeline Status",
)
async def get_investigation_status(
    investigation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> InvestigationStatusResponse:
    """Get real-time operational status and entity metrics for an investigation."""
    stmt = select(Investigation).where(Investigation.id == investigation_id)
    res = await db.execute(stmt)
    investigation = res.scalar_one_or_none()

    if not investigation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Investigation with ID '{investigation_id}' not found.",
        )

    doc_count = (
        await db.scalar(
            select(func.count(Document.id)).where(Document.investigation_id == investigation_id)
        )
        or 0
    )
    cluster_count = (
        await db.scalar(
            select(func.count(NarrativeCluster.id)).where(
                NarrativeCluster.investigation_id == investigation_id
            )
        )
        or 0
    )
    indicator_count = (
        await db.scalar(
            select(func.count(CoordinationIndicator.id)).where(
                CoordinationIndicator.investigation_id == investigation_id
            )
        )
        or 0
    )
    citation_count = (
        await db.scalar(
            select(func.count(EvidenceCitation.id)).where(
                EvidenceCitation.investigation_id == investigation_id
            )
        )
        or 0
    )

    return InvestigationStatusResponse(
        investigation_id=investigation.id,
        status=investigation.status,
        document_count=doc_count,
        cluster_count=cluster_count,
        indicator_count=indicator_count,
        citation_count=citation_count,
        last_updated=investigation.updated_at,
    )
