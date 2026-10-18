"""Narrative clustering and evidence claim verification endpoints."""

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
from app.db.models import Document, EvidenceCitation, NarrativeCluster, NarrativeDocument
from app.schemas.common import PaginatedResponse
from app.services.narrative_scraper_service import narrative_scraper_service

router = APIRouter(tags=["Narratives & Evidence"])


class NarrativeClusterItem(BaseModel):
    """Brief representation of a narrative cluster."""

    id: uuid.UUID
    investigation_id: uuid.UUID
    label: str
    description: Optional[str]
    representative_text: Optional[str]
    cluster_size: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class NarrativeDocumentItem(BaseModel):
    """Document associated with a narrative cluster."""

    document_id: uuid.UUID
    title: Optional[str]
    snippet: str
    similarity_score: float


class NarrativeClusterDetail(NarrativeClusterItem):
    """Detailed narrative cluster with associated document member references."""

    documents: List[NarrativeDocumentItem] = Field(default_factory=list)


class EvidenceCitationResponse(BaseModel):
    """Evidence citation claim details with supporting and refuting sources."""

    id: uuid.UUID
    investigation_id: uuid.UUID
    claim_text: str
    supporting_sources: List[Dict[str, Any]]
    contradicting_sources: List[Dict[str, Any]]
    evidence_status: str
    uncertainty_notes: Optional[str]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class NarrativeListResponse(PaginatedResponse[NarrativeClusterItem]):
    """Paginated collection of narrative clusters."""
    pass


class EvidenceListResponse(PaginatedResponse[EvidenceCitationResponse]):
    """Paginated collection of evidence citations."""
    pass


class LiveNarrativeScrapeRequest(BaseModel):
    """Request payload for scraping news sites, social media, and verifying truth results."""

    query: Optional[str] = Field(None, description="Topic, claim, or public controversy to search")
    article_url: Optional[str] = Field(None, description="Direct URL of a news or magazine article")
    investigation_id: Optional[uuid.UUID] = Field(None, description="Optional target investigation UUID")
    max_items_per_source: int = Field(8, ge=2, le=25, description="Items to fetch per platform")


@router.get(
    "/narratives",
    response_model=NarrativeListResponse,
    status_code=status.HTTP_200_OK,
    summary="List Narrative Clusters",
    description="Retrieve discovered narrative themes, optionally filtered by investigation.",
)
async def list_narratives(
    investigation_id: Optional[uuid.UUID] = Query(None, description="Filter by investigation UUID"),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> NarrativeListResponse:
    """List narrative clusters with pagination."""
    query = select(NarrativeCluster)
    if investigation_id:
        query = query.where(NarrativeCluster.investigation_id == investigation_id)

    total_query = select(func.count()).select_from(query.subquery())
    total = (await db.scalar(total_query)) or 0

    offset = (page - 1) * size
    stmt = query.order_by(NarrativeCluster.cluster_size.desc()).offset(offset).limit(size)
    records = (await db.scalars(stmt)).all()

    items = [NarrativeClusterItem.model_validate(r) for r in records]
    total_pages = math.ceil(total / size) if size > 0 else 0

    return NarrativeListResponse(
        items=items,
        total=total,
        page=page,
        size=size,
        pages=total_pages,
    )


@router.get(
    "/narratives/{cluster_id}",
    response_model=NarrativeClusterDetail,
    status_code=status.HTTP_200_OK,
    summary="Get Narrative Cluster Details",
    description="Fetch deep information on a narrative cluster including associated documents.",
)
async def get_narrative_cluster(
    cluster_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> NarrativeClusterDetail:
    """Fetch details of a single narrative cluster and its constituent documents."""
    cluster = await db.scalar(
        select(NarrativeCluster).where(NarrativeCluster.id == cluster_id)
    )
    if not cluster:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Narrative cluster '{cluster_id}' not found.",
        )

    # Fetch associated documents and similarity scores
    stmt = (
        select(NarrativeDocument, Document)
        .join(Document, NarrativeDocument.document_id == Document.id)
        .where(NarrativeDocument.cluster_id == cluster_id)
        .order_by(NarrativeDocument.similarity_score.desc())
        .limit(100)
    )
    results = await db.execute(stmt)
    rows = results.all()

    doc_items = [
        NarrativeDocumentItem(
            document_id=doc.id,
            title=doc.title,
            snippet=doc.content[:200] + ("..." if len(doc.content) > 200 else ""),
            similarity_score=assoc.similarity_score,
        )
        for assoc, doc in rows
    ]

    return NarrativeClusterDetail(
        id=cluster.id,
        investigation_id=cluster.investigation_id,
        label=cluster.label,
        description=cluster.description,
        representative_text=cluster.representative_text,
        cluster_size=cluster.cluster_size,
        created_at=cluster.created_at,
        documents=doc_items,
    )


@router.get(
    "/evidence",
    response_model=EvidenceListResponse,
    status_code=status.HTTP_200_OK,
    summary="List Evidence Citations",
    description="Retrieve all fact-checked claim citations with supporting and contradicting sources.",
)
async def list_evidence_citations(
    investigation_id: Optional[uuid.UUID] = Query(None, description="Filter by investigation UUID"),
    status_filter: Optional[str] = Query(None, description="Filter by status (verified, debunked, disputed, unverified)"),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> EvidenceListResponse:
    """List fact-check evidence claims with pagination."""
    query = select(EvidenceCitation)
    if investigation_id:
        query = query.where(EvidenceCitation.investigation_id == investigation_id)
    if status_filter:
        query = query.where(EvidenceCitation.evidence_status == status_filter)

    total_query = select(func.count()).select_from(query.subquery())
    total = (await db.scalar(total_query)) or 0

    offset = (page - 1) * size
    stmt = query.order_by(EvidenceCitation.created_at.desc()).offset(offset).limit(size)
    records = (await db.scalars(stmt)).all()

    items = [EvidenceCitationResponse.model_validate(r) for r in records]
    total_pages = math.ceil(total / size) if size > 0 else 0

    return EvidenceListResponse(
        items=items,
        total=total,
        page=page,
        size=size,
        pages=total_pages,
    )


@router.get(
    "/evidence/{citation_id}",
    response_model=EvidenceCitationResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Evidence Citation",
    description="Inspect fact-check claim evidence, supporting citations, and conflicting sources.",
)
async def get_evidence_citation(
    citation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> EvidenceCitationResponse:
    """Retrieve an evidence claim record by ID."""
    citation = await db.scalar(
        select(EvidenceCitation).where(EvidenceCitation.id == citation_id)
    )
    if not citation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Evidence citation '{citation_id}' not found.",
        )

    return EvidenceCitationResponse.model_validate(citation)


@router.post(
    "/narratives/scrape-narrative",
    status_code=status.HTTP_200_OK,
    summary="Scrape News & Social Media for True Narrative Results",
    description="Crawl newspapers, magazines, Reddit, and forums to synthesize cross-source evidence and true results.",
)
@router.post(
    "/narratives/fact-check",
    status_code=status.HTTP_200_OK,
    summary="Fact-Check Narrative across Multi-Platform Sources",
)
async def scrape_and_verify_narrative(
    payload: LiveNarrativeScrapeRequest,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Execute live web scraping across news and social media, synthesize claims, and determine true results."""
    query = payload.query or ""
    article_url = payload.article_url

    if not query.strip() and not article_url:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Either a search query or a news article URL must be provided.",
        )

    try:
        results = await narrative_scraper_service.execute_narrative_investigation(
            query=query,
            article_url=article_url,
            investigation_id=payload.investigation_id,
            max_items_per_source=payload.max_items_per_source,
            db=db,
        )
        return results
    except Exception as exc:
        logger.error(f"Error during narrative scraping and verification: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Narrative scraper failed: {exc}",
        )
