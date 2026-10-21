"""4chan public JSON API scraper.

Scrapes boards and threads directly using 4chan's official read-only JSON API.
Requires no credentials or API keys.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import httpx
from bs4 import BeautifulSoup

from .base import BaseScraper, ScrapedContent, StandardDocument
from .rate_limiter import rate_limiter

logger = logging.getLogger(__name__)

CHAN_URL_PATTERN = re.compile(
    r"(?:https?://)?(?:boards\.)?4chan(?:nel)?\.org/(?P<board>[a-zA-Z0-9_-]+)(?:/thread/(?P<thread_no>\d+))?",
    re.IGNORECASE,
)
BOARD_SHORTHAND_PATTERN = re.compile(r"^/?(?:r/)?(?P<board>[a-zA-Z0-9_-]+)/?$", re.IGNORECASE)


class ChanScraper(BaseScraper):
    """Scraper for 4chan / 4channel boards and threads."""

    PLATFORM_NAME = "4chan"

    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": "application/json",
    }

    def can_handle(self, target: str) -> bool:
        """Check if target is a 4chan URL or board shorthand."""
        t = target.strip()
        if "4chan" in t or "4channel" in t:
            return bool(CHAN_URL_PATTERN.search(t))
        return False

    def _parse_target(self, target: str) -> Tuple[Optional[str], Optional[int]]:
        """Extract (board, thread_no) from URL or shorthand string."""
        t = target.strip()
        m = CHAN_URL_PATTERN.search(t)
        if m:
            board = m.group("board")
            thread_str = m.group("thread_no")
            thread_no = int(thread_str) if thread_str else None
            return board, thread_no

        # Check shorthand like "/pol/" or "pol"
        if not t.startswith("http"):
            cleaned = t.strip("/")
            if cleaned and "/" not in cleaned and len(cleaned) <= 10:
                return cleaned, None

        return None, None

    def _clean_comment(self, html_text: str) -> str:
        """Strip HTML and format greentext appropriately."""
        if not html_text:
            return ""
        soup = BeautifulSoup(html_text, "html.parser")

        # Convert <br> to newline
        for br in soup.find_all("br"):
            br.replace_with("\n")

        # Convert quote links like >>123456
        for q in soup.find_all("a", class_="quotelink"):
            q.replace_with(q.get_text())

        text = soup.get_text()
        return text.strip()

    async def _download_image(self, client: httpx.AsyncClient, url: str) -> Optional[bytes]:
        """Download an image with safety timeout and size caps."""
        try:
            resp = await client.get(url, timeout=6.0)
            if resp.status_code == 200 and len(resp.content) <= 10 * 1024 * 1024:
                return resp.content
        except Exception as exc:
            logger.debug(f"Image download failed for {url}: {exc}")
        return None

    async def scrape(
        self,
        target: str,
        max_items: int = 50,
        download_images: bool = True,
        max_images: int = 3,
        **kwargs,
    ) -> ScrapedContent:
        """Scrape a 4chan thread or board catalog."""
        board, thread_no = self._parse_target(target)
        if not board:
            return ScrapedContent(
                platform=self.PLATFORM_NAME,
                target=target,
                target_type="invalid",
                errors=[f"Could not parse 4chan board or thread from target '{target}'"],
            )

        async with httpx.AsyncClient(headers=self.HEADERS, follow_redirects=True) as client:
            if thread_no:
                return await self._scrape_thread(client, board, thread_no, max_items, download_images, max_images)
            else:
                return await self._scrape_board(client, board, max_items, download_images, max_images)

    async def _scrape_thread(
        self,
        client: httpx.AsyncClient,
        board: str,
        thread_no: int,
        max_items: int,
        download_images: bool,
        max_images: int,
    ) -> ScrapedContent:
        """Scrape a single 4chan thread and its replies."""
        api_url = f"https://a.4cdn.org/{board}/thread/{thread_no}.json"
        await rate_limiter.wait("4chan")

        try:
            resp = await client.get(api_url, timeout=10.0)
            if resp.status_code == 404:
                return ScrapedContent(
                    platform=self.PLATFORM_NAME,
                    target=f"/{board}/{thread_no}",
                    target_type="thread",
                    errors=[f"Thread {thread_no} on /{board}/ was archived, deleted, or does not exist (HTTP 404)."],
                )
            if resp.status_code != 200:
                return ScrapedContent(
                    platform=self.PLATFORM_NAME,
                    target=f"/{board}/{thread_no}",
                    target_type="thread",
                    errors=[f"4chan API returned HTTP {resp.status_code}"],
                )
            data = resp.json()
        except Exception as exc:
            return ScrapedContent(
                platform=self.PLATFORM_NAME,
                target=f"/{board}/{thread_no}",
                target_type="thread",
                errors=[f"Network error querying 4chan: {exc}"],
            )

        posts = data.get("posts", [])
        if not posts:
            return ScrapedContent(
                platform=self.PLATFORM_NAME,
                target=f"/{board}/{thread_no}",
                target_type="thread",
                errors=["No posts found in thread JSON."],
            )

        op = posts[0]
        op_title = op.get("sub", "")
        op_text = self._clean_comment(op.get("com", ""))
        op_time = datetime.fromtimestamp(op.get("time", 0), tz=timezone.utc) if op.get("time") else None

        # Build image URL if present
        op_images = []
        op_bytes = []
        if op.get("tim") and op.get("ext"):
            img_url = f"https://i.4cdn.org/{board}/{op['tim']}{op['ext']}"
            op_images.append(img_url)
            if download_images:
                b = await self._download_image(client, img_url)
                if b:
                    op_bytes.append(b)

        thread_url = f"https://boards.4chan.org/{board}/thread/{thread_no}"
        main_doc = StandardDocument(
            source_platform=self.PLATFORM_NAME,
            source_url=thread_url,
            doc_type="thread",
            title=op_title,
            text=op_text,
            author=op.get("name", "Anonymous"),
            author_id=op.get("id", ""),
            image_urls=op_images,
            image_bytes_list=op_bytes,
            score=op.get("replies", 0),
            reply_count=op.get("replies", 0),
            published_at=op_time,
            board=board,
            thread_id=str(thread_no),
            doc_id=f"4chan-{board}-{thread_no}-op",
            extra_metadata={
                "unique_ips": op.get("unique_ips", 0),
                "images_in_thread": op.get("images", 0),
            },
        )

        reply_docs: List[StandardDocument] = []
        images_downloaded = len(op_bytes)

        for p in posts[1 : max_items + 1]:
            p_no = p.get("no")
            p_text = self._clean_comment(p.get("com", ""))
            p_time = datetime.fromtimestamp(p.get("time", 0), tz=timezone.utc) if p.get("time") else None

            p_images = []
            p_bytes = []
            if p.get("tim") and p.get("ext"):
                p_img_url = f"https://i.4cdn.org/{board}/{p['tim']}{p['ext']}"
                p_images.append(p_img_url)
                if download_images and images_downloaded < max_images:
                    img_data = await self._download_image(client, p_img_url)
                    if img_data:
                        p_bytes.append(img_data)
                        images_downloaded += 1

            doc = StandardDocument(
                source_platform=self.PLATFORM_NAME,
                source_url=f"{thread_url}#p{p_no}",
                doc_type="comment",
                title="",
                text=p_text,
                author=p.get("name", "Anonymous"),
                author_id=p.get("id", ""),
                image_urls=p_images,
                image_bytes_list=p_bytes,
                score=0,
                published_at=p_time,
                board=board,
                thread_id=str(thread_no),
                parent_id=str(p.get("resto", thread_no)),
                doc_id=f"4chan-{board}-{p_no}",
            )
            reply_docs.append(doc)

        return ScrapedContent(
            platform=self.PLATFORM_NAME,
            target=thread_url,
            target_type="thread",
            main_document=main_doc,
            documents=reply_docs,
            total_scraped=1 + len(reply_docs),
            source_metadata={
                "board": board,
                "thread_no": thread_no,
                "title": op_title or f"Thread #{thread_no}",
                "reply_count": op.get("replies", len(reply_docs)),
                "image_count": op.get("images", 0),
            },
        )

    async def _scrape_board(
        self,
        client: httpx.AsyncClient,
        board: str,
        max_items: int,
        download_images: bool,
        max_images: int,
    ) -> ScrapedContent:
        """Scrape the catalog of active threads on a board."""
        api_url = f"https://a.4cdn.org/{board}/catalog.json"
        await rate_limiter.wait("4chan")

        try:
            resp = await client.get(api_url, timeout=10.0)
            if resp.status_code != 200:
                return ScrapedContent(
                    platform=self.PLATFORM_NAME,
                    target=f"/{board}/",
                    target_type="board_catalog",
                    errors=[f"Board /{board}/ catalog query returned HTTP {resp.status_code}"],
                )
            pages = resp.json()
        except Exception as exc:
            return ScrapedContent(
                platform=self.PLATFORM_NAME,
                target=f"/{board}/",
                target_type="board_catalog",
                errors=[f"Failed to fetch catalog: {exc}"],
            )

        thread_docs: List[StandardDocument] = []
        images_downloaded = 0

        for page in pages:
            for t in page.get("threads", []):
                if len(thread_docs) >= max_items:
                    break

                t_no = t.get("no")
                sub = t.get("sub", "")
                com = self._clean_comment(t.get("com", ""))
                p_time = datetime.fromtimestamp(t.get("time", 0), tz=timezone.utc) if t.get("time") else None

                t_images = []
                t_bytes = []
                if t.get("tim") and t.get("ext"):
                    img_url = f"https://i.4cdn.org/{board}/{t['tim']}{t['ext']}"
                    t_images.append(img_url)
                    if download_images and images_downloaded < max_images:
                        b = await self._download_image(client, img_url)
                        if b:
                            t_bytes.append(b)
                            images_downloaded += 1

                doc = StandardDocument(
                    source_platform=self.PLATFORM_NAME,
                    source_url=f"https://boards.4chan.org/{board}/thread/{t_no}",
                    doc_type="thread",
                    title=sub,
                    text=com,
                    author=t.get("name", "Anonymous"),
                    author_id=t.get("id", ""),
                    image_urls=t_images,
                    image_bytes_list=t_bytes,
                    score=t.get("replies", 0),
                    reply_count=t.get("replies", 0),
                    published_at=p_time,
                    board=board,
                    thread_id=str(t_no),
                    doc_id=f"4chan-{board}-{t_no}",
                )
                thread_docs.append(doc)

            if len(thread_docs) >= max_items:
                break

        return ScrapedContent(
            platform=self.PLATFORM_NAME,
            target=f"https://boards.4chan.org/{board}/",
            target_type="board_catalog",
            documents=thread_docs,
            total_scraped=len(thread_docs),
            source_metadata={
                "board": board,
                "title": f"/{board}/ - Active Board Catalog",
                "threads_found": len(thread_docs),
            },
        )
