"""Data ingestion endpoints supporting CSV/JSON uploads, URL scraping, and RSS feeds."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import feedparser
import httpx
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import sanitize_html, sanitize_text, validate_file, validate_url
from app.db.models import DataSource, Document, Investigation
from app.schemas.common import PaginatedResponse

router = APIRouter(prefix="/ingestion", tags=["Ingestion"])


class UrlIngestionRequest(BaseModel):
    """Payload for ingesting text from a web page."""

    investigation_id: uuid.UUID = Field(..., description="Target investigation UUID")
    url: str = Field(..., description="Target web page URL")
    title: Optional[str] = Field(None, description="Optional title override")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Custom metadata tags")


class RssIngestionRequest(BaseModel):
    """Payload for ingesting content from an RSS/Atom feed."""

    investigation_id: uuid.UUID = Field(..., description="Target investigation UUID")
    feed_url: str = Field(..., description="RSS or Atom feed URL")
    max_items: int = Field(50, ge=1, le=500, description="Maximum items to ingest")


class IngestionSummaryResponse(BaseModel):
    """Summary result returned after completing an ingestion batch."""

    status: str = "success"
    investigation_id: uuid.UUID
    source_type: str
    documents_ingested: int
    duplicates_skipped: int = 0
    message: str


class DocumentItemResponse(BaseModel):
    """Document representation in search/listing views."""

    id: uuid.UUID
    investigation_id: uuid.UUID
    title: Optional[str]
    content: str
    content_hash: str
    url: Optional[str]
    author: Optional[str]
    language: str
    source_type: str
    published_at: Optional[datetime]
    created_at: datetime


class DocumentListResponse(PaginatedResponse[DocumentItemResponse]):
    """Paginated collection of documents."""
    pass


@router.post(
    "/upload",
    response_model=IngestionSummaryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload CSV or JSON Dataset",
    description="Ingest structured batches from CSV or JSON files into an investigation.",
)
async def upload_file(
    investigation_id: uuid.UUID = Form(..., description="Target investigation UUID"),
    file: UploadFile = File(..., description="CSV or JSON file containing documents"),
    db: AsyncSession = Depends(get_db),
) -> IngestionSummaryResponse:
    """Parse and persist documents from an uploaded file."""
    # Ensure investigation exists
    inv = await db.scalar(select(Investigation).where(Investigation.id == investigation_id))
    if not inv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Investigation '{investigation_id}' does not exist.",
        )

    content_bytes = await file.read()
    filename = file.filename or "upload"
    valid, err = validate_file(filename, len(content_bytes))
    if not valid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=err)

    records: List[Dict[str, Any]] = []

    if filename.endswith(".json"):
        try:
            parsed = json.loads(content_bytes.decode("utf-8", errors="replace"))
            if isinstance(parsed, list):
                records = parsed
            elif isinstance(parsed, dict) and "documents" in parsed:
                records = parsed["documents"]
            else:
                records = [parsed]
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid JSON file format: {exc}",
            )
    elif filename.endswith(".csv"):
        try:
            decoded = content_bytes.decode("utf-8", errors="replace")
            reader = csv.DictReader(io.StringIO(decoded))
            records = list(reader)
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid CSV file format: {exc}",
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported file extension. Only .csv and .json are supported.",
        )

    ingested_count = 0
    duplicates_count = 0

    # Register DataSource record
    data_source = DataSource(
        investigation_id=investigation_id,
        source_type="file_upload",
        name=filename,
        config={"records_total": len(records)},
    )
    db.add(data_source)
    await db.flush()

    for item in records:
        raw_text = item.get("content") or item.get("text") or item.get("body") or ""
        text = sanitize_text(str(raw_text))
        if not text:
            continue

        h = hashlib.sha256(text.encode("utf-8")).hexdigest()

        # Check deduplication
        existing = await db.scalar(
            select(Document.id).where(
                Document.investigation_id == investigation_id,
                Document.content_hash == h,
            )
        )
        if existing:
            duplicates_count += 1
            continue

        doc = Document(
            investigation_id=investigation_id,
            source_id=data_source.id,
            content=text,
            content_hash=h,
            title=item.get("title"),
            url=item.get("url"),
            author=item.get("author"),
            language=item.get("language", "en"),
            source_type="file",
            metadata_={k: v for k, v in item.items() if k not in ("content", "text", "body")},
        )
        db.add(doc)
        ingested_count += 1

    await db.commit()

    return IngestionSummaryResponse(
        investigation_id=investigation_id,
        source_type="file",
        documents_ingested=ingested_count,
        duplicates_skipped=duplicates_count,
        message=f"Successfully ingested {ingested_count} documents from '{filename}'.",
    )


@router.post(
    "/url",
    response_model=IngestionSummaryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Ingest Web Page by URL",
    description="Fetch, sanitize, and extract text from an HTTP/HTTPS URL with SSRF protection.",
)
async def ingest_url(
    payload: UrlIngestionRequest,
    db: AsyncSession = Depends(get_db),
) -> IngestionSummaryResponse:
    """Ingest web page content securely."""
    inv = await db.scalar(select(Investigation).where(Investigation.id == payload.investigation_id))
    if not inv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Investigation '{payload.investigation_id}' does not exist.",
        )

    # SSRF Protection
    is_safe, reason = validate_url(payload.url)
    if not is_safe:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"URL rejected by security policy: {reason}",
        )

    try:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            resp = await client.get(
                payload.url,
                headers={"User-Agent": "NarrativeLens-AI/0.1.0"},
            )
            if resp.status_code >= 400:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Remote server responded with HTTP {resp.status_code}",
                )
            raw_html = resp.text
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to fetch content from URL: {exc}",
        )

    cleaned_text = sanitize_html(raw_html)
    if not cleaned_text:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No readable text extracted from the provided webpage.",
        )

    content_hash = hashlib.sha256(cleaned_text.encode("utf-8")).hexdigest()

    # Create DataSource and Document
    data_source = DataSource(
        investigation_id=payload.investigation_id,
        source_type="url",
        url=payload.url,
        name=payload.title or payload.url[:60],
        config={"url": payload.url},
    )
    db.add(data_source)
    await db.flush()

    doc = Document(
        investigation_id=payload.investigation_id,
        source_id=data_source.id,
        content=cleaned_text,
        content_hash=content_hash,
        title=payload.title or payload.url,
        url=payload.url,
        language="en",
        source_type="url",
        metadata_=payload.metadata,
    )
    db.add(doc)
    await db.commit()

    return IngestionSummaryResponse(
        investigation_id=payload.investigation_id,
        source_type="url",
        documents_ingested=1,
        duplicates_skipped=0,
        message=f"Successfully extracted document from {payload.url}",
    )


@router.post(
    "/rss",
    response_model=IngestionSummaryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Ingest RSS / Atom Feed",
    description="Subscribe to and scrape feed entries with SSRF verification.",
)
async def ingest_rss(
    payload: RssIngestionRequest,
    db: AsyncSession = Depends(get_db),
) -> IngestionSummaryResponse:
    """Fetch and parse feed entries from an RSS/Atom URL."""
    inv = await db.scalar(select(Investigation).where(Investigation.id == payload.investigation_id))
    if not inv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Investigation '{payload.investigation_id}' does not exist.",
        )

    # Validate Feed URL
    is_safe, reason = validate_url(payload.feed_url)
    if not is_safe:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"RSS URL rejected by security policy: {reason}",
        )

    try:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            resp = await client.get(
                payload.feed_url,
                headers={"User-Agent": "NarrativeLens-AI/0.1.0"},
            )
            raw_xml = resp.text
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to retrieve RSS feed: {exc}",
        )

    feed = feedparser.parse(raw_xml)
    entries = feed.entries[: payload.max_items]

    if not entries:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Feed parsed successfully but contained 0 entries.",
        )

    data_source = DataSource(
        investigation_id=payload.investigation_id,
        source_type="rss",
        url=payload.feed_url,
        name=getattr(feed.feed, "title", payload.feed_url),
        config={"entries_in_feed": len(entries)},
    )
    db.add(data_source)
    await db.flush()

    ingested = 0
    duplicates = 0

    for entry in entries:
        content_snippet = getattr(entry, "summary", "") or getattr(entry, "description", "")
        clean_content = sanitize_html(content_snippet)
        if not clean_content:
            continue

        h = hashlib.sha256(clean_content.encode("utf-8")).hexdigest()
        exists = await db.scalar(
            select(Document.id).where(
                Document.investigation_id == payload.investigation_id,
                Document.content_hash == h,
            )
        )
        if exists:
            duplicates += 1
            continue

        doc = Document(
            investigation_id=payload.investigation_id,
            source_id=data_source.id,
            content=clean_content,
            content_hash=h,
            title=getattr(entry, "title", None),
            url=getattr(entry, "link", None),
            author=getattr(entry, "author", None),
            language="en",
            source_type="rss",
            metadata_={"guid": getattr(entry, "id", None)},
        )
        db.add(doc)
        ingested += 1

    await db.commit()

    return IngestionSummaryResponse(
        investigation_id=payload.investigation_id,
        source_type="rss",
        documents_ingested=ingested,
        duplicates_skipped=duplicates,
        message=f"Ingested {ingested} articles from RSS feed '{payload.feed_url}'.",
    )


@router.get(
    "/documents",
    response_model=DocumentListResponse,
    status_code=status.HTTP_200_OK,
    summary="List Ingested Documents",
    description="Retrieve paginated documents matching search and filter constraints.",
)
async def list_documents(
    investigation_id: Optional[uuid.UUID] = Query(None, description="Filter by investigation UUID"),
    source_type: Optional[str] = Query(None, description="Filter by source type (file, url, rss)"),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> DocumentListResponse:
    """Retrieve documents."""
    query = select(Document)
    if investigation_id:
        query = query.where(Document.investigation_id == investigation_id)
    if source_type:
        query = query.where(Document.source_type == source_type)

    count_q = select(func.count()).select_from(query.subquery())
    total = (await db.scalar(count_q)) or 0

    offset = (page - 1) * size
    stmt = query.order_by(Document.created_at.desc()).offset(offset).limit(size)
    records = (await db.scalars(stmt)).all()

    items = [
        DocumentItemResponse(
            id=d.id,
            investigation_id=d.investigation_id,
            title=d.title,
            content=d.content[:300] + ("..." if len(d.content) > 300 else ""),
            content_hash=d.content_hash,
            url=d.url,
            author=d.author,
            language=d.language,
            source_type=d.source_type,
            published_at=d.published_at,
            created_at=d.created_at,
        )
        for d in records
    ]

    total_pages = math.ceil(total / size) if size > 0 else 0

    return DocumentListResponse(
        items=items,
        total=total,
        page=page,
        size=size,
        pages=total_pages,
    )


class ScrapeNarrativePayload(BaseModel):
    query: Optional[str] = Field(None, description="Topic, claim, or search term")
    article_url: Optional[str] = Field(None, description="Direct URL of news or magazine page")
    investigation_id: Optional[uuid.UUID] = Field(None, description="Target investigation UUID")
    max_items_per_source: int = Field(8, ge=2, le=30)


@router.post(
    "/scrape-narrative",
    status_code=status.HTTP_200_OK,
    summary="Scrape News & Social Media for True Narrative Results",
)
async def scrape_narrative_ingestion(
    payload: ScrapeNarrativePayload,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Scrape web news, magazines, and social media platforms and persist into investigation."""
    from app.services.narrative_scraper_service import narrative_scraper_service

    query = payload.query or ""
    article_url = payload.article_url

    if not query.strip() and not article_url:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Either a search query or a news article URL must be provided.",
        )

    return await narrative_scraper_service.execute_narrative_investigation(
        query=query,
        article_url=article_url,
        investigation_id=payload.investigation_id,
        max_items_per_source=payload.max_items_per_source,
        db=db,
    )

