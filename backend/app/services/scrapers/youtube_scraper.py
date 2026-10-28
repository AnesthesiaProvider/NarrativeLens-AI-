"""YouTube video and comments scraper integrating YouTube Data API v3 and fallback extraction."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx

from app.core.config import settings
from app.services.comment_hate_detector_service import comment_hate_detector_service
from .base import BaseScraper, ScrapedContent, StandardDocument
from .rate_limiter import rate_limiter

logger = logging.getLogger(__name__)


class YouTubeScraper(BaseScraper):
    """Scrapes YouTube videos, channel context, and user discussion comments."""

    PLATFORM_NAME = "youtube"

    def can_handle(self, target: str) -> bool:
        """Check if target is a YouTube video URL or identifier."""
        t = target.strip().lower()
        if "youtube.com" in t or "youtu.be" in t or t.startswith("yt:"):
            return True
        return False

    async def scrape(
        self,
        target: str,
        max_items: int = 50,
        download_images: bool = False,
        **kwargs,
    ) -> ScrapedContent:
        """Fetch YouTube video metadata and user discussion comments."""
        t = target.strip()
        await rate_limiter.wait("youtube")

        video_id = comment_hate_detector_service.extract_youtube_video_id(t)
        if t.startswith("yt:"):
            video_id = t[3:].strip()

        async with httpx.AsyncClient(headers={"User-Agent": "NarrativeLens/1.0"}) as client:
            try:
                if video_id:
                    meta, comments = await comment_hate_detector_service.fetch_youtube_video_info(video_id, client)
                else:
                    # Treat as topic search
                    meta, comments = await comment_hate_detector_service.search_and_fetch_youtube_topic(t, client)
            except Exception as exc:
                logger.warning(f"YouTube scrape failed for '{target}': {exc}")
                return ScrapedContent(
                    platform=self.PLATFORM_NAME,
                    target=target,
                    target_type="video",
                    errors=[f"YouTube query failed: {exc}"],
                )

        pub_dt = None
        if meta.get("published_at"):
            try:
                pub_dt = datetime.fromisoformat(meta["published_at"].replace("Z", "+00:00"))
            except Exception:
                pass

        main_doc = StandardDocument(
            source_platform=self.PLATFORM_NAME,
            source_url=meta.get("url", target),
            doc_type="video",
            title=meta.get("title", "YouTube Video"),
            text=meta.get("description", ""),
            author=meta.get("channel", "YouTube Creator"),
            score=meta.get("like_count", 0),
            view_count=meta.get("view_count", 0),
            reply_count=meta.get("comment_count", len(comments)),
            published_at=pub_dt,
            doc_id=f"youtube-v-{meta.get('id', 'main')}",
        )

        comment_docs: List[StandardDocument] = []
        for i, c in enumerate(comments[:max_items]):
            c_pub = None
            if c.get("published_at"):
                try:
                    c_pub = datetime.fromisoformat(c["published_at"].replace("Z", "+00:00"))
                except Exception:
                    pass

            c_id = c.get("id") or str(i + 1)
            comment_docs.append(
                StandardDocument(
                    source_platform=self.PLATFORM_NAME,
                    source_url=f"{meta.get('url', target)}&lc={c_id}",
                    doc_type="comment",
                    text=c.get("text", ""),
                    author=c.get("author", "Anonymous User"),
                    score=c.get("like_count", 0),
                    published_at=c_pub,
                    parent_id=main_doc.doc_id,
                    doc_id=f"youtube-c-{c_id}",
                )
            )

        return ScrapedContent(
            platform=self.PLATFORM_NAME,
            target=target,
            target_type="video",
            main_document=main_doc,
            documents=comment_docs,
            total_scraped=1 + len(comment_docs),
            source_metadata={
                "video_title": meta.get("title"),
                "channel": meta.get("channel"),
                "view_count": meta.get("view_count"),
                "like_count": meta.get("like_count"),
                "comment_count": meta.get("comment_count"),
            },
        )
