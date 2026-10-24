"""Universal web article, blog, and forum excerpt scraper.

Uses Trafilatura for primary NLP-based article extraction, with Newspaper4k
and BeautifulSoup as fallbacks. Breaks down long articles into paragraph-level
StandardDocuments for fine-grained toxicity and hate speech scanning.
"""

from __future__ import annotations

import logging
import re
import urllib.parse
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx
from bs4 import BeautifulSoup

from app.core.security import sanitize_text, validate_url
from .base import BaseScraper, ScrapedContent, StandardDocument
from .rate_limiter import rate_limiter

logger = logging.getLogger(__name__)

try:
    import trafilatura
    TRAFILATURA_AVAILABLE = True
except ImportError:
    TRAFILATURA_AVAILABLE = False

try:
    from newspaper import Article as NewspaperArticle
    NEWSPAPER_AVAILABLE = True
except ImportError:
    NEWSPAPER_AVAILABLE = False


RE_MARKDOWN_IMAGE = re.compile(r"!\[.*?\]\(.*?\)")
RE_MARKDOWN_LINK = re.compile(r"\[([^\]]+)\]\([^\)]+\)")
RE_WIKI_CITATIONS = re.compile(r"\[(?:edit|\d+|citation needed)\]", re.IGNORECASE)


def _clean_article_text(raw_text: str) -> str:
    """Strip markdown images, wiki citations, and link syntax to leave clean prose."""
    if not raw_text:
        return ""
    # Remove markdown image embeds: ![alt](url)
    text = RE_MARKDOWN_IMAGE.sub("", raw_text)
    # Remove wiki citation markers: [1], [edit], [citation needed]
    text = RE_WIKI_CITATIONS.sub("", text)
    # Convert markdown links [Text](url) to just Text
    text = RE_MARKDOWN_LINK.sub(r"\1", text)
    # Clean whitespace
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    return "\n".join(lines).strip()


class WebScraper(BaseScraper):
    """Generic web scraper for articles, news, blogs, and public forums."""

    PLATFORM_NAME = "web"

    HEADERS = {
        "User-Agent": "NarrativeLensBot/1.0 (https://github.com/AnesthesiaProvider/NarrativeLens-AI-; research)",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }

    def can_handle(self, target: str) -> bool:
        """Handles any standard HTTP/HTTPS web URL."""
        t = target.strip().lower()
        return t.startswith("http://") or t.startswith("https://")

    async def _download_image(self, client: httpx.AsyncClient, url: str) -> Optional[bytes]:
        """Download leading article image for visual CLIP inspection."""
        try:
            resp = await client.get(url, timeout=6.0)
            if resp.status_code == 200 and len(resp.content) <= 8 * 1024 * 1024:
                return resp.content
        except Exception:
            pass
        return None

    async def scrape(
        self,
        target: str,
        max_items: int = 50,
        download_images: bool = True,
        max_images: int = 2,
        **kwargs,
    ) -> ScrapedContent:
        """Fetch and parse article, splitting text into scanned paragraphs."""
        url = target.strip()

        # SSRF check
        is_safe, reason = validate_url(url)
        if not is_safe:
            return ScrapedContent(
                platform=self.PLATFORM_NAME,
                target=url,
                target_type="article",
                errors=[f"URL blocked by security policy: {reason}"],
            )

        await rate_limiter.wait("web")

        try:
            async with httpx.AsyncClient(headers=self.HEADERS, timeout=15.0, follow_redirects=True) as client:
                resp = await client.get(url)
                if resp.status_code >= 400:
                    return ScrapedContent(
                        platform=self.PLATFORM_NAME,
                        target=url,
                        target_type="article",
                        errors=[f"Target server returned HTTP {resp.status_code}"],
                    )
                raw_html = resp.text
                final_url = str(resp.url)
        except Exception as exc:
            return ScrapedContent(
                platform=self.PLATFORM_NAME,
                target=url,
                target_type="article",
                errors=[f"Network request failed: {exc}"],
            )

        # 1. Extraction Strategy: Trafilatura (Best for articles)
        title = ""
        author = "Anonymous"
        paragraphs: List[str] = []
        image_urls: List[str] = []
        language = "en"

        if TRAFILATURA_AVAILABLE:
            try:
                extracted = trafilatura.bare_extraction(
                    raw_html,
                    url=final_url,
                    with_metadata=True,
                    include_images=True,
                )
                if extracted:
                    title = extracted.title or ""
                    author = extracted.author or "Anonymous"
                    language = extracted.language or "en"
                    if extracted.image:
                        image_urls.append(extracted.image)

                    if extracted.text:
                        raw_paras = [_clean_article_text(p) for p in extracted.text.split("\n\n")]
                        paragraphs = [p for p in raw_paras if len(p) >= 25]
            except Exception as exc:
                logger.debug(f"Trafilatura extraction skipped: {exc}")

        # 2. Strategy: Newspaper4k
        if (not title or not paragraphs) and NEWSPAPER_AVAILABLE:
            try:
                art = NewspaperArticle(final_url)
                art.set_html(raw_html)
                art.parse()
                title = title or art.title
                author = author if author != "Anonymous" else (", ".join(art.authors) if art.authors else "Anonymous")
                if art.top_image:
                    image_urls.append(art.top_image)
                if not paragraphs and art.text:
                    paragraphs = [p.strip() for p in art.text.split("\n\n") if len(p.strip()) >= 25]
            except Exception as exc:
                logger.debug(f"Newspaper4k extraction skipped: {exc}")

        # 3. Strategy: BeautifulSoup Fallback
        soup = BeautifulSoup(raw_html, "html.parser")
        if not title:
            og_title = soup.find("meta", property="og:title")
            if og_title and og_title.get("content"):
                title = og_title["content"].strip()
            elif soup.title and soup.title.string:
                title = soup.title.string.strip()
            else:
                title = "Web Document"

        if not image_urls:
            og_img = soup.find("meta", property="og:image")
            if og_img and og_img.get("content"):
                image_urls.append(og_img["content"].strip())

        if not paragraphs:
            for p in soup.find_all("p"):
                pt = sanitize_text(p.get_text(strip=True))
                # Skip cookie notices and standard noise
                if len(pt) >= 30 and not any(
                    s in pt.lower() for s in ["cookie", "privacy policy", "terms of use", "subscribe to newsletter"]
                ):
                    paragraphs.append(pt)

        # Download images if requested
        img_bytes_list: List[bytes] = []
        if download_images and image_urls:
            async with httpx.AsyncClient(headers=self.HEADERS, timeout=7.0, follow_redirects=True) as img_client:
                for img_url in image_urls[:max_images]:
                    b = await self._download_image(img_client, img_url)
                    if b:
                        img_bytes_list.append(b)

        # Domain/Publisher and Author resolution
        parsed_url = urllib.parse.urlparse(final_url)
        publisher = parsed_url.netloc.replace("www.", "")

        if "wikipedia.org" in final_url.lower():
            author = "Wikipedia Contributors"
        elif len(author) > 40 or any(
            bad in author.lower()
            for bad in ["authority control", "database", "navbox", "sidebar", "cookie", "category", "international"]
        ):
            author = publisher

        # Create Main Document (Full text or first 3 paragraphs)
        lead_text = "\n\n".join(paragraphs[:3]) if paragraphs else title
        main_doc = StandardDocument(
            source_platform=self.PLATFORM_NAME,
            source_url=final_url,
            doc_type="article",
            title=title,
            text=lead_text,
            author=author,
            image_urls=image_urls,
            image_bytes_list=img_bytes_list,
            language=language,
            doc_id=f"web-{hash(final_url) & 0xFFFFFFFF:x}-main",
        )

        # Create sub-documents for each paragraph to enable fine-grained scanning
        sub_docs: List[StandardDocument] = []
        for i, para in enumerate(paragraphs[:max_items]):
            sub_docs.append(
                StandardDocument(
                    source_platform=self.PLATFORM_NAME,
                    source_url=f"{final_url}#p{i+1}",
                    doc_type="article_excerpt",
                    title="",
                    text=para,
                    author=f"{publisher} Section #{i+1}",
                    language=language,
                    parent_id=main_doc.doc_id,
                    doc_id=f"web-{hash(final_url) & 0xFFFFFFFF:x}-p{i+1}",
                )
            )

        return ScrapedContent(
            platform=self.PLATFORM_NAME,
            target=final_url,
            target_type="article",
            main_document=main_doc,
            documents=sub_docs,
            total_scraped=1 + len(sub_docs),
            source_metadata={
                "domain": publisher,
                "title": title,
                "paragraphs_extracted": len(paragraphs),
                "author": author,
            },
        )
